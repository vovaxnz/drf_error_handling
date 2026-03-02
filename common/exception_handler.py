from rest_framework.views import exception_handler
from rest_framework.response import Response

from common.exceptions import DomainError

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, DomainError):
        return Response(
            {
                "error": exc.code,
                "detail": exc.message,
            },
            status=exc.http_status,
        )

    return response