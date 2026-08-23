def app_lang(request):
    return {'APP_LANG': request.session.get('app_lang', 'en')}
