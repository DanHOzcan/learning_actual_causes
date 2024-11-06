import json
import threading
import time

from main.causality.binary_models.generating_tasks.generating_las_tasks_binary_modified import \
    extract_variables_from_piecewise, extract_actual_val_atoms, generate_relevant_exogenous_facts, \
    distinguish_first_level_variables, extract_variables
from main.utils.clingo_runners.run_clingo import parse_clingo_output, run_clingo_external
from main.utils.memory_montors.memory_monitoring import monitor_memory


def generate_first_level_asp_rules_lean(first_level_endogenous_vars, json_data):
    # Extract the context to find the values set to exogenous variables
    context = json_data["query"]["context"]
    context_dict = {item.split(" = ")[0]: item.split(" = ")[1] for item in context}

    # Add comments for readability in the final program
    val_rules = ["", "% First-level endogenous variables", ""]

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
            val_rule = f"val({var},{value})."
            val_rules.append(val_rule)

        else:
            raise KeyError(
                f"Exogenous variable '{exogenous_variable}' present in the equation is not present in the context.")

    return val_rules



def generate_initial_asp_rules_lean(json_data):
    """
    Generate the initial ASP rules from the JSON data and Java code.

    Args:
    json_data (dict): The JSON data as a dictionary.
    java_code (str): The Java code as a string.

    Returns:
    list: A list of initial ASP rules.
    """
    # Start memory monitoring
    # Start memory monitoring
    stop_event = threading.Event()
    peak_memory = [0]  # Shared list to store peak memory
    memory_thread = threading.Thread(target=monitor_memory, args=(stop_event, peak_memory))
    memory_thread.start()

    first_level_endogenous, mixed_dependency, non_first_level_endogenous = distinguish_first_level_variables(json_data)

    val_rules = []

    constraint = ":- val(X,true), val(X,false)."

    # Generate Rules for first level endogenous variables

    first_level_val_rules = generate_first_level_asp_rules_lean(first_level_endogenous, json_data)
    val_rules.extend(first_level_val_rules)

    val_rules.extend(["", "% Non-first level endogenous variables ", ""])

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
                structural_equation_rule = f"val({headvar},{headval}) :- {conjuncts_str}."
                val_rules.append(structural_equation_rule)

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
    ]

    # Stop memory monitoring
    stop_event.set()
    memory_thread.join()

    return asp_rules


def generate_and_evaluate_static(json_data):
    """
    Generates the background knowledge stripped of intervention rules and atoms

    Args:
    json_data (dict): The JSON data as a dictionary.
    java_code (str): The Java code as a string.

    Returns:
    list: A list of complete ASP rules including actual_val/2 atoms.
    """
    # Start timing
    start_time = time.perf_counter()

    # Start memory monitoring
    stop_event = threading.Event()
    peak_memory = [0]  # Shared list to store peak memory
    memory_thread = threading.Thread(target=monitor_memory, args=(stop_event, peak_memory))
    memory_thread.start()

    # Step 1: Generate initial ASP rules
    initial_asp_rules = generate_initial_asp_rules_lean(json_data)
    # print(f"Initial ASP Rules are {initial_asp_rules}")

    # Step 2: Run Clingo to get the actual values
    answer_sets = parse_clingo_output(run_clingo_external(initial_asp_rules))
    print(f"Result of running initial ASP Rules: {answer_sets}")
    actual_val_atoms = extract_actual_val_atoms(answer_sets)
    print(actual_val_atoms)


    # Stop memory monitoring
    stop_event.set()
    memory_thread.join()

    # End timing
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Time taken: {elapsed_time:.2f} seconds")

    return peak_memory[0], actual_val_atoms, elapsed_time


## Need to measure memory and then return max memory and time along with val atoms.


# path = "/homes/dozcan/projects/checking_queries_processed/AssassinFIRST/processed_test_Assassin_firstVariant0e4107a6-20bf-4ee4-a9e3-ec6c212dc3fa.json"
#
# with open(path,'r') as file:
#     data = json.load(file)
#
# atoms = generate_and_evaluate_static(data)
#
# print(atoms)