from django.urls import path

from . import views, helpers
from .factors import totp, email, u2f, fido2


app_name = 'multifactor'

urlpatterns = [
    path('', views.index, name="home"),

    path('totp/start/', totp.start, name="totp_start"),
    path('totp/get-token/', totp.get_token, name="totp_get"),
    path('totp/verify/', totp.verify, name="totp_verify"),
    path('totp/auth/', totp.auth, name="totp_auth"),
    path('totp/recheck/', totp.recheck, name="totp_recheck"),

    path('email/start/', email.start, name="email_start"),
    path('email/auth/', email.auth, name="email_auth"),

    path('u2f/', u2f.start, name="u2f_start"),
    path('u2f/bind/', u2f.bind, name="u2f_bind"),
    path('u2f/auth/', u2f.auth, name="u2f_auth"),
    path('u2f/process-recheck/', u2f.process_recheck, name="u2f_recheck"),
    path('u2f/verify/', u2f.verify, name="u2f_verify"),

    path('fido2/', fido2.start, name="fido2_start"),
    path('fido2/auth/', fido2.auth, name="fido2_auth"),
    path('fido2/begin-auth/', fido2.authenticate_begin, name="fido2_begin_auth"),
    path('fido2/complete-auth/', fido2.authenticate_complete, name="fido2_complete_auth"),
    path('fido2/begin-reg/', fido2.begin_registration, name="fido2_begin_reg"),
    path('fido2/complete-reg/', fido2.complete_reg, name="fido2_complete_reg"),

    path('goto/<str:method>/', views.goto, name="goto"),
    path('authenticate/', views.authenticate, name="authenticate"),
    path('recheck/', helpers.recheck, name="recheck"),
    path('toggle-key/', views.toggle_key, name="toggle_key"),
    path('delete/', views.del_key, name="del_key"),
    path('reset/', views.reset_cookie, name="reset_cookie"),
]
