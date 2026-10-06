from io import BytesIO

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.deletion import ProtectedError
from django.db.models import Avg, Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from openpyxl import Workbook

from .forms import DepartmentForm, MajorForm, RegisterForm, RoomForm, SetupUploadForm, SubjectForm, TeacherForm, UploadForm
from .demo_workbooks import demo_workbooks
from .excel_export import build_analytics_workbook
from .filters import analytics_filters, filter_capacity_rows, filter_students
from .master_import import SHEETS
from .setup_import import SETUP_SPECS, import_setup_rows, setup_template, validate_setup_workbook
from .models import Attendance, Department, ImportBatch, Major, Performance, Room, Student, Subject, Teacher
from .services import chart, dashboard_context, import_rows, matched_scatter, validate_workbook


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your analyst account is ready.")
        return redirect("dashboard")
    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard(request):
    return render(request, "analytics/dashboard.html", dashboard_context())


@login_required
def insights(request):
    return render(request, "analytics/insights.html", dashboard_context())


@login_required
def enrollment_dashboard(request):
    context = dashboard_context()
    selected, filter_context = analytics_filters(request)
    analysis = context["capacity_analysis"]
    rows = filter_capacity_rows(analysis["groups"], selected)
    students = filter_students(Student.objects.all(), selected)
    by_dept = students.values("department__code").annotate(value=Count("id")).order_by("department__code")
    by_major = students.values("major__name").annotate(value=Count("id")).order_by("major__name")
    by_shift = students.values("shift").annotate(value=Count("id")).order_by("shift")
    required_by_major = {}
    for row in rows:
        required_by_major[row["major__name"]] = required_by_major.get(row["major__name"], 0) + row["required"]
    pairs = {(row["major__department__code"], row["shift"]) for row in rows}
    teacher_pools = [pool for pool in analysis["teacher_pools"] if (pool["department"], pool["shift"]) in pairs]
    shifts = {row["shift"] for row in rows}
    shift_pools = [pool for pool in analysis["shift_pools"] if pool["shift"] in shifts]
    context.update(filter_context)
    context.update({"page_title": "Enrollment & Capacity", "capacity_rows": rows,
                    "has_any_data": context["has_data"], "has_data": bool(rows),
                    "filtered_students": students.count(),
                    "total_required": sum(row["required"] for row in rows),
                    "teacher_pools": teacher_pools,
                    "teacher_shortage_pools": [pool for pool in teacher_pools if pool["shortage"]],
                    "shift_pools": shift_pools,
                    "section_occupancy": [{"major": row["major__name"], "shift": row["shift"], **section}
                                          for row in rows for section in row["sections"]],
                    "enrollment_department": chart([row["department__code"] for row in by_dept], [row["value"] for row in by_dept]),
                    "enrollment_major": chart([row["major__name"] for row in by_major], [row["value"] for row in by_major]),
                    "enrollment_shift": chart([row["shift"] for row in by_shift], [row["value"] for row in by_shift]),
                    "required_major": chart(required_by_major.keys(), required_by_major.values()),
                    "capacity_chart": {"labels": [f'{pool["department"]} / {pool["shift"]}' for pool in teacher_pools],
                                       "required": [pool["required"] for pool in teacher_pools],
                                       "teachers": [pool["capacity"] for pool in teacher_pools]},
                    "room_chart": {"labels": [pool["shift"] for pool in shift_pools],
                                   "required": [pool["required"] for pool in shift_pools],
                                   "rooms": [pool["capacity"] for pool in shift_pools]}})
    return render(request, "analytics/enrollment_dashboard.html", context)


@login_required
def performance_dashboard(request):
    selected, filter_context = analytics_filters(request)
    records = filter_students(Performance.objects.select_related("student", "subject"), selected, "student__")
    stats = records.aggregate(avg=Avg("score"), total=Count("id"), passed=Count("id", filter=Q(passed=True)))
    total = stats["total"] or 0
    subjects = list(records.values("subject__name").annotate(average=Avg("score"), total=Count("id"), failed=Count("id", filter=Q(passed=False))).order_by("subject__name"))
    grades = list(records.values("letter_grade").annotate(value=Count("id")).order_by("letter_grade"))
    context = {
        **filter_context,
        "has_data": bool(total), "has_any_data": Performance.objects.exists(),
        "average": round(float(stats["avg"]), 1) if stats["avg"] is not None else None,
        "pass_rate": round((stats["passed"] or 0) / total * 100, 1) if total else None,
        "fail_rate": round((total - (stats["passed"] or 0)) / total * 100, 1) if total else None,
        "average_grade_point": records.aggregate(v=Avg("grade_point"))["v"],
        "subjects": subjects, "best": max(subjects, key=lambda x: x["average"]) if subjects else None,
        "weakest": min(subjects, key=lambda x: x["average"]) if subjects else None,
        "low_scores": records.filter(score__lt=50).order_by("score")[:20],
        "subject_chart": {"labels": [x["subject__name"] for x in subjects], "values": [float(x["average"]) for x in subjects]},
        "grade_chart": {"labels": [x["letter_grade"] for x in grades], "values": [x["value"] for x in grades]},
    }
    return render(request, "analytics/performance_dashboard.html", context)


@login_required
def attendance_dashboard(request):
    selected, filter_context = analytics_filters(request)
    records = filter_students(Attendance.objects.select_related("student", "subject"), selected, "student__")
    average = records.aggregate(v=Avg("attendance_percentage"))["v"]
    statuses = {name: records.filter(status=name).count() for name in ["Good", "Warning", "High Risk", "Critical"]}
    subjects = list(records.values("subject__name").annotate(average=Avg("attendance_percentage")).order_by("subject__name"))
    performance = filter_students(Performance.objects.select_related("student", "subject"), selected, "student__")
    scatter, _, _ = matched_scatter(performance, records)
    context = {**filter_context, "has_data": records.exists(), "has_any_data": Attendance.objects.exists(),
               "average": round(float(average), 1) if average is not None else None,
               "statuses": statuses,
               "low_attendance": records.exclude(status="Good").order_by(
                   "attendance_percentage", "student__student_id", "subject__code"
               ),
               "subject_chart": {"labels": [x["subject__name"] for x in subjects], "values": [float(x["average"]) for x in subjects]},
               "status_chart": chart(statuses.keys(), statuses.values()), "scatter": scatter}
    return render(request, "analytics/attendance_dashboard.html", context)


@login_required
def export_university_analytics(request):
    generated_at = timezone.localtime()
    workbook = build_analytics_workbook(generated_at)
    output = BytesIO()
    workbook.save(output)
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="University_Analytics_Report_{generated_at:%Y-%m-%d}.xlsx"'
    )
    return response


@login_required
def export_analytics(request, dataset_type):
    """Export the same filtered analytics shown on each module page."""
    if dataset_type not in {"enrollment", "performance", "attendance"}:
        raise Http404("Unknown report")
    selected, _ = analytics_filters(request)
    from .module_reports import build_module_report
    generated_at = timezone.localtime()
    workbook = build_module_report(dataset_type, selected, generated_at)
    output = BytesIO()
    workbook.save(output)
    response = HttpResponse(output.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    filenames = {"enrollment": "Enrollment_Capacity_Report", "performance": "Academic_Performance_Report", "attendance": "Attendance_Analytics_Report"}
    response["Content-Disposition"] = f'attachment; filename="{filenames[dataset_type]}_{generated_at:%Y-%m-%d}.xlsx"'
    return response


@login_required
def upload_data(request):
    selected_dataset = request.GET.get("dataset_type", "enrollment")
    if selected_dataset not in {"enrollment", "performance", "attendance"}:
        selected_dataset = "enrollment"
    form = UploadForm(request.POST or None, request.FILES or None, initial={"dataset_type": selected_dataset})
    if request.method == "POST" and form.is_valid():
        file = form.cleaned_data["file"]
        dataset_type = form.cleaned_data["dataset_type"]
        try:
            summary, valid_rows, issues = validate_workbook(file, dataset_type)
        except ValueError as exc:
            form.add_error("file", str(exc))
        else:
            batch = ImportBatch.objects.create(dataset_type=dataset_type, filename=file.name, uploaded_by=request.user,
                                               summary=summary, valid_rows=valid_rows, issues=issues)
            return redirect("import_review", pk=batch.pk)
    return render(request, "analytics/upload.html", {"form": form, "recent_batches": ImportBatch.objects.filter(uploaded_by=request.user)[:8]})


@login_required
def setup_import(request, kind):
    if kind not in SETUP_SPECS:
        raise Http404("Unknown setup dataset")
    form = SetupUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        file = form.cleaned_data["file"]
        try:
            summary, valid_rows, issues = validate_setup_workbook(file, kind)
        except ValueError as exc:
            form.add_error("file", str(exc))
        else:
            batch = ImportBatch.objects.create(
                dataset_type=kind, filename=file.name, uploaded_by=request.user,
                summary=summary, valid_rows=valid_rows, issues=issues,
            )
            return redirect("import_review", pk=batch.pk)
    return render(request, "analytics/setup_upload.html", {"form": form, "kind": kind, "title": kind.title()})


@login_required
def setup_template_download(request, kind):
    if kind not in SETUP_SPECS:
        raise Http404("Unknown setup dataset")
    response = HttpResponse(setup_template(kind), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{kind}_template.xlsx"'
    return response


@login_required
def import_review(request, pk):
    batch = get_object_or_404(ImportBatch, pk=pk, uploaded_by=request.user)
    template = "analytics/master_import_review.html" if batch.dataset_type == "master" else "analytics/import_review.html"
    summary = batch.summary
    total_rows = summary.get("total_rows")
    if total_rows is None and batch.dataset_type == "master":
        total_rows = sum(summary.get(name, {}).get("total", 0) for name in SHEETS)
    quality = {
        "total_rows": total_rows or 0,
        "valid_rows": summary.get("valid_rows", 0),
        "rejected_rows": summary.get("rejected_rows", 0),
        "duplicate_rows": summary.get("duplicate_rows"),
        "missing_value_rows": summary.get("missing_value_rows"),
        "invalid_references": summary.get("invalid_references"),
        "invalid_numeric_rows": summary.get("invalid_numeric_rows"),
    }
    quality["data_quality_percentage"] = round(quality["valid_rows"] / quality["total_rows"] * 100, 1) if quality["total_rows"] else None
    context = {"batch": batch, "quality": quality}
    if batch.dataset_type == "master":
        context["master_summaries"] = [(name, batch.summary[name]) for name in SHEETS]
    return render(request, template, context)


@login_required
def import_confirm(request, pk):
    if request.method != "POST":
        return redirect("import_review", pk=pk)
    batch = get_object_or_404(ImportBatch, pk=pk, uploaded_by=request.user)
    if batch.dataset_type == "master":
        messages.error(request, "The combined master-data importer has been retired. Use the individual setup imports instead.")
        return redirect("import_review", pk=pk)
    if batch.imported_at:
        messages.info(request, "This batch has already been imported.")
    else:
        try:
            with transaction.atomic():
                if batch.dataset_type in SETUP_SPECS:
                    created, updated = import_setup_rows(batch.dataset_type, batch.valid_rows)
                else:
                    created, updated = import_rows(batch)
                batch.imported_at = timezone.now()
                batch.save(update_fields=["imported_at"])
        except (ObjectDoesNotExist, IntegrityError, ValueError) as exc:
            messages.error(request, f"Import could not finish because setup data changed after validation: {exc}. Upload the workbook again.")
        else:
            messages.success(request, f"Import complete: {created} created, {updated} updated, {batch.summary['rejected_rows']} rejected.")
    return redirect("import_review", pk=pk)


@login_required
def download_demo(request, dataset_type):
    if dataset_type == "master":
        raise Http404("Combined setup import is no longer available")
    workbooks = demo_workbooks()
    if dataset_type not in workbooks:
        return redirect("upload_data")
    filename, payload = workbooks[dataset_type]
    response = HttpResponse(payload, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def excel_template(request, dataset_type):
    headers = {
        "enrollment": ["student_id", "student_name", "department_code", "major_code", "shift", "gender"],
        "performance": ["student_id", "subject_code", "score"],
        "attendance": ["student_id", "subject_code", "total_sessions", "absent_count"],
    }
    if dataset_type not in headers:
        return redirect("upload_data")
    workbook = Workbook(); sheet = workbook.active; sheet.title = dataset_type.title()
    sheet.append(headers[dataset_type])
    samples = {"enrollment": ["ST001", "Example Student", "CSE", "SE", "Morning", "Female"],
               "performance": ["ST001", "DB101", 78], "attendance": ["ST001", "DB101", 20, 2]}
    sheet.append(samples[dataset_type])
    output = BytesIO(); workbook.save(output); output.seek(0)
    response = HttpResponse(output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{dataset_type}_template.xlsx"'
    return response


class BaseListView(LoginRequiredMixin, ListView):
    template_name = "analytics/master_list.html"
    context_object_name = "objects"
    title = ""
    columns = []
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.kind == "teacher":
            return queryset.select_related("department").prefetch_related("subjects_can_teach")
        return queryset
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(title=self.title, columns=self.columns, create_url=self.create_url, kind=self.kind)
        return context


class BaseCreateView(LoginRequiredMixin, CreateView):
    template_name = "analytics/master_form.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs); context.update(title=f"Add {self.title}", list_url=self.success_url, kind=self.kind); return context
    def form_valid(self, form):
        messages.success(self.request, f"{self.title} created."); return super().form_valid(form)


class BaseUpdateView(LoginRequiredMixin, UpdateView):
    template_name = "analytics/master_form.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs); context.update(title=f"Edit {self.title}", list_url=self.success_url, kind=self.kind); return context
    def form_valid(self, form):
        messages.success(self.request, f"{self.title} updated."); return super().form_valid(form)


class BaseDeleteView(LoginRequiredMixin, DeleteView):
    template_name = "analytics/master_confirm_delete.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs); context.update(title=f"Delete {self.title}", list_url=self.success_url); return context
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, f"{self.title} cannot be deleted because analytics or setup data depends on it.")
            return redirect(self.success_url)
        messages.success(self.request, f"{self.title} deleted.")
        return response


def make_crud(model, form, title, kind, columns):
    url = reverse_lazy(f"{kind}_list")
    attrs = {"model": model, "title": title, "kind": kind, "columns": columns, "create_url": reverse_lazy(f"{kind}_create")}
    return (type(f"{title}List", (BaseListView,), attrs),
            type(f"{title}Create", (BaseCreateView,), {"model": model, "form_class": form, "title": title, "kind": kind, "success_url": url}),
            type(f"{title}Update", (BaseUpdateView,), {"model": model, "form_class": form, "title": title, "kind": kind, "success_url": url}),
            type(f"{title}Delete", (BaseDeleteView,), {"model": model, "title": title, "success_url": url}))


DepartmentList, DepartmentCreate, DepartmentUpdate, DepartmentDelete = make_crud(Department, DepartmentForm, "Department", "department", [("code", "Code"), ("name", "Name")])
MajorList, MajorCreate, MajorUpdate, MajorDelete = make_crud(Major, MajorForm, "Major", "major", [("code", "Code"), ("name", "Name"), ("department", "Department")])
SubjectList, SubjectCreate, SubjectUpdate, SubjectDelete = make_crud(Subject, SubjectForm, "Subject", "subject", [("code", "Code"), ("name", "Name"), ("major", "Major")])
RoomList, RoomCreate, RoomUpdate, RoomDelete = make_crud(Room, RoomForm, "Room", "room", [("code", "Code"), ("capacity", "Capacity"), ("active", "Active")])
TeacherList, TeacherCreate, TeacherUpdate, TeacherDelete = make_crud(Teacher, TeacherForm, "Teacher", "teacher", [])
