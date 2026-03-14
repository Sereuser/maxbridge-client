class MaxException(Exception):
    pass


class ConnectionError(MaxException):
    pass


class AuthenticationError(MaxException):
    pass


class APIError(MaxException):
    def __init__(self, error_code: int, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"API Error {error_code}: {message}")