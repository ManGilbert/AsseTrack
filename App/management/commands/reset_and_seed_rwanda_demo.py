from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from App.models import Branch, Device, DeviceAssignment, Employee, HeadOffice, Request, User


class Command(BaseCommand):
    help = "Delete all AsseTrack business data and seed Rwanda-based demo records."

    def handle(self, *args, **options):
        with transaction.atomic():
            self._reset_data()
            seeded = self._seed_data()

        self.stdout.write(self.style.SUCCESS("Database reset and Rwanda demo data seeded successfully."))
        for key, value in seeded.items():
            self.stdout.write(f"{key}: {value}")

    def _reset_data(self):
        BlacklistedToken.objects.all().delete()
        OutstandingToken.objects.all().delete()
        Request.objects.all().delete()
        DeviceAssignment.objects.all().delete()
        Device.objects.all().delete()
        Branch.objects.all().delete()
        Employee.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        HeadOffice.objects.all().delete()

    def _seed_data(self):
        head_offices = [
            "Kigali Central Head Office",
            "Nyarugenge Operations Head Office",
            "Gasabo Digital Services Head Office",
            "Kicukiro Asset Control Head Office",
            "Musanze Regional Head Office",
            "Rubavu Lake Region Head Office",
            "Huye Southern Head Office",
            "Rwamagana Eastern Head Office",
            "Nyagatare Frontier Head Office",
            "Rusizi Western Corridor Head Office",
        ]
        created_head_offices = [HeadOffice.objects.create(name=name) for name in head_offices]

        branch_specs = [
            ("Kigali Branch", 0),
            ("Musanze Branch", 4),
            ("Rubavu Branch", 5),
            ("Huye Branch", 6),
            ("Rwamagana Branch", 7),
            ("Nyagatare Branch", 8),
            ("Rusizi Branch", 9),
            ("Muhanga Branch", 3),
            ("Karongi Branch", 5),
            ("Bugesera Branch", 2),
        ]
        created_branches = [
            Branch.objects.create(name=name, head_office=created_head_offices[head_office_index])
            for name, head_office_index in branch_specs
        ]

        user_specs = [
            {
                "email": "claudine.mukamana@assetrack.rw",
                "password": "StrongPass123!",
                "role": User.Roles.HEAD_OFFICE_MANAGER,
                "employee": {
                    "first_name": "Claudine",
                    "last_name": "Mukamana",
                    "phone": "+250788100001",
                    "position": "Chief Operations Officer",
                    "department": "Operations",
                    "hire_date": date(2021, 3, 12),
                    "branch": None,
                },
            },
            {
                "email": "eric.habimana@assetrack.rw",
                "password": "StrongPass123!",
                "role": User.Roles.BRANCH_MANAGER,
                "employee": {
                    "first_name": "Eric",
                    "last_name": "Habimana",
                    "phone": "+250788100002",
                    "position": "Kigali Branch Manager",
                    "department": "Administration",
                    "hire_date": date(2021, 7, 19),
                    "branch": created_branches[0],
                },
            },
            {
                "email": "ingabire.keza@assetrack.rw",
                "password": "StrongPass123!",
                "role": User.Roles.BRANCH_MANAGER,
                "employee": {
                    "first_name": "Keza",
                    "last_name": "Ingabire",
                    "phone": "+250788100003",
                    "position": "Musanze Branch Manager",
                    "department": "Administration",
                    "hire_date": date(2022, 1, 15),
                    "branch": created_branches[1],
                },
            },
            {
                "email": "patrick.ndayisaba@assetrack.rw",
                "password": "StrongPass123!",
                "role": User.Roles.BRANCH_MANAGER,
                "employee": {
                    "first_name": "Patrick",
                    "last_name": "Ndayisaba",
                    "phone": "+250788100004",
                    "position": "Huye Branch Manager",
                    "department": "Administration",
                    "hire_date": date(2020, 11, 2),
                    "branch": created_branches[3],
                },
            },
            {
                "email": "aline.niyigena@assetrack.rw",
                "password": "StrongPass123!",
                "role": User.Roles.EMPLOYEE,
                "employee": {
                    "first_name": "Aline",
                    "last_name": "Niyigena",
                    "phone": "+250788100005",
                    "position": "Finance Officer",
                    "department": "Finance",
                    "hire_date": date(2022, 5, 9),
                    "branch": created_branches[0],
                },
            },
            {
                "email": "jean.bosco.uwase@assetrack.rw",
                "password": "StrongPass123!",
                "role": User.Roles.EMPLOYEE,
                "employee": {
                    "first_name": "Jean Bosco",
                    "last_name": "Uwase",
                    "phone": "+250788100006",
                    "position": "IT Support Specialist",
                    "department": "ICT",
                    "hire_date": date(2023, 2, 21),
                    "branch": created_branches[1],
                },
            },
            {
                "email": "grace.mukeshimana@assetrack.rw",
                "password": "StrongPass123!",
                "role": User.Roles.EMPLOYEE,
                "employee": {
                    "first_name": "Grace",
                    "last_name": "Mukeshimana",
                    "phone": "+250788100007",
                    "position": "Procurement Officer",
                    "department": "Procurement",
                    "hire_date": date(2021, 10, 4),
                    "branch": created_branches[2],
                },
            },
            {
                "email": "samuel.nzeyimana@assetrack.rw",
                "password": "StrongPass123!",
                "role": User.Roles.EMPLOYEE,
                "employee": {
                    "first_name": "Samuel",
                    "last_name": "Nzeyimana",
                    "phone": "+250788100008",
                    "position": "Monitoring Officer",
                    "department": "Programs",
                    "hire_date": date(2020, 9, 28),
                    "branch": created_branches[3],
                },
            },
            {
                "email": "diane.uwimana@assetrack.rw",
                "password": "StrongPass123!",
                "role": User.Roles.EMPLOYEE,
                "employee": {
                    "first_name": "Diane",
                    "last_name": "Uwimana",
                    "phone": "+250788100009",
                    "position": "Customer Care Officer",
                    "department": "Service Desk",
                    "hire_date": date(2024, 1, 17),
                    "branch": created_branches[4],
                },
            },
            {
                "email": "emmanuel.kayitesi@assetrack.rw",
                "password": "StrongPass123!",
                "role": User.Roles.EMPLOYEE,
                "employee": {
                    "first_name": "Emmanuel",
                    "last_name": "Kayitesi",
                    "phone": "+250788100010",
                    "position": "Logistics Officer",
                    "department": "Logistics",
                    "hire_date": date(2022, 8, 11),
                    "branch": created_branches[5],
                },
            },
        ]

        created_users = []
        created_employees = []
        for spec in user_specs:
            user = User.objects.create_user(
                email=spec["email"],
                password=spec["password"],
                role=spec["role"],
                is_staff=(spec["role"] == User.Roles.HEAD_OFFICE_MANAGER),
            )
            created_users.append(user)
            employee = Employee.objects.create(user=user, **spec["employee"])
            created_employees.append(employee)

        created_branches[0].manager = created_employees[1]
        created_branches[0].save(update_fields=["manager"])
        created_branches[1].manager = created_employees[2]
        created_branches[1].save(update_fields=["manager"])
        created_branches[3].manager = created_employees[3]
        created_branches[3].save(update_fields=["manager"])

        device_specs = [
            ("Dell Latitude 5440", "laptop", created_branches[0], "RW-KGL-LT-001", "Dell", "Latitude 5440", date(2025, 2, 15)),
            ("HP ProBook 450", "laptop", created_branches[1], "RW-MUS-LT-002", "HP", "ProBook 450", date(2024, 12, 10)),
            ("Lenovo ThinkPad E14", "laptop", created_branches[2], "RW-RUB-LT-003", "Lenovo", "ThinkPad E14", date(2025, 1, 20)),
            ("Canon iR 2630", "printer", created_branches[3], "RW-HUY-PR-004", "Canon", "iR 2630", date(2023, 11, 5)),
            ("Samsung Galaxy Tab S9", "tablet", created_branches[4], "RW-RWA-TB-005", "Samsung", "Galaxy Tab S9", date(2025, 3, 7)),
            ("Dell OptiPlex 7010", "desktop", created_branches[5], "RW-NYA-DT-006", "Dell", "OptiPlex 7010", date(2024, 7, 3)),
            ("Epson EcoTank L3250", "printer", created_branches[6], "RW-RUS-PR-007", "Epson", "EcoTank L3250", date(2024, 10, 14)),
            ("MacBook Air M2", "laptop", created_branches[7], "RW-MUH-LT-008", "Apple", "MacBook Air M2", date(2025, 2, 28)),
            ("Acer Aspire 5", "laptop", created_branches[8], "RW-KAR-LT-009", "Acer", "Aspire 5", date(2024, 9, 9)),
            ("Brother DCP-L2550DW", "printer", created_branches[9], "RW-BUG-PR-010", "Brother", "DCP-L2550DW", date(2023, 6, 18)),
        ]
        created_devices = []
        for name, device_type, branch, serial_number, brand, model, purchase_date in device_specs:
            created_devices.append(
                Device.objects.create(
                    name=name,
                    device_type=device_type,
                    branch=branch,
                    serial_number=serial_number,
                    brand=brand,
                    model=model,
                    purchase_date=purchase_date,
                    status=Device.Statuses.AVAILABLE,
                )
            )

        assignment_targets = [
            (0, 4, False),
            (1, 5, False),
            (2, 6, False),
            (3, 7, False),
            (4, 8, False),
            (5, 9, False),
            (6, 1, True),
            (7, 2, False),
            (8, 3, False),
            (9, 4, True),
        ]
        created_assignments = []
        now = timezone.now()
        for index, employee_index, returned in assignment_targets:
            assigned_at = now - timedelta(days=30 - index)
            assignment = DeviceAssignment.objects.create(
                device=created_devices[index],
                employee=created_employees[employee_index],
                branch=created_employees[employee_index].branch,
                assigned_at=assigned_at,
            )
            if assigned_at:
                DeviceAssignment.objects.filter(pk=assignment.pk).update(assigned_at=assigned_at)
                assignment.assigned_at = assigned_at
            if returned:
                returned_at = assigned_at + timedelta(days=7)
                assignment.returned_at = returned_at
                assignment.save(update_fields=["returned_at"])
                created_devices[index].status = Device.Statuses.AVAILABLE
            else:
                created_devices[index].status = Device.Statuses.NOT_AVAILABLE
            created_devices[index].branch = created_employees[employee_index].branch
            created_devices[index].save(update_fields=["status", "branch"])
            created_assignments.append(assignment)

        request_specs = [
            (4, 0, Request.Statuses.PENDING, None, None, "", ""),
            (5, 1, Request.Statuses.APPROVED_BY_BRANCH, created_employees[2], None, "", ""),
            (6, 2, Request.Statuses.APPROVED_BY_HEAD_OFFICE, created_employees[2], created_employees[0], "", ""),
            (7, 3, Request.Statuses.RESOLVED, created_employees[3], created_employees[0], "", "Printer serviced in Huye."),
            (8, 4, Request.Statuses.REJECTED, created_employees[1], None, "Screen replacement is required instead of repair.", ""),
            (9, 5, Request.Statuses.PENDING, None, None, "", ""),
            (1, 6, Request.Statuses.APPROVED_BY_BRANCH, created_employees[1], None, "", ""),
            (2, 7, Request.Statuses.RESOLVED, created_employees[2], created_employees[0], "", "Battery replaced and device tested."),
            (3, 8, Request.Statuses.APPROVED_BY_HEAD_OFFICE, created_employees[3], created_employees[0], "", ""),
            (4, 9, Request.Statuses.REJECTED, created_employees[1], created_employees[0], "Replacement approved instead of repairing old printer.", ""),
        ]

        created_requests = []
        for offset, (employee_index, device_index, status_value, branch_manager, head_office_manager, reason, notes) in enumerate(request_specs):
            created_at = now - timedelta(days=15 - offset)
            req = Request.objects.create(
                employee=created_employees[employee_index],
                device=created_devices[device_index],
                issue_description=f"Issue report for {created_devices[device_index].name} in Rwanda operations batch #{offset + 1}.",
                status=status_value,
                branch_manager=branch_manager,
                head_office_manager=head_office_manager,
                rejection_reason=reason,
                resolution_notes=notes,
            )
            updates = {"created_at": created_at, "updated_at": created_at + timedelta(hours=3)}
            if status_value in [Request.Statuses.APPROVED_BY_BRANCH, Request.Statuses.APPROVED_BY_HEAD_OFFICE, Request.Statuses.RESOLVED]:
                updates["approved_by_branch_at"] = created_at + timedelta(hours=1)
            if status_value in [Request.Statuses.APPROVED_BY_HEAD_OFFICE, Request.Statuses.RESOLVED]:
                updates["approved_by_head_office_at"] = created_at + timedelta(hours=2)
            if status_value == Request.Statuses.RESOLVED:
                updates["resolved_at"] = created_at + timedelta(hours=6)
            if status_value == Request.Statuses.REJECTED:
                updates["rejected_at"] = created_at + timedelta(hours=2)
            Request.objects.filter(pk=req.pk).update(**updates)
            created_requests.append(req)

        return {
            "head_offices": len(created_head_offices),
            "branches": len(created_branches),
            "users": len(created_users),
            "employees": len(created_employees),
            "devices": len(created_devices),
            "assignments": len(created_assignments),
            "requests": len(created_requests),
            "default_password": "StrongPass123!",
        }
