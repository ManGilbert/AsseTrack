from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Branch, Device, DeviceAssignment, Employee, HeadOffice, Request, User, Notification


class SimpleHeadOfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeadOffice
        fields = ["id", "name"]


class SimpleBranchSerializer(serializers.ModelSerializer):
    head_office = SimpleHeadOfficeSerializer(read_only=True)

    class Meta:
        model = Branch
        fields = ["id", "name", "head_office"]


class SimpleEmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "full_name",
            "first_name",
            "last_name",
            "branch",
            "head_office",
            "position",
            "department",
        ]


class UserSerializer(serializers.ModelSerializer):
    employee = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "role", "is_active", "created_at", "employee"]

    def get_employee(self, obj):
        employee = getattr(obj, "employee_profile", None)
        if not employee:
            return None
        return {
            "id": employee.id,
            "full_name": employee.full_name,
            "branch_id": employee.branch_id,
            "branch_name": employee.branch.name if employee.branch_id else None,
            "head_office_id": employee.head_office_id,
            "head_office_name": employee.head_office.name if employee.head_office_id else None,
            "position": employee.position,
        }


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=User.Roles.choices)
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    phone = serializers.CharField(max_length=20, required=False)
    position = serializers.CharField(max_length=100, required=False)
    department = serializers.CharField(max_length=100, required=False)
    hire_date = serializers.DateField(required=False)
    branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),
        allow_null=True,
        required=False,
    )
    head_office = serializers.PrimaryKeyRelatedField(
        queryset=HeadOffice.objects.all(),
        allow_null=True,
        required=False,
    )

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        role = attrs["role"]
        required_profile_fields = ["first_name", "last_name", "phone", "position", "department", "hire_date"]

        if User.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})

        missing_fields = [field for field in required_profile_fields if not attrs.get(field)]
        if missing_fields:
            raise serializers.ValidationError(
                {field: "This field is required for registration." for field in missing_fields}
            )

        if role == User.Roles.HEAD_OFFICE_MANAGER:
            if not attrs.get("head_office"):
                raise serializers.ValidationError({"head_office": "Head office is required for this role."})

        if role in [User.Roles.BRANCH_MANAGER, User.Roles.EMPLOYEE]:
            if not attrs.get("branch"):
                raise serializers.ValidationError({"branch": "Branch is required for this role."})

        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.Roles.choices, required=False)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        role = attrs.get("role")

        user = authenticate(request=self.context.get("request"), username=email, password=password)
        if not user:
            raise serializers.ValidationError({"detail": "Invalid email or password."})

        if role and user.role != role:
            raise serializers.ValidationError({"role": f"This account belongs to '{user.role}'."})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "This account is inactive."})

        employee = getattr(user, "employee_profile", None)
        if employee and not employee.is_active:
            raise serializers.ValidationError({"detail": "This employee profile is inactive."})

        attrs["user"] = user
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class HeadOfficeSerializer(serializers.ModelSerializer):
    branch_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = HeadOffice
        fields = ["id", "name", "branch_count", "created_at"]


class BranchSerializer(serializers.ModelSerializer):
    head_office_detail = SimpleHeadOfficeSerializer(source="head_office", read_only=True)
    manager_detail = SimpleEmployeeSerializer(source="manager", read_only=True)

    class Meta:
        model = Branch
        fields = [
            "id",
            "name",
            "head_office",
            "head_office_detail",
            "manager",
            "manager_detail",
            "created_at",
        ]


class EmployeeUserWriteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    role = serializers.ChoiceField(choices=User.Roles.choices)
    is_active = serializers.BooleanField(required=False)

    def validate_password(self, value):
        validate_password(value)
        return value


class EmployeeWriteSerializer(serializers.ModelSerializer):
    user = EmployeeUserWriteSerializer(required=False)

    class Meta:
        model = Employee
        fields = [
            "id",
            "user",
            "branch",
            "head_office",
            "first_name",
            "last_name",
            "phone",
            "position",
            "department",
            "hire_date",
            "is_active",
        ]

    def validate(self, attrs):
        user_data = attrs.get("user", {})
        role = user_data.get("role", getattr(getattr(self.instance, "user", None), "role", None))
        branch = attrs.get("branch", getattr(self.instance, "branch", None))
        head_office = attrs.get("head_office", getattr(self.instance, "head_office", None))

        if role == User.Roles.HEAD_OFFICE_MANAGER:
            if branch is not None:
                raise serializers.ValidationError({"branch": "Head office managers cannot be attached to a branch."})
            if head_office is None:
                raise serializers.ValidationError({"head_office": "Head office is required for head office managers."})

        if role in [User.Roles.BRANCH_MANAGER, User.Roles.EMPLOYEE]:
            if branch is None:
                raise serializers.ValidationError({"branch": "Branch is required for branch managers and employees."})
            if head_office is not None:
                raise serializers.ValidationError({"head_office": "Head office should be empty for branch-linked users."})

        if self.instance is None:
            if "user" not in attrs:
                raise serializers.ValidationError({"user": "This field is required."})
            if User.objects.filter(email=user_data.get("email")).exists():
                raise serializers.ValidationError({"user": {"email": "This email is already in use."}})
            if not user_data.get("password"):
                raise serializers.ValidationError({"user": {"password": "Password is required."}})
        return attrs


class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    branch_detail = SimpleBranchSerializer(source="branch", read_only=True)
    head_office_detail = SimpleHeadOfficeSerializer(source="head_office", read_only=True)
    assigned_devices_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "user",
            "branch",
            "branch_detail",
            "head_office",
            "head_office_detail",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "position",
            "department",
            "hire_date",
            "is_active",
            "is_head_office",
            "assigned_devices_count",
            "created_at",
        ]


class DeviceSerializer(serializers.ModelSerializer):
    branch_detail = SimpleBranchSerializer(source="branch", read_only=True)
    display_name = serializers.SerializerMethodField()
    assignment_scope = serializers.SerializerMethodField()
    current_assignments = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            "id",
            "name",
            "display_name",
            "device_type",
            "branch",
            "branch_detail",
            "assignment_scope",
            "serial_number",
            "brand",
            "model",
            "purchase_date",
            "assign_to_all_branches",
            "current_assignments",
            "created_at",
        ]

    def get_display_name(self, obj):
        if obj.serial_number:
            return f"{obj.name} ({obj.serial_number})"
        return obj.name

    def get_assignment_scope(self, obj):
        if obj.assign_to_all_branches:
            return "All branches and head office"
        return obj.branch.name if obj.branch_id else "Head office only"

    def get_current_assignments(self, obj):
        assignments = obj.assignments.filter(returned_at__isnull=True).select_related("employee")
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if user and getattr(user, "role", None) == User.Roles.BRANCH_MANAGER:
            employee = getattr(user, "employee_profile", None)
            assignments = assignments.filter(employee__branch_id=getattr(employee, "branch_id", None))
        elif user and getattr(user, "role", None) == User.Roles.EMPLOYEE:
            employee = getattr(user, "employee_profile", None)
            assignments = assignments.filter(employee_id=getattr(employee, "id", None))

        return [
            {
                "assignment_id": assignment.id,
                "employee_id": assignment.employee_id,
                "employee_name": assignment.employee.full_name,
                "assigned_at": assignment.assigned_at,
            }
            for assignment in assignments
        ]


class DeviceAssignmentSerializer(serializers.ModelSerializer):
    device_detail = DeviceSerializer(source="device", read_only=True)
    employee_detail = EmployeeSerializer(source="employee", read_only=True)
    branch_detail = SimpleBranchSerializer(source="branch", read_only=True)
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = DeviceAssignment
        fields = [
            "id",
            "device",
            "device_detail",
            "employee",
            "employee_detail",
            "branch",
            "branch_detail",
            "assigned_at",
            "returned_at",
            "is_active",
        ]


class AssignDeviceSerializer(serializers.Serializer):
    device = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.select_related("user", "branch"))


class ReturnDeviceSerializer(serializers.Serializer):
    returned_at = serializers.DateTimeField(required=False)


class RequestSerializer(serializers.ModelSerializer):
    employee_detail = EmployeeSerializer(source="employee", read_only=True)
    device_detail = DeviceSerializer(source="device", read_only=True)
    branch_manager_detail = SimpleEmployeeSerializer(source="branch_manager", read_only=True)
    head_office_manager_detail = SimpleEmployeeSerializer(source="head_office_manager", read_only=True)
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Request
        fields = [
            "id",
            "employee",
            "employee_detail",
            "device",
            "device_detail",
            "issue_description",
            "status",
            "branch_manager",
            "branch_manager_detail",
            "head_office_manager",
            "head_office_manager_detail",
            "rejection_reason",
            "resolution_notes",
            "approved_by_branch_at",
            "approved_by_head_office_at",
            "rejected_at",
            "resolved_at",
            "progress_percentage",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "branch_manager",
            "head_office_manager",
            "rejection_reason",
            "resolution_notes",
            "approved_by_branch_at",
            "approved_by_head_office_at",
            "rejected_at",
            "resolved_at",
        ]

    def get_progress_percentage(self, obj):
        return obj.progress()


class RequestCreateSerializer(serializers.Serializer):
    device = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())
    issue_description = serializers.CharField()


class RequestDecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class NotificationSerializer(serializers.ModelSerializer):
    device_detail = DeviceSerializer(source="related_device", read_only=True)
    employee_detail = EmployeeSerializer(source="related_employee", read_only=True)
    request_detail = RequestSerializer(source="related_request", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "is_read",
            "device_detail",
            "employee_detail",
            "request_detail",
            "created_at",
            "read_at",
        ]
        read_only_fields = [
            "notification_type",
            "title",
            "message",
            "device_detail",
            "employee_detail",
            "request_detail",
            "created_at",
            "read_at",
        ]
