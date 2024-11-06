import re
import json
import os
import threading
import time

import psutil

from main.utils.clingo_runners.run_clingo import run_clingo_external

# Checks
from main.utils.validity_checks.is_valid_phi import is_valid_phi
from main.utils.validity_checks.is_valid_cause import is_valid_cause
from main.utils.validity_checks.is_valid_context import is_valid_context
from main.utils.validity_checks.is_valid_causal_model import is_valid_causal_model


def generate_las_task_from_json(json_data, background_knowledge=None):
    # Run Checks at the point of data creation
    is_valid_phi(json_data)
    is_valid_cause(json_data)
    is_valid_context(json_data)
    is_valid_causal_model(json_data)

    # Use provided background knowledge or generate it if not provided
    if background_knowledge is None:
        background_knowledge = generate_background_knowledge_binary(json_data)

    # Generate ac1 example
    ac1_example = generate_ac1_example_from_json(json_data)

    # Generate ac2 example
    ac2_example = generate_ac2_example_from_json(json_data)

    # Generate hypothesis space

    hypothesis_space = generate_search_space(json_data)

    components = [background_knowledge, ac1_example, ac2_example, hypothesis_space]

    LAS_task = '\n'.join(components)

    #     # Print the LAS task for inspection
    #     print("LAS Task Output:\n")
    #     print(LAS_task)

    return LAS_task


def generate_search_space(json_data):
    # Extract candidate cause from JSON
    cause = json_data["query"]["candidateCause"]

    # Generate in_cause atoms
    cause_atoms = translate_to_in_cause_atoms(cause)

    # Initialize list for search space atoms
    search_space_atoms = ['', ' %%%%% Search Space %%%%%', '']

    # Generate Search Space atoms with lengths and rules
    search_space_atoms = search_space_atoms + [f" 1 ~ {in_cause_atom} " for in_cause_atom in cause_atoms]

    # Generate Search Space as a string
    search_space = '\n'.join(search_space_atoms)

    return search_space


def extract_variables_from_piecewise(expression):
    """
    Extract variables from a given piecewise expression string.

    Args:
    expression (str): A piecewise expression in string format.

    Returns:
    set: A set of variable names used in the expression.

    Raises:
    ValueError: If the expression does not contain an 'if' keyword.
    """
    try:
        # Extract the condition part of the piecewise expression
        condition = expression.split("if")[1].strip()

        # Remove '= true' or '= false' from the condition
        condition = condition.replace("= true", "").replace("= false", "")

        # Split by logical operators to get individual variables
        variables = {var.strip() for var in condition.split() if var not in {'&', '|', '~', '(', ')'}}

        return variables
    except IndexError:
        raise ValueError("The provided expression does not contain an 'if' keyword.")


def distinguish_first_level_variables(json_data):
    """
    Identify first-level, mixed dependency, and non-first-level endogenous variables.

    Args:
    json_data (dict): The JSON data as a dictionary.

    Returns:
    tuple: A tuple containing three dictionaries: first-level endogenous variables,
           mixed dependency endogenous variables, and non-first-level endogenous variables.
    """
    first_level_endogenous = {}
    mixed_dependency = {}
    non_first_level_endogenous = {}

    endo_vars = set(json_data["causal_model"]["variables"]["endogenous"].keys())
    exo_vars = set(json_data["causal_model"]["variables"]["exogenous"])

    for var, details in json_data["causal_model"]["variables"]["endogenous"].items():
        equations = details.get("equations", {})
        piecewise_true = equations.get("piecewise_true", "")

        # Since we are dealing with binary models, the same variables will be in piecewise_true and
        # piecewise_false
        all_vars = extract_variables_from_piecewise(piecewise_true)

        depends_on_exo = any(v in exo_vars for v in all_vars)
        depends_on_endo = any(v in endo_vars and v != var for v in all_vars)

        if depends_on_exo:
            if depends_on_endo:
                mixed_dependency[var] = details
                non_first_level_endogenous[var] = details
            else:
                first_level_endogenous[var] = details
        else:
            non_first_level_endogenous[var] = details

    return first_level_endogenous, mixed_dependency, non_first_level_endogenous


def generate_relevant_exogenous_facts(context, mixed_dependency):
    """
    Generate ASP facts for relevant exogenous variables.

    Args:
    context (list): The context variables as a list of strings.
    mixed_dependency (dict): The mixed dependency variables and their equations.

    Returns:
    list: A list of ASP facts for exogenous variables.
    """
    exo_facts = []
    for var, details in mixed_dependency.items():
        equations = details.get("equations", [])
        piecewise_true = equations.get("piecewise_true", "")
        piecewise_false = equations.get("piecewise_false", "")
        # If the exogenous variable is in the equation of a mixed dependency variable, we need that fact
        for ctx in context:
            if ctx in piecewise_true:
                exo_var, val = ctx.split(" = ")
                exo_facts.append(f"val({exo_var},{val}).")
                context_found = True
            elif ctx in piecewise_false:
                exo_var, val = ctx.split(" = ")
                exo_facts.append(f"val({exo_var},{val}).")
                context_found = True
        if not context_found:
            raise ValueError("There is No corresponding context for mixed-dependency endogenous variable!")
    return exo_facts


def generate_range_facts(endogenous_variables):
    """
    Generate ASP range facts for endogenous variables.

    Args:
    endogenous_variables (dict): The endogenous variables.

    Returns:
    list: A list of ASP range facts.
    """
    range_facts = []
    for var in endogenous_variables:
        fact1 = f"range({var},true)."
        fact2 = f"range({var},false)."
        range_facts.append(fact1)
        range_facts.append(fact2)
    return range_facts


def generate_first_level_asp_rules(first_level_endogenous_vars, json_data):
    # Extract the context to find the values set to exogenous variables
    context = json_data["query"]["context"]
    context_dict = {item.split(" = ")[0]: item.split(" = ")[1] for item in context}

    # Add comments for readability in the final program
    val_rules = ["", "% First-level endogenous variables", ""]
    intervention_rules = ["", "% First-level endogenous variables", ""]

    for var in first_level_endogenous_vars:
        # Since binary, only need one of the equations - same variables in both
        piecewise_true = first_level_endogenous_vars[var]["equations"]["piecewise_true"]

        # Extract exogenous variables from the equation
        exogenous_variables = extract_variables(piecewise_true)

        if len(exogenous_variables) != 1:
            raise ValueError(
                f"Expected exactly one exogenous variable in the equation for {var}, but found {len(exogenous_variables)}.")

        exogenous_variable = exogenous_variables.pop()

        if exogenous_variable in context_dict:
            value = context_dict[exogenous_variable]
            val_rule = f"val({var},{value}) :- not intervened_on({var},{value})."
            val_rules.append(val_rule)

            # Construct the intervention rule according to whether val = true or val = false
            if value == 'false':
                intervention_rule = f"intervened_on({var},{value}) :- val({var},true)."
                intervention_rules.append(intervention_rule)

            elif value == 'true':
                intervention_rule = f"intervened_on({var},{value}) :- val({var},false)."
                intervention_rules.append(intervention_rule)
            else:
                raise ValueError("Value of the exogenous variable appears to be neither true nor false.")
        else:
            raise KeyError(
                f"Exogenous variable '{exogenous_variable}' present in the equation is not present in the context.")

    return val_rules, intervention_rules


def extract_variables(equation):
    """
    Extract variables from a given equation.

    Args:
    equation (str): The equation string.

    Returns:
    Set[str]: A set of variables found in the equation.
    """
    # Remove brackets and split the equation by ' if ' to get the right-hand side
    rhs = equation.replace('(', '').replace(')', '').split(' if ')[-1]
    # Split by ' | ' for disjunction and by ' & ' for conjunction
    variables = set()
    for disjunct in rhs.split(' | '):
        for conjunct in disjunct.split(' & '):
            var = conjunct.split(' = ')[0].strip()
            variables.add(var)
    return variables


def generate_initial_asp_rules(json_data):
    """
    Generate the initial ASP rules from the JSON data and Java code.

    Args:
    json_data (dict): The JSON data as a dictionary.
    java_code (str): The Java code as a string.

    Returns:
    list: A list of initial ASP rules.
    """
    first_level_endogenous, mixed_dependency, non_first_level_endogenous = distinguish_first_level_variables(json_data)

    val_rules = []
    intervened_on_rules = []
    range_facts = []

    constraint = ":- val(X,true), val(X,false)."

    # Generate Rules for first level endogenous variables

    first_level_val_rules, first_level_intervention_rules = generate_first_level_asp_rules(first_level_endogenous,
                                                                                           json_data)
    val_rules.extend(first_level_val_rules)
    intervened_on_rules.extend(first_level_intervention_rules)
    val_rules.extend(["", "% Non-first level endogenous variables ", ""])
    intervened_on_rules.extend(["", "% Non-first level endogenous variables", ""])

    # Generate exogenous facts for endogenous variables which depend on an exogenous and endogenous variable
    context = json_data["query"]["context"]
    exo_facts = generate_relevant_exogenous_facts(context, mixed_dependency)
    val_rules.extend(exo_facts)

    for var, details in non_first_level_endogenous.items():
        equations = details.get("equations", {})
        piecewise_true = equations.get("piecewise_true", "")
        piecewise_false = equations.get("piecewise_false", "")
        for equation in [piecewise_true, piecewise_false]:
            head, body = equation.split(' if ')
            headvar, headval = head.split(' = ')
            body_disjuncts = body.split(' | ')
            for disjunct in body_disjuncts:

                conjuncts = disjunct.replace('(', '').replace(')', '').split(' & ')
                if len(conjuncts) == 0:
                    raise ValueError("Error with conjunct splitting - empty list")

                conjuncts_split = [conjunct.split(' = ') for conjunct in conjuncts]
                conjuncts_asp_format = [f"val({var.strip()},{val.strip()})" for var, val in conjuncts_split]
                conjuncts_str = ', '.join(conjuncts_asp_format)

                # Construct structural equation rule
                structural_equation_rule = f"val({headvar},{headval}) :- {conjuncts_str}, not intervened_on({headvar},{headval})."
                val_rules.append(structural_equation_rule)

                # Construct intervention rule according to whether val = true or val = false
                if headval == 'true':
                    intervention_rule = f"intervened_on({headvar},{headval}) :- {conjuncts_str}, val({headvar},false)."
                    intervened_on_rules.append(intervention_rule)
                elif headval == 'false':
                    intervention_rule = f"intervened_on({headvar},{headval}) :- {conjuncts_str}, val({headvar},true)."
                    intervened_on_rules.append(intervention_rule)
                else:
                    raise ValueError("Value of variable appears to be neither true nor false.")

    # Combine the rules with comments
    asp_rules = [
        "%%%%% Constraint: variables cannot take on more than one value at a time %%%%%",
        "",
        constraint,
        "",
        "%%%%% Structural Equation rules %%%%%",
        "",
        *val_rules,
        "",
        "%%%%% Intervention Rules %%%%%",
        "",
        *intervened_on_rules
    ]

    return asp_rules


def extract_actual_val_atoms(answer_sets):
    """
    Extract actual_val/2 atoms from the answer set, excluding atoms with 'exo' in their names.

    Args:
    answer_sets (set): A set of atoms as strings.

    Returns:
    list: A list of actual_val/2 atoms.
    """
    actual_val_atoms = []

    for atom in answer_sets:
        # Check if the atom starts with "val(" to identify val/2 atoms
        if atom.startswith("val("):
            # Extract arguments by removing "val(" and ")" and splitting by ","
            arguments = atom[4:-1].split(",")
            actual_val_atoms.append(f"actual_val({arguments[0].strip()},{arguments[1].strip()}).")

    # Filter out any atoms containing "exo"
    actual_val_atoms = [atom for atom in actual_val_atoms if "exo" not in atom]

    return actual_val_atoms



def generate_background_knowledge_binary(json_data):
    """
    Generate the complete background knowledge in ASP format.

    Args:
    json_data (dict): The JSON data as a dictionary.
    java_code (str): The Java code as a string.

    Returns:
    list: A list of complete ASP rules including actual_val/2 atoms.
    """
    # Step 1: Generate initial ASP rules
    initial_asp_rules = generate_initial_asp_rules(json_data)

    # Step 2: Run Clingo to get the actual values
    answer_sets = run_clingo_external(initial_asp_rules)
    actual_val_atoms = extract_actual_val_atoms(answer_sets)

    # Step 3: Combine initial ASP rules with actual_val atoms
    asp_rules = initial_asp_rules + actual_val_atoms

    # Step 4: Join list of rules into single string representation

    background_knowledge = '\n'.join(asp_rules)

    return background_knowledge


def monitor_memory_usage(pid, memory_usage_result, stop_event):
    process = psutil.Process(pid)
    max_memory_usage = 0
    while not stop_event.is_set():  # Check if the stop flag has been set
        try:
            memory_info = process.memory_info()
            memory_usage = memory_info.rss  # Get the current memory usage (Resident Set Size)
            max_memory_usage = max(max_memory_usage, memory_usage)
            print(f"Current memory usage: {memory_usage / (1024 * 1024):.2f} MB")  # Print current memory usage
            time.sleep(1)  # Sleep for 1 second to avoid overwhelming the CPU
        except psutil.NoSuchProcess:
            break

    memory_usage_result['max_memory_usage'] = max_memory_usage


def generate_background_knowledge_binary_with_monitoring(json_data):
    memory_usage_result = {}
    pid = os.getpid()  # Get the current process ID
    stop_event = threading.Event()  # Create an event to stop the monitoring thread

    # Start memory monitoring in a separate thread
    memory_thread = threading.Thread(target=monitor_memory_usage, args=(pid, memory_usage_result, stop_event))
    memory_thread.start()

    try:
        # The original generate_background_knowledge_binary function
        background_knowledge = generate_background_knowledge_binary(json_data)
    finally:
        # Set the stop flag to stop the monitoring thread
        stop_event.set()
        # Wait for the memory monitoring thread to finish
        memory_thread.join()

    # Log or return the memory usage results
    max_memory_usage_mb = memory_usage_result['max_memory_usage'] / (1024 * 1024)  # Convert to MB
    print(f"Max memory usage: {max_memory_usage_mb:.2f} MB")
    return background_knowledge, memory_usage_result


def generate_ac2_example_from_json(json_data):
    """
    Generates an ASP positive example for AC2 from the provided JSON data.

    Args:
        json_data (dict): The JSON data containing the context, cause, and phi.

    Returns:
        str: The formatted ASP positive example string.
    """

    #### Generating the in_cause rules #####

    # Extract cause and phi from JSON data
    cause = json_data["query"]["candidateCause"]

    # Generate the in_cause/2 literals
    in_cause_atoms = translate_to_in_cause_atoms(cause)

    # Generate rules for each in_cause atom
    in_cause_rules = generate_in_cause_rules(in_cause_atoms)

    # Join the rules with a newline separator
    in_cause_rules_str = "\n".join(in_cause_rules)

    #### Generate the ~phi rules ########

    phi = json_data["query"]["phi"]

    translated_disjuncts = translate_to_asp_atoms(phi)

    # Check if the phi_asp_atoms list is flat or nested
    is_flat_list = all(not isinstance(i, list) for i in translated_disjuncts)

    # Generate the not_phi rules
    if is_flat_list:
        phi_conjunction = ', '.join(translated_disjuncts)
        not_phi_str = f" :- {phi_conjunction}. "
    else:
        joined_conjunctions = [', '.join(conjunction) for conjunction in translated_disjuncts]
        not_phi_rules = [f" :- {conjunction}. " for conjunction in joined_conjunctions]
        not_phi_str = '\n'.join(not_phi_rules)

    # Generate the ASP positive example string
    ac2_positive_example = f""" 

% AC2 Example

#pos(ac2,{{}},{{}},
{{
{in_cause_rules_str}
{not_phi_str}
0 {{val(X, V)}} 1 :- actual_val(X, V).
}}). 
"""
    return ac2_positive_example


def generate_ac1_example_from_json(json_data):
    """
    Generates an ASP positive example from the provided JSON data.

    Args:
        json_data (dict): The JSON data containing the context, cause, and phi.

    Returns:
        str: The formatted ASP positive example string.
    """
    # Extract context, cause, and phi from JSON
    context = json_data["query"]["context"]
    cause = json_data["query"]["candidateCause"]
    phi = json_data["query"]["phi"]

    # Generate the val/2 atoms for the cause
    cause_asp_atoms = translate_to_asp_atoms(cause)
    cause_str = ", ".join(cause_asp_atoms)

    # Generate the val/2 atoms for phi
    phi_asp_atoms = translate_to_asp_atoms(phi)

    # Check if the phi_asp_atoms list is flat or nested
    is_flat_list = all(not isinstance(i, list) for i in phi_asp_atoms)

    # Generate the ac1 rules (meaning not a disjunction)
    if is_flat_list:
        phi_conjunction = ', '.join(phi_asp_atoms)
        phi_ac1_rules_str = f"phi :- {phi_conjunction}."
    else:
        joined_conjunctions = [', '.join(conjunction) for conjunction in phi_asp_atoms]
        phi_rules = [f"phi :- {conjunction}." for conjunction in joined_conjunctions]
        phi_ac1_rules_str = '\n'.join(phi_rules)

    # Generate the ASP positive example string
    ac1_positive_example = f"""
%%%%% Examples %%%%%

% AC1 Example

#pos(ac1,{{}},{{}},
{{
% X = x is true in (M,u)
:- in_cause(X,V), not val(X,V).

% phi is true in (M,u)
{phi_ac1_rules_str}

:- not phi.
}}).
"""

    return ac1_positive_example


def translate_to_asp_atoms(phi):
    """
    This function takes a boolean combination of primitive events in DNF and converts it
    into a list of ASP atoms. Each variable and its value are
    transformed into the ASP format `val(variable, value)`, and negations are
    mapped to default negation in ASP. If there is no disjunctions, the function returns a
    flat list. If there are, the function returns a nested list, with translation group by disjunct.

    Args:
        phi (str): The logical expression to be translated. The expression
                   should be in the form of disjuncts separated by '|', with
                   each disjunct consisting of conjuncts separated by '&',
                   and variables and their values separated by '='.

    Returns:
        list: A list of lists if there are disjunctions, where each inner list
              contains the ASP rules for a corresponding disjunct in the input
              expression. If there are no disjunctions, returns a flat list.

    Example:
        Input with disjunctions:
            'a = 1 & ~b = 1 | a = 1 & ~sh = 1 | c = 0 & ~b = 1 | c = 0 & ~sh = 1'
        Output:
            [
                ['val(a,1)', 'not val(b,1)'],
                ['val(a,1)', 'not val(sh,1)'],
                ['val(c,0)', 'not val(b,1)'],
                ['val(c,0)', 'not val(sh,1)']
            ]
        Input without disjunctions:
            'a = 1 & ~b = 1 & c = 0'
        Output:
            ['val(a,1)', 'not val(b,1)', 'val(c,0)']
    """

    # Since the candidateCause is a list with the separate disjuncts, we join the list in that case.
    if isinstance(phi, list):
        phi = ' & '.join(phi)

    # Step 1: Split by '|' to get the disjuncts
    disjuncts = phi.split(' | ')

    #     print(disjuncts)

    # Step 2: Initialize a list to hold the ASP rules for each disjunct
    asp_atoms_by_disjunct = []

    # Step 3: Process each disjunct
    for conjunction in disjuncts:
        # Step 4: Split by '&' to get the conjuncts
        conjuncts = conjunction.split(' & ')

        # Step 5: Initialize a list to hold the ASP rules for this disjunct
        asp_atoms = []

        # Step 6: Process each conjunct
        for conjunct in conjuncts:
            # Step 7: Strip spaces and split by '=' to get the variable and value
            var, val = conjunct.strip().split('=')
            var = var.strip()
            val = val.strip()

            # Step 8: Handle negation and create the ASP rule
            if '~' in var:
                var = var.replace('~', '').strip()
                asp_atom = f"not val({var},{val})"
            else:
                asp_atom = f"val({var},{val})"

            # Step 9: Add the ASP rule to the list for this disjunct
            asp_atoms.append(asp_atom)

        # Step 10: Add the list of ASP rules for this disjunct to the main list
        asp_atoms_by_disjunct.append(asp_atoms)

    #################
    # If there are no disjunctions, return a flat list
    if len(disjuncts) == 1:
        return asp_atoms_by_disjunct[0]
    else:

        return asp_atoms_by_disjunct
    ################


def translate_to_in_cause_atoms(candidateCause):
    in_cause_atoms = []

    for conjunct in candidateCause:
        variable, value = conjunct.split(' = ')
        in_cause_atoms.append(f"in_cause({variable},{value}).")

    return in_cause_atoms


def generate_in_cause_rules(in_cause_atoms):
    in_cause_rules = []
    for in_cause_atom in in_cause_atoms:
        var, val = re.search(r'in_cause\((.*?),(.*?)\)', in_cause_atom).groups()
        var = var.strip()
        val = val.strip()
        if val == 'true':
            rule = f"val({var},false) :- in_cause({var},{val})."
        elif val == 'false':
            rule = f"val({var},true) :- in_cause({var},{val})."
        else:
            raise ValueError("Value appears to be neither true nor false.")
        in_cause_rules.append(rule)
    return in_cause_rules


def process_all_files_into_las(input_directory, output_directory_base):
    # Get a list of subdirectories in the input directory
    subdirectories = [d for d in os.listdir(input_directory) if os.path.isdir(os.path.join(input_directory, d))]

    for subdir in subdirectories:
        subdir_path = os.path.join(input_directory, subdir)
        print(f"Processing sub-directory: {subdir_path}")

        # List all JSON files in the sub-directory
        json_files = [f for f in os.listdir(subdir_path) if f.startswith('processed_') and f.endswith('.json')]

        if not json_files:
            print(f"No JSON files found in {subdir_path}")
            continue  # Skip to the next sub-directory if no JSON files are found

        background_knowledge = None

        for idx, filename in enumerate(json_files):
            input_file_path = os.path.join(subdir_path, filename)

            with open(input_file_path, 'r') as input_file:
                json_data = json.load(input_file)
                print(f"Currently processing {input_file_path}")

                # Generate background knowledge once per sub-directory
                if background_knowledge is None:
                    print(f"Generating background knowledge for {subdir_path}")
                    background_knowledge = generate_background_knowledge_binary(json_data)

                # Generate LAS task from JSON data with pre-generated background knowledge
                las_task = generate_las_task_from_json(json_data, background_knowledge=background_knowledge)

                # Modify the filename
                output_filename = filename.replace('processed_', 'LAS_').replace('.json', '.las')

                # Create a corresponding subdirectory in the output base directory
                output_subdir = os.path.join(output_directory_base, subdir)

                # Ensure the output subdirectory exists
                os.makedirs(output_subdir, exist_ok=True)

                # Define the output file path in the correct subdirectory
                output_file_path = os.path.join(output_subdir, output_filename)

                # Write the LAS task to the output file
                with open(output_file_path, 'w') as output_file:
                    output_file.write(las_task)

                print(f"Saved LAS task to {output_file_path}")

#
# # # # Example usage
# # input_directory = '/homes/dozcan/projects/checking_queries_processed'
# # output_directory_base = '/homes/dozcan/projects/ilasp_tasks'
# # process_all_files_into_las(input_directory, output_directory_base)
#
# # json_file_path = "/homes/dozcan/projects/checking_queries_processed/StealMasterKey650Users/processed_test_StealMasterKey_650Users2ebd7baa-3916-4958-9ae9-213f5b089bbc.json"
# json_file_path = "/homes/dozcan/projects/checking_queries_processed/AbstractBinaryExtended2/processed_test_DummyCombinedWithBinaryTree2228eaa18-35ad-4425-9a7b-41534a014d58.json"
# with open(json_file_path, 'r') as json_file:
#     json_data = json.load(json_file)
# generate_background_knowledge_binary_with_monitoring(json_data)
