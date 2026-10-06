"""Deterministic, clearly synthetic workbooks for the classroom walkthrough."""

import random
from io import BytesIO

from openpyxl import Workbook


MASTER_ROWS = {
    "Departments": [
        ["code", "name"],
        ["CSE", "Computer Science and Engineering"],
        ["BUS", "Business Administration"],
        ["ENG", "English"],
    ],
    "Majors": [
        ["code", "name", "department_code"],
        ["SE", "Software Engineering", "CSE"],
        ["CYB", "Cybersecurity", "CSE"],
        ["BBA", "Business Administration", "BUS"],
        ["ENG", "English Language", "ENG"],
    ],
    "Subjects": [
        ["code", "name", "major_code"],
        ["SE101", "Programming Fundamentals", "SE"],
        ["SE102", "Database Systems", "SE"],
        ["SE103", "Web Development", "SE"],
        ["CY101", "Network Fundamentals", "CYB"],
        ["CY102", "Cybersecurity Fundamentals", "CYB"],
        ["BBA101", "Introduction to Business", "BBA"],
        ["ENG101", "Academic English", "ENG"],
    ],
    "Teachers": [
        ["name", "email", "department_code", "available_shifts"],
        ["Dara Sok", "dara@example.com", "CSE", "Morning"],
        ["Sreyneang Lim", "sreyneang@example.com", "CSE", "Morning,Evening"],
        ["Vannak Kim", "vannak@example.com", "BUS", "Morning,Evening"],
        ["Sophea Chan", "sophea@example.com", "BUS", "Afternoon"],
        ["Lina Meas", "lina@example.com", "ENG", "Evening"],
        ["Sokha Rin", "sokha@example.com", "ENG", "Evening"],
    ],
    "Rooms": [
        ["code", "capacity", "active"],
        ["A101", 25, True],
        ["A102", 25, True],
        ["A103", 25, True],
        ["B201", 25, True],
    ],
}

ENROLLMENT_GROUPS = [
    ("CSE", "SE", "Morning", 70),
    ("CSE", "SE", "Afternoon", 22),
    ("CSE", "CYB", "Morning", 28),
    ("BUS", "BBA", "Morning", 24),
    ("BUS", "BBA", "Afternoon", 23),
    ("ENG", "ENG", "Evening", 18),
]

SUBJECTS_BY_MAJOR = {
    "SE": ["SE101", "SE102", "SE103"],
    "CYB": ["CY101", "CY102"],
    "BBA": ["BBA101"],
    "ENG": ["ENG101"],
}

BASE_SCORES = {
    "SE101": 76, "SE102": 58, "SE103": 72,
    "CY101": 70, "CY102": 68, "BBA101": 75, "ENG101": 78,
}


def _workbook_bytes(sheets):
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        sheet = workbook.create_sheet(name)
        for row in rows:
            sheet.append(row)
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def demo_workbooks():
    """Return four valid .xlsx payloads; never change the database."""
    rng = random.Random(2026)
    enrollment = [["student_id", "student_name", "department_code", "major_code", "shift"]]
    performance = [["student_id", "subject_code", "score"]]
    attendance = [["student_id", "subject_code", "total_sessions", "absent_count"]]
    index = 0

    for department, major, shift, count in ENROLLMENT_GROUPS:
        for _ in range(count):
            index += 1
            student_id = f"SHOW{index:04d}"
            enrollment.append([student_id, f"Synthetic Student {index:04d}", department, major, shift])
            if index % 15 == 0:
                absent = rng.randint(9, 11)
            elif index % 7 == 0:
                absent = rng.randint(6, 8)
            elif index % 4 == 0:
                absent = rng.randint(4, 5)
            else:
                absent = rng.randint(0, 3)
            attendance_percentage = (20 - absent) / 20 * 100
            for subject_code in SUBJECTS_BY_MAJOR[major]:
                noise = rng.gauss(0, 8)
                score = round(max(0, min(100, BASE_SCORES[subject_code] + (attendance_percentage - 85) * 0.38 + noise)), 1)
                performance.append([student_id, subject_code, score])
                attendance.append([student_id, subject_code, 20, absent])

    return {
        "master": ("demo_master_data.xlsx", _workbook_bytes(MASTER_ROWS)),
        "enrollment": ("demo_enrollment.xlsx", _workbook_bytes({"Enrollment": enrollment})),
        "performance": ("demo_performance.xlsx", _workbook_bytes({"Performance": performance})),
        "attendance": ("demo_attendance.xlsx", _workbook_bytes({"Attendance": attendance})),
    }
