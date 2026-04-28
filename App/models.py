from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, role="employee", **extra_fields):
        if not email:
            raise ValueError("Email is required.")

        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Roles.HEAD_OFFICE_MANAGER)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class HeadOffice(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class User(AbstractBaseUser, PermissionsMixin):
    class Roles(models.TextChoices):
        HEAD_OFFICE_MANAGER = "head_office_manager", "Head Office Manager"
        BRANCH_MANAGER = "branch_manager", "Branch Manager"
        EMPLOYEE = "employee", "Employee"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=30, choices=Roles.choices, default=Roles.EMPLOYEE)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email


class Branch(models.Model):
    name = models.CharField(max_length=255)
    head_office = models.ForeignKey(
        HeadOffice,
        on_delete=models.CASCADE,
        related_name="branches",
    )
    manager = models.OneToOneField(
        "Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_branch",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("head_office", "name")

    def __str__(self):
        return self.name


class Employee(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="employee_profile",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="employees",
        null=True,
        blank=True,
    )
    is_head_office = models.BooleanField(default=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    hire_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["first_name", "last_name"]

    @property
    def role(self):
        return self.user.role

    @property
    def is_branch_manager(self):
        return self.user.role == User.Roles.BRANCH_MANAGER

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def clean(self):
        if self.user.role == User.Roles.HEAD_OFFICE_MANAGER and self.branch_id:
            raise ValidationError("Head office managers cannot belong to a branch.")

    def save(self, *args, **kwargs):
        self.is_head_office = self.user.role == User.Roles.HEAD_OFFICE_MANAGER
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name


class Device(models.Model):
    class Statuses(models.TextChoices):
        AVAILABLE = "available", "Available"
        NOT_AVAILABLE = "not_available", "Not Available"

    name = models.CharField(max_length=255)
    device_type = models.CharField(max_length=100)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        related_name="devices",
        null=True,
        blank=True,
    )
    serial_number = models.CharField(max_length=100, unique=True)
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Statuses.choices,
        default=Statuses.AVAILABLE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "serial_number"]

    def __str__(self):
        return f"{self.name} ({self.serial_number})"


class DeviceAssignment(models.Model):
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="device_assignments",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["device"],
                condition=Q(returned_at__isnull=True),
                name="unique_active_device_assignment",
            )
        ]

    @property
    def is_active(self):
        return self.returned_at is None

    def mark_returned(self):
        self.returned_at = timezone.now()

    def __str__(self):
        return f"{self.device.name} -> {self.employee.full_name}"


class Request(models.Model):
    class Statuses(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED_BY_BRANCH = "approved_by_branch", "Approved by Branch"
        REJECTED = "rejected", "Rejected"
        APPROVED_BY_HEAD_OFFICE = "approved_by_head_office", "Approved by Head Office"
        RESOLVED = "resolved", "Resolved"

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="requests",
    )
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="requests",
    )
    issue_description = models.TextField()
    status = models.CharField(
        max_length=30,
        choices=Statuses.choices,
        default=Statuses.PENDING,
    )
    branch_manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="branch_approved_requests",
    )
    head_office_manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headoffice_approved_requests",
    )
    rejection_reason = models.TextField(blank=True)
    resolution_notes = models.TextField(blank=True)
    approved_by_branch_at = models.DateTimeField(null=True, blank=True)
    approved_by_head_office_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def progress(self):
        flow = {
            self.Statuses.PENDING: 10,
            self.Statuses.APPROVED_BY_BRANCH: 40,
            self.Statuses.APPROVED_BY_HEAD_OFFICE: 70,
            self.Statuses.RESOLVED: 100,
            self.Statuses.REJECTED: 0,
        }
        return flow.get(self.status, 0)

    def __str__(self):
        return f"Request #{self.pk} - {self.status}"
