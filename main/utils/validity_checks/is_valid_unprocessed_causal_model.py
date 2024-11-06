from typing import Dict, Any, Set
from main.exceptions.invalid_causal_model_exception import InvalidCausalModelException

def is_valid_unprocessed_causal_model(model: Dict[str, Any]) -> bool:
    """
    Validate the causal model by checking for circular dependencies and other criteria.

    Args:
    model (Dict[str, Any]): The causal model in JSON format.

    Returns:
    bool: True if the causal model is valid, False otherwise.
    """
    if 'causal_model' not in model:
        raise KeyError("'causal_model' key not found in the model")

    if 'variables' not in model['causal_model']:
        raise KeyError("'variables' key not found in the model['causal_model']")

    if 'endogenous' not in model['causal_model']['variables']:
        raise KeyError("'endogenous' key not found in the model['causal_model']['variables']")

    if 'exogenous' not in model['causal_model']['variables']:
        raise KeyError("'exogenous' key not found in the model['causal_model']['variables']")

    # Extract endogenous equations
    equations = {var: details['equation'] for var, details in model['causal_model']['variables']['endogenous'].items()}

    # Extract exogenous variables
    exogenous_variables = set(model['causal_model']['variables']['exogenous'])

    all_variables = set(equations.keys()).union(exogenous_variables)
    used_variables = set()

    # Collect variables used in equations
    for var, eq_str in equations.items():
        if isinstance(eq_str, str):
            try:
                used_variables.update(extract_variables(eq_str))
            except Exception as e:
                print(f"Error parsing equation for variable '{var}': {eq_str}")
                raise e
        else:
            print(f"Skipping non-string equation for variable '{var}': {eq_str}")

    exists_definition_for_each_variable = len(equations) + len(exogenous_variables) == len(all_variables)
    exists_no_duplicate_equation_for_each_variable = len(equations) == len(set(equations.keys()))

    memo = {}
    exists_circular_dependency = any(
        is_variable_in_equation(var, eq_str, equations, exogenous_variables, memo)
        for var, eq_str in equations.items()
    )

    exogenous_variable_called_like_dummy = any(var == "DUMMY_VAR_NAME" for var in exogenous_variables)

    if not (exists_definition_for_each_variable and exists_no_duplicate_equation_for_each_variable and
            not exists_circular_dependency and not exogenous_variable_called_like_dummy):
        raise InvalidCausalModelException()

    return True


def is_variable_in_equation(variable: str, equation: str, equations: Dict[str, str], exogenous_variables: Set[str],
                            memo: Dict[str, bool]) -> bool:
    """
    Check if a variable is in the equation, using memoization to optimize repeated checks.

    Args:
    variable (str): The variable to check.
    equation (str): The equation string.
    equations (Dict[str, str]): The dictionary of equations.
    exogenous_variables (Set[str]): The set of exogenous variables.
    memo (Dict[str, bool]): Memoization dictionary.

    Returns:
    bool: True if the variable is in the equation, False otherwise.
    """
    if equation in memo:
        return memo[equation]

    variables_in_equation = extract_variables(equation)

    if variable in variables_in_equation:
        memo[equation] = True
        return True

    for v in variables_in_equation:
        if v not in exogenous_variables and v != variable:
            eq = equations.get(v)
            if eq:
                if is_variable_in_equation(variable, eq, equations, exogenous_variables, memo):
                    memo[equation] = True
                    return True

    memo[equation] = False
    return False


def extract_variables(equation: str) -> Set[str]:
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
