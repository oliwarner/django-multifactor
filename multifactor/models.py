from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import JSONField


KEY_TYPE_FIDO2 = 'FIDO2'
KEY_TYPE_U2F = 'U2F'
KEY_TYPE_TOPT = 'TOTP'
KEY_TYPE_EMAIL = 'Email'

KEY_CHOICES = (
    (KEY_TYPE_FIDO2, "FIDO2 Security Device"),
    (KEY_TYPE_U2F, "U2F Security Key"),
    (KEY_TYPE_TOPT, "TOTP Authenticator"),
    (KEY_TYPE_EMAIL, "OTP-over-Email"),
)


class UserKey(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, related_name="multifactor_keys")
    properties = JSONField(null=True)
    key_type = models.CharField(max_length=25, choices=KEY_CHOICES)
    enabled = models.BooleanField(default=True)

    added_on = models.DateTimeField(auto_now_add=True)
    expires = models.DateTimeField(null=True, default=None, blank=True)
    last_used = models.DateTimeField(null=True, default=None, blank=True)

    def __str__(self):
        return f"{self.user} -- {self.get_key_type_display()}"

    @property
    def device(self):
        if self.key_type == KEY_TYPE_FIDO2:
            return self.properties.get("type", "----")
        elif self.key_type == KEY_TYPE_U2F:
            return self.properties.get("device", "----")
        return ""

    @property
    def auth_url(self):
        from .common import method_url
        return method_url(self.key_type)
    