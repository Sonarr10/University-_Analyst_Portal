# University Data Analytics Portal

A Django Version 1 decision-support portal for university enrollment, capacity, academic performance, and attendance analysis. Its core workflow is: Excel upload → validation and cleaning → transformation → analysis → visualization → supported insight → management decision.

## Setup and run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`, choose **Create an account**, and register with full name, email, and password. Passwords use Django's secure hashing; there is no preset password or public demo account.

To run verification:

```bash
python manage.py check
python manage.py test
```

To generate the four classroom demo workbooks without changing the database:

```bash
python manage.py generate_demo_files
```

The older `seed_demo --students 220` command still exists, but it writes records directly into the database. Use the new workbook flow below when demonstrating validation and import.

## Teacher demo: 5–10 minutes

Start from an empty database. If this local database already contains records, make a backup and run `python manage.py flush` only if you intend to remove **all** records, including accounts; then register again. Do not run `seed_demo` before this walkthrough.

1. Register or sign in. Show the empty dashboard: zero students, teachers, and rooms, with “No Data” score and attendance cards.
2. Open **Departments → Add Department** and create `CSE` / `Computer Science and Engineering`. Open **Majors → Add Major** and create `SE` / `Software Engineering` under `CSE`.
3. Download **Master Data Demo** from **Upload Data**, then open **Import Master Data** in the sidebar. Upload `demo_master_data.xlsx`, review the five-sheet summary, and click **Import valid rows**. The existing `CSE` and `SE` records update instead of duplicating.
4. Download and upload `demo_enrollment.xlsx` as **Enrollment**. Show its cleaning summary, confirm the import, then open **Enrollment & Capacity**. Point out 70 Software Engineering Morning students, three required sections, the shared CSE Morning teacher shortage, shift-wide shared-room demand, and supported-seat recommendations.
5. Upload and confirm `demo_performance.xlsx` as **Academic Performance**. Open **Performance** to show the weak Database Systems average and failure rate.
6. Upload and confirm `demo_attendance.xlsx` as **Attendance**. Open **Attendance** to show risk groups and the attendance-versus-score scatter chart.
7. Return to **Dashboard** and walk through the management insights. Each number comes from the imported database records.

All four workbooks are downloadable from the Upload Data page. `generate_demo_files` also writes physical copies to `demo_data/`:

| File | Contents |
|---|---|
| `demo_master_data.xlsx` | Departments, Majors, Subjects, Teachers, Rooms |
| `demo_enrollment.xlsx` | 185 synthetic students in six major/shift groups |
| `demo_performance.xlsx` | 397 synthetic student/subject scores |
| `demo_attendance.xlsx` | 397 synthetic student/subject attendance records |

The master workbook requires these headers: Departments (`code`, `name`); Majors (`code`, `name`, `department_code`); Subjects (`code`, `name`, `major_code`); Teachers (`name`, `email`, `department_code`, `available_shifts`); Rooms (`code`, `capacity`, `active`). Teacher shifts are comma-separated, for example `Morning,Afternoon`. Email may be blank; the other teacher columns are required. A legacy `max_sections` column is accepted but ignored. Invalid rows are shown with reasons and excluded from import. Existing records match by code, or teacher email/name and department, and are updated on confirmation.

The synthetic data intentionally produces: Software Engineering Morning 70 → 3 sections; combined CSE Morning demand across Software Engineering and Cybersecurity is 5 sections versus 2 active Morning teachers, a shortage of 3. Morning needs 6 shared rooms while 4 are active, so this shift exceeds room capacity. Software Engineering Afternoon has a teacher shortage, Business Administration Morning has a room-capacity limit, Business Administration Afternoon is near capacity, and English Evening has supported capacity. Database Systems is the weakest subject, and 12 students have at least one Critical attendance record. The precise results come from imported rows, not dashboard constants.

## Dependencies

- Python 3.12+
- Django 5.2
- pandas 2.x
- NumPy 2.x
- OpenPyXL 3.x
- Bootstrap 5, Bootstrap Icons, and Chart.js 4 (loaded by CDN)
- SQLite (included with Python)

## Excel formats

Only `.xlsx` files up to 10 MB are accepted. Downloadable starter templates are available on the Upload Data page.

| Dataset | Required columns | Optional columns |
|---|---|---|
| Enrollment | `student_id`, `student_name`, `department_code`, `major_code`, `shift` | `gender` |
| Performance | `student_id`, `subject_code`, `score` | — |
| Attendance | `student_id`, `subject_code`, `total_sessions`, `absent_count` | — |

Enrollment references must already exist in setup data. Performance and attendance require imported students and configured subjects. Every batch shows valid, duplicate, missing, invalid-reference, and rejected counts before confirmation. Invalid rows remain visible in the issue table and are never silently imported.

## Project structure

```text
university_portal/       Django settings and root URLs
analytics/               Models, forms, views, analytics/import services
  management/commands/   Demo workbook generator and legacy seed command
  migrations/            Database schema
  templatetags/           Presentation helpers
templates/               Reusable Django templates and dashboards
static/css/               Technical-grid dashboard design
static/js/                Chart.js configuration
manage.py                 Django command entry point
requirements.txt          Python dependencies
```

## Business rules implemented

- One email-based Admin / Data Analyst account type; all internal routes require login.
- Master-data CRUD for departments, majors, subjects, rooms, and teachers.
- Morning, Afternoon, and Evening shifts only.
- Required sections = `ceil(students / 25)`, grouped by major and shift.
- Each active teacher contributes one section of capacity in each selected shift, counted by department and shift. Teacher subjects can be selected only from that department, up to three per teacher. No timetable or individual assignment is inferred.
- Shared room demand is the sum of required sections across all majors in each shift. All active rooms count for each shift; rooms are never permanently assigned to majors. The portal compares shift demand with active rooms but never recommends building rooms.
- Supported remaining enrollment is current calculated section seats plus potential sections only when both a spare department/shift teacher and a spare shared room exist. Near Capacity means at most five supported seats remain; Full means none remain and another section is unsupported. Alternatives are scored for other shifts of the same major only.
- Section occupancy labels are Normal (0–19), Getting Full (20–22), Near Full (23–24), and Full (25).
- Pass threshold is 50. Grades and average grade points use the defined scale and are explicitly presented as simplified, not official GPA.
- Attendance status is based on attendance percentage: Good ≥85%, Warning ≥75%, High Risk ≥60%, Critical <60%.
- Dashboard values and insights come from database queries; no KPI values are hardcoded.

## Known Version 1 limitations

- One academic period (`2026 / Semester 1`) and no historical progression.
- Teacher capacity is a department/shift aggregate; it is not a timetable or optimization engine.
- Shared spare teacher and room capacity is a what-if scenario for each major, not a reservation; simultaneous recommendations are not additive. Room size is not used in the Version 1 shared-room count, which follows the university's active-room rule.
- Legacy `max_sections` and `assigned_sections` database columns are retained to avoid deleting existing data, but are hidden from the teacher form/list and ignored by analytics.
- The refreshed `demo_data/demo_master_data.xlsx` and downloadable workbook use the shift-based teacher format. Older master workbooks with a `max_sections` column remain importable; that column is ignored.
- Re-importing a valid student or student/subject record updates the existing record.
- Chart and UI libraries require internet access unless their CDN assets are vendored locally.
- SQLite and the development secret/debug settings are suitable for coursework/local use, not production deployment.

## Future improvements

- Add academic-period selection and historical trend analysis without student lifecycle automation.
- Add explicit section-to-teacher assignments for more precise workload utilization.
- Add downloadable issue reports and import rollback/audit tooling.
- Vendor front-end assets and add browser-based accessibility/visual regression tests.
- Move secrets to environment variables and use a production database/server for deployment.
