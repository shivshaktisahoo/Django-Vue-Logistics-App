from django.core.management.base import BaseCommand

from apps.demo.seed import seed_demo


class Command(BaseCommand):
    help = "Create (or with --reset, rebuild) the public demo workspace."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete and rebuild demo data.")

    def handle(self, *args, reset: bool, **options):
        org = seed_demo(reset=reset)
        self.stdout.write(self.style.SUCCESS(f"Demo workspace ready: {org.name} ({org.id})"))
