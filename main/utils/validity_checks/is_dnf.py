from sympy.logic.boolalg import Not, And, Or
def is_literal(expr):
    """Check if an expression is a literal (a variable or its negation)."""
    return expr.is_Atom or (isinstance(expr, Not) and expr.args[0].is_Atom)


def is_conjunction_of_literals(expr):
    """Check if an expression is a conjunction of literals."""
    if isinstance(expr, And):
        return all(is_literal(arg) for arg in expr.args)
    return is_literal(expr)


def is_dnf(expr):
    """Check if an expression is in Disjunctive Normal Form (DNF)."""
    if isinstance(expr, Or):
        return all(is_conjunction_of_literals(arg) for arg in expr.args)
    return is_conjunction_of_literals(expr)