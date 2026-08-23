import time

from .context import bind_request, unbind_request
from .models import AuditLog, record

SKIP_PREFIXES = ('/static/', '/media/', '/favicon')
AUTH_EVENT_URLS = {'login', 'logout'}


class AuditMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        bind_request(request)
        started = time.monotonic()
        try:
            response = self.get_response(request)
        finally:
            duration_ms = int((time.monotonic() - started) * 1000)
            path = request.path
            if not any(path.startswith(p) for p in SKIP_PREFIXES):
                try:
                    url_name = resolve(path).url_name or ''
                except Exception:
                    url_name = ''
                if url_name not in AUTH_EVENT_URLS:
                    user = getattr(request, 'user', None)
                    record(
                        AuditLog.VIEW,
                        actor=user if (user and user.is_authenticated) else None,
                        module='http',
                        object_repr=f"{request.method} {path}",
                        status_code=response.status_code,
                        duration_ms=duration_ms,
                    )
        unbind_request()
        return response
