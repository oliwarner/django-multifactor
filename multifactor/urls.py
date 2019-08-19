from django.urls import path

from . import views
from .factors import totp, email, u2f, fido2


app_name = 'multifactor'

urlpatterns = [
    path('', views.index, name="home"),

    path('totp/start/', totp.create, name="totp_start"),
    path('totp/auth/', totp.auth, name="totp_auth"),

    path('email/start/', email.create, name="email_start"),
    path('email/auth/', email.auth, name="email_auth"),

    path('u2f/', u2f.start, name="u2f_start"),
    path('u2f/auth/', u2f.auth, name="u2f_auth"),

    path('fido2/', fido2.start, name="fido2_start"),
    path('fido2/auth/', fido2.auth, name="fido2_auth"),
    path('fido2/begin-auth/', fido2.authenticate_begin, name="fido2_begin_auth"),
    path('fido2/complete-auth/', fido2.authenticate_complete, name="fido2_complete_auth"),
    path('fido2/begin-reg/', fido2.begin_registration, name="fido2_begin_reg"),
    path('fido2/complete-reg/', fido2.complete_reg, name="fido2_complete_reg"),

    path('authenticate/', views.authenticate, name="authenticate"),
    path('toggle-key/<int:key_id>/', views.toggle_key, name="toggle_key"),
    path('delete/<int:key_id>/', views.del_key, name="delete_key"),
    path('reset/', views.reset_cookie, name="reset_cookie"),
]
