from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import exceptions
from rest_framework.views import exception_handler


class DomainError(Exception):
    """Raised by services for business-rule violations; rendered as HTTP 400."""

    def __init__(self, message: str, code: str = "domain_error", field: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.field = field


def api_exception_handler(exc, context):
    if isinstance(exc, DomainError):
        detail = {exc.field: [exc.message]} if exc.field else {"detail": exc.message}
        exc = exceptions.ValidationError(detail, code=exc.code)
    elif isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, "error_dict") else {"detail": exc.messages}
        exc = exceptions.ValidationError(detail)
    return exception_handler(exc, context)
