from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Branch, Device, DeviceAssignment, Employee, HeadOffice, Request, User
from .openapi import build_openapi_schema
from .permissions import (
    AssignmentAccessPermission,
    DeviceAccessPermission,
    EmployeeAccessPermission,
    IsAuthenticatedAndActive,
    IsBranchManager,
    IsEmployee,
    IsHeadOfficeManager,
    IsHeadOfficeOrBranchManager,
    RequestAccessPermission,
)
from .serializers import (
    AssignDeviceSerializer,
    BranchSerializer,
    DeviceAssignmentSerializer,
    DeviceSerializer,
    EmployeeSerializer,
    EmployeeWriteSerializer,
    HeadOfficeSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    RequestCreateSerializer,
    RequestDecisionSerializer,
    RequestSerializer,
    UserSerializer,
)
from .services import (
    AccessService,
    BranchService,
    DeviceAssignmentService,
    DeviceService,
    EmployeeService,
    HeadOfficeService,
    RequestService,
)


class AuthViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedAndActive]

    def get_permissions(self):
        if self.action in ["register", "login"]:
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=["post"])
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        role = validated["role"]
        user = User.objects.create_user(
            email=validated["email"],
            password=validated["password"],
            role=role,
            is_staff=(role == User.Roles.HEAD_OFFICE_MANAGER),
        )

        Employee.objects.create(
            user=user,
            branch=validated.get("branch"),
            head_office=validated.get("head_office"),
            first_name=validated["first_name"],
            last_name=validated["last_name"],
            phone=validated["phone"],
            position=validated["position"],
            department=validated["department"],
            hire_date=validated["hire_date"],
        )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Registration successful.",
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def login(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": f"Login successful as {user.role}.",
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )

    @action(detail=False, methods=["post"])
    def logout(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = RefreshToken(serializer.validated_data["refresh"])
        token.blacklist()
        return Response({"message": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(UserSerializer(request.user).data)

class HeadOfficeViewSet(viewsets.ModelViewSet):
    serializer_class = HeadOfficeSerializer
    permission_classes = [IsHeadOfficeManager]

    def get_queryset(self):
        return HeadOffice.objects.annotate(branch_count=Count("branches")).all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = HeadOfficeService.create(serializer.validated_data)
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        instance = HeadOfficeService.update(instance, serializer.validated_data)
        return Response(self.get_serializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        HeadOfficeService.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def branches(self, request, pk=None):
        head_office = self.get_object()
        serializer = BranchSerializer(head_office.branches.select_related("head_office", "manager").all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def devices(self, request, pk=None):
        head_office = self.get_object()
        devices = Device.objects.select_related("branch", "branch__head_office").filter(
            branch__head_office=head_office
        )
        serializer = DeviceSerializer(devices, many=True)
        return Response(serializer.data)


class BranchViewSet(viewsets.ModelViewSet):
    serializer_class = BranchSerializer
    permission_classes = [IsHeadOfficeOrBranchManager]

    def get_queryset(self):
        queryset = Branch.objects.select_related("head_office", "manager", "manager__user")
        if AccessService.is_branch_manager(self.request.user):
            branch = AccessService.manager_branch(self.request.user)
            return queryset.filter(pk=getattr(branch, "pk", None))
        return queryset

    def create(self, request, *args, **kwargs):
        if not AccessService.is_head_office_manager(request.user):
            return Response({"detail": "Only head office managers can create branches."}, status=403)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = BranchService.create(serializer.validated_data)
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if AccessService.is_branch_manager(request.user):
            return Response({"detail": "Branch managers cannot edit branch records."}, status=403)

        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        instance = BranchService.update(instance, serializer.validated_data)
        return Response(self.get_serializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if AccessService.is_branch_manager(request.user):
            return Response({"detail": "Branch managers cannot delete branches."}, status=403)
        BranchService.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOfficeManager])
    def assign_manager(self, request, pk=None):
        branch = self.get_object()
        manager_id = request.data.get("manager")
        manager = Employee.objects.select_related("user", "branch").filter(pk=manager_id).first() if manager_id else None
        if manager_id and manager is None:
            return Response({"detail": "Manager not found."}, status=404)
        branch = BranchService.assign_manager(branch, manager)
        return Response(self.get_serializer(branch).data)

    @action(detail=True, methods=["get"])
    def employees(self, request, pk=None):
        branch = self.get_object()
        employees = branch.employees.select_related("user", "branch", "branch__head_office").annotate(
            assigned_devices_count=Count("assignments", filter=Q(assignments__returned_at__isnull=True))
        )
        serializer = EmployeeSerializer(employees, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def devices(self, request, pk=None):
        branch = self.get_object()
        serializer = DeviceSerializer(branch.devices.select_related("branch", "branch__head_office").all(), many=True)
        return Response(serializer.data)


class EmployeeViewSet(viewsets.ModelViewSet):
    permission_classes = [EmployeeAccessPermission]

    def get_queryset(self):
        queryset = Employee.objects.select_related("user", "branch", "branch__head_office").annotate(
            assigned_devices_count=Count("assignments", filter=Q(assignments__returned_at__isnull=True))
        )
        user = self.request.user
        if AccessService.is_head_office_manager(user):
            return queryset
        if AccessService.is_branch_manager(user):
            branch = AccessService.manager_branch(user)
            return queryset.filter(branch=branch)

        employee = AccessService.employee_for_user(user)
        return queryset.filter(pk=getattr(employee, "pk", None))

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return EmployeeWriteSerializer
        return EmployeeSerializer

    def create(self, request, *args, **kwargs):
        if AccessService.is_employee(request.user):
            return Response({"detail": "Employees cannot create devices."}, status=403)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if AccessService.is_branch_manager(request.user):
            if payload["user"]["role"] != User.Roles.EMPLOYEE:
                return Response({"detail": "Branch managers can only create employee accounts."}, status=403)
            AccessService.ensure_branch_scope(request.user, payload["branch"])

        instance = EmployeeService.create(payload)
        return Response(EmployeeSerializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if AccessService.is_employee(request.user):
            return Response({"detail": "Employees cannot update devices."}, status=403)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if AccessService.is_branch_manager(request.user):
            if "user" in payload and payload["user"].get("role", instance.user.role) != User.Roles.EMPLOYEE:
                return Response({"detail": "Branch managers can only manage employee accounts."}, status=403)
            target_branch = payload.get("branch", instance.branch)
            AccessService.ensure_branch_scope(request.user, target_branch)

        updated = EmployeeService.update(instance, payload)
        return Response(EmployeeSerializer(updated).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if AccessService.is_branch_manager(request.user) and instance.user.role != User.Roles.EMPLOYEE:
            return Response({"detail": "Branch managers can only delete employee accounts."}, status=403)
        EmployeeService.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"])
    def profile(self, request):
        employee = AccessService.employee_for_user(request.user)
        if not employee:
            return Response({"detail": "No employee profile found for this account."}, status=404)
        return Response(EmployeeSerializer(employee).data)

    @action(detail=True, methods=["get"])
    def devices(self, request, pk=None):
        employee = self.get_object()
        assignments = DeviceAssignment.objects.select_related("device", "employee", "branch").filter(employee=employee)
        return Response(DeviceAssignmentSerializer(assignments, many=True).data)


class DeviceViewSet(viewsets.ModelViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [DeviceAccessPermission]

    def get_queryset(self):
        queryset = Device.objects.select_related("branch", "branch__head_office").prefetch_related(
            Prefetch(
                "assignments",
                queryset=DeviceAssignment.objects.select_related("employee").filter(returned_at__isnull=True),
            )
        )
        user = self.request.user

        if AccessService.is_head_office_manager(user):
            pass
        elif AccessService.is_branch_manager(user):
            queryset = queryset.filter(branch=AccessService.manager_branch(user))
        else:
            employee = AccessService.employee_for_user(user)
            queryset = queryset.filter(assignments__employee=employee, assignments__returned_at__isnull=True)

        status_value = self.request.query_params.get("status")
        branch_value = self.request.query_params.get("branch")
        device_type = self.request.query_params.get("device_type")

        if status_value:
            queryset = queryset.filter(status=status_value)
        if branch_value and AccessService.is_head_office_manager(user):
            queryset = queryset.filter(branch_id=branch_value)
        if device_type:
            queryset = queryset.filter(device_type__iexact=device_type)

        return queryset.distinct()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if AccessService.is_branch_manager(request.user):
            payload["branch"] = AccessService.manager_branch(request.user)

        instance = DeviceService.create(payload)
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if AccessService.is_branch_manager(request.user):
            payload["branch"] = AccessService.manager_branch(request.user)

        updated = DeviceService.update(instance, payload)
        return Response(self.get_serializer(updated).data)

    def destroy(self, request, *args, **kwargs):
        if AccessService.is_employee(request.user):
            return Response({"detail": "Employees cannot delete devices."}, status=403)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOfficeOrBranchManager])
    def mark_available(self, request, pk=None):
        device = self.get_object()
        if device.assignments.filter(returned_at__isnull=True).exists():
            return Response({"detail": "Device cannot be marked available while assignment is active."}, status=400)
        DeviceService.set_status(device, Device.Statuses.AVAILABLE)
        return Response(self.get_serializer(device).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOfficeOrBranchManager])
    def mark_not_available(self, request, pk=None):
        device = self.get_object()
        DeviceService.set_status(device, Device.Statuses.NOT_AVAILABLE)
        return Response(self.get_serializer(device).data)


class DeviceAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = DeviceAssignmentSerializer
    permission_classes = [AssignmentAccessPermission]

    def get_queryset(self):
        queryset = DeviceAssignment.objects.select_related(
            "device",
            "employee",
            "employee__user",
            "branch",
            "branch__head_office",
        )
        user = self.request.user
        if AccessService.is_head_office_manager(user):
            return queryset
        if AccessService.is_branch_manager(user):
            return queryset.filter(branch=AccessService.manager_branch(user))
        employee = AccessService.employee_for_user(user)
        return queryset.filter(employee=employee)

    def create(self, request, *args, **kwargs):
        if AccessService.is_employee(request.user):
            return Response({"detail": "Employees cannot assign devices."}, status=403)

        serializer = AssignDeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = serializer.validated_data["device"]
        employee = serializer.validated_data["employee"]

        if AccessService.is_branch_manager(request.user):
            AccessService.ensure_branch_scope(request.user, employee.branch)
            AccessService.ensure_device_scope(request.user, device)

        assignment = DeviceAssignmentService.assign_device(device, employee)
        return Response(self.get_serializer(assignment).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        return Response({"detail": "Assignments cannot be edited directly."}, status=405)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Assignments cannot be edited directly."}, status=405)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Assignments cannot be deleted directly."}, status=405)

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOfficeOrBranchManager])
    def return_device(self, request, pk=None):
        assignment = self.get_object()
        if AccessService.is_branch_manager(request.user):
            AccessService.ensure_branch_scope(request.user, assignment.branch)
        assignment = DeviceAssignmentService.return_device(assignment)
        return Response(self.get_serializer(assignment).data)


class RequestViewSet(viewsets.ModelViewSet):
    serializer_class = RequestSerializer
    permission_classes = [RequestAccessPermission]

    def get_queryset(self):
        queryset = Request.objects.select_related(
            "employee",
            "employee__user",
            "employee__branch",
            "employee__branch__head_office",
            "device",
            "device__branch",
            "branch_manager",
            "head_office_manager",
        )
        user = self.request.user
        if AccessService.is_head_office_manager(user):
            return queryset
        if AccessService.is_branch_manager(user):
            return queryset.filter(employee__branch=AccessService.manager_branch(user))
        employee = AccessService.employee_for_user(user)
        return queryset.filter(employee=employee)

    def get_serializer_class(self):
        if self.action == "create":
            return RequestCreateSerializer
        if self.action in ["reject", "resolve"]:
            return RequestDecisionSerializer
        return RequestSerializer

    def create(self, request, *args, **kwargs):
        if not AccessService.is_employee(request.user):
            return Response({"detail": "Only employees can create requests."}, status=403)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = AccessService.employee_for_user(request.user)
        req = RequestService.create_request(
            employee=employee,
            device=serializer.validated_data["device"],
            issue_description=serializer.validated_data["issue_description"],
        )
        return Response(RequestSerializer(req).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        return Response({"detail": "Requests must be managed through workflow actions."}, status=405)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Requests must be managed through workflow actions."}, status=405)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Requests cannot be deleted directly."}, status=405)

    @action(detail=True, methods=["post"], permission_classes=[IsBranchManager])
    def approve_branch(self, request, pk=None):
        req = self.get_object()
        manager = AccessService.employee_for_user(request.user)
        req = RequestService.approve_by_branch(req, manager)
        return Response(RequestSerializer(req).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOfficeManager])
    def approve_head_office(self, request, pk=None):
        req = self.get_object()
        manager = AccessService.employee_for_user(request.user)
        req = RequestService.approve_by_head_office(req, manager)
        return Response(RequestSerializer(req).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOfficeOrBranchManager])
    def reject(self, request, pk=None):
        req = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        actor = AccessService.employee_for_user(request.user)
        if AccessService.is_branch_manager(request.user):
            AccessService.ensure_branch_scope(request.user, req.employee.branch)

        req = RequestService.reject(req, actor=actor, reason=serializer.validated_data.get("reason", ""))
        return Response(RequestSerializer(req).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHeadOfficeManager])
    def resolve(self, request, pk=None):
        req = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = RequestService.resolve(req, notes=serializer.validated_data.get("notes", ""))
        return Response(RequestSerializer(req).data)

    @action(detail=True, methods=["get"])
    def progress(self, request, pk=None):
        req = self.get_object()
        return Response(
            {
                "request_id": req.id,
                "status": req.status,
                "progress_percentage": req.progress(),
            }
        )


def openapi_schema_view(request):
    return JsonResponse(build_openapi_schema())


def swagger_ui_view(request):
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AsseTrack API Docs</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
  <style>
    body { margin: 0; background: #f5f7fb; }
    .topbar { display: none; }
    .swagger-ui .info { margin: 24px 0; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = function() {
      window.ui = SwaggerUIBundle({
        url: '/api/docs/openapi.json',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        layout: "BaseLayout",
        persistAuthorization: true,
        docExpansion: "list",
        displayRequestDuration: true,
      });
    };
  </script>
</body>
</html>
"""
    return HttpResponse(html)


from django.shortcuts import render, redirect, get_object_or_404

def index(request):
    return render(request, "Index.html")


def login_page(request):
    return render(request, "Auth/login.html")


def head_office_console(request):
    pending_request_statuses = [
        Request.Statuses.APPROVED_BY_BRANCH,
        Request.Statuses.APPROVED_BY_HEAD_OFFICE,
    ]
    head_office_records = HeadOffice.objects.annotate(branch_count=Count("branches")).order_by("-created_at")
    manager_records = (
        Employee.objects.select_related("user", "head_office")
        .filter(user__role=User.Roles.HEAD_OFFICE_MANAGER)
        .order_by("-created_at")
    )

    return render(
        request,
        "HeadOfficeManager/dashboard.html",
        {
            "page_title": "Head Office Manager Console",
            "current_app": "head_office",
            "overview": {
                "head_offices": HeadOffice.objects.count(),
                "managers": Employee.objects.filter(user__role=User.Roles.HEAD_OFFICE_MANAGER).count(),
                "branches": Branch.objects.count(),
                "devices": Device.objects.count(),
                "requests": Request.objects.count(),
                "pending_requests": Request.objects.filter(status__in=pending_request_statuses).count(),
            },
            "head_office_records": head_office_records,
            "manager_records": manager_records,
        },
    )
