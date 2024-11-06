from main.utils.clingo_runners.run_clingo import run_clingo_external

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

        for ctx in context:
            if f"{ctx}" in piecewise_true:
                var, val = ctx.split(" = ")
                exo_facts.append(f"val({var},{val}).")
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


def generate_first_level_asp_rules(context):
    """
    Generate ASP rules for first-level endogenous variables.

    Args:
    context (list): The context variables as a list of strings.

    Returns:
    tuple: Two lists, one for val rules and one for intervened_on rules.
    """
    val_rules = ["", "% First-level endogenous variables", ""]
    intervened_on_rules = ["", " % First-level endogenous variables", ""]

    for ctx in context:
        variable, value = ctx.split(' = ')
        variable = variable[:-4]
        val_rules.append(f"val({variable},{value}) :- not intervened_on({variable},{value}).")
        intervened_on_rules.append(
            f"intervened_on({variable},{value}) :- val({variable}, V), range({variable},V), V != {value}.")

    return val_rules, intervened_on_rules


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

    # Generate the range facts for binary variables
    endo_vars = list(json_data["causal_model"]["variables"]["endogenous"].keys())
    range_facts = generate_range_facts(endo_vars)

    context = json_data["query"]["context"]
    first_level_val_rules, first_level_intervened_on_rules = generate_first_level_asp_rules(context)

    val_rules.extend(first_level_val_rules)
    intervened_on_rules.extend(first_level_intervened_on_rules)

    val_rules.extend(["", "% Non-first level endogenous variables ", ""])
    intervened_on_rules.extend(["", "% Non-first level endogenous variables", ""])

    exo_facts = generate_relevant_exogenous_facts(context, mixed_dependency)
    val_rules.extend(exo_facts)

    for var, details in non_first_level_endogenous.items():
        equations = details.get("equations", {})
        piecewise_true = equations.get("piecewise_true", "")
        piecewise_false = equations.get("piecewise_false", "")
        for equation in [piecewise_true, piecewise_false]:
            head, body = equation.split(' if ')
            headvar, headval = head.split('=')
            headvar = headvar.strip()
            headval = headval.strip()

            body_disjuncts = body.split(' | ')
            for disjunct in body_disjuncts:
                conjuncts = disjunct.replace('(', '').replace(')', '').split(' & ')
                if len(conjuncts) == 1:
                    bodyvar, bodyval = conjuncts[0].split(' = ')
                    structural_equation_rule = f"val({headvar},{headval}) :- val({bodyvar},{bodyval}), not intervened_on({headvar},{headval})."
                    val_rules.append(structural_equation_rule)
                    intervention_rule = f"intervened_on({headvar},{headval}) :- val({bodyvar},{bodyval}),val({headvar},V),range({headvar},V), V != {headval}."
                    intervened_on_rules.append(intervention_rule)
                else:
                    conjuncts_split = [conjunct.split('=') for conjunct in conjuncts]
                    conjuncts_asp_format = [f"val({var.strip()},{val.strip()})" for var, val in conjuncts_split]
                    conjuncts_str = ', '.join(conjuncts_asp_format)
                    structural_equation_rule = f"val({headvar},{headval}) :- {conjuncts_str}, not intervened_on({headvar},{headval})."
                    val_rules.append(structural_equation_rule)
                    intervention_rule = f"intervened_on({headvar},{headval}) :- {conjuncts_str}, val({headvar},V),range({headvar},V), V != {headval}."
                    intervened_on_rules.append(intervention_rule)

    # Combine the rules with comments
    asp_rules = [
        "%%%%% Constraint: variables cannot take on more than one value at a time %%%%%",
        "",
        constraint,
        "",
        "%%%%% Range Facts %%%%",
        "",
        *range_facts,
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
    Extract actual_val/2 atoms from the answer sets.

    Args:
    answer_sets (list): The list of answer sets.

    Returns:
    list: A list of actual_val/2 atoms.
    """
    actual_val_atoms = []
    for answer_set in answer_sets:
        for atom in answer_set:
            if atom.match("val", 2):
                actual_val_atoms.append(f"actual_val({atom.arguments[0]},{atom.arguments[1]}).")

    actual_val_atoms = [atom for atom in actual_val_atoms if "exo" not in atom]

    actual_val_atoms = ["", '%%%%% Actual value facts %%%%%', ""] + actual_val_atoms
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
