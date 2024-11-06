from sympy import sympify
from main.utils.validity_checks.is_dnf import is_dnf
from main.exceptions.invalid_phi_exception import InvalidPhiException


def is_valid_phi(json_data):

    phi = json_data["query"]["phi"]
    phi_formula = sympify(phi.replace(' = true','').replace(' = false', ''))
    phi_list = list(phi_formula.free_symbols)
    phi_list = [str(variable) for variable in phi_list]

    endogenous_variables = set(json_data["causal_model"]["variables"]["endogenous"].keys())

    dnf = is_dnf(phi_formula)

    if not dnf:
        raise InvalidPhiException("Phi not in DNF!")

    for variable in phi_list:
        if variable not in endogenous_variables:
            raise InvalidPhiException(f"Phi variable {variable} is not an endogeonus variable!")

    return True

