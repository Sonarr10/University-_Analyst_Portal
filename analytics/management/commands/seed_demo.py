import random
from pathlib import Path

from django.core.management.base import BaseCommand
from openpyxl import Workbook

from analytics.models import Attendance, Department, Major, Performance, Room, Shift, Student, Subject, Teacher
from analytics.services import attendance_status, grade_for


class Command(BaseCommand):
    help = "Create clearly marked synthetic demo data and matching Excel files."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=220)
        parser.add_argument("--seed", type=int, default=2026)

    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        departments_spec = {
            "CSE": ("Computer Science and Engineering", [("SE", "Software Engineering"), ("DS", "Data Science"), ("CY", "Cybersecurity")]),
            "BUS": ("Business", [("ACC", "Accounting"), ("MKT", "Marketing")]),
            "ENG": ("Engineering", [("CE", "Civil Engineering"), ("EE", "Electrical Engineering")]),
        }
        majors = []
        for code, (name, major_specs) in departments_spec.items():
            department, _ = Department.objects.update_or_create(code=code, defaults={"name": name})
            for major_code, major_name in major_specs:
                major, _ = Major.objects.update_or_create(code=major_code, defaults={"name": major_name, "department": department})
                majors.append(major)
        subjects = []
        for major in majors:
            for number, suffix in enumerate(["Foundations", "Data Applications"], 1):
                subject, _ = Subject.objects.update_or_create(code=f"{major.code}{number}01", defaults={"name": f"{major.name} {suffix}", "major": major})
                subjects.append(subject)
        for i in range(1, 11):
            Room.objects.update_or_create(code=f"R{i:02d}", defaults={"capacity": rng.choice([25, 30, 35]), "active": True})
        for department in Department.objects.all():
            department_subjects = Subject.objects.filter(major__department=department)
            for i in range(1, 5):
                teacher, _ = Teacher.objects.update_or_create(name=f"{department.code} Demo Teacher {i}", defaults={
                    "email": f"{department.code.lower()}.teacher{i}@example.edu", "department": department,
                    "available_shifts": [Shift.MORNING] if i < 4 else [Shift.AFTERNOON, Shift.EVENING],
                    "active": True,
                })
                teacher.subjects_can_teach.set(department_subjects[:3])
        enrollment_rows, performance_rows, attendance_rows = [], [], []
        weights = [5 if major.code == "SE" else 2 if major.department.code == "CSE" else 1 for major in majors]
        for i in range(1, options["students"] + 1):
            major = rng.choices(majors, weights=weights, k=1)[0]
            shift = rng.choices(Shift.values, weights=[6, 3, 1], k=1)[0]
            student, _ = Student.objects.update_or_create(student_id=f"DEMO{i:04d}", defaults={
                "student_name": f"Synthetic Student {i:04d}", "department": major.department, "major": major,
                "shift": shift, "gender": rng.choice(["Female", "Male", "Prefer not to say"]),
            })
            enrollment_rows.append([student.student_id, student.student_name, major.department.code, major.code, shift, student.gender])
            for subject in rng.sample(list(major.subjects.all()), k=min(2, major.subjects.count())):
                absent = min(20, max(0, int(rng.gauss(3, 3))))
                attendance_pct = (20 - absent) / 20 * 100
                base_score = 42 if subject.code == "SE201" else 67
                score = max(0, min(100, round(base_score + (attendance_pct - 75) * .38 + rng.gauss(0, 10), 1)))
                grade, point = grade_for(score)
                Performance.objects.update_or_create(student=student, subject=subject, defaults={"score": score, "letter_grade": grade, "grade_point": point, "passed": score >= 50})
                Attendance.objects.update_or_create(student=student, subject=subject, defaults={"total_sessions": 20, "absent_count": absent, "attendance_percentage": attendance_pct, "status": attendance_status(attendance_pct)})
                performance_rows.append([student.student_id, subject.code, score]); attendance_rows.append([student.student_id, subject.code, 20, absent])
        output_dir = Path("demo_data"); output_dir.mkdir(exist_ok=True)
        self.write_book(output_dir / "synthetic_enrollment.xlsx", ["student_id", "student_name", "department_code", "major_code", "shift", "gender"], enrollment_rows)
        self.write_book(output_dir / "synthetic_performance.xlsx", ["student_id", "subject_code", "score"], performance_rows)
        self.write_book(output_dir / "synthetic_attendance.xlsx", ["student_id", "subject_code", "total_sessions", "absent_count"], attendance_rows)
        self.stdout.write(self.style.SUCCESS(f"Created synthetic demo data for {options['students']} students and files in {output_dir}/"))

    @staticmethod
    def write_book(path, headers, rows):
        book = Workbook(); sheet = book.active; sheet.append(headers)
        for row in rows: sheet.append(row)
        book.save(path)
