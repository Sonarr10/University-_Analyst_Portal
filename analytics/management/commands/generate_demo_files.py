from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from analytics.demo_workbooks import demo_workbooks, messy_demo_workbooks


README_TEXT = """# Synthetic university demo datasets

These files are fictional teaching examples. They do not contain real student records.

## Good Data

The eight workbooks in `Good Data/` contain valid setup and analytics rows. Import them
in this order, reviewing and confirming each batch in the portal:

1. `department.xlsx`
2. `major.xlsx`
3. `subject.xlsx`
4. `teacher.xlsx`
5. `room.xlsx`
6. `enrollment.xlsx`
7. `performance.xlsx`
8. `attendance.xlsx`

The setup hierarchy is Science and Technology (Computer Science and Engineering,
Business Information Technology, Data Science), Languages (English, Chinese Language),
and Business (Business Administration, Marketing). Enrollment uses varied fictional
Cambodian-style names. Performance and Attendance use the same student IDs; student
names are resolved from Enrollment after import.

## Messy Data

The eight workbooks in `Messy Data/` are **new incoming batches**, not copies of
Good Data. Import Good Data first. Then validate Messy Data in the same order above,
review the row-level issues, and confirm only valid rows if you want to demonstrate
cleaning. Later messy analytics files reference the valid new enrollment IDs
`SHOW9001`–`SHOW9003`, so confirm valid messy Enrollment rows before validating
messy Performance and Attendance.

Intentional problems include conflicts with existing codes/IDs, duplicate rows,
missing fields, bad references, invalid shifts/booleans/numbers, and impossible
attendance counts. Some rows only need safe whitespace or casing cleanup and should
remain valid. A duplicate code with a different name is rejected, never treated as
a new department, major, subject, or room. Conflicting existing student and
student/subject records are likewise rejected rather than silently overwritten.

The generator changes files only; it does not modify the database.
"""

LEGACY_FILENAMES = (
    "demo_master_data.xlsx", "demo_enrollment.xlsx",
    "demo_performance.xlsx", "demo_attendance.xlsx",
)


class Command(BaseCommand):
    help = "Generate separate Good Data and Messy Data Excel workbooks in demo_data/ (no database changes)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Replace only the 16 named Good/Messy workbooks if they already exist.")

    def handle(self, *args, **options):
        target = Path("demo_data")
        planned = [
            *((target / "Good Data" / filename, payload) for filename, payload in demo_workbooks().values()),
            *((target / "Messy Data" / filename, payload) for filename, payload in messy_demo_workbooks().values()),
        ]
        readme_path = target / "README.md"
        existing = [str(path) for path, _ in planned if path.exists()]
        if readme_path.exists():
            existing.append(str(readme_path))
        if existing and not options["force"]:
            raise CommandError("Demo files already exist: " + ", ".join(existing) + ". Use --force to replace these named files.")
        target.mkdir(exist_ok=True)
        for path, payload in planned:
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(payload)
            self.stdout.write(str(path))
        readme_path.write_text(README_TEXT, encoding="utf-8")
        self.stdout.write(str(readme_path))
        for filename in LEGACY_FILENAMES:
            legacy_path = target / filename
            if legacy_path.is_file():
                legacy_path.unlink()
                self.stdout.write(f"Removed obsolete {legacy_path}")
        self.stdout.write(self.style.SUCCESS("16 synthetic demo workbooks generated; database unchanged."))
