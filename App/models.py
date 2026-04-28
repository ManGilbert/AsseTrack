from django.db import models
from django.contrib.auth.hashers import make_password, check_password

# =========================
# HEAD OFFICE
# =========================
class HeadOffice(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# =========================
# USER
# =========================
class User(models.Model):
    ROLE_CHOICES = (
        ('head_office', 'Head Office Manager'),
        ('branch_manager', 'Branch Manager'),
        ('employee', 'Employee'),
    )

    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def save(self, *args, **kwargs):
        # ONLY hash if password is not already hashed
        if self.password and not self.password.startswith("pbkdf2_"):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


# =========================
# BRANCH
# =========================
class Branch(models.Model):
    name = models.CharField(max_length=255)

    head_office = models.ForeignKey(
        HeadOffice,
        on_delete=models.CASCADE,
        related_name='branches'
    )

    manager = models.OneToOneField(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_branch'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# =========================
# EMPLOYEE
# =========================
class Employee(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='employee_profile'
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='employees',
        null=True,
        blank=True
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

    # ROLE HELPERS
    @property
    def role(self):
        return self.user.role

    @property
    def is_branch_manager(self):
        return self.user.role == 'branch_manager'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# =========================
# DEVICE
# =========================
class Device(models.Model):
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('not_available', 'Not Available'),
    )

    name = models.CharField(max_length=255)
    device_type = models.CharField(max_length=100)

    serial_number = models.CharField(max_length=100, unique=True)
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)

    purchase_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.serial_number})"


# =========================
# DEVICE ASSIGNMENT
# =========================
class DeviceAssignment(models.Model):
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='assignments'
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='assignments'
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    assigned_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['device'],
                condition=models.Q(returned_at__isnull=True),
                name='unique_active_device_assignment'
            )
        ]

    def save(self, *args, **kwargs):
        self.device.status = 'not_available'
        self.device.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.device.status = 'available'
        self.device.save()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.device.name} -> {self.employee.first_name}"


# =========================
# REQUEST
# =========================
class Request(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved_by_branch', 'Approved by Branch'),
        ('rejected', 'Rejected'),
        ('approved_by_head_office', 'Approved by Head Office'),
        ('resolved', 'Resolved'),
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='requests'
    )

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='requests'
    )

    issue_description = models.TextField()

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending'
    )

    branch_manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='branch_approved_requests'
    )

    head_office_manager = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headoffice_approved_requests'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # PROGRESS
    def progress(self):
        flow = {
            'pending': 10,
            'approved_by_branch': 40,
            'approved_by_head_office': 70,
            'resolved': 100,
            'rejected': 0
        }
        return flow.get(self.status, 0)

    def __str__(self):
        return f"Request #{self.id} - {self.status}"