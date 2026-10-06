"""Explainable enrollment, teacher, and shared-room capacity scenarios."""

import math
from collections import defaultdict

from django.db.models import Count

from .models import Room, Shift, Student, Teacher


MAX_STUDENTS_PER_SECTION = 25


def required_sections(student_count):
    """Return the conceptual sections needed for this major and shift."""
    return math.ceil(student_count / MAX_STUDENTS_PER_SECTION)


def occupancy_status(students):
    if students == MAX_STUDENTS_PER_SECTION:
        return "Full"
    if students >= 23:
        return "Near Full"
    if students >= 20:
        return "Getting Full"
    return "Normal"


def section_occupancy(student_count):
    """Conceptual sections only; no students, rooms, or teachers are assigned."""
    sections = []
    for index in range(required_sections(student_count)):
        students = min(MAX_STUDENTS_PER_SECTION, student_count - index * MAX_STUDENTS_PER_SECTION)
        sections.append({
            "section": f"Section {chr(65 + index)}" if index < 26 else f"Section {index + 1}",
            "students": students,
            "maximum": MAX_STUDENTS_PER_SECTION,
            "remaining_seats": MAX_STUDENTS_PER_SECTION - students,
            "percentage": round(students / MAX_STUDENTS_PER_SECTION * 100),
            "status": occupancy_status(students),
        })
    return sections


def supported_remaining_seats(students, sections, department_required, teachers, shift_required, rooms):
    """Available seats for one scenario; shared spare resources are not reserved."""
    if department_required > teachers or shift_required > rooms:
        return 0, 0
    current_seats = sections * MAX_STUDENTS_PER_SECTION - students
    additional_sections = min(teachers - department_required, rooms - shift_required)
    return current_seats + additional_sections * MAX_STUDENTS_PER_SECTION, additional_sections


def capacity_status(remaining, teacher_shortage, room_shortage):
    if teacher_shortage and room_shortage:
        return "Over Capacity"
    if teacher_shortage:
        return "Teacher Shortage"
    if room_shortage:
        return "Room Capacity Limit"
    if remaining == 0:
        return "Full"
    if remaining <= 5:
        return "Near Capacity"
    return "Available"


def capacity_analysis():
    student_groups = list(
        Student.objects.values("major_id", "major__name", "major__department_id", "major__department__code", "shift")
        .annotate(students=Count("id"))
        .order_by("major__name", "shift")
    )
    teacher_capacity = defaultdict(int)
    for teacher in Teacher.objects.filter(active=True):
        for shift in set(teacher.available_shifts or []):
            if shift in Shift.values:
                teacher_capacity[(teacher.department_id, shift)] += 1

    department_required = defaultdict(int)
    shift_required = defaultdict(int)
    groups = []
    occupancy = []
    for group in student_groups:
        sections = section_occupancy(group["students"])
        department_key = (group["major__department_id"], group["shift"])
        department_required[department_key] += len(sections)
        shift_required[group["shift"]] += len(sections)
        for section in sections:
            occupancy.append({"major": group["major__name"], "shift": group["shift"], **section})
        groups.append({
            **group, "required": len(sections), "required_rooms": len(sections),
            "sections": sections,
        })

    active_rooms = Room.objects.filter(active=True).count()
    shift_pools = []
    for shift in Shift.values:
        used = shift_required[shift]
        shift_pools.append({
            "shift": shift, "required": used, "capacity": active_rooms,
            "remaining": max(active_rooms - used, 0),
            "shortage": max(used - active_rooms, 0),
            "status": "Room Capacity Limit" if used > active_rooms else "At Room Capacity" if used and used == active_rooms else "Available",
        })
    room_by_shift = {pool["shift"]: pool for pool in shift_pools}

    teacher_pools = []
    for (department_id, shift), required in sorted(department_required.items(), key=lambda item: (item[0][1], item[0][0])):
        sample = next(group for group in groups if group["major__department_id"] == department_id and group["shift"] == shift)
        available = teacher_capacity[(department_id, shift)]
        shortage = max(required - available, 0)
        teacher_pools.append({
            "department": sample["major__department__code"], "shift": shift,
            "required": required, "capacity": available,
            "shortage": shortage, "spare": max(available - required, 0),
            "status": "Teacher Shortage" if shortage else "At Capacity" if required == available else "Good",
        })

    pool_by_key = {(pool["department"], pool["shift"]): pool for pool in teacher_pools}
    for group in groups:
        pool = pool_by_key[(group["major__department__code"], group["shift"])]
        room_pool = room_by_shift[group["shift"]]
        remaining, additional_sections = supported_remaining_seats(
            group["students"], group["required"], pool["required"], pool["capacity"],
            room_pool["required"], room_pool["capacity"],
        )
        group["department_required"] = pool["required"]
        group["teacher_capacity"] = pool["capacity"]
        group["teacher_shortage"] = pool["shortage"]
        group["teacher_spare"] = pool["spare"]
        group["shift_rooms_available"] = room_pool["capacity"]
        group["shift_rooms_used"] = room_pool["required"]
        group["shift_rooms_remaining"] = room_pool["remaining"]
        group["room_shortage"] = room_pool["shortage"]
        group["current_supported_capacity"] = group["required"] * MAX_STUDENTS_PER_SECTION
        group["remaining_seats"] = group["current_supported_capacity"] - group["students"]
        group["supported_remaining_seats"] = remaining
        group["potential_additional_sections"] = additional_sections
        group["can_open_section"] = additional_sections > 0
        group["status"] = capacity_status(remaining, pool["shortage"], room_pool["shortage"])
        resource_notes = []
        if pool["shortage"]:
            resource_notes.append(f'{pool["shortage"]} additional active teacher(s) required in {group["major__department__code"]} {group["shift"]}.')
        if room_pool["shortage"]:
            resource_notes.append(f'{room_pool["shift"]} requires {room_pool["required"]} shared rooms; {room_pool["capacity"]} are active.')
        elif room_pool["remaining"] == 0:
            resource_notes.append("All available rooms are currently required for this shift.")
        group["resource_note"] = " ".join(resource_notes)

    # Evaluate every other shift for the same major, including shifts without enrollment.
    by_major_shift = {(group["major_id"], group["shift"]): group for group in groups}
    for group in groups:
        group["recommended_shift"] = None
        group["recommended_capacity"] = 0
        group["recommendation"] = ""
        if group["status"] == "Available":
            continue
        alternatives = []
        for shift in Shift.values:
            if shift == group["shift"]:
                continue
            target = by_major_shift.get((group["major_id"], shift))
            students = target["students"] if target else 0
            sections = required_sections(students)
            capacity, _ = supported_remaining_seats(
                students, sections,
                department_required[(group["major__department_id"], shift)],
                teacher_capacity[(group["major__department_id"], shift)],
                shift_required[shift], active_rooms,
            )
            if capacity > 0:
                alternatives.append((capacity, shift))
        if alternatives:
            capacity, shift = max(alternatives, key=lambda item: item[0])
            group["recommended_shift"] = shift
            group["recommended_capacity"] = capacity
            group["recommendation"] = f"Among other shifts, {shift} has the most supported enrollment capacity for {group['major__name']} ({capacity} seats)."
        else:
            group["recommendation"] = "No alternative shift currently has sufficient capacity."

    return {"groups": groups, "teacher_pools": teacher_pools, "shift_pools": shift_pools, "occupancy": occupancy}
