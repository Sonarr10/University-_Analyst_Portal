# Synthetic university demo datasets

These files are fictional teaching examples. They do not contain real student records.

## Good Data

The eight workbooks in `Good Data/` contain valid setup and analytics rows. Import them
in this order, reviewing and confirming each batch in the portal:

1. `department.xlsx`
2. `major.xlsx`
3. `subject.xlsx`
4. `teacher.xlsx`
5. `room.xlsx`
6. `enrollment.xlsx`
7. `performance.xlsx`
8. `attendance.xlsx`

The setup hierarchy is Science and Technology (Computer Science and Engineering,
Business Information Technology, Data Science), Languages (English, Chinese Language),
and Business (Business Administration, Marketing). Enrollment uses varied fictional
Cambodian-style names. Performance and Attendance use the same student IDs; student
names are resolved from Enrollment after import.

## Messy Data

The eight workbooks in `Messy Data/` are **new incoming batches**, not copies of
Good Data. Import Good Data first. Then validate Messy Data in the same order above,
review the row-level issues, and confirm only valid rows if you want to demonstrate
cleaning. Later messy analytics files reference the valid new enrollment IDs
`SHOW9001`–`SHOW9003`, so confirm valid messy Enrollment rows before validating
messy Performance and Attendance.

Intentional problems include conflicts with existing codes/IDs, duplicate rows,
missing fields, bad references, invalid shifts/booleans/numbers, and impossible
attendance counts. Some rows only need safe whitespace or casing cleanup and should
remain valid. A duplicate code with a different name is rejected, never treated as
a new department, major, subject, or room. Conflicting existing student and
student/subject records are likewise rejected rather than silently overwritten.

The generator changes files only; it does not modify the database.
