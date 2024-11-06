import re


def extract_variables_from_numeric_equation(expression):
    """
    Extract variable names from a given numeric equation string.

    Args:
    expression (str): A numeric equation in string format.

    Returns:
    set: A set of variable names used in the equation.

    Raises:
    ValueError: If no variables are found in the expression.
    """
    # Regular expression to match variable names (starting with a letter or underscore, followed by alphanumerics)
    variable_pattern = re.compile(r'\b[a-zA-Z_]\w*\b')

    # Find all matches that are not purely digits
    variables = {match.group() for match in re.finditer(variable_pattern, expression) if not match.group().isdigit()}

    if not variables:
        raise ValueError("No variables found in the provided expression.")

    return variables


expression = "3 * x + 5 * y - n_12"
variables = extract_variables_from_numeric_equation(expression)
print(variables)  # Output: {"x", "y", "n_12"}


def numeric_distinguish_first_level_variables(json_data):
    """
    Identify first-level, mixed dependency, and non-first-level endogenous variables for numeric models.

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
        equation = details.get("equation", "")

        # Extract all variables used in the equation
        all_vars = extract_variables_from_numeric_equation(equation)

        # Check dependencies
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


def numeric_generate_relevant_exogenous_facts(context, mixed_dependency):
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
        equation = details.get("equation", "")

        for ctx in context:
            if f"{ctx}" in equation:
                var, val = ctx.split(" = ")
                exo_facts.append(f"val({var},{val}).")
    return exo_facts
