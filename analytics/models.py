from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, username=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = models.CharField(max_length=254, unique=True, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    def save(self, *args, **kwargs):
        self.email = self.email.lower().strip()
        self.username = self.email
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.full_name


class Department(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    class Meta: ordering = ["code"]
    def __str__(self): return f"{self.code} — {self.name}"


class Major(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="majors")
    class Meta: ordering = ["code"]
    def __str__(self): return f"{self.code} — {self.name}"


class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    major = models.ForeignKey(Major, on_delete=models.PROTECT, related_name="subjects")
    class Meta: ordering = ["code"]
    def __str__(self): return f"{self.code} — {self.name}"


class Shift(models.TextChoices):
    MORNING = "Morning", "Morning"
    AFTERNOON = "Afternoon", "Afternoon"
    EVENING = "Evening", "Evening"


class Room(models.Model):
    code = models.CharField(max_length=30, unique=True)
    capacity = models.PositiveIntegerField()
    active = models.BooleanField(default=True)
    class Meta: ordering = ["code"]
    def __str__(self): return self.code


class Teacher(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="teachers")
    available_shifts = models.JSONField(default=list)
    subjects_can_teach = models.ManyToManyField(Subject, blank=True, related_name="teachers")
    # Legacy columns retained to preserve existing data; neither drives capacity.
    max_sections = models.PositiveIntegerField(default=1)
    assigned_sections = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    class Meta: ordering = ["name"]
    def __str__(self): return self.name


class Student(models.Model):
    student_id = models.CharField(max_length=30, unique=True)
    student_name = models.CharField(max_length=150)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="students")
    major = models.ForeignKey(Major, on_delete=models.PROTECT, related_name="students")
    shift = models.CharField(max_length=20, choices=Shift.choices)
    gender = models.CharField(max_length=30, blank=True)
    academic_period = models.CharField(max_length=50, default="2026 / Semester 1")
    class Meta: ordering = ["student_id"]
    def __str__(self): return f"{self.student_id} — {self.student_name}"


class Performance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="performances")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="performances")
    score = models.DecimalField(max_digits=5, decimal_places=2)
    letter_grade = models.CharField(max_length=2)
    grade_point = models.DecimalField(max_digits=2, decimal_places=1)
    passed = models.BooleanField()
    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "subject"], name="unique_student_subject_performance")]
    def __str__(self): return f"{self.student.student_id} / {self.subject.code}"


class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance_records")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="attendance_records")
    total_sessions = models.PositiveIntegerField()
    absent_count = models.PositiveIntegerField()
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=20)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "subject"], name="unique_student_subject_attendance")]
    def __str__(self): return f"{self.student.student_id} / {self.subject.code}"


class ImportBatch(models.Model):
    DATASET_CHOICES = [("master", "Master Data"), ("enrollment", "Enrollment"), ("performance", "Academic Performance"), ("attendance", "Attendance"),
                       ("department", "Departments"), ("major", "Majors"), ("subject", "Subjects"), ("teacher", "Teachers"), ("room", "Rooms")]
    dataset_type = models.CharField(max_length=20, choices=DATASET_CHOICES)
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    summary = models.JSONField(default=dict)
    valid_rows = models.JSONField(default=list)
    issues = models.JSONField(default=list)
    imported_at = models.DateTimeField(null=True, blank=True)
    class Meta: ordering = ["-uploaded_at"]
