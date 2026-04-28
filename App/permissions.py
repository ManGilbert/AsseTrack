from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import User
from .services import AccessService


class IsAuthenticatedAndActive(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class IsHeadOfficeManager(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Roles.HEAD_OFFICE_MANAGER
        )


class IsBranchManager(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Roles.BRANCH_MANAGER
        )


class IsEmployee(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role == User.Roles.EMPLOYEE
        )


class IsHeadOfficeOrBranchManager(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in [User.Roles.HEAD_OFFICE_MANAGER, User.Roles.BRANCH_MANAGER]
        )


class EmployeeAccessPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        AccessService.ensure_employee_scope(request.user, obj)
        return True


class DeviceAccessPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        AccessService.ensure_device_scope(request.user, obj)
        return True


class RequestAccessPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.role == User.Roles.HEAD_OFFICE_MANAGER:
            return True
        if request.user.role == User.Roles.BRANCH_MANAGER:
            manager_branch = AccessService.manager_branch(request.user)
            return obj.employee.branch_id == getattr(manager_branch, "id", None)
        request_employee = AccessService.employee_for_user(request.user)
        return request_employee and obj.employee_id == request_employee.id


class AssignmentAccessPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.role == User.Roles.HEAD_OFFICE_MANAGER:
            return True
        if request.user.role == User.Roles.BRANCH_MANAGER:
            manager_branch = AccessService.manager_branch(request.user)
            return obj.branch_id == getattr(manager_branch, "id", None)
        request_employee = AccessService.employee_for_user(request.user)
        return request_employee and obj.employee_id == request_employee.id


class ReadOnlyForEmployees(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in [User.Roles.HEAD_OFFICE_MANAGER, User.Roles.BRANCH_MANAGER]
        )
