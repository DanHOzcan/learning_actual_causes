class InvalidCauseException(Exception):
    """Exception raised for invalid causes. Each cause needs to be defined in the equations"""
    def __init__(self, message="Cause not valid"):
        self.message = message
        super().__init__(self.message)
