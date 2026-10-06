# University Data Analytics Portal

A Django Version 1 decision-support portal for university enrollment, capacity, academic performance, and attendance analysis. Its core workflow is: Excel upload → validation and cleaning → transformation → analysis → visualization → supported insight → management decision.

## Setup and run

Make sure **Python 3.12+** is installed.

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Windows

#### PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

If PowerShell prevents the virtual environment activation script from running, use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

#### Command Prompt (CMD)

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

> On some Windows installations, use `py` instead of `python`:
>
> ```powershell
> py -m venv .venv
> py manage.py migrate
> py manage.py runserver
> ```

### Open the portal

Open `http://127.0.0.1:8000/`, choose **Create an account**, and register with full name, email, and password. Passwords use Django's secure hashing; there is no preset password or public demo account.

### Verification

On Linux, macOS, or Windows:

```bash
python manage.py check
python manage.py test
```

### Generate demo files

To generate eight clean and eight intentionally messy workbooks without changing the database:

```bash
python manage.py generate_demo_files
```

This creates `demo_data/Good Data/`, `demo_data/Messy Data/`, and `demo_data/README.md`. Use `--force` only when you intentionally want to replace the 16 named workbooks. The obsolete root-level `demo_*.xlsx` files are removed; no combined master workbook is generated.

The older `seed_demo --students 220` command still exists, but it writes records directly into the database. Use the new workbook flow below when demonstrating validation and import.

## Teacher demo: 5–10 minutes

Start from an empty database. If this local database already contains records, make a backup and run `python manage.py flush` only if you intend to remove **all** records, including accounts; then register again. Do not run `seed_demo` before this walkthrough.

1. Register or sign in. Show the empty dashboard: zero students, teachers, and rooms, with “No Data” score and attendance cards.
2. Open **Departments → Add Department** and create `SCI` / `Science and Technology`. Open **Majors → Add Major** and create `CSE` / `Computer Science and Engineering` under `SCI`.
3. Open each setup list in order—**Departments**, **Majors**, **Subjects**, **Teachers**, **Rooms**—and import its matching workbook from `demo_data/Good Data/`. Review each preview and confirm valid rows. The manually created `SCI` and `CSE` rows are flagged as existing and skipped, never overwritten.
4. Upload `demo_data/Good Data/enrollment.xlsx` as **Enrollment**. Show its cleaning summary, confirm the import, then open **Enrollment & Capacity**. Point out 70 Computer Science and Engineering Morning students, three required sections, the shared Science and Technology Morning teacher shortage, shift-wide shared-room demand, and the supported Afternoon alternative.
5. Upload and confirm `demo_data/Good Data/performance.xlsx` as **Academic Performance**. Open **Performance** to show the weak Database Systems average and failure rate.
6. Upload and confirm `demo_data/Good Data/attendance.xlsx` as **Attendance**. Open **Attendance** to show risk groups and the attendance-versus-score scatter chart.
7. Return to **Dashboard** and walk through the management insights. Each number comes from the imported database records. Use **View details** to open the relevant analysis page.

On each analytics page, the Department, Major, and Shift filters work together and carry through to **Export Excel Report**. Each module workbook has a styled Overview, detail and insight sheets, and native Excel charts linked to numeric cells. Filtered enrollment reports label teacher supply as department-wide and shared-room supply as university-wide by shift; those resources are not counted independently for each major. The dashboard's “Last successful import” time comes from a confirmed import, not the current clock.

### Consolidated analytics workbook

Use **Export Analytics Excel** on the main Dashboard to download a current, university-wide `University_Analytics_Report_YYYY-MM-DD.xlsx` snapshot. It contains Dashboard, Enrollment, Performance, Attendance, and Capacity sheets. The Dashboard has native Excel charts for enrollment by department/major/shift, required sections by major/shift, average score by subject, pass/fail, and attendance risk. A hidden `_ChartData` sheet holds the real summarized cells those charts reference; unhide it to inspect or edit the chart source values in Excel. Charts for missing datasets are omitted cleanly. This consolidated report is separate from the existing filtered exports on individual analytics pages.

The generator writes separate Department, Major, Subject, Teacher, Room, Enrollment, Performance, and Attendance workbooks under both `Good Data/` and `Messy Data/`. The clean Enrollment workbook has 227 fictional students; clean Performance and Attendance each have 451 student/subject records. See [demo_data/README.md](demo_data/README.md) for the exact filenames, import order, and validation-demo guidance.

The synthetic setup hierarchy is: **Science and Technology** → Computer Science and Engineering, Business Information Technology, Data Science; **Languages** → English, Chinese Language; **Business** → Business Administration, Marketing. Setup templates include this hierarchy. Student IDs are unique, and names are generated deterministically from diverse Cambodian-style name combinations. Performance and Attendance files reference the same student IDs, so imported records and reports resolve to the Enrollment names.

Each setup list has **Add**, **Import Excel**, and **Download Template**. Individual import headers are: Department (`code`, `name`); Major (`code`, `name`, `department_code`); Subject (`code`, `name`, `major_code`); Teacher (`name`, `email`, `department_code`, `available_shifts`, `subjects_can_teach`, `active`); Room (`code`, `capacity`, `active`). Teacher shifts and subjects are comma-separated, for example `Morning,Afternoon` and `CSE101,CSE102`; at most three subjects are allowed, all in the selected department. Email and subject list may be blank. Import relationships must already exist in the database, so use the listed order. Duplicate or existing rows are reported and skipped; imports never overwrite records. The preview shows row-level reasons before confirmation.

### Module report workbooks

| Page | Workbook sheets | Native Excel charts |
|---|---|---|
| Enrollment & Capacity | Overview, Enrollment Data, Major & Shift Analysis, Capacity Analysis, Insights | Enrollment by department/major/shift, required sections by major/shift, department-shift demand vs active teachers, university-wide shared room demand vs active rooms |
| Performance | Overview, Student Performance, Subject Analysis, Grade Distribution, Insights | Average score by subject/major, pass vs fail, grade distribution, pass rate by subject |
| Attendance | Overview, Attendance Records, Subject Attendance, Risk Analysis, Attendance vs Performance, Insights | Risk distribution, attendance by subject/major, absences by subject, matched attendance-vs-score scatter |

Each workbook also contains a hidden `_ChartData` sheet with numeric source cells. Unhide it to inspect or edit chart source values in Excel. Missing datasets omit unsupported charts. Reports are read-only database snapshots and do not change imported records.

The synthetic data intentionally produces: Computer Science and Engineering Morning 70 → 3 sections; combined Science and Technology Morning demand across Computer Science and Engineering and Business Information Technology is 5 sections versus 2 active Morning teachers, a shortage of 3. Morning needs 6 shared rooms while 4 are active, so this shift exceeds room capacity. Computer Science and Engineering Afternoon has 28 supported seats available as an alternative, Business Administration Morning has a room-capacity limit, Business Administration Afternoon is near capacity, and English Evening has supported capacity. Database Systems is the weakest subject, and 15 students have at least one Critical attendance record. The precise results come from imported rows, not dashboard constants.

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

Enrollment references must already exist in setup data. Performance and attendance require imported students and configured subjects. Every batch shows total, valid, rejected, duplicate, missing, invalid-reference, and invalid-numeric row counts plus the valid-row percentage before confirmation. Invalid rows remain visible in the issue table and are never silently imported.

## Project structure

```text
university_portal/       Django settings and root URLs
analytics/               Models, forms, views, analytics/import services
  excel_export.py         Consolidated, native-chart Excel report builder
  module_reports.py       Three filtered, native-chart module report builders
  setup_import.py         Individual setup templates, validation, and import
  demo_names.py           Deterministic fictional Cambodian-style student names
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
- The old combined master-data importer and `demo_master_data.xlsx` output have been retired. Use the five individual setup workbooks.
- Exact matching re-imports are idempotent; conflicting existing student IDs and student/subject records are rejected during validation rather than silently overwritten.
- Chart and UI libraries require internet access unless their CDN assets are vendored locally.
- SQLite and the development secret/debug settings are suitable for coursework/local use, not production deployment.

## Future improvements

- Add academic-period selection and historical trend analysis without student lifecycle automation.
- Add richer validation issue downloads and import audit/rollback tooling while preserving the aggregate capacity model.
- Vendor front-end assets and add browser-based accessibility/visual regression tests.
- Move secrets to environment variables and use a production database/server for deployment.
