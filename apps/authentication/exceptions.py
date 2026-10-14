import traceback
import structlog
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = structlog.get_logger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    view = context.get("view")
    request = context.get("request")
    view_name = view.__class__.__name__ if view else "Unknown"
    method = request.method if request else "Unknown"
    path = request.path if request else "Unknown"

    if response is None:
        logger.error(
            "unhandled_exception",
            view=view_name,
            method=method,
            path=path,
            exc_type=type(exc).__name__,
            exc_message=str(exc),
            traceback=traceback.format_exc(),
        )
        return Response(
            {
                "message": "An unexpected error occurred. Please try again later.",
                "error_type": type(exc).__name__,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    logger.warning(
        "handled_exception",
        view=view_name,
        method=method,
        path=path,
        status_code=response.status_code,
        exc_type=type(exc).__name__,
        exc_message=str(exc),
    )

    data = response.data
    if isinstance(data, list):
        response.data = {"errors": data}

    return response