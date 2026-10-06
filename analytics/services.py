from collections import Counter
from decimal import Decimal, InvalidOperation

import pandas as pd
import numpy as np
from django.db.models import Avg, Count, Q

from .models import Attendance, Department, ImportBatch, Major, Performance, Room, Shift, Student, Subject, Teacher
from .capacity import MAX_STUDENTS_PER_SECTION, capacity_analysis

REQUIRED_COLUMNS = {
    "enrollment": ["student_id", "student_name", "department_code", "major_code", "shift"],
    "performance": ["student_id", "subject_code", "score"],
    "attendance": ["student_id", "subject_code", "total_sessions", "absent_count"],
}


def clean_cell(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def finite_number(value):
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        return None
    return number if number.is_finite() else None


def grade_for(score):
    if score >= 85: return "A", 4.0
    if score >= 80: return "B+", 3.5
    if score >= 70: return "B", 3.0
    if score >= 65: return "C+", 2.5
    if score >= 60: return "C", 2.0
    if score >= 50: return "D", 1.0
    return "F", 0.0


def attendance_status(percentage):
    if percentage >= 85: return "Good"
    if percentage >= 75: return "Warning"
    if percentage >= 60: return "High Risk"
    return "Critical"


def validate_workbook(file, dataset_type):
    try:
        frame = pd.read_excel(file, engine="openpyxl", dtype=object)
    except Exception as exc:
        raise ValueError(f"Excel file could not be read: {exc}") from exc
    frame.columns = [str(col).strip().lower() for col in frame.columns]
    required = REQUIRED_COLUMNS[dataset_type]
    missing_columns = [col for col in required if col not in frame.columns]
    if missing_columns:
        raise ValueError("Missing required columns: " + ", ".join(missing_columns))
    valid_rows, issues = [], []
    duplicate_count = 0
    missing_count = 0
    invalid_reference_count = 0
    invalid_numeric_count = 0
    invalid_department = invalid_major = invalid_shift = 0
    seen = set()
    departments = {x.code.upper(): x for x in Department.objects.all()}
    majors = {x.code.upper(): x for x in Major.objects.select_related("department")}
    students = {x.student_id.upper(): x for x in Student.objects.select_related("department", "major")}
    subjects = {x.code.upper(): x for x in Subject.objects.all()}
    existing_results = {}
    if dataset_type == "performance":
        existing_results = {
            (record.student.student_id.upper(), record.subject.code.upper()): record
            for record in Performance.objects.select_related("student", "subject")
        }
    elif dataset_type == "attendance":
        existing_results = {
            (record.student.student_id.upper(), record.subject.code.upper()): record
            for record in Attendance.objects.select_related("student", "subject")
        }
    for index, raw in frame.iterrows():
        row_number = index + 2
        row = {col: clean_cell(raw.get(col, "")) for col in frame.columns}
        errors = []
        invalid_reference = False
        invalid_numeric = False
        missing = [col for col in required if not row.get(col)]
        if missing:
            missing_count += 1
            errors.append("Missing: " + ", ".join(missing))
        if dataset_type == "enrollment":
            key = row.get("student_id", "").upper()
            duplicate_in_file = bool(key and key in seen)
            if duplicate_in_file:
                duplicate_count += 1; errors.append("Duplicate student_id in file")
            if key:
                seen.add(key)
            if len(row.get("student_id", "")) > 30 or len(row.get("student_name", "")) > 150:
                errors.append("Student ID or name is too long")
            if len(row.get("gender", "")) > 30:
                errors.append("Gender is too long")
            dept = departments.get(row.get("department_code", "").upper())
            major = majors.get(row.get("major_code", "").upper())
            if row.get("department_code") and not dept:
                invalid_department += 1; invalid_reference = True; errors.append("Unknown department_code")
            if row.get("major_code") and not major:
                invalid_major += 1; invalid_reference = True; errors.append("Unknown major_code")
            elif dept and major and major.department_id != dept.id:
                invalid_major += 1; invalid_reference = True; errors.append("Major does not belong to department")
            normalized_shift = row.get("shift", "").title()
            if row.get("shift") and normalized_shift not in Shift.values:
                invalid_shift += 1; errors.append("Shift must be Morning, Afternoon, or Evening")
            row["shift"] = normalized_shift
            existing = students.get(key)
            if existing and (
                existing.student_name != row.get("student_name")
                or existing.department.code.upper() != row.get("department_code", "").upper()
                or existing.major.code.upper() != row.get("major_code", "").upper()
                or existing.shift != normalized_shift
            ):
                if not duplicate_in_file:
                    duplicate_count += 1
                errors.append("Existing student_id conflicts with stored enrollment; edit it manually")
        elif dataset_type == "performance":
            key = (row.get("student_id", "").upper(), row.get("subject_code", "").upper())
            duplicate_in_file = all(key) and key in seen
            if duplicate_in_file:
                duplicate_count += 1; errors.append("Duplicate student/subject in file")
            if all(key):
                seen.add(key)
            if row.get("student_id") and key[0] not in students:
                invalid_reference = True; errors.append("Unknown student_id")
            if row.get("subject_code") and key[1] not in subjects:
                invalid_reference = True; errors.append("Unknown subject_code")
            if row.get("score"):
                score = finite_number(row["score"])
                if score is None or not 0 <= score <= 100:
                    invalid_numeric = True; errors.append("Score must be numeric from 0 to 100")
                else:
                    row["score"] = float(score)
                    existing = existing_results.get(key)
                    if existing and float(existing.score) != row["score"]:
                        if not duplicate_in_file:
                            duplicate_count += 1
                        errors.append("Existing student/subject score conflicts with stored performance; edit it manually")
        else:
            key = (row.get("student_id", "").upper(), row.get("subject_code", "").upper())
            duplicate_in_file = all(key) and key in seen
            if duplicate_in_file:
                duplicate_count += 1; errors.append("Duplicate student/subject in file")
            if all(key):
                seen.add(key)
            if row.get("student_id") and key[0] not in students:
                invalid_reference = True; errors.append("Unknown student_id")
            if row.get("subject_code") and key[1] not in subjects:
                invalid_reference = True; errors.append("Unknown subject_code")
            if row.get("total_sessions") and row.get("absent_count"):
                total = finite_number(row["total_sessions"])
                absent = finite_number(row["absent_count"])
                if (total is None or absent is None or total != total.to_integral_value()
                        or absent != absent.to_integral_value() or total <= 0 or absent < 0
                        or absent > total or total > 9223372036854775807):
                    invalid_numeric = True
                    errors.append("Sessions must be whole numbers; total > 0 and 0 ≤ absent ≤ total")
                else:
                    row.update(total_sessions=int(total), absent_count=int(absent))
                    existing = existing_results.get(key)
                    if existing and (existing.total_sessions != row["total_sessions"] or existing.absent_count != row["absent_count"]):
                        if not duplicate_in_file:
                            duplicate_count += 1
                        errors.append("Existing student/subject attendance conflicts with stored record; edit it manually")
        invalid_reference_count += int(invalid_reference)
        invalid_numeric_count += int(invalid_numeric)
        if errors:
            issues.append({"row": row_number, "data": row, "errors": errors})
        else:
            valid_rows.append(row)
    summary = {
        "total_rows": len(frame), "valid_rows": len(valid_rows), "duplicate_rows": duplicate_count,
        "missing_value_rows": missing_count, "invalid_references": invalid_reference_count,
        "invalid_department_rows": invalid_department, "invalid_major_rows": invalid_major,
        "invalid_shift_rows": invalid_shift, "invalid_numeric_rows": invalid_numeric_count,
        "rejected_rows": len(issues),
        "data_quality_percentage": round(len(valid_rows) / len(frame) * 100, 1) if len(frame) else None,
    }
    return summary, valid_rows, issues


def import_rows(batch):
    created = updated = 0
    for row in batch.valid_rows:
        if batch.dataset_type == "enrollment":
            dept = Department.objects.get(code__iexact=row["department_code"])
            major = Major.objects.get(code__iexact=row["major_code"])
            existing = Student.objects.filter(student_id__iexact=row["student_id"]).first()
            student_id = existing.student_id if existing else row["student_id"]
            _, was_created = Student.objects.update_or_create(student_id=student_id, defaults={
                "student_name": row["student_name"], "department": dept, "major": major,
                "shift": row["shift"], "gender": row.get("gender", ""),
            })
        elif batch.dataset_type == "performance":
            student = Student.objects.get(student_id__iexact=row["student_id"])
            subject = Subject.objects.get(code__iexact=row["subject_code"])
            grade, point = grade_for(float(row["score"]))
            _, was_created = Performance.objects.update_or_create(student=student, subject=subject, defaults={
                "score": row["score"], "letter_grade": grade, "grade_point": point, "passed": row["score"] >= 50,
            })
        else:
            student = Student.objects.get(student_id__iexact=row["student_id"])
            subject = Subject.objects.get(code__iexact=row["subject_code"])
            pct = (row["total_sessions"] - row["absent_count"]) / row["total_sessions"] * 100
            _, was_created = Attendance.objects.update_or_create(student=student, subject=subject, defaults={
                "total_sessions": row["total_sessions"], "absent_count": row["absent_count"],
                "attendance_percentage": round(pct, 2), "status": attendance_status(pct),
            })
        created += int(was_created); updated += int(not was_created)
    return created, updated


def capacity_rows():
    return capacity_analysis()["groups"]


def chart(labels, values):
    return {"labels": list(labels), "values": [float(v or 0) for v in values]}


def matched_scatter(performance_records, attendance_records):
    """Only compare records for the same student and subject."""
    attendance_by_pair = {(row.student_id, row.subject_id): row for row in attendance_records}
    points, low_scores, good_scores = [], [], []
    for record in performance_records:
        matched = attendance_by_pair.get((record.student_id, record.subject_id))
        if not matched:
            continue
        percentage = float(matched.attendance_percentage)
        score = float(record.score)
        points.append({
            "x": percentage, "y": score,
            "student_id": record.student.student_id,
            "student_name": record.student.student_name,
            "subject": record.subject.name,
            "status": matched.status,
        })
        if percentage < 75:
            low_scores.append(score)
        elif percentage >= 85:
            good_scores.append(score)
    return points, low_scores, good_scores


def dashboard_context():
    performance = Performance.objects.select_related("student", "subject")
    attendance = Attendance.objects.all()
    scores = performance.aggregate(avg=Avg("score"), total=Count("id"), passed=Count("id", filter=Q(passed=True)))
    att_avg = attendance.aggregate(avg=Avg("attendance_percentage"))["avg"]
    risk_count = attendance.exclude(status="Good").values("student_id").distinct().count()
    by_dept = Student.objects.values("department__code").annotate(value=Count("id")).order_by("department__code")
    by_major = Student.objects.values("major__name").annotate(value=Count("id")).order_by("major__name")
    by_shift = Student.objects.values("shift").annotate(value=Count("id")).order_by("shift")
    by_subject = performance.values("subject__name").annotate(value=Avg("score")).order_by("subject__name")
    status_counts = Counter(attendance.values_list("status", flat=True))
    capacity = capacity_analysis()
    groups = capacity["groups"]
    pass_rate = scores["passed"] / scores["total"] * 100 if scores["total"] else None
    insights = []
    dashboard_candidates = []
    for row in groups:
        insights.append({
            "level": "info",
            "category": "Enrollment & Capacity",
            "text": f'{row["major__name"]} {row["shift"]} has {row["students"]} students: ceil({row["students"]} / {MAX_STUDENTS_PER_SECTION}) = {row["required"]} sections and {row["required_rooms"]} analytical rooms. Current sections have {row["remaining_seats"]} seats remaining.',
            "decision": "Use these calculated sections for capacity review; no students or rooms have been assigned.",
        })
        if row["status"] != "Available":
            level = "danger" if row["status"] in {"Over Capacity", "Full"} else "warning"
            insights.append({
                "level": level,
                "category": "Enrollment & Capacity",
                "text": f'{row["major__name"]} {row["shift"]} is {row["status"]}. Current section seats remaining: {row["remaining_seats"]}; shared teacher shortage: {row["teacher_shortage"]}; shift room shortage: {row["room_shortage"]}.',
                "decision": row["recommendation"],
            })
            if row["status"] in {"Near Capacity", "Full", "Over Capacity"}:
                dashboard_candidates.append({
                    "level": level,
                    "summary": f'{row["major__name"]} {row["shift"]} is {row["status"].lower()}',
                    "url": "enrollment_dashboard",
                })
            if row["recommended_shift"]:
                dashboard_candidates.append({
                    "level": "info",
                    "summary": f'{row["recommended_shift"]} has supported capacity for {row["major__name"]}',
                    "url": "enrollment_dashboard",
                })
    for pool in capacity["teacher_pools"]:
        if pool["shortage"]:
            # Presentation severity only; the underlying shortage is unchanged.
            level = "danger" if pool["shortage"] >= 2 else "warning"
            insights.append({
                "level": level,
                "category": "Teacher Capacity",
                "text": f'{pool["department"]} {pool["shift"]} requires {pool["required"]} teachers for {pool["required"]} sections across its majors, but only {pool["capacity"]} active teachers are available. {pool["shortage"]} additional teacher(s) required.',
                "decision": "Review teacher availability for this department and shift.",
            })
            dashboard_candidates.append({
                "level": level,
                "summary": f'Teacher shortage in {pool["department"]} {pool["shift"]}',
                "url": "enrollment_dashboard",
            })
        elif pool["status"] == "At Capacity":
            insights.append({
                "level": "info",
                "category": "Teacher Capacity",
                "text": f'{pool["department"]} {pool["shift"]} is at teacher capacity: {pool["required"]} required sections and {pool["capacity"]} active teachers.',
                "decision": "Monitor new enrollment because there is no spare teacher capacity.",
            })
    for pool in capacity["shift_pools"]:
        if pool["shortage"]:
            insights.append({
                "level": "warning",
                "category": "Enrollment & Capacity",
                "text": f'{pool["shift"]} requires {pool["required"]} simultaneous shared rooms, but only {pool["capacity"]} active rooms are available. Room capacity limit: {pool["shortage"]}.',
                "decision": "Compare supported capacity in other shifts; do not treat rooms as permanently assigned.",
            })
            dashboard_candidates.append({
                "level": "warning", "summary": f'{pool["shift"]} has a shared-room capacity limit',
                "url": "enrollment_dashboard",
            })
        elif pool["status"] == "At Room Capacity":
            insights.append({
                "level": "info",
                "category": "Enrollment & Capacity",
                "text": f'{pool["shift"]} is currently using all {pool["capacity"]} active rooms for {pool["required"]} analytical sections.',
                "decision": "Existing section seats may remain, but another simultaneous section needs shared room capacity.",
            })
    for section in capacity["occupancy"]:
        if section["status"] in {"Full", "Near Full", "Getting Full"}:
            insights.append({
                "level": "info",
                "category": "Enrollment & Capacity",
                "text": f'{section["major"]} {section["shift"]} {section["section"]} is {section["status"].lower()} at {section["students"]}/{section["maximum"]} students, with {section["remaining_seats"]} seats remaining.',
                "decision": "This is a conceptual section only; use the major/shift status for supported availability.",
            })

    subject_stats = list(performance.values("subject__name").annotate(
        average=Avg("score"), total=Count("id"), failed=Count("id", filter=Q(passed=False))
    ))
    if subject_stats:
        weakest = min(subject_stats, key=lambda subject: subject["average"])
        highest_failure = max(subject_stats, key=lambda subject: subject["failed"] / subject["total"])
        extra = " It also has the highest failure rate." if weakest == highest_failure and weakest["failed"] else ""
        insights.append({
            "level": "warning" if weakest["failed"] else "info",
            "category": "Performance",
            "text": f'{weakest["subject__name"]} has the lowest average score ({float(weakest["average"]):.1f}).{extra}',
            "decision": "Review assessment outcomes and academic support.",
        })
        dashboard_candidates.append({
            "level": "warning" if weakest["failed"] else "info",
            "summary": f'{weakest["subject__name"]} has the lowest average score',
            "url": "performance_dashboard",
        })

    critical_students = attendance.filter(status="Critical").values("student_id").distinct().count()
    if critical_students:
        insights.append({
            "level": "danger", "category": "Attendance",
            "text": f"{critical_students} students have at least one Critical attendance record.",
            "decision": "Prioritize student follow-up.",
        })
        dashboard_candidates.append({
            "level": "danger", "summary": f"{critical_students} students have critical attendance",
            "url": "attendance_dashboard",
        })

    scatter, low_scores, good_scores = matched_scatter(performance, attendance)
    if low_scores and good_scores:
        low_average = sum(low_scores) / len(low_scores)
        good_average = sum(good_scores) / len(good_scores)
        if low_average < good_average:
            insights.append({
                "level": "info",
                "category": "Attendance",
                "text": f"Matched low-attendance results average {low_average:.1f}, compared with {good_average:.1f} for good attendance.",
                "decision": "Use this descriptive relationship to prioritize support; it does not prove causation.",
            })
            dashboard_candidates.append({
                "level": "info", "summary": "Matched low-attendance results have lower average scores",
                "url": "attendance_dashboard",
            })
    if len(scatter) >= 3:
        x_values = [point["x"] for point in scatter]
        y_values = [point["y"] for point in scatter]
        if np.std(x_values) and np.std(y_values):
            correlation = float(np.corrcoef(x_values, y_values)[0, 1])
            if correlation >= 0.3:
                insights.append({"level": "info", "category": "Attendance", "text": f"Matched attendance and score records show a positive relationship (correlation {correlation:.2f}).", "decision": "Use this as a descriptive signal and follow up with at-risk students; do not interpret it as causation."})

    by_required_major = {}
    for group in groups:
        by_required_major[group["major__name"]] = by_required_major.get(group["major__name"], 0) + group["required"]
    onboarding_steps = [
        {"label": "Add Departments", "done": Department.objects.exists(), "url": "department_create"},
        {"label": "Add Majors", "done": Major.objects.exists(), "url": "major_create"},
        {"label": "Add Subjects", "done": Subject.objects.exists(), "url": "subject_create"},
        {"label": "Add Teachers", "done": Teacher.objects.exists(), "url": "teacher_create"},
        {"label": "Add Rooms", "done": Room.objects.exists(), "url": "room_create"},
        {"label": "Confirm Shifts: Morning / Afternoon / Evening", "done": True, "url": ""},
        {"label": "Upload Enrollment", "done": Student.objects.exists(), "url": "upload_data"},
        {"label": "Upload Performance", "done": Performance.objects.exists(), "url": "upload_data"},
        {"label": "Upload Attendance", "done": Attendance.objects.exists(), "url": "upload_data"},
    ]
    shortage_pools = [pool for pool in capacity["teacher_pools"] if pool["shortage"]]
    availability_priority = {"Over Capacity": 0, "Teacher Shortage": 1, "Room Capacity Limit": 2, "Full": 3, "Near Capacity": 4}
    availability_alerts = sorted(
        (row for row in groups if row["status"] in availability_priority),
        key=lambda row: (availability_priority[row["status"]], row["supported_remaining_seats"], -row["students"]),
    )[:3]
    priority = {"danger": 0, "warning": 1, "info": 2}
    insights.sort(key=lambda item: priority[item["level"]])
    dashboard_candidates.sort(key=lambda item: priority[item["level"]])
    dashboard_insights = dashboard_candidates[:5] if any(item["level"] != "info" for item in dashboard_candidates) else []
    return {
        "has_data": Student.objects.exists(),
        "has_performance": bool(scores["total"]),
        "has_attendance": att_avg is not None,
        "last_imported_at": ImportBatch.objects.filter(imported_at__isnull=False).order_by("-imported_at").values_list("imported_at", flat=True).first(),
        "onboarding_steps": onboarding_steps,
        "kpis": {"students": Student.objects.count(), "teachers": Teacher.objects.filter(active=True).count(), "rooms": Room.objects.filter(active=True).count(), "departments": Department.objects.count(), "majors": Major.objects.count(), "average_score": round(float(scores["avg"]), 1) if scores["avg"] is not None else None, "pass_rate": round(pass_rate, 1) if pass_rate is not None else None, "average_attendance": round(float(att_avg), 1) if att_avg is not None else None, "risk_count": risk_count},
        "enrollment_department": chart([x["department__code"] for x in by_dept], [x["value"] for x in by_dept]),
        "enrollment_major": chart([x["major__name"] for x in by_major], [x["value"] for x in by_major]),
        "enrollment_shift": chart([x["shift"] for x in by_shift], [x["value"] for x in by_shift]),
        "required_major": chart(by_required_major.keys(), by_required_major.values()),
        "subject_scores": chart([x["subject__name"] for x in by_subject], [x["value"] for x in by_subject]),
        "pass_fail": chart(["Pass", "Fail"], [scores["passed"], (scores["total"] or 0) - (scores["passed"] or 0)]),
        "attendance_status": chart(["Good", "Warning", "High Risk", "Critical"], [status_counts[x] for x in ["Good", "Warning", "High Risk", "Critical"]]),
        "capacity_chart": {"labels": [f'{x["department"]} / {x["shift"]}' for x in capacity["teacher_pools"]],
                           "required": [x["required"] for x in capacity["teacher_pools"]],
                           "teachers": [x["capacity"] for x in capacity["teacher_pools"]]},
        "room_chart": {"labels": [x["shift"] for x in capacity["shift_pools"]],
                       "required": [x["required"] for x in capacity["shift_pools"]],
                       "rooms": [x["capacity"] for x in capacity["shift_pools"]]},
        "scatter": scatter, "capacity": groups, "capacity_analysis": capacity, "insights": insights,
        "dashboard_insights": dashboard_insights,
        "availability_alerts": availability_alerts,
        "teacher_shortage_pools": shortage_pools,
        "teacher_shortage_critical": any(pool["shortage"] >= 2 for pool in shortage_pools),
    }
