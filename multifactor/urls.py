from django.urls import path

from . import views
from .factors import fido2, u2f, totp, fallback


app_name = 'multifactor'

urlpatterns = [
    path('', views.List.as_view(), name="home"),
    path('<str:action>:<slug:ident>/', views.List.as_view(), name="action"),
    path('help/', views.Help.as_view(), name="help"),
    path('authenticate/', views.Authenticate.as_view(), name="authenticate"),
    path('add/', views.Add.as_view(), name="add"),
    path('rename/<int:pk>/', views.Rename.as_view(), name="rename"),

    path('fido2/new/', fido2.start, name="fido2_start"),
    path('fido2/auth/', fido2.auth, name="fido2_auth"),
    path('fido2/begin-auth/', fido2.authenticate_begin, name="fido2_begin_auth"),
    path('fido2/complete-auth/', fido2.authenticate_complete, name="fido2_complete_auth"),
    path('fido2/begin-reg/', fido2.begin_registration, name="fido2_begin_reg"),
    path('fido2/complete-reg/', fido2.complete_reg, name="fido2_complete_reg"),

    path('u2f/new/', u2f.Create.as_view(), name="u2f_start"),
    path('u2f/auth/', u2f.Auth.as_view(), name="u2f_auth"),

    path('totp/new/', totp.Create.as_view(), name="totp_start"),
    path('totp/auth/', totp.Auth.as_view(), name="totp_auth"),

    path('fallback/auth/', fallback.Auth.as_view(), name="fallback_auth"),
]
