PENDING_UNITE_SESSION_KEY = "pending_unite_id"


def set_pending_unite(request, unite_id):
    request.session[PENDING_UNITE_SESSION_KEY] = str(unite_id)


def get_pending_unite_and_clear(request):
    unite_id = request.session.get(PENDING_UNITE_SESSION_KEY)
    if unite_id:
        del request.session[PENDING_UNITE_SESSION_KEY]
    return unite_id
