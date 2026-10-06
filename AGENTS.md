**# AGENTS.md**



**## Project Name**

University Data Analytics Portal



**## Project Purpose**



Build a Django web application for a **\*\*Data Analyst subject\*\***.



The main purpose is NOT to create a complete university management system.



The core purpose is:



**\*\*Upload Excel data -> validate and clean data -> analyze data -> visualize data -> generate useful insights for university management\*\***



The project should focus on:



1\. Enrollment & Capacity Analytics

2\. Academic Performance Analytics

3\. Attendance Analytics

4\. Teacher and Room Capacity Support



The system should feel like a real-world university decision-support dashboard.



**---**



**# 1. Important Project Rule**



Every major feature should follow:



**\*\*Question -> Analysis -> Visualization -> Insight -> Decision\*\***



Example:



Question:

Do we have enough capacity for Software Engineering students in the Morning shift?



Analysis:

\- Students = 82

\- Maximum = 25 students per section

\- Required sections = 4

\- Available teacher capacity = 3 sections



Visualization:

Required Sections vs Teacher Capacity



Insight:

Teacher capacity is short by 1 section.



Decision:

University management should review teacher allocation or add teaching capacity.



Do not create charts only for decoration.



**---**



**# 2. Technology Stack**



Use:



\- Python

\- Django

\- Django Templates

\- Django ORM

\- SQLite

\- Pandas

\- NumPy if useful

\- OpenPyXL

\- Chart.js

\- Bootstrap 5

\- Bootstrap Icons

\- HTML

\- CSS

\- JavaScript



Do NOT use for Version 1:



\- React

\- Next.js

\- Vue

\- Django REST Framework

\- Celery

\- Redis

\- Docker

\- Microservices

\- Apache Superset



Use Chart.js for data visualization.



**---**



**# 3. Authentication**



Use Django authentication.



Version 1 has only one user type:



**\*\*Admin / Data Analyst\*\***



The user can:



\- Register

\- Login

\- Logout

\- Manage university setup data

\- Upload Excel datasets

\- Review data-cleaning results

\- View dashboards

\- View warnings and insights



Account fields:



\- full_name

\- email

\- password



Requirements:



\- Password must use Django secure hashing

\- Never store plaintext passwords

\- All internal pages require login

\- Do not implement complex roles or RBAC in Version 1



**---**



**# 4. University Setup Data**



Small data should be entered directly through website forms.



**## Department**



Fields:



\- code

\- name



Example:



\- CSE

\- Computer Science and Engineering



**---**



**## Major**



Fields:



\- code

\- name

\- department



Relationship:



One Department -> Many Majors



Example:



Department:

Computer Science and Engineering



Majors:

\- Software Engineering

\- Cybersecurity

\- Data Science



**---**



**## Subject**



Fields:



\- code

\- name

\- major



For Version 1:



\- each subject belongs to one major

\- do not build a full curriculum management system



Subjects are mainly used for Performance and Attendance analysis.



**---**



**## Shift**



Use only:



\- Morning

\- Afternoon

\- Evening



Weekdays only.



Do not implement Weekend shift in Version 1.



**---**



**## Room**



Fields:



\- code or name

\- capacity

\- active



Version 1:



\- only one generic study-room type

\- do not implement room categories such as Lab, Lecture Hall, etc.



**---**



**## Teacher**



Fields:



\- name

\- email optional

\- department

\- available_shifts

\- subjects_can_teach

\- max_sections

\- active



Teacher workload:



\`workload_percentage = assigned_sections / max_sections \* 100\`



Version 1 simplification:



\- Do not calculate salary

\- Do not calculate exact teaching hours

\- Do not implement payroll

\- Do not implement full timetable generation

\- Do not implement advanced scheduling optimization



If teacher-subject matching becomes too complex, simplify teacher capacity analysis to:



\- department

\- shift

\- max_sections



**---**



**# 5. Excel Uploads**



Large university data should be uploaded using Excel.



Use:



\- Pandas

\- OpenPyXL



Accepted file type:



\`.xlsx\`



Main dataset types:



1\. Enrollment

2\. Academic Performance

3\. Attendance



Each upload should:



1\. Check required columns

2\. Validate rows

3\. Detect duplicate records

4\. Detect missing values

5\. Detect invalid references

6\. Clean safe data issues

7\. Reject invalid rows

8\. Show an import summary

9\. Import valid rows



Never silently hide errors.



**---**



**# 6. Enrollment Excel**



Expected columns:



\- student_id

\- student_name

\- department_code

\- major_code

\- shift



Optional:



\- gender



Version 1 uses only one academic period, for example:



**\*\*Academic Year 2026 / Semester 1\*\***



Do NOT implement:



\- automatic Year 1 -> Year 2 promotion

\- graduation workflow

\- student lifecycle management

\- historical multi-year progression



Validation rules:



\- student_id must exist

\- student_id cannot be duplicated in the same dataset

\- department_code must exist

\- major_code must exist

\- major must belong to department

\- shift must be Morning, Afternoon, or Evening

\- required fields cannot be empty



Show a cleaning summary:



\- Total rows

\- Valid rows

\- Duplicate rows

\- Missing values

\- Invalid department rows

\- Invalid major rows

\- Invalid shift rows

\- Rejected rows



Do not silently create unknown Departments or Majors.



**---**



**# 7. Enrollment & Capacity Analysis**



Maximum students per section:



\`25\`



Group students by:



\`major + shift\`



Example:



Software Engineering + Morning



Calculate:



\`required_sections = ceil(student_count / 25)\`



Examples:



\- 25 students -> 1 section

\- 26 students -> 2 sections

\- 58 students -> 3 sections

\- 73 students -> 3 sections



The system may create simple section grouping:



\- Section A

\- Section B

\- Section C



Example:



58 students:



\- Section A = 25

\- Section B = 25

\- Section C = 8



This is allowed.



Do NOT generate a complete weekly timetable.



Capacity analysis should compare:



\- number of students

\- required sections

\- available rooms

\- teacher capacity



Teacher capacity can be calculated using:



\- teacher department

\- teacher available shift

\- teacher max_sections



Generate useful alerts.



Examples:



"Software Engineering Morning requires 4 sections but teacher capacity supports only 3."



"Teacher capacity shortage: 1 section."



"Room capacity is sufficient."



"Room shortage detected."



Do not automatically reject enrollment.



This system provides analysis and recommendations.



**---**



**# 8. Academic Performance Excel**



Expected columns:



\- student_id

\- subject_code

\- score



Score range:



0-100



Validation:



\- student exists

\- subject exists

\- score is numeric

\- score is between 0 and 100



The system should derive:



\- Pass / Fail

\- Letter Grade

\- Grade Point

\- Optional Simplified GPA



Pass rule:



\`score >= 50 -> Pass\`



\`score < 50 -> Fail\`



Suggested grading:



\- 85-100 -> A -> 4.0

\- 80-84 -> B+ -> 3.5

\- 70-79 -> B -> 3.0

\- 65-69 -> C+ -> 2.5

\- 60-64 -> C -> 2.0

\- 50-59 -> D -> 1.0

\- Below 50 -> F -> 0.0



Important:



If Subjects do not have credit values, do not call the result official GPA.



Call it:



\- Simplified GPA

or

\- Average Grade Point



Raw Score remains the main performance metric.



**---**



**# 9. Attendance Excel**



Expected columns:



\- student_id

\- subject_code

\- total_sessions

\- absent_count



Validation:



\- student exists

\- subject exists

\- total_sessions > 0

\- absent_count >= 0

\- absent_count <= total_sessions



Calculate:



\`attendance_percentage = ((total_sessions - absent_count) / total_sessions) \* 100\`



Attendance status:



\- >= 85% -> Good

\- 75%-84.99% -> Warning

\- 60%-74.99% -> High Risk

\- < 60% -> Critical



Display:



\- attendance percentage

\- absence count

\- attendance status



Do not use only a fixed absence-count warning because different subjects may have different session counts.



**---**



**# 10. Data Analyst Requirements**



This project must clearly demonstrate Data Analyst skills.



Include:



\- Data collection/import

\- Data validation

\- Data cleaning

\- Data transformation

\- Descriptive statistics

\- KPI calculation

\- Comparative analysis

\- Relationship analysis

\- Visualization

\- Management insights



Do not build only CRUD pages.



**---**



**# 11. Dashboard**



The Main Dashboard should show important KPIs.



Suggested KPI cards:



\- Total Students

\- Total Teachers

\- Total Rooms

\- Total Departments

\- Total Majors

\- Average Score

\- Pass Rate

\- Average Attendance

\- Attendance Risk Count



Suggested charts:



\- Enrollment by Department

\- Enrollment by Major

\- Students by Shift

\- Required Sections by Major

\- Teacher Capacity vs Required Sections

\- Average Score by Subject

\- Pass vs Fail

\- Attendance Risk Distribution

\- Attendance vs Score



Insights section should show meaningful findings.



Examples:



"CSE Morning requires 4 sections but teacher capacity supports 3."



"Database Systems has the highest failure rate."



"18 students are in Critical Attendance status."



"Students with lower attendance generally show lower average scores."



Only show conclusions supported by actual data.



**---**



**# 12. Enrollment & Capacity Dashboard**



Show:



\- Students by Department

\- Students by Major

\- Students by Shift

\- Required Sections

\- Teacher Capacity

\- Room Capacity

\- Shortages

\- Utilization indicators



Recommended visuals:



\- Bar chart

\- Horizontal bar chart

\- KPI cards

\- Status table



**---**



**# 13. Performance Dashboard**



Show:



\- Average Score

\- Pass Rate

\- Fail Rate

\- Average Score by Subject

\- Highest Performing Subject

\- Lowest Performing Subject

\- Students with low scores

\- Grade distribution

\- Simplified GPA only if useful



**---**



**# 14. Attendance Dashboard**



Show:



\- Average Attendance

\- Good Attendance count

\- Warning count

\- High Risk count

\- Critical count

\- Attendance by Subject

\- Students with low attendance

\- Attendance vs Score scatter chart



**---**



**# 15. Data Cleaning UI**



Every uploaded Excel file should show a data-quality summary.



Example:



File:

\`enrollment_2026.xlsx\`



Summary:



\- Total Rows: 500

\- Valid Rows: 486

\- Duplicate Rows: 7

\- Missing Values: 5

\- Invalid References: 2



Actions:



\- View Issues

\- Import Valid Rows

\- Cancel



Do not hide problems.



**---**



**# 16. Empty Dashboard State**



When the database has no data, do not show meaningless empty charts.



Show onboarding steps:



1\. Add Departments

2\. Add Majors

3\. Add Subjects

4\. Add Teachers

5\. Add Rooms

6\. Confirm Shifts

7\. Upload Enrollment

8\. Upload Performance

9\. Upload Attendance



Buttons:



\- Start Setup

\- Upload Enrollment

\- Upload Performance

\- Upload Attendance



KPI values may show:



\- 0

\- No Data



**---**



**

# 17. UI / Design Style

## Design Goal

Use a **clean, modern university analytics dashboard** with a warm technical-grid background.

The reference image should influence mainly the **background feeling**, not the arcade/game styling.

The interface must feel:

- clean
- modern
- calm
- professional
- data-focused
- easy to read
- suitable for a university analytics system

Do NOT make the website colorful just for decoration.

Do NOT make it look like:
- an arcade website
- a gaming dashboard
- a neon interface
- a retro pixel UI

The design should prioritize **data readability**.

---

## Color System

Use a very small color palette.

### Main Colors

- Background: `#F3F0E8`
- Surface / Card: `#FFFDF8`
- Primary Blue: `#2563EB`
- Main Text: `#111827`
- Secondary Text: `#6B7280`
- Border: `#D8D4C8`

### Status Colors

Only use these when they communicate actual meaning:

- Success / Good: `#16A34A`
- Warning: `#D97706`
- Critical / Error: `#DC2626`

Do NOT use pink, purple, yellow, green, and red as decorative colors.

Blue should be the main interface and chart accent.

Status colors should appear only for:
- warnings
- errors
- success states
- attendance risk
- capacity alerts

---

## Background

Use a warm cream background inspired by the provided reference image.

Add a **very subtle graph-paper / technical-grid pattern**.

The grid must be soft enough that it never competes with tables or charts.

Use:

```css
body {
  background-color: #F3F0E8;

  background-image:
    linear-gradient(
      rgba(17, 24, 39, 0.04) 1px,
      transparent 1px
    ),
    linear-gradient(
      90deg,
      rgba(17, 24, 39, 0.04) 1px,
      transparent 1px
    );

  background-size: 28px 28px;

  color: #111827;
}
```

Important:

- Keep grid opacity low.
- Do not use a dark grid.
- Do not place charts directly on the page grid.
- Charts and tables must sit inside clean cards.

---

## Cards

Use simple, clean analytics cards.

Recommended style:

```css
.dashboard-card {
  background: #FFFDF8;
  border: 1px solid #D8D4C8;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(17, 24, 39, 0.05);
}
```

Avoid:
- heavy shadows
- glowing effects
- colorful gradients
- excessive rounded corners
- thick borders

Cards should feel quiet and professional.

---

## Sidebar

Use a simple sidebar.

Recommended:

- warm off-white or dark navy sidebar
- blue active item
- simple icons
- no colorful menu items
- clear section grouping

Navigation:

- Dashboard
- Upload Data
- Enrollment & Capacity
- Performance
- Attendance

Setup:
- Departments
- Majors
- Subjects
- Teachers
- Rooms

The active navigation item may use:
- blue text
- pale blue background
- small blue indicator

---

## Top Header

Keep the top header minimal.

Include:
- page title
- short subtitle if useful
- account/profile menu
- logout

Do not fill the header with unnecessary controls.

---

## Typography

Use a clean modern font.

Preferred:
- Inter
- Geist
- IBM Plex Sans

Use `IBM Plex Mono` only for small technical labels such as:

- `DATASET / ENROLLMENT`
- `2026 / SEMESTER 1`
- `STUDENT / ST001`

Do not use a pixel font.

Suggested hierarchy:

- Page Title: 28-32px, semibold
- Section Title: 18-22px, semibold
- KPI Value: 28-36px, bold
- Body: 14-16px
- Small Label: 12-13px

---

## Buttons

Use one main button style.

Primary button:
- blue background
- white text
- simple hover state

Secondary button:
- transparent or off-white
- thin border
- dark text

Danger button:
- red only for destructive actions

Avoid having many differently colored buttons.

---

## Tables

Tables should be simple and readable.

Use:
- clean white/off-white surface
- subtle row separators
- small status badges
- clear column labels
- enough spacing

Do not use strong alternating row colors.

Use blue only for links/actions.

---

## Data Visualization Design

Data visualization is a core part of this project.

Charts should feel consistent with the clean UI.

Use **blue as the default chart color**.

Use other colors only when they encode meaning.

Examples:

- Enrollment by Department -> blue bars
- Enrollment by Shift -> blue shades
- Average Score by Subject -> blue bars
- Pass vs Fail -> blue + muted gray
- Attendance Risk -> green / amber / red only because status meaning requires it
- Attendance vs Score -> blue scatter points

Avoid rainbow charts.

Avoid using a different bright color for every category.

Prefer:
- one main blue
- different blue opacity/shades
- neutral gray
- status colors only when necessary

Chart cards must have solid backgrounds so the technical page grid does not reduce readability.

Keep chart gridlines light.

Keep legends small.

Do not overload charts with labels.

---

## Dashboard Layout

Use a responsive dashboard layout:

- Left Sidebar
- Top Header
- Main Content Area

Main dashboard structure:

1. KPI overview cards
2. Enrollment & Capacity section
3. Academic Performance section
4. Attendance section
5. Management Insights / Alerts

Use enough whitespace.

Do not try to fill every empty space.

---

## KPI Cards

KPI cards should be minimal.

Example:

```text
TOTAL STUDENTS
1,284
```

Optional small context:

```text
ATTENDANCE RISK
18 students
```

Use the same card design for all KPI cards.

Do not assign a different color to every card.

---

## Alerts and Insights

Use color only when meaning is important.

Examples:

- Normal information -> blue or neutral
- Good -> green
- Warning -> amber
- Critical -> red

Example:

`Teacher capacity shortage: 1 section`

should use a warning style.

Do not make every insight visually loud.

---

## Empty State

The no-data screen should remain clean.

Use:
- simple icon
- short explanation
- setup checklist
- one or two main action buttons

Do not use a large illustration unless necessary.

---

## Responsive Design

Support:
- desktop
- tablet
- reasonable mobile behavior

Desktop is the primary target because analytics dashboards are easier to use on larger screens.

Sidebar may collapse on smaller screens.

Charts should resize responsively.

---

## Final Visual Rule

The overall visual direction is:

**Warm cream technical-grid background + clean off-white cards + dark text + one strong blue accent + minimal semantic status colors.**

The reference image is used mainly for its **warm background and subtle grid feeling**.

The rest of the interface must remain modern, clean, professional, and optimized for data visualization.