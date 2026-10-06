"""Small, shared GET filters for the three analytics reports."""

from .models import Department, Major, Shift


def _valid_pk(value):
    return value if len(value) <= 18 and value.isascii() and value.isdigit() else None


def analytics_filters(request):
    departments = Department.objects.all()
    department_id = _valid_pk(request.GET.get("department", ""))
    major_id = _valid_pk(request.GET.get("major", ""))
    department = departments.filter(pk=department_id).first() if department_id else None
    majors = Major.objects.select_related("department")
    major = majors.filter(pk=major_id).first() if major_id else None
    if department and major and major.department_id != department.pk:
        major = None
    shift = request.GET.get("shift", "")
    if shift not in Shift.values:
        shift = ""
    selected = {"department": department.pk if department else None, "major": major.pk if major else None, "shift": shift}
    return selected, {"filter_departments": departments, "filter_majors": majors, "filters": selected, "has_filters": any(selected.values())}


def filter_students(queryset, selected, prefix=""):
    if selected["department"]:
        queryset = queryset.filter(**{f"{prefix}department_id": selected["department"]})
    if selected["major"]:
        queryset = queryset.filter(**{f"{prefix}major_id": selected["major"]})
    if selected["shift"]:
        queryset = queryset.filter(**{f"{prefix}shift": selected["shift"]})
    return queryset


def filter_capacity_rows(rows, selected):
    return [row for row in rows if
            (not selected["department"] or row["major__department_id"] == selected["department"])
            and (not selected["major"] or row["major_id"] == selected["major"])
            and (not selected["shift"] or row["shift"] == selected["shift"])]
