"""Custom exception hierarchy for the application."""


class AppBaseError(Exception):
    """Base class for all application-specific exceptions."""

    def __init__(self, message: str = 'An application error occurred', *args):
        self.message = message
        super().__init__(message, *args)


class ValidationError(AppBaseError):
    """Raised when user input fails validation."""

    def __init__(self, message: str = 'Validation failed', field: str = None, *args):
        self.field = field
        super().__init__(message, *args)


class ScrapingError(AppBaseError):
    """Raised when external scraping fails."""

    def __init__(self, message: str = 'Scraping failed', url: str = None, *args):
        self.url = url
        super().__init__(message, *args)


class DataIntegrityError(AppBaseError):
    """Raised when database constraints are violated."""

    def __init__(self, message: str = 'Data integrity violation', *args):
        super().__init__(message, *args)


class CardmarketError(AppBaseError):
    """Raised when Cardmarket API interactions fail."""

    def __init__(self, message: str = 'Cardmarket API error', status_code: int = None, *args):
        self.status_code = status_code
        super().__init__(message, *args)


class ConfigurationError(AppBaseError):
    """Raised when required configuration is missing or invalid."""

    def __init__(self, message: str = 'Configuration error', config_key: str = None, *args):
        self.config_key = config_key
        super().__init__(message, *args)
