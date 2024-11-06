from typing import Dict, Set, Any
from main.exceptions.invalid_causal_model_exception import InvalidCausalModelException
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


def is_variable_in_equation(variable: str, equation: str, equations: Dict[str, Dict[str, str]],
                            exogenous_variables: Set[str], memo: Dict[str, bool]) -> bool:
    """
    Check if a variable is in the piecewise_true equation, using memoization to optimize repeated checks.

    Args:
    variable (str): The variable to check.
    equation (str): The piecewise_true equation string.
    equations (Dict[str, Dict[str, str]]): The dictionary of equations.
    exogenous_variables (Set[str]): The set of exogenous variables.
    memo (Dict[str, bool]): Memoization dictionary.

    Returns:
    bool: True if the variable is in the piecewise_true equation, False otherwise.
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
                piecewise_true = eq.get('piecewise_true')
                if piecewise_true and is_variable_in_equation(variable, piecewise_true, equations, exogenous_variables,
                                                              memo):
                    memo[equation] = True
                    return True

    memo[equation] = False
    return False


def is_valid_causal_model(model: Dict[str, Any]) -> bool:
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
    equations = {var: details['equations'] for var, details in model['causal_model']['variables']['endogenous'].items()}

    # Extract exogenous variables
    exogenous_variables = set(model['causal_model']['variables']['exogenous'])

    all_variables = set(equations.keys()).union(exogenous_variables)
    used_variables = set()

    # Collect variables used in equations
    for var, eq_dict in equations.items():
        for key in ['piecewise_true', 'piecewise_false']:
            eq = eq_dict.get(key)
            if isinstance(eq, str):
                try:
                    used_variables.update(extract_variables(eq))
                except Exception as e:
                    print(f"Error parsing equation for variable '{var}': {eq}")
                    raise e
            else:
                print(f"Skipping non-string equation for variable '{var}': {eq}")

    exists_definition_for_each_variable = len(equations) + len(exogenous_variables) == len(all_variables)
    exists_no_duplicate_equation_for_each_variable = len(equations) == len(set(equations.keys()))

    memo = {}
    exists_circular_dependency = any(
        is_variable_in_equation(var, eq['piecewise_true'], equations, exogenous_variables, memo) or
        is_variable_in_equation(var, eq['piecewise_false'], equations, exogenous_variables, memo)
        for var, eq in equations.items()
    )

    exogenous_variable_called_like_dummy = any(var == "DUMMY_VAR_NAME" for var in exogenous_variables)

    # Debugging statements to identify the invalid condition
    if not exists_definition_for_each_variable:
        print("Validation failed: Not every variable has a definition.")
    if not exists_no_duplicate_equation_for_each_variable:
        print("Validation failed: There are duplicate equations for some variables.")
    if exists_circular_dependency:
        print("Validation failed: There is a circular dependency in the equations.")
    if exogenous_variable_called_like_dummy:
        print("Validation failed: There is an exogenous variable named 'DUMMY_VAR_NAME'.")

    if not (exists_definition_for_each_variable and exists_no_duplicate_equation_for_each_variable and
            not exists_circular_dependency and not exogenous_variable_called_like_dummy):
        raise InvalidCausalModelException("Causal Model is Invalid")

    return True

