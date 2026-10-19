from django.core.management.base import BaseCommand

from multifactor import throttle


class Command(BaseCommand):
    help = "Delete stored OTP attempts older than ATTEMPT_RETENTION_DAYS (or --days)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, help="Override MULTIFACTOR['ATTEMPT_RETENTION_DAYS'].")

    def handle(self, *args, days=None, **options):
        deleted = throttle.prune(days)
        self.stdout.write(f"Deleted {deleted} attempt(s).")
