class RecommendationError(Exception):
    """Base exception for recommendation domain."""
    pass


class ServiceNotReadyError(RecommendationError):
    """Raised when recommendation service has not refreshed or loaded state."""
    pass


class InvalidBasketError(RecommendationError):
    """Raised when user basket is invalid."""
    pass
