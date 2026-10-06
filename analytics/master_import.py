"""Validation and confirmed import for the five-sheet master-data workbook."""

from decimal import Decimal, InvalidOperation

import pandas as pd
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .models import Department, Major, Room, Shift, Subject, Teacher
from .services import clean_cell


SHEETS = {
    "Departments": ("code", "name"),
    "Majors": ("code", "name", "department_code"),
    "Subjects": ("code", "name", "major_code"),
    "Teachers": ("name", "email", "department_code", "available_shifts"),
    "Rooms": ("code", "capacity", "active"),
}


def positive_integer(value):
    try:
        number = Decimal(value)
        if not number.is_finite() or number != number.to_integral_value() or number <= 0:
            raise ValueError
        return int(number)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Must be a positive whole number") from None


def active_boolean(value):
    normalized = value.lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    raise ValueError("Active must be true or false")


def validate_master_workbook(file):
    try:
        frames = pd.read_excel(file, sheet_name=None, engine="openpyxl", dtype=object)
    except Exception as exc:
        raise ValueError(f"Excel file could not be read: {exc}") from exc

    missing_sheets = [sheet for sheet in SHEETS if sheet not in frames]
    if missing_sheets:
        raise ValueError("Missing required sheets: " + ", ".join(missing_sheets))

    for sheet, required in SHEETS.items():
        frames[sheet].columns = [str(column).strip().lower() for column in frames[sheet].columns]
        missing_columns = [column for column in required if column not in frames[sheet].columns]
        if missing_columns:
            raise ValueError(f"{sheet} is missing required columns: {', '.join(missing_columns)}")

    valid = {sheet: [] for sheet in SHEETS}
    issues = []
    summary = {sheet: {"total": len(frames[sheet]), "valid": 0, "rejected": 0} for sheet in SHEETS}
    summary.update({"duplicate_rows": 0, "missing_value_rows": 0, "invalid_references": 0, "invalid_numeric_rows": 0})
    known_departments = {code.upper() for code in Department.objects.values_list("code", flat=True)}
    known_majors = {code.upper() for code in Major.objects.values_list("code", flat=True)}
    seen = {sheet: set() for sheet in SHEETS}

    for sheet, required in SHEETS.items():
        for index, raw in frames[sheet].iterrows():
            row = {column: clean_cell(raw.get(column, "")) for column in required}
            errors = []
            missing = [column for column in required if not row[column] and not (sheet == "Teachers" and column == "email")]
            if missing:
                summary["missing_value_rows"] += 1
                errors.append("Missing: " + ", ".join(missing))
            invalid_reference = False

            if sheet in {"Departments", "Majors", "Subjects", "Rooms"}:
                row["code"] = row["code"].upper()
                identity = row["code"]
                if len(identity) > (30 if sheet == "Rooms" else 20):
                    errors.append("Code is too long")
            else:
                row["department_code"] = row["department_code"].upper()
                row["email"] = row["email"].lower()
                identity = row["email"] or (row["name"].casefold(), row["department_code"])
            if identity in seen[sheet]:
                summary["duplicate_rows"] += 1
                errors.append("Duplicate record in sheet")
            seen[sheet].add(identity)

            if sheet == "Departments":
                if len(row["name"]) > 150:
                    errors.append("Name is too long")
            elif sheet == "Majors":
                row["department_code"] = row["department_code"].upper()
                if row["department_code"] and row["department_code"] not in known_departments:
                    invalid_reference = True
                    errors.append("Unknown department_code")
                if len(row["name"]) > 150:
                    errors.append("Name is too long")
            elif sheet == "Subjects":
                row["major_code"] = row["major_code"].upper()
                if row["major_code"] and row["major_code"] not in known_majors:
                    invalid_reference = True
                    errors.append("Unknown major_code")
                if len(row["name"]) > 150:
                    errors.append("Name is too long")
            elif sheet == "Teachers":
                if row["department_code"] and row["department_code"] not in known_departments:
                    invalid_reference = True
                    errors.append("Unknown department_code")
                if len(row["name"]) > 150:
                    errors.append("Name is too long")
                if row["email"]:
                    try:
                        validate_email(row["email"])
                    except ValidationError:
                        errors.append("Invalid email address")
                shifts = [part.strip().title() for part in row["available_shifts"].split(",") if part.strip()]
                if not shifts or len(shifts) != len(set(shifts)) or any(shift not in Shift.values for shift in shifts):
                    invalid_reference = True
                    errors.append("Available shifts must be unique Morning, Afternoon, or Evening values")
                else:
                    row["available_shifts"] = shifts
            elif sheet == "Rooms":
                if row["capacity"]:
                    try:
                        row["capacity"] = positive_integer(row["capacity"])
                    except ValueError as exc:
                        summary["invalid_numeric_rows"] += 1
                        errors.append(f"capacity: {exc}")
                if row["active"]:
                    try:
                        row["active"] = active_boolean(row["active"])
                    except ValueError as exc:
                        errors.append(str(exc))

            summary["invalid_references"] += int(invalid_reference)

            if errors:
                summary[sheet]["rejected"] += 1
                issues.append({"sheet": sheet, "row": index + 2, "data": row, "errors": errors})
            else:
                summary[sheet]["valid"] += 1
                valid[sheet].append(row)
                if sheet == "Departments":
                    known_departments.add(row["code"])
                elif sheet == "Majors":
                    known_majors.add(row["code"])

    summary["rejected_rows"] = len(issues)
    summary["valid_rows"] = sum(summary[sheet]["valid"] for sheet in SHEETS)
    total_rows = sum(summary[sheet]["total"] for sheet in SHEETS)
    summary["total_rows"] = total_rows
    summary["data_quality_percentage"] = round(summary["valid_rows"] / total_rows * 100, 1) if total_rows else None
    return summary, valid, issues


def import_master_rows(valid_rows):
    """Call inside a transaction, after the analyst confirms the preview."""
    created = updated = 0

    def count(was_created):
        nonlocal created, updated
        created += int(was_created)
        updated += int(not was_created)

    for row in valid_rows.get("Departments", []):
        instance = Department.objects.filter(code__iexact=row["code"]).first()
        was_created = instance is None
        instance = instance or Department(code=row["code"])
        instance.name = row["name"]
        instance.save()
        count(was_created)

    for row in valid_rows.get("Majors", []):
        department = Department.objects.get(code__iexact=row["department_code"])
        instance = Major.objects.filter(code__iexact=row["code"]).first()
        was_created = instance is None
        instance = instance or Major(code=row["code"])
        instance.name, instance.department = row["name"], department
        instance.save()
        count(was_created)

    for row in valid_rows.get("Subjects", []):
        major = Major.objects.get(code__iexact=row["major_code"])
        instance = Subject.objects.filter(code__iexact=row["code"]).first()
        was_created = instance is None
        instance = instance or Subject(code=row["code"])
        instance.name, instance.major = row["name"], major
        instance.save()
        count(was_created)

    for row in valid_rows.get("Teachers", []):
        department = Department.objects.get(code__iexact=row["department_code"])
        instance = Teacher.objects.filter(email__iexact=row["email"]).first() if row["email"] else None
        instance = instance or Teacher.objects.filter(name__iexact=row["name"], department=department).first()
        was_created = instance is None
        instance = instance or Teacher()
        instance.name, instance.email, instance.department = row["name"], row["email"], department
        instance.available_shifts = row["available_shifts"]
        instance.save()
        count(was_created)

    for row in valid_rows.get("Rooms", []):
        instance = Room.objects.filter(code__iexact=row["code"]).first()
        was_created = instance is None
        instance = instance or Room(code=row["code"])
        instance.capacity, instance.active = row["capacity"], row["active"]
        instance.save()
        count(was_created)

    return created, updated
