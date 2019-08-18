from django.shortcuts import redirect
from django.http import HttpResponse
from django.conf import settings
from django.utils.module_loading import import_string

from .models import UserKey, KEY_CHOICES
from .common import render, method_url
from .app_settings import mf_settings


def index(request):
    return render(request, "multifactor/home.html", {
        "keys": UserKey.objects.filter(user=request.user),
        "available_methods": [
            (f"multifactor:{value.lower()}_start", label)
            for value, label in KEY_CHOICES
        ]
    })

def authenticate(request):
    keys = UserKey.objects.filter(user=request.user, enabled=True)
    methods = list(set([k.key_type for k in keys]))

    request.session["multifactor_methods"] = methods
    if len(methods) == 1:
        return redirect(method_url(methods[0]))

    method_names = dict(KEY_CHOICES)

    return render(request, 'multifactor/authenticate.html', {
        'methods': [
            (method_url(method), method_names[method])
            for method in methods
        ]
    })


def reset_cookie(request):
    del request.session['multifactor']
    return redirect(settings.LOGIN_URL)


def login(request):
    if 'multifactor-next' in request.session:
        return redirect(request.session['multifactor-next'])

    callback = mf_settings['LOGIN_CALLBACK']
    if callback:
        callable_func = import_string(callback)
        return callable_func(request, username=request.session["base_username"])

    return redirect(settings.LOGIN_URL)


def del_key(request):
    try:
        UserKey.objects.get(user=request.user, id=request.GET["id"]).delete()
        return HttpResponse("Deleted Successfully")
    except UserKey.DoesNotExist:
        return HttpResponse("Error: You own this token so you can't delete it")


def toggle_key(request):
    try:
        key = UserKey.objects.get(user=request.user, id=request.GET["id"])
        key.enabled = not key.enabled
        key.save()
        return HttpResponse("OK")
    except UserKey.DoesNotExist:
        return HttpResponse("Error")


def goto(request, method):
    return redirect(method_url(method))
