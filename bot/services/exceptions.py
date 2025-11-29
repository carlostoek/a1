"""
Custom exception classes for service errors.
"""


class ServiceError(Exception):
    """Base exception class for service errors."""
    pass


class TokenInvalidError(ServiceError):
    """Raised when a token is invalid or already used."""
    pass


class TokenNotFoundError(ServiceError):
    """Raised when a token is not found."""
    pass


class SubscriptionError(ServiceError):
    """Raised for subscription-related errors."""
    pass


class ConfigError(ServiceError):
    """Raised for configuration-related errors."""
    pass