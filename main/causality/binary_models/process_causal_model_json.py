import json
import os
import sympy
from sympy.logic.boolalg import Not, to_dnf, Equivalent
from main.utils.validity_checks.is_dnf import is_dnf

def process_numeric_variables(var):
    # If the variable ends with '_exo', process the part before '_exo'
    if var.endswith('_exo'):
        base_var = var[:-4]
        if base_var.isnumeric():
            return f'n_{base_var}_exo'
        else:
            return f'{base_var}_exo'
    # If the variable is numeric, prepend 'n_'
    elif var.isnumeric():
        return f'n_{var}'
    else:
        return var


def preprocess_variables(expression):
    # Split the expression into tokens and process each token
    tokens = expression.split()
    processed_tokens = []
    for token in tokens:
        token = token.lower()
        if token == 'ff':
            processed_tokens.append('var_ff')
        elif token == '~ff':
            processed_tokens.append('~var_ff')
        else:
            processed_tokens.append(process_numeric_variables(token))
    return ' '.join(processed_tokens)


def transform_expression(sympy_expression):
    """
    Transforms a formula in semi-propositional form into one with primitive events.

    This function converts a SymPy logical expression into a string where each variable
    and its negation are transformed according to the rules:
    - `~var` becomes `var = false`
    - `var` becomes `var = true`
    - Logical operators such as `&`, `|`, and `if` are preserved

    Args:
        sympy_expression (sympy.logic.boolalg.Boolean): A SymPy logical expression.

    Returns:
        str: A string representing the transformed expression with primitive events.

    Example:
        >>> import sympy
        >>> expr = sympy.sympify('~b if ~b_exo')
        >>> transform_expression(expr)
        'b = false if b_exo = false'
    """
    # Convert the SymPy expression to a string for processing
    sympy_string = str(sympy_expression)

    # Split the string into tokens
    tokens = sympy_string.split()

    # Initialize a list to hold the transformed tokens
    transformed_tokens = []

    # Process each token
    for token in tokens:
        if token.startswith('~'):
            # Remove the negation sign and append = false
            if token.endswith(')'):
                transformed_tokens.append(f"{token.replace(')', '')[1:]} = false)")
            else:
                transformed_tokens.append(f"{token[1:]} = false")

        elif token.startswith('(~'):
            transformed_tokens.append(f"{token.replace('~', '')} = false")

        elif token in ['&', '|', 'if']:
            # Keep logical operators unchanged
            transformed_tokens.append(token)
        else:
            # Append = true to non-negated variables
            if token.endswith(')'):

                transformed_tokens.append(f"{token.replace(')', '')} = true)")
            else:
                transformed_tokens.append(f"{token} = true")

    # Join the transformed tokens back into a string
    transformed_expr = ' '.join(transformed_tokens)

    return transformed_expr


# def process_context(context):
#     processed_context = []
#     for var in context:
#         var = preprocess_variables(var)
#         if var.startswith('~'):
#             processed_context.append(f"{var[1:]} = false")
#         else:
#             processed_context.append(f"{var} = true")
#     return processed_context

# def process_candidate_causes(candidates):
#     processed_candidates = []
#     for var in candidates:
#         var = preprocess_variables(var)
#         if var.startswith('~'):
#             processed_candidates.append(f"{var[1:]} = false")
#         else:
#             processed_candidates.append(f"{var} = true")
#     return processed_candidates

def process_phi(phi, first_endogenous_var):
    if phi == '$true':
        return f"{first_endogenous_var} = true | {first_endogenous_var} = false"
    elif phi == '$false':
        return f"{first_endogenous_var} = true & {first_endogenous_var} = false"
    else:
        phi = preprocess_variables(phi)
        return transform_expression(to_dnf(sympy.sympify(phi)))


def process_query(query, first_endogenous_var):
    processed_query = query.copy()
    processed_query["context"] = query["context"]

    # Account for contexts with numeric variables
    for i, setting in enumerate(processed_query["context"]):
        variable, value = setting.split(' = ')
        variable_base = variable[:-4]
        if variable_base.isdigit():
            variable_new = f'n_{variable}'
            if '_exo' not in variable_new:
                raise ValueError("Exogenous variables in context not correctly processed ")
            processed_query["context"][i] = f'{variable_new} = {value}'

    processed_query["candidateCause"] = query["candidateCause"]

    # Account for candidate causes with numeric variables
    for i, setting in enumerate(processed_query["candidateCause"]):
        variable, value = setting.split(' = ')
        variable_base = variable[:-4]
        if variable_base.isdigit():
            variable_new = f'n_{variable}'
            if '_exo' not in variable_new:
                raise ValueError("Exogenous variables in candidate cause not correctly processed ")
            processed_query["candidate_cause"][i] = f'{variable_new} = {value}'

    # Process the phi with consideration for $true and $false
    processed_query["phi"] = process_phi(query["phi"], first_endogenous_var)

    return processed_query


def process_endogenous(var: str, details: dict) -> dict:
    """
    Process an endogenous variable equation into piecewise_true and piecewise_false forms.

    Args:
    var (str): The variable name.
    details (dict): The details dictionary containing the equation.

    Returns:
    dict: A dictionary containing the piecewise_true and piecewise_false equations.
    """
    equation = details["equation"].strip()
    if not equation:
        raise ValueError("No Equation Found!")

    lhs, rhs = equation.split(' = ')
    lhs_expr = sympy.sympify(preprocess_variables(lhs.replace('and', '&').replace('or', '|').replace('not', '~')))
    rhs_expr = sympy.sympify(preprocess_variables(rhs.replace('and', '&').replace('or', '|').replace('not', '~')))

    # Extract the conditional parts of piecewise expressions for verification
    # piecewise_true_body = to_dnf(rhs_expr, True)
    # piecewise_false_body = to_dnf(Not(rhs_expr), True)

    try:
        piecewise_true_body = to_dnf(rhs_expr, simplify=True,force=False)
        piecewise_false_body = to_dnf(Not(rhs_expr), simplify=True,force=False)
    except ValueError as e:
        # If simplification fails, convert to DNF without simplification
        print(f"Simplification failed for variable {var}. Converting to DNF without simplification.")
        piecewise_true_body = to_dnf(rhs_expr, force=False)
        piecewise_false_body = to_dnf(Not(rhs_expr), force=False)

    # Check if the body of piecewise_false is the negation of piecewise_true's body
    equivalent = Equivalent(piecewise_false_body, Not(piecewise_true_body))
    if not equivalent:
        raise ValueError("The body of piecewise_false is not the negation of the body  of piecewise_true")

    elif not is_dnf(piecewise_true_body):
        raise ValueError(f"The body of the piecewise true equation is not in DNF: {piecewise_true_body}")


    elif not is_dnf(piecewise_false_body):
        raise ValueError(f"The body of the piecewise false equation is not in DNF: {piecewise_false_body}")

    try:
        piecewise_true = transform_expression(f"{lhs_expr} if {piecewise_true_body}")
        piecewise_false = transform_expression(f"{Not(lhs_expr)} if {piecewise_false_body}")

        return {
            "equations": {
                "piecewise_true": piecewise_true,
                "piecewise_false": piecewise_false
            }
        }
    except SympifyError as e:
        print(f"Failed to process equation for variable {var}: {equation}")
        raise e


def process_causal_model_JSON(input_data):
    print(f"Processing model: {input_data['causal_model']['name']}")

    # Extract the first endogenous variable for handling $true and $false in phi
    first_endogenous_var = list(input_data["causal_model"]["variables"]["endogenous"].keys())[0]

    new_data = {
        "causal_model": {
            "name": input_data["causal_model"]["name"] + "_piecewise",
            "variables": {
                "endogenous": {preprocess_variables(var): process_endogenous(var, details)
                               for var, details in input_data["causal_model"]["variables"]["endogenous"].items()},
                "exogenous": [
                    preprocess_variables(process_numeric_variables(var)) for var in
                    input_data["causal_model"]["variables"]["exogenous"]
                ]
            }
        },
        "query": process_query(input_data["query"], first_endogenous_var)
    }
    return new_data


def process_all_files(input_directory, output_directory):
    """
    Processes all JSON files in the input directory and outputs the processed files to the output directory.

    Args:
        input_directory (str): Path to the input directory containing JSON files.
        output_directory (str): Path to the output directory to save processed JSON files.
    """
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    files = os.listdir(input_directory)
    for file in files:
        input_file_path = os.path.join(input_directory, file)
        if os.path.isfile(input_file_path) and file.endswith('.json') and not file.startswith('.'):
            output_file_name = 'processed_' + file
            output_file_path = os.path.join(output_directory, output_file_name)
            with open(input_file_path, 'r', encoding='utf-8') as json_file:
                input_data = json.load(json_file)
                print(f" Currently processing {file}")
            processed_data = process_causal_model_JSON(input_data)
            with open(output_file_path, 'w', encoding='utf-8') as json_file:
                json.dump(processed_data, json_file, indent=2)
            print(f"Processed: {input_file_path} -> {output_file_path}")


# # # Define the input and output directories
# input_directory = '/Users/danozcan/Learning_Causes_Experimentation/Tests/ILASP_TASKS/Optimization_Queries'
# output_directory = '/Users/danozcan/Learning_Causes_Experimentation/Tests/ILASP_TASKS/Optimization_Queries_Processed'
#
# # # Call the function to process all files
# process_all_files(input_directory, output_directory)


