class InvalidPhiException(Exception):
    """Exception raised for invalid phis. Thrown if either (i) some literal in phi does not have an equation or (ii)
    phi is not in DNF"""
    def __init__(self, message="Phi not valid"):
        self.message = message
        super().__init__(self.message)
