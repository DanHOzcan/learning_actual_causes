class InvalidContextException(Exception):
    """Exception raised for invalid contexts. Every exogenous variable needs to be assigned a value and no variable other than an exogenous
    variable should be assigned a value."""

    def __init__(self, message="Context is not valid"):
        self.message = message
        super().__init__(self.message)
