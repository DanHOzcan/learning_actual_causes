class InvalidCausalModelException(Exception):
    """Exception raised for invalid causal models."""

    def __init__(self, message="Causal Model not valid"):
        self.message = message
        super().__init__(self.message)

