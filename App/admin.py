from django.contrib import admin
from .models import (
    HeadOffice, User, Branch,
    Employee, Device, DeviceAssignment, Request
)

# =========================
# HEAD OFFICE
# =========================
@admin.register(HeadOffice)
class HeadOfficeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)


# =========================
# USER
# =========================
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('email',)
    readonly_fields = ('created_at',)


# =========================
# EMPLOYEE INLINE (for Branch)
# =========================
class EmployeeInline(admin.TabularInline):
    model = Employee
    extra = 0


# =========================
# BRANCH
# =========================
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'head_office', 'manager', 'created_at')
    list_filter = ('head_office',)
    search_fields = ('name',)
    inlines = [EmployeeInline]


# =========================
# EMPLOYEE
# =========================
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'first_name', 'last_name', 'user',
        'branch', 'position', 'department',
        'is_active', 'created_at'
    )
    list_filter = ('branch', 'department', 'is_active')
    search_fields = ('first_name', 'last_name', 'user__email', 'phone')
    readonly_fields = ('created_at',)


# =========================
# DEVICE
# =========================
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'device_type',
        'serial_number', 'brand',
        'status', 'created_at'
    )
    list_filter = ('status', 'device_type', 'brand')
    search_fields = ('name', 'serial_number', 'brand', 'model')
    readonly_fields = ('created_at',)


# =========================
# DEVICE ASSIGNMENT
# =========================
@admin.register(DeviceAssignment)
class DeviceAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'device', 'employee',
        'branch', 'assigned_at', 'returned_at'
    )
    list_filter = ('branch', 'assigned_at', 'returned_at')
    search_fields = (
        'device__name',
        'employee__first_name',
        'employee__last_name'
    )
    readonly_fields = ('assigned_at',)


# =========================
# REQUEST
# =========================
@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'employee', 'device',
        'status', 'branch_manager',
        'head_office_manager',
        'created_at'
    )
    list_filter = ('status', 'created_at')
    search_fields = (
        'employee__first_name',
        'employee__last_name',
        'device__name'
    )
    readonly_fields = ('created_at', 'updated_at')

    def progress_percentage(self, obj):
        return f"{obj.progress()}%"
    progress_percentage.short_description = "Progress"