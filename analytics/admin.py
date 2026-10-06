from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import TeacherForm
from .models import Attendance, Department, ImportBatch, Major, Performance, Room, Student, Subject, Teacher, User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    ordering = ("email",)
    list_display = ("email", "full_name", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("Profile", {"fields": ("full_name",)}),)

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    form = TeacherForm
    fields = ("name", "email", "department", "available_shifts", "subjects_can_teach", "active")
    list_display = ("name", "department", "active")
    list_filter = ("department", "active")


admin.site.register([Department, Major, Subject, Room, Student, Performance, Attendance, ImportBatch])
