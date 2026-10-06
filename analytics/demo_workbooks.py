"""Deterministic, clearly synthetic workbooks for the classroom walkthrough."""

import random
from io import BytesIO

from openpyxl import Workbook

from .demo_names import cambodian_student_names


MASTER_ROWS = {
    "Departments": [
        ["code", "name"],
        ["SCI", "Science and Technology"],
        ["LANG", "Languages"],
        ["BUS", "Business"],
    ],
    "Majors": [
        ["code", "name", "department_code"],
        ["CSE", "Computer Science and Engineering", "SCI"],
        ["BIT", "Business Information Technology", "SCI"],
        ["DS", "Data Science", "SCI"],
        ["ENG", "English", "LANG"],
        ["CHI", "Chinese Language", "LANG"],
        ["BBA", "Business Administration", "BUS"],
        ["MKT", "Marketing", "BUS"],
    ],
    "Subjects": [
        ["code", "name", "major_code"],
        ["CSE101", "Programming Fundamentals", "CSE"],
        ["CSE102", "Database Systems", "CSE"],
        ["CSE103", "Web Development", "CSE"],
        ["BIT101", "Business Systems", "BIT"],
        ["BIT102", "Information Systems", "BIT"],
        ["DS101", "Data Analysis Foundations", "DS"],
        ["DS102", "Statistics for Data Science", "DS"],
        ["ENG101", "Academic English", "ENG"],
        ["CHI101", "Chinese Language Fundamentals", "CHI"],
        ["BBA101", "Introduction to Business", "BBA"],
        ["MKT101", "Marketing Fundamentals", "MKT"],
    ],
    "Teachers": [
        ["name", "email", "department_code", "available_shifts", "subjects_can_teach", "active"],
        ["Dara Sok", "dara@example.com", "SCI", "Morning,Afternoon", "CSE101,CSE102,CSE103", "true"],
        ["Sreyneang Lim", "sreyneang@example.com", "SCI", "Morning,Afternoon,Evening", "BIT101,BIT102,DS101", "true"],
        ["Vannak Kim", "vannak@example.com", "BUS", "Morning,Evening", "BBA101,MKT101", "true"],
        ["Sophea Chan", "sophea@example.com", "BUS", "Afternoon", "BBA101", "true"],
        ["Lina Meas", "lina@example.com", "LANG", "Evening", "ENG101", "true"],
        ["Sokha Rin", "sokha@example.com", "LANG", "Evening", "CHI101", "true"],
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
    ("SCI", "CSE", "Morning", 70),
    ("SCI", "CSE", "Afternoon", 22),
    ("SCI", "BIT", "Morning", 28),
    ("BUS", "BBA", "Morning", 24),
    ("BUS", "BBA", "Afternoon", 23),
    ("LANG", "ENG", "Evening", 18),
    ("SCI", "DS", "Evening", 12),
    ("LANG", "CHI", "Evening", 14),
    ("BUS", "MKT", "Evening", 16),
]

SUBJECTS_BY_MAJOR = {
    "CSE": ["CSE101", "CSE102", "CSE103"],
    "BIT": ["BIT101", "BIT102"],
    "DS": ["DS101", "DS102"],
    "BBA": ["BBA101"],
    "ENG": ["ENG101"],
    "CHI": ["CHI101"],
    "MKT": ["MKT101"],
}

BASE_SCORES = {
    "CSE101": 76, "CSE102": 58, "CSE103": 72,
    "BIT101": 70, "BIT102": 68, "DS101": 73, "DS102": 69,
    "BBA101": 75, "ENG101": 78, "CHI101": 74, "MKT101": 76,
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
    """Return eight valid, separate .xlsx payloads; never change the database."""
    rng = random.Random(2026)
    enrollment = [["student_id", "student_name", "department_code", "major_code", "shift"]]
    performance = [["student_id", "subject_code", "score"]]
    attendance = [["student_id", "subject_code", "total_sessions", "absent_count"]]
    index = 0
    student_names = cambodian_student_names(sum(group[3] for group in ENROLLMENT_GROUPS))

    for department, major, shift, count in ENROLLMENT_GROUPS:
        for _ in range(count):
            index += 1
            student_id = f"SHOW{index:04d}"
            enrollment.append([student_id, student_names[index - 1], department, major, shift])
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

    setup = {
        kind: (f"{kind}.xlsx", _workbook_bytes({sheet: MASTER_ROWS[sheet]}))
        for kind, sheet in (
            ("department", "Departments"), ("major", "Majors"),
            ("subject", "Subjects"), ("teacher", "Teachers"), ("room", "Rooms"),
        )
    }
    return {
        **setup,
        "enrollment": ("enrollment.xlsx", _workbook_bytes({"Enrollment": enrollment})),
        "performance": ("performance.xlsx", _workbook_bytes({"Performance": performance})),
        "attendance": ("attendance.xlsx", _workbook_bytes({"Attendance": attendance})),
    }


def messy_demo_workbooks():
    """Independent incoming batches, intended for preview after Good Data is imported."""
    extra_names = cambodian_student_names(sum(group[3] for group in ENROLLMENT_GROUPS) + 3)[-3:]
    existing_name = cambodian_student_names(1)[0]
    conflicting_name = "Sok Dara" if existing_name != "Sok Dara" else "Chan Vannak"
    duplicate_name = "Chan Vannak" if extra_names[0] != "Chan Vannak" else "Lim Sreypov"
    rows = {
        "department": [
            ["code", "name"],
            [" EDU ", " Education "],                     # Safe whitespace cleaning; new code.
            ["SCI", "Faculty of Science"],                # Existing code, conflicting name.
            ["edu", "Faculty of Education"],              # Conflicting duplicate in this file.
            ["", "Environmental Studies"],               # Missing required code.
            ["LANG", "Modern Languages"],                 # Existing code, conflicting name.
        ],
        "major": [
            ["code", "name", "department_code"],
            [" AI ", " Applied Informatics ", " sci "],    # New major, casing/whitespace cleanup.
            ["CSE", "Computing", "SCI"],                   # Existing code, conflicting name.
            ["AI", "Artificial Intelligence", "SCI"],    # Conflicting duplicate in this file.
            ["NEW1", "Unknown Faculty Major", "UNKNOWN"],
            ["NEW2", "", "LANG"],                         # Missing name.
        ],
        "subject": [
            ["code", "name", "major_code"],
            [" CSE104 ", " Software Testing ", " cse "],  # New subject under existing major.
            ["CSE102", "Data Warehousing", "CSE"],       # Existing code, conflicting name.
            ["cse104", "Quality Assurance", "CSE"],     # Conflicting duplicate in this file.
            ["NEW101", "Unlinked Subject", "UNKNOWN"],
            ["NEW102", "", "BIT"],                        # Missing name.
        ],
        "teacher": [
            ["name", "email", "department_code", "available_shifts", "subjects_can_teach", "active"],
            ["Sok Chantha", "sok.chantha@example.com", " sci ", " morning , Afternoon ", "CSE101,CSE102", " true "],
            ["Lina New", "dara@example.com", "SCI", "Morning", "CSE101", "true"],
            ["Invalid Shift", "invalid.shift@example.com", "SCI", "Weekend", "CSE101", "true"],
            ["Too Many", "too.many@example.com", "SCI", "Morning", "CSE101,CSE102,CSE103,BIT101", "true"],
            ["Wrong Department", "wrong.dept@example.com", "SCI", "Evening", "BBA101", "true"],
            ["Invalid Active", "invalid.active@example.com", "LANG", "Evening", "ENG101", "maybe"],
            ["Missing Department", "missing.dept@example.com", "UNKNOWN", "Morning", "", "true"],
            ["", "missing.name@example.com", "SCI", "Morning", "CSE101", "true"],
        ],
        "room": [
            ["code", "capacity", "active"],
            [" C301 ", 25, " true "],                       # New room, whitespace cleanup.
            ["A101", 40, "true"],                         # Existing code, conflicting capacity.
            ["C301", 50, "false"],                        # Conflicting duplicate in this file.
            ["C302", 0, "true"],                          # Invalid numeric value.
            ["C303", 25, "maybe"],                        # Invalid boolean.
            ["", 25, "true"],                             # Missing code.
        ],
        "enrollment": [
            ["student_id", "student_name", "department_code", "major_code", "shift"],
            [" SHOW9001 ", extra_names[0], " sci ", " cse ", " morning "],
            ["SHOW9002", extra_names[1], "BUS", "BBA", "Afternoon"],
            ["SHOW9003", extra_names[2], "SCI", "BIT", "Afternoon"],
            ["SHOW0001", conflicting_name, "SCI", "CSE", "Morning"],  # Existing-ID conflict.
            ["SHOW9001", duplicate_name, "SCI", "CSE", "Morning"],  # Conflicting in-file duplicate.
            ["", "Chea Ratha", "SCI", "CSE", "Morning"],
            ["SHOW9004", "Kim Sophea", "UNKNOWN", "CSE", "Morning"],
            ["SHOW9005", "Noun Sokha", "SCI", "UNKNOWN", "Morning"],
            ["SHOW9006", "Heng Sreynich", "SCI", "BBA", "Morning"],
            ["SHOW9007", "Chhim Piseth", "SCI", "CSE", "Weekend"],
        ],
        "performance": [
            ["student_id", "subject_code", "score"],
            ["SHOW9001", "CSE101", 82],
            ["SHOW9002", "BBA101", 67],
            ["SHOW9003", "BIT101", 74],
            ["SHOW0001", "CSE101", 0],                   # Existing pair conflicts with Good Data.
            ["SHOW9001", "CSE101", 43],                  # Conflicting in-file duplicate.
            ["UNKNOWN", "CSE101", 70],
            ["SHOW9001", "UNKNOWN", 70],
            ["SHOW9001", "CSE102", "not-a-score"],
            ["SHOW9001", "CSE103", -5],
            ["SHOW9002", "CSE101", 105],
            ["SHOW9002", "BBA101", ""],                 # Missing value plus duplicate.
        ],
        "attendance": [
            ["student_id", "subject_code", "total_sessions", "absent_count"],
            ["SHOW9001", "CSE101", 20, 2],
            ["SHOW9002", "BBA101", 20, 5],
            ["SHOW9003", "BIT101", 20, 3],
            ["SHOW0001", "CSE101", 20, 20],              # Existing pair conflicts with Good Data.
            ["SHOW9001", "CSE101", 20, 4],              # Conflicting in-file duplicate.
            ["UNKNOWN", "CSE101", 20, 2],
            ["SHOW9001", "UNKNOWN", 20, 2],
            ["SHOW9001", "CSE102", 0, 0],
            ["SHOW9001", "CSE103", 20, -1],
            ["SHOW9002", "CSE101", 20, 21],
            ["SHOW9003", "BIT102", "twenty", 2],
            ["SHOW9002", "BBA101", "", 2],              # Missing value plus duplicate.
        ],
    }
    sheet_names = {
        "department": "Departments", "major": "Majors", "subject": "Subjects",
        "teacher": "Teachers", "room": "Rooms", "enrollment": "Enrollment",
        "performance": "Performance", "attendance": "Attendance",
    }
    return {
        kind: (f"{kind}_messy.xlsx", _workbook_bytes({sheet_names[kind]: data}))
        for kind, data in rows.items()
    }
