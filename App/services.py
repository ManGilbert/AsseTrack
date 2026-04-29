from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Branch, Device, DeviceAssignment, Employee, HeadOffice, Request, User


class AccessService:
    @staticmethod
    def employee_for_user(user):
        return getattr(user, "employee_profile", None)

    @staticmethod
    def manager_branch(user):
        employee = AccessService.employee_for_user(user)
        return getattr(employee, "branch", None)

    @staticmethod
    def is_head_office_manager(user):
        return bool(user and user.is_authenticated and user.role == User.Roles.HEAD_OFFICE_MANAGER)

    @staticmethod
    def is_branch_manager(user):
        return bool(user and user.is_authenticated and user.role == User.Roles.BRANCH_MANAGER)

    @staticmethod
    def is_employee(user):
        return bool(user and user.is_authenticated and user.role == User.Roles.EMPLOYEE)

    @staticmethod
    def ensure_branch_scope(user, branch):
        if AccessService.is_head_office_manager(user):
            return
        if not AccessService.is_branch_manager(user):
            raise PermissionDenied("You do not have permission for this branch.")

        manager_branch = AccessService.manager_branch(user)
        if not manager_branch or manager_branch.pk != branch.pk:
            raise PermissionDenied("You can only manage your own branch.")

    @staticmethod
    def ensure_employee_scope(user, employee):
        if AccessService.is_head_office_manager(user):
            return
        if AccessService.is_branch_manager(user):
            manager_branch = AccessService.manager_branch(user)
            if employee.branch_id != getattr(manager_branch, "id", None):
                raise PermissionDenied("You can only manage employees in your branch.")
            return

        request_employee = AccessService.employee_for_user(user)
        if not request_employee or request_employee.pk != employee.pk:
            raise PermissionDenied("You can only access your own profile.")

    @staticmethod
    def ensure_device_scope(user, device):
        if AccessService.is_head_office_manager(user):
            return
        if AccessService.is_branch_manager(user):
            manager_branch = AccessService.manager_branch(user)
            if device.branch_id != getattr(manager_branch, "id", None):
                raise PermissionDenied("You can only manage devices in your branch.")
            return

        request_employee = AccessService.employee_for_user(user)
        if not request_employee:
            raise PermissionDenied("Employee profile is required.")

        has_device = device.assignments.filter(
            employee=request_employee,
            returned_at__isnull=True,
        ).exists()
        if not has_device:
            raise PermissionDenied("You can only access your assigned devices.")


class HeadOfficeService:
    @staticmethod
    def create(data):
        return HeadOffice.objects.create(**data)

    @staticmethod
    def update(instance, data):
        for field in ["name"]:
            if field in data:
                setattr(instance, field, data[field])
        instance.save()
        return instance

    @staticmethod
    def delete(instance):
        instance.delete()


class BranchService:
    @staticmethod
    def create(data):
        manager = data.pop("manager", None)
        branch = Branch.objects.create(**data)
        if manager:
            BranchService.assign_manager(branch, manager)
        return branch

    @staticmethod
    def update(instance, data):
        has_manager_field = "manager" in data
        manager = data.pop("manager", None) if has_manager_field else None
        for field in ["name", "head_office"]:
            if field in data:
                setattr(instance, field, data[field])
        instance.save()
        if has_manager_field:
            BranchService.assign_manager(instance, manager)
        return instance

    @staticmethod
    def assign_manager(branch, employee):
        if employee is None:
            branch.manager = None
            branch.save(update_fields=["manager"])
            return branch

        if employee.user.role != User.Roles.BRANCH_MANAGER:
            raise ValidationError("Assigned manager must have the branch_manager role.")
        if employee.branch_id and employee.branch_id != branch.pk:
            raise ValidationError("Branch manager must belong to the same branch.")

        employee.branch = branch
        employee.save(update_fields=["branch"])
        branch.manager = employee
        branch.save(update_fields=["manager"])
        return branch

    @staticmethod
    def delete(instance):
        instance.delete()


class EmployeeService:
    @staticmethod
    @transaction.atomic
    def create(data):
        user_data = data.pop("user")
        password = user_data.pop("password")
        user = User.objects.create_user(password=password, **user_data)
        employee = Employee(user=user, **data)
        employee.full_clean()
        employee.save()
        return employee

    @staticmethod
    @transaction.atomic
    def update(instance, data):
        user_data = data.pop("user", None)

        if user_data:
            password = user_data.pop("password", None)
            for field, value in user_data.items():
                setattr(instance.user, field, value)
            if password:
                instance.user.set_password(password)
            instance.user.save()

        for field, value in data.items():
            setattr(instance, field, value)

        instance.full_clean()
        instance.save()
        return instance

    @staticmethod
    def delete(instance):
        instance.user.delete()


class DeviceService:
    @staticmethod
    def create(data):
        return Device.objects.create(**data)

    @staticmethod
    def update(instance, data):
        for field, value in data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

    @staticmethod
    def set_status(instance, status_value):
        instance.status = status_value
        instance.save(update_fields=["status"])
        return instance


class DeviceAssignmentService:
    @staticmethod
    @transaction.atomic
    def assign_device(device, employee):
        if DeviceAssignment.objects.filter(device=device, returned_at__isnull=True).exists():
            raise ValidationError("This device is already assigned to another employee.")

        if employee.user.role == User.Roles.HEAD_OFFICE_MANAGER:
            raise ValidationError("Devices cannot be assigned to a head office manager profile.")
        if not employee.branch:
            raise ValidationError("Devices can only be assigned to employees who belong to a branch.")

        assignment = DeviceAssignment.objects.create(
            device=device,
            employee=employee,
            branch=employee.branch,
        )
        device.branch = employee.branch
        device.status = Device.Statuses.NOT_AVAILABLE
        device.save(update_fields=["branch", "status"])
        return assignment

    @staticmethod
    @transaction.atomic
    def return_device(assignment):
        if assignment.returned_at:
            raise ValidationError("This device assignment is already closed.")

        assignment.mark_returned()
        assignment.save(update_fields=["returned_at"])
        assignment.device.status = Device.Statuses.AVAILABLE
        assignment.device.save(update_fields=["status"])
        return assignment


class RequestService:
    @staticmethod
    def _ensure_device_belongs_to_employee(employee, device):
        has_active_assignment = DeviceAssignment.objects.filter(
            employee=employee,
            device=device,
            returned_at__isnull=True,
        ).exists()
        if not has_active_assignment:
            raise ValidationError("Employees can only create requests for their assigned devices.")

    @staticmethod
    @transaction.atomic
    def create_request(employee, device, issue_description):
        RequestService._ensure_device_belongs_to_employee(employee, device)
        return Request.objects.create(
            employee=employee,
            device=device,
            issue_description=issue_description,
        )

    @staticmethod
    @transaction.atomic
    def approve_by_branch(instance, manager):
        if manager is None:
            raise ValidationError("Branch manager profile is required for approval.")
        if instance.status != Request.Statuses.PENDING:
            raise ValidationError("Only pending requests can be approved by the branch manager.")
        if instance.employee.branch_id != manager.branch_id:
            raise PermissionDenied("You can only approve requests for your branch.")

        instance.status = Request.Statuses.APPROVED_BY_BRANCH
        instance.branch_manager = manager
        instance.approved_by_branch_at = timezone.now()
        instance.save(update_fields=["status", "branch_manager", "approved_by_branch_at", "updated_at"])
        return instance

    @staticmethod
    @transaction.atomic
    def approve_by_head_office(instance, manager):
        if manager is None:
            raise ValidationError("Head office manager profile is required for approval.")
        if instance.status != Request.Statuses.APPROVED_BY_BRANCH:
            raise ValidationError("Request must be approved by branch before head office approval.")

        instance.status = Request.Statuses.APPROVED_BY_HEAD_OFFICE
        instance.head_office_manager = manager
        instance.approved_by_head_office_at = timezone.now()
        instance.save(
            update_fields=["status", "head_office_manager", "approved_by_head_office_at", "updated_at"]
        )
        return instance

    @staticmethod
    @transaction.atomic
    def reject(instance, actor, reason=""):
        if actor is None:
            raise ValidationError("An employee profile is required to reject a request.")
        if instance.status in [Request.Statuses.RESOLVED, Request.Statuses.REJECTED]:
            raise ValidationError("Resolved or rejected requests cannot be rejected again.")

        instance.status = Request.Statuses.REJECTED
        instance.rejection_reason = reason or instance.rejection_reason
        instance.rejected_at = timezone.now()

        if actor.user.role == User.Roles.BRANCH_MANAGER:
            instance.branch_manager = actor
        elif actor.user.role == User.Roles.HEAD_OFFICE_MANAGER:
            instance.head_office_manager = actor

        instance.save(
            update_fields=[
                "status",
                "rejection_reason",
                "rejected_at",
                "branch_manager",
                "head_office_manager",
                "updated_at",
            ]
        )
        return instance

    @staticmethod
    @transaction.atomic
    def resolve(instance, notes=""):
        if instance.status != Request.Statuses.APPROVED_BY_HEAD_OFFICE:
            raise ValidationError("Only head-office-approved requests can be resolved.")

        instance.status = Request.Statuses.RESOLVED
        instance.resolution_notes = notes or instance.resolution_notes
        instance.resolved_at = timezone.now()
        instance.save(update_fields=["status", "resolution_notes", "resolved_at", "updated_at"])
        return instance


def validate_model(instance):
    try:
        instance.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict)
