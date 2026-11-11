"""Domain-specific exceptions for camera configuration and encoder selection."""


class DomainError(Exception):
    """Base exception for all pure domain validation and invariant failures."""


class InvalidStreamConfigError(DomainError):
    """Raised when resolution, frame rate, or bitrate violates camera limits."""


class InvalidEndpointError(DomainError):
    """Raised when a network host, port, or stream path is invalid."""


class UnknownEncoderError(DomainError):
    """Raised when an unregistered H.264 encoder kind is requested."""
