import threading

_ctx = threading.local()


def bind_request(request):
    _ctx.request = request


def unbind_request():
    _ctx.request = None


def current_context():
    request = getattr(_ctx, 'request', None)
    if request is None:
        return {'user': None, 'ip': None, 'ua': '', 'method': '', 'path': ''}
    user = getattr(request, 'user', None)
    if user is not None and not user.is_authenticated:
        user = None
    return {
        'user': user,
        'ip': request.META.get('REMOTE_ADDR'),
        'ua': request.META.get('HTTP_USER_AGENT', '')[:300],
        'method': request.method,
        'path': request.path,
    }
