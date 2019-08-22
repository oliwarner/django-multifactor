from django.urls import path

from . import views
from .factors import fido2, u2f, totp, fallback


app_name = 'multifactor'

urlpatterns = [
    path('', views.index, name="home"),
    path('authenticate/', views.authenticate, name="authenticate"),
    path('toggle-factor/', views.toggle_factor, name="toggle_factor"),
    path('toggle-fallback/', views.toggle_fallback, name="toggle_fallback"),
    path('delete/', views.delete_factor, name="delete_factor"),
    path('reset/', views.reset_cookie, name="reset_cookie"),

    path('fido2/', fido2.start, name="fido2_start"),
    path('fido2/auth/', fido2.auth, name="fido2_auth"),
    path('fido2/begin-auth/', fido2.authenticate_begin, name="fido2_begin_auth"),
    path('fido2/complete-auth/', fido2.authenticate_complete, name="fido2_complete_auth"),
    path('fido2/begin-reg/', fido2.begin_registration, name="fido2_begin_reg"),
    path('fido2/complete-reg/', fido2.complete_reg, name="fido2_complete_reg"),

    path('u2f/', u2f.Create.as_view(), name="u2f_start"),
    path('u2f/auth/', u2f.Auth.as_view(), name="u2f_auth"),

    path('totp/start/', totp.Create.as_view(), name="totp_start"),
    path('totp/auth/', totp.Auth.as_view(), name="totp_auth"),

    path('fallback/auth/', fallback.Auth.as_view(), name="fallback_auth"),
]
