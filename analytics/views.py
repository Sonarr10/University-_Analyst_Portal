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
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from openpyxl import Workbook

from .forms import DepartmentForm, MajorForm, MasterUploadForm, RegisterForm, RoomForm, SubjectForm, TeacherForm, UploadForm
from .demo_workbooks import demo_workbooks
from .master_import import SHEETS, import_master_rows, validate_master_workbook
from .models import Attendance, Department, ImportBatch, Major, Performance, Room, Student, Subject, Teacher
from .services import capacity_rows, dashboard_context, import_rows, validate_workbook


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
    analysis = context["capacity_analysis"]
    rows = analysis["groups"]
    context.update({"page_title": "Enrollment & Capacity", "capacity_rows": rows,
                    "total_required": sum(row["required"] for row in rows),
                    "teacher_pools": analysis["teacher_pools"],
                    "shift_pools": analysis["shift_pools"],
                    "section_occupancy": analysis["occupancy"]})
    return render(request, "analytics/enrollment_dashboard.html", context)


@login_required
def performance_dashboard(request):
    records = Performance.objects.select_related("student", "subject")
    stats = records.aggregate(avg=Avg("score"), total=Count("id"), passed=Count("id", filter=Q(passed=True)))
    total = stats["total"] or 0
    subjects = list(records.values("subject__name").annotate(average=Avg("score"), total=Count("id"), failed=Count("id", filter=Q(passed=False))).order_by("subject__name"))
    grades = list(records.values("letter_grade").annotate(value=Count("id")).order_by("letter_grade"))
    context = {
        "has_data": bool(total), "average": round(float(stats["avg"]), 1) if stats["avg"] is not None else None,
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
    records = Attendance.objects.select_related("student", "subject")
    average = records.aggregate(v=Avg("attendance_percentage"))["v"]
    statuses = {name: records.filter(status=name).count() for name in ["Good", "Warning", "High Risk", "Critical"]}
    subjects = list(records.values("subject__name").annotate(average=Avg("attendance_percentage")).order_by("subject__name"))
    main = dashboard_context()
    context = {"has_data": records.exists(), "average": round(float(average), 1) if average is not None else None,
               "statuses": statuses, "low_attendance": records.exclude(status="Good").order_by("attendance_percentage")[:20],
               "subject_chart": {"labels": [x["subject__name"] for x in subjects], "values": [float(x["average"]) for x in subjects]},
               "status_chart": main["attendance_status"], "scatter": main["scatter"]}
    return render(request, "analytics/attendance_dashboard.html", context)


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
def import_master_data(request):
    form = MasterUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        file = form.cleaned_data["file"]
        try:
            summary, valid_rows, issues = validate_master_workbook(file)
        except ValueError as exc:
            form.add_error("file", str(exc))
        else:
            batch = ImportBatch.objects.create(
                dataset_type="master", filename=file.name, uploaded_by=request.user,
                summary=summary, valid_rows=valid_rows, issues=issues,
            )
            return redirect("import_review", pk=batch.pk)
    return render(request, "analytics/master_upload.html", {"form": form})


@login_required
def import_review(request, pk):
    batch = get_object_or_404(ImportBatch, pk=pk, uploaded_by=request.user)
    template = "analytics/master_import_review.html" if batch.dataset_type == "master" else "analytics/import_review.html"
    context = {"batch": batch}
    if batch.dataset_type == "master":
        context["master_summaries"] = [(name, batch.summary[name]) for name in SHEETS]
    return render(request, template, context)


@login_required
def import_confirm(request, pk):
    if request.method != "POST":
        return redirect("import_review", pk=pk)
    batch = get_object_or_404(ImportBatch, pk=pk, uploaded_by=request.user)
    if batch.imported_at:
        messages.info(request, "This batch has already been imported.")
    else:
        try:
            with transaction.atomic():
                if batch.dataset_type == "master":
                    created, updated = import_master_rows(batch.valid_rows)
                else:
                    created, updated = import_rows(batch)
                batch.imported_at = timezone.now()
                batch.save(update_fields=["imported_at"])
        except (ObjectDoesNotExist, IntegrityError, ValueError) as exc:
            messages.error(request, f"Import could not finish because setup data changed after validation: {exc}. Upload the workbook again.")
        else:
            if batch.dataset_type == "master":
                messages.success(request, f"Master data imported successfully. {created} created, {updated} updated, {batch.summary['rejected_rows']} rejected.")
            else:
                messages.success(request, f"Import complete: {created} created, {updated} updated, {batch.summary['rejected_rows']} rejected.")
    return redirect("import_review", pk=pk)


@login_required
def download_demo(request, dataset_type):
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
