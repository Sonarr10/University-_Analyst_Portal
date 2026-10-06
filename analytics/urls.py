from django.contrib.auth import views as auth_views
from django.urls import path
from .forms import LoginForm
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html", authentication_form=LoginForm), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("insights/", views.insights, name="insights"),
    path("enrollment/", views.enrollment_dashboard, name="enrollment_dashboard"),
    path("performance/", views.performance_dashboard, name="performance_dashboard"),
    path("attendance/", views.attendance_dashboard, name="attendance_dashboard"),
    path("reports/analytics/", views.export_university_analytics, name="export_university_analytics"),
    path("reports/<str:dataset_type>/", views.export_analytics, name="export_analytics"),
    path("upload/", views.upload_data, name="upload_data"),
    path("setup/<str:kind>/import/", views.setup_import, name="setup_import"),
    path("setup/<str:kind>/template/", views.setup_template_download, name="setup_template"),
    path("demo/<str:dataset_type>/", views.download_demo, name="download_demo"),
    path("imports/<int:pk>/", views.import_review, name="import_review"),
    path("imports/<int:pk>/confirm/", views.import_confirm, name="import_confirm"),
    path("templates/<str:dataset_type>/", views.excel_template, name="excel_template"),
]

for kind, classes in {
    "department": (views.DepartmentList, views.DepartmentCreate, views.DepartmentUpdate, views.DepartmentDelete),
    "major": (views.MajorList, views.MajorCreate, views.MajorUpdate, views.MajorDelete),
    "subject": (views.SubjectList, views.SubjectCreate, views.SubjectUpdate, views.SubjectDelete),
    "teacher": (views.TeacherList, views.TeacherCreate, views.TeacherUpdate, views.TeacherDelete),
    "room": (views.RoomList, views.RoomCreate, views.RoomUpdate, views.RoomDelete),
}.items():
    urlpatterns += [
        path(f"setup/{kind}s/", classes[0].as_view(), name=f"{kind}_list"),
        path(f"setup/{kind}s/add/", classes[1].as_view(), name=f"{kind}_create"),
        path(f"setup/{kind}s/<int:pk>/edit/", classes[2].as_view(), name=f"{kind}_update"),
        path(f"setup/{kind}s/<int:pk>/delete/", classes[3].as_view(), name=f"{kind}_delete"),
    ]
