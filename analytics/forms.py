from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Department, Major, Room, Shift, Subject, Teacher, User


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                # Django applies widget attributes to the group container too.
                # Bootstrap's form-check-input would shrink that container to 1em.
                field.widget.attrs["class"] = "checkbox-choices"
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs.setdefault("class", "form-control")


class RegisterForm(StyledFormMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ("full_name", "email", "password1", "password2")


class LoginForm(StyledFormMixin, AuthenticationForm):
    username = forms.EmailField(label="Email")


class DepartmentForm(StyledFormMixin, forms.ModelForm):
    class Meta: model = Department; fields = ["code", "name"]


class MajorForm(StyledFormMixin, forms.ModelForm):
    class Meta: model = Major; fields = ["code", "name", "department"]


class SubjectForm(StyledFormMixin, forms.ModelForm):
    class Meta: model = Subject; fields = ["code", "name", "major"]


class RoomForm(StyledFormMixin, forms.ModelForm):
    class Meta: model = Room; fields = ["code", "capacity", "active"]


class TeacherForm(StyledFormMixin, forms.ModelForm):
    available_shifts = forms.MultipleChoiceField(choices=Shift.choices, widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = Teacher
        fields = ["name", "email", "department", "available_shifts", "subjects_can_teach", "active"]
        widgets = {"subjects_can_teach": forms.CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        subjects = Subject.objects.select_related("major").order_by("name", "code")
        self.subjects_by_department = {}
        for subject in subjects:
            self.subjects_by_department.setdefault(str(subject.major.department_id), []).append({
                "id": str(subject.pk), "label": f"{subject.name} ({subject.code})",
            })
        department_id = self.data.get(self.add_prefix("department")) if self.is_bound else self.initial.get("department")
        if not department_id and self.instance.pk:
            department_id = self.instance.department_id
        if isinstance(department_id, Department):
            department_id = department_id.pk
        if department_id and not str(department_id).isdigit():
            department_id = None
        self.fields["subjects_can_teach"].queryset = subjects.filter(major__department_id=department_id) if department_id else Subject.objects.none()
        self.fields["subjects_can_teach"].help_text = "Select up to 3 subjects."

    def clean_subjects_can_teach(self):
        subjects = self.cleaned_data["subjects_can_teach"]
        if len(subjects) > 3:
            raise forms.ValidationError("Select no more than 3 subjects.")
        return subjects

    def clean(self):
        cleaned = super().clean()
        department = cleaned.get("department")
        subjects = cleaned.get("subjects_can_teach")
        if department and subjects and any(subject.major.department_id != department.pk for subject in subjects):
            self.add_error("subjects_can_teach", "Subjects must belong to the selected department.")
        return cleaned


class UploadForm(StyledFormMixin, forms.Form):
    dataset_type = forms.ChoiceField(choices=[("enrollment", "Enrollment"), ("performance", "Academic Performance"), ("attendance", "Attendance")])
    file = forms.FileField(help_text="Only .xlsx files are accepted.")

    def clean_file(self):
        file = self.cleaned_data["file"]
        if not file.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Upload an Excel .xlsx file.")
        if file.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File size must be 10 MB or less.")
        return file


class SetupUploadForm(StyledFormMixin, forms.Form):
    file = forms.FileField(label="Setup Excel workbook", help_text="Upload a .xlsx file with this setup type's template columns (10 MB maximum).")

    def clean_file(self):
        file = self.cleaned_data["file"]
        if not file.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Upload an Excel .xlsx file.")
        if file.size > 10 * 1024 * 1024:
            raise forms.ValidationError("File size must be 10 MB or less.")
        return file
