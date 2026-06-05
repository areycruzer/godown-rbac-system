import threading
from typing import Any

_audit_context = threading.local()


class AuditContextMiddleware:
    """
    Middleware that captures the current request's user, tenant, and IP address
    into a thread-local context. This makes request context available to Django
    signals (which run in the same thread as the request/view but don't have
    direct access to the request object).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _audit_context.user = getattr(request, "user", None)
        _audit_context.tenant = getattr(request, "tenant", None)
        _audit_context.ip_address = _get_client_ip(request)
        _audit_context.user_agent = request.META.get("HTTP_USER_AGENT", "")

        try:
            return self.get_response(request)
        finally:
            # Clean up context after response is generated to avoid memory leaks
            _audit_context.user = None
            _audit_context.tenant = None
            _audit_context.ip_address = None
            _audit_context.user_agent = None


def _get_client_ip(request) -> str | None:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def get_audit_context() -> dict[str, Any]:
    """Retrieve the current thread-local audit context."""
    return {
        "user": getattr(_audit_context, "user", None),
        "tenant": getattr(_audit_context, "tenant", None),
        "ip_address": getattr(_audit_context, "ip_address", None),
        "user_agent": getattr(_audit_context, "user_agent", "") or "",
    }
