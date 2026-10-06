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


## Business rules implemented

- One email-based Admin / Data Analyst account type; all internal routes require login.
- Master-data CRUD for departments, majors, subjects, rooms, and teachers.
- Morning, Afternoon, and Evening shifts only.
- Required Class Groups = `ceil(students / 25)`, grouped by major and shift. This shows how many student groups are needed when each group supports a maximum of 25 students.
- Each active teacher contributes one class group of capacity in each selected shift, counted by department and shift. Teacher subjects can be selected only from that department, up to three per teacher. No timetable or individual assignment is inferred.
- Shared room demand is the sum of required class groups across all majors in each shift. All active rooms count for each shift; rooms are never permanently assigned to majors. The portal compares shift demand with active rooms but never recommends building rooms.
- Supported remaining enrollment is empty seats within current calculated groups plus potential group seats only when both a spare department/shift teacher and a spare shared room exist. Near Capacity means at most five supported seats remain; Full means none remain and another group is unsupported. Alternatives are scored for other shifts of the same major only.
- Calculated group occupancy labels are Normal (0–19), Getting Full (20–22), Near Full (23–24), and Full (25).
- Pass threshold is 50. Grades and average grade points use the defined scale and are explicitly presented as simplified, not official GPA.
- Attendance status is based on attendance percentage: Good ≥85%, Warning ≥75%, High Risk ≥60%, Critical <60%.
- Dashboard values and insights come from database queries; no KPI values are hardcoded.


## Future improvements

- Add academic-period selection and historical trend analysis without student lifecycle automation.
- Add richer validation issue downloads and import audit/rollback tooling while preserving the aggregate capacity model.
- Vendor front-end assets and add browser-based accessibility/visual regression tests.
- Move secrets to environment variables and use a production database/server for deployment.
