from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from analytics.demo_workbooks import demo_workbooks


class Command(BaseCommand):
    help = "Generate four synthetic demo Excel workbooks in demo_data/ (no database changes)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Replace only the four named demo workbooks if they already exist.")

    def handle(self, *args, **options):
        target = Path("demo_data")
        workbooks = demo_workbooks()
        existing = [name for name, _ in workbooks.values() if (target / name).exists()]
        if existing and not options["force"]:
            raise CommandError("Demo files already exist: " + ", ".join(existing) + ". Use --force to replace these four files.")
        target.mkdir(exist_ok=True)
        for filename, payload in workbooks.values():
            (target / filename).write_bytes(payload)
            self.stdout.write(str(target / filename))
        self.stdout.write(self.style.SUCCESS("Synthetic demo workbooks generated; database unchanged."))
