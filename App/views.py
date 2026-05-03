import csv
import io
import zipfile
from xml.etree import ElementTree as ET

from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Branch, Device, DeviceAssignment, Employee, HeadOffice, Request, User, Notification
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
    NotificationSerializer,
    RegisterSerializer,
    RequestCreateSerializer,
    RequestDecisionSerializer,
    RequestSerializer,
    UserSerializer,
    UserUpdateSerializer,
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


def create_account_activity_notifications(actor_user, employee, title, message):
    recipients = {employee.user}
    actor_employee = AccessService.employee_for_user(actor_user)

    if actor_user and actor_user.is_authenticated:
        recipients.add(actor_user)

    if employee.branch and employee.branch.manager:
        recipients.add(employee.branch.manager.user)

    if actor_employee and actor_employee.branch and actor_employee.branch.manager:
        recipients.add(actor_employee.branch.manager.user)

    recipients.update(
        User.objects.filter(role=User.Roles.HEAD_OFFICE_MANAGER, is_active=True)
    )

    for recipient in recipients:
        Notification.objects.create(
            user=recipient,
            notification_type=Notification.NotificationTypes.SYSTEM_UPDATE,
            title=title,
            message=message,
            related_employee=employee,
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

        employee = Employee.objects.create(
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
        create_account_activity_notifications(
            request.user if request.user.is_authenticated else user,
            employee,
            "Account Created",
            f"Account created for {employee.full_name}.",
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

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        if request.method == "PATCH":
            serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(UserSerializer(request.user).data)
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
            Q(assign_to_all_branches=True) | Q(branch__head_office=head_office) | Q(branch__isnull=True)
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
        devices = Device.objects.select_related("branch", "branch__head_office").filter(
            Q(branch=branch) | Q(assign_to_all_branches=True)
        )
        serializer = DeviceSerializer(devices.distinct(), many=True)
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

        data = request.data.copy()
        if AccessService.is_branch_manager(request.user):
            data["branch"] = AccessService.manager_branch(request.user).id if AccessService.manager_branch(request.user) else None

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if AccessService.is_branch_manager(request.user):
            if payload["user"]["role"] != User.Roles.EMPLOYEE:
                return Response({"detail": "Branch managers can only create employee accounts."}, status=403)
            payload["branch"] = AccessService.manager_branch(request.user)

        instance = EmployeeService.create(payload)
        create_account_activity_notifications(
            request.user,
            instance,
            "Account Created",
            f"Account created for {instance.full_name}.",
        )
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
        create_account_activity_notifications(
            request.user,
            updated,
            "Account Updated",
            f"Account updated for {updated.full_name}.",
        )
        return Response(EmployeeSerializer(updated).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if AccessService.is_branch_manager(request.user) and instance.user.role != User.Roles.EMPLOYEE:
            return Response({"detail": "Branch managers can only delete employee accounts."}, status=403)
        create_account_activity_notifications(
            request.user,
            instance,
            "Account Removed",
            f"Account removed for {instance.full_name}.",
        )
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
            manager_branch = AccessService.manager_branch(user)
            queryset = queryset.filter(
                Q(branch=manager_branch)
                | Q(assign_to_all_branches=True)
                | Q(assignments__employee__branch=manager_branch, assignments__returned_at__isnull=True)
            )
        else:
            employee = AccessService.employee_for_user(user)
            queryset = queryset.filter(assignments__employee=employee, assignments__returned_at__isnull=True)

        branch_value = self.request.query_params.get("branch")
        device_type = self.request.query_params.get("device_type")

        if branch_value and AccessService.is_head_office_manager(user):
            queryset = queryset.filter(Q(branch_id=branch_value) | Q(assign_to_all_branches=True))
        if device_type:
            queryset = queryset.filter(device_type__iexact=device_type)

        return queryset.distinct()

    def create(self, request, *args, **kwargs):
        if AccessService.is_employee(request.user):
            return Response({"detail": "Employees cannot create devices."}, status=403)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if AccessService.is_branch_manager(request.user):
            payload["branch"] = AccessService.manager_branch(request.user)

        instance = DeviceService.create(payload)
        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if AccessService.is_employee(request.user):
            return Response({"detail": "Employees cannot update devices."}, status=403)
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

    @action(detail=False, methods=["get"], permission_classes=[IsHeadOfficeManager])
    def report(self, request):
        devices = self.filter_queryset(self.get_queryset())

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=asse_track_device_report.csv"

        writer = csv.writer(response)
        writer.writerow([
            "Device Name",
            "Serial Number",
            "Device Type",
            "Brand",
            "Model",
            "Branch",
            "Assigned Employee",
            "Assigned At",
            "Assignment Active",
        ])

        for device in devices:
            assignment = next((a for a in device.assignments.all() if a.returned_at is None), None)
            writer.writerow(
                [
                    device.name,
                    device.serial_number,
                    device.device_type,
                    device.brand,
                    device.model,
                    device.branch.name if device.branch else "Head Office",
                    assignment.employee.full_name if assignment else "",
                    assignment.assigned_at.isoformat() if assignment else "",
                    "Yes" if assignment else "No",
                ]
            )

        return response

    @action(detail=False, methods=["post"], permission_classes=[IsHeadOfficeManager])
    def bulk_register(self, request):
        upload_file = request.FILES.get("file")
        if not upload_file:
            return Response({"detail": "No file uploaded."}, status=400)

        file_name = upload_file.name.lower()
        if file_name.endswith(".csv"):
            content = io.TextIOWrapper(upload_file.file, encoding="utf-8", errors="replace")
            reader = csv.DictReader(content)
            rows = [row for row in reader]
        elif file_name.endswith(".xlsx"):
            rows = self._parse_xlsx(upload_file)
        else:
            return Response({"detail": "Unsupported file format. Upload a CSV or XLSX file."}, status=400)

        created = 0
        skipped = 0
        errors = []

        for index, row in enumerate(rows, start=1):
            if not row:
                continue

            serial_number = (row.get("serial_number") or row.get("Serial Number") or "").strip()
            name = (row.get("name") or row.get("Device Name") or "").strip()
            device_type = (row.get("device_type") or row.get("Device Type") or "").strip()
            brand = (row.get("brand") or row.get("Brand") or "").strip()
            model = (row.get("model") or row.get("Model") or "").strip()
            purchase_date = (row.get("purchase_date") or row.get("Purchase Date") or "").strip()
            branch_name = (row.get("branch") or row.get("Branch") or "").strip()
            assign_to_all_branches = str(row.get("assign_to_all_branches") or row.get("Assign To All Branches") or "").strip().lower() in ["true", "1", "yes"]

            if not serial_number or not name:
                skipped += 1
                errors.append(f"Row {index}: missing required device name or serial number.")
                continue

            if Device.objects.filter(serial_number=serial_number).exists():
                skipped += 1
                continue

            branch = None
            if branch_name:
                branch = Branch.objects.filter(name__iexact=branch_name).first()

            try:
                device = Device.objects.create(
                    name=name,
                    device_type=device_type or "Unknown",
                    serial_number=serial_number,
                    brand=brand,
                    model=model,
                    purchase_date=purchase_date or None,
                    branch=branch,
                    assign_to_all_branches=assign_to_all_branches,
                )
                created += 1
            except Exception as exc:
                skipped += 1
                errors.append(f"Row {index}: {str(exc)}")

        return Response(
            {
                "created": created,
                "skipped": skipped,
                "errors": errors,
            }
        )

    def _parse_xlsx(self, uploaded_file):
        workbook = zipfile.ZipFile(uploaded_file)
        shared_strings = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            for si in root.findall(".//a:si", namespace):
                texts = [t.text or "" for t in si.findall(".//a:t", namespace)]
                shared_strings.append("".join(texts))

        sheet_name = "xl/worksheets/sheet1.xml"
        if sheet_name not in workbook.namelist():
            raise ValueError("Workbook does not contain sheet1.xml.")

        sheet = ET.fromstring(workbook.read(sheet_name))
        namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        rows = []
        for row in sheet.findall(".//a:row", namespace):
            values = []
            for cell in row.findall("a:c", namespace):
                cell_type = cell.get("t")
                value_element = cell.find("a:v", namespace)
                if value_element is None:
                    values.append("")
                    continue
                raw = value_element.text or ""
                if cell_type == "s":
                    values.append(shared_strings[int(raw)])
                else:
                    values.append(raw)
            rows.append(values)

        if not rows:
            return []

        header = [str(header).strip().lower().replace(" ", "_") for header in rows[0]]
        return [dict(zip(header, row)) for row in rows[1:]]


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
        elif AccessService.is_head_office_manager(request.user):
            actor = AccessService.employee_for_user(request.user)
            if employee.user.role == User.Roles.HEAD_OFFICE_MANAGER and employee.pk != getattr(actor, "pk", None):
                return Response({"detail": "Head office managers can only assign devices to themselves or branch managers."}, status=403)
            if employee.user.role not in [User.Roles.HEAD_OFFICE_MANAGER, User.Roles.BRANCH_MANAGER]:
                return Response({"detail": "Head office managers can assign devices to branch managers or themselves."}, status=403)

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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = AccessService.employee_for_user(request.user)
        if not employee:
            return Response({"detail": "An employee profile is required to create requests."}, status=403)
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


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticatedAndActive]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).select_related(
            "related_device",
            "related_employee",
            "related_employee__user",
            "related_request",
        )

    def create(self, request, *args, **kwargs):
        return Response({"detail": "Notifications cannot be created directly."}, status=405)

    def update(self, request, *args, **kwargs):
        return Response({"detail": "Notifications cannot be edited directly."}, status=405)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Notifications cannot be edited directly."}, status=405)

    def destroy(self, request, *args, **kwargs):
        notification = self.get_object()
        if notification.user_id != request.user.id:
            return Response({"detail": "You can only delete your own notifications."}, status=403)
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        if notification.user_id != request.user.id:
            return Response({"detail": "You can only update your own notifications."}, status=403)
        notification.mark_as_read()
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"])
    def mark_all_as_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True,
            read_at=timezone.now(),
        )
        return Response({"detail": "All notifications marked as read."})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"unread_count": count})


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
  <div style="padding: 16px; background: #fff7d9; border-bottom: 1px solid #e2d2a0; font-family: Arial, sans-serif;">
    <strong>Demo login:</strong> admin@admin.com / Aa@2026123
    <div style="font-size: 0.9rem; margin-top: 4px; color: #4d4d4d;">Use POST <code>/api/auth/login/</code> to obtain a Bearer token, then authorize protected endpoints through Swagger UI.</div>
  </div>
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
    user = request.user
    dashboard_cards = []
    dashboard_activity = []

    if user.is_authenticated:
        unread_notifications = Notification.objects.filter(user=user, is_read=False).count()
        pending_request_statuses = [
            Request.Statuses.PENDING,
            Request.Statuses.APPROVED_BY_BRANCH,
            Request.Statuses.APPROVED_BY_HEAD_OFFICE,
        ]

        if AccessService.is_head_office_manager(user):
            dashboard_cards = [
                {"count": HeadOffice.objects.count(), "label": "Head Offices", "icon": "feather-home"},
                {"count": Branch.objects.count(), "label": "Branches", "icon": "feather-git-branch"},
                {"count": Device.objects.count(), "label": "Devices", "icon": "feather-monitor"},
                {"count": Request.objects.filter(status__in=pending_request_statuses).count(), "label": "Open Requests", "icon": "feather-alert-circle"},
                {"count": unread_notifications, "label": "Unread Notifications", "icon": "feather-bell"},
            ]
            recent_requests = (
                Request.objects.select_related("employee__user", "employee__branch", "device")
                .order_by("-created_at")[:5]
            )
            dashboard_activity = [
                {
                    "name": request_item.device.name if request_item.device else "Device Request",
                    "details": request_item.employee.full_name if request_item.employee else "Unknown employee",
                    "status": request_item.get_status_display(),
                    "updated": request_item.created_at,
                    "note": request_item.issue_description[:80] if request_item.issue_description else "",
                }
                for request_item in recent_requests
            ]
        elif AccessService.is_branch_manager(user):
            branch = AccessService.manager_branch(user)
            dashboard_cards = [
                {"count": Device.objects.filter(Q(assign_to_all_branches=True) | Q(branch=branch)).count(), "label": "Active Devices", "icon": "feather-monitor"},
                {"count": Request.objects.filter(employee__branch=branch, status__in=pending_request_statuses).count(), "label": "Open Requests", "icon": "feather-alert-circle"},
                {"count": Employee.objects.filter(branch=branch).count(), "label": "Team Members", "icon": "feather-users"},
                {"count": unread_notifications, "label": "Unread Notifications", "icon": "feather-bell"},
            ]
            recent_requests = (
                Request.objects.select_related("employee__user", "employee__branch", "device")
                .filter(employee__branch=branch)
                .order_by("-created_at")[:5]
            )
            dashboard_activity = [
                {
                    "name": request_item.device.name if request_item.device else "Device Request",
                    "details": request_item.employee.full_name if request_item.employee else "Unknown employee",
                    "status": request_item.get_status_display(),
                    "updated": request_item.created_at,
                    "note": request_item.issue_description[:80] if request_item.issue_description else "",
                }
                for request_item in recent_requests
            ]
        elif AccessService.is_employee(user):
            employee = AccessService.employee_for_user(user)
            dashboard_cards = [
                {"count": DeviceAssignment.objects.filter(employee=employee, returned_at__isnull=True).count(), "label": "Assigned Devices", "icon": "feather-layers"},
                {"count": Request.objects.filter(employee=employee).exclude(status=Request.Statuses.RESOLVED).count(), "label": "Open Requests", "icon": "feather-alert-circle"},
                {"count": Branch.objects.filter(manager=employee).count(), "label": "Branch Access", "icon": "feather-map-pin"},
                {"count": unread_notifications, "label": "Unread Notifications", "icon": "feather-bell"},
            ]
            recent_requests = (
                Request.objects.select_related("employee__user", "employee__branch", "device")
                .filter(employee=employee)
                .order_by("-created_at")[:5]
            )
            dashboard_activity = [
                {
                    "name": request_item.device.name if request_item.device else "Device Request",
                    "details": request_item.get_status_display(),
                    "status": request_item.get_status_display(),
                    "updated": request_item.created_at,
                    "note": request_item.issue_description[:80] if request_item.issue_description else "",
                }
                for request_item in recent_requests
            ]

    return render(request, "Index.html", {"dashboard_cards": dashboard_cards, "dashboard_activity": dashboard_activity})


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


def branch_manager_console(request):
    # This page is protected on the client side using JWT session data stored in localStorage.
    # The template initializes the branch manager console and the JS client enforces role access.
    return render(
        request,
        "BranchManager/dashboard.html",
        {
            "page_title": "Branch Manager Console",
            "current_app": "branch_manager",
            "overview": {
                "employees": 0,
                "devices": 0,
                "requests": 0,
                "pending_requests": 0,
            },
            "branch_record": {"name": "Your Branch"},
        },
    )


def employee_dashboard(request):
    return render(
        request,
        "Employee/dashboard.html",
        {
            "page_title": "Employee Dashboard",
            "current_app": "employee",
        },
    )


def profile_page(request):
    return render(request, "Profile.html", {"page_title": "Profile Details", "current_app": "profile"})


def account_settings_page(request):
    return render(request, "AccountSettings.html", {"page_title": "Account Settings", "current_app": "account_settings"})


def device_report_page(request):
    return render(request, "HeadOfficeManager/device-report.html", {"page_title": "Device Report", "current_app": "device_report"})


def register_devices_page(request):
    return render(request, "HeadOfficeManager/register-devices.html", {"page_title": "Register Devices", "current_app": "register_devices"})
