from datetime import date, timedelta

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from App.models import Branch, Device, DeviceAssignment, Employee, HeadOffice, Notification, Request, User


DEFAULT_PASSWORD = "Aa@2026123"


class Command(BaseCommand):
    help = "Reset business data and seed the requested Rwanda demo dataset."

    def handle(self, *args, **options):
        with transaction.atomic():
            self._reset_data()
            summary = self._seed_data()

        self.stdout.write(self.style.SUCCESS("Requested Rwanda dataset seeded successfully."))
        for key, value in summary.items():
            self.stdout.write(f"{key}: {value}")

    def _reset_data(self):
        BlacklistedToken.objects.all().delete()
        OutstandingToken.objects.all().delete()
        Notification.objects.all().delete()
        Request.objects.all().delete()
        DeviceAssignment.objects.all().delete()
        Device.objects.all().delete()
        Branch.objects.all().delete()
        Employee.objects.all().delete()
        User.objects.all().delete()
        HeadOffice.objects.all().delete()

    def _create_employee_profile(
        self,
        *,
        encoded_password,
        email,
        role,
        first_name,
        last_name,
        phone,
        position,
        department,
        hire_date,
        branch=None,
        head_office=None,
        is_staff=False,
        is_superuser=False,
    ):
        user = User.objects.create(
            email=email,
            password=encoded_password,
            role=role,
            is_staff=is_staff,
            is_superuser=is_superuser,
            is_active=True,
        )
        employee = Employee.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            position=position,
            department=department,
            hire_date=hire_date,
            branch=branch,
            head_office=head_office,
            is_active=True,
        )
        return employee

    def _seed_data(self):
        encoded_password = make_password(DEFAULT_PASSWORD)
        head_office = HeadOffice.objects.create(name="Kigali Head Office")
        head_manager = self._create_employee_profile(
            encoded_password=encoded_password,
            email="admin@assert.ac.rw",
            role=User.Roles.HEAD_OFFICE_MANAGER,
            first_name="Aline",
            last_name="Mukamana",
            phone="+250788600001",
            position="Head Office Administrator",
            department="Administration",
            hire_date=date(2020, 1, 15),
            head_office=head_office,
            is_staff=True,
            is_superuser=True,
        )

        branch_specs = [
            ("Kigali Branch", "Kigali"),
            ("Huye Branch", "Huye"),
            ("Musanze Branch", "Musanze"),
            ("Rubavu Branch", "Rubavu"),
            ("Rwamagana Branch", "Rwamagana"),
            ("Nyagatare Branch", "Nyagatare"),
            ("Rusizi Branch", "Rusizi"),
            ("Muhanga Branch", "Muhanga"),
            ("Karongi Branch", "Karongi"),
            ("Bugesera Branch", "Bugesera"),
        ]
        branches = [Branch.objects.create(name=name, head_office=head_office) for name, _district in branch_specs]

        manager_names = [
            ("Eric", "Habimana"),
            ("Claudine", "Uwase"),
            ("Patrick", "Ndayisenga"),
            ("Diane", "Mukeshimana"),
            ("Jean Bosco", "Nshimiyimana"),
            ("Grace", "Ingabire"),
            ("Emmanuel", "Nkurunziza"),
            ("Sandrine", "Uwamahoro"),
            ("Samuel", "Munyaneza"),
            ("Josiane", "Nyirahabimana"),
        ]

        branch_managers = []
        for index, branch in enumerate(branches):
            first_name, last_name = manager_names[index]
            manager = self._create_employee_profile(
                encoded_password=encoded_password,
                email=f"{last_name.lower()}@asset.sc.rw",
                role=User.Roles.BRANCH_MANAGER,
                first_name=first_name,
                last_name=last_name,
                phone=f"+25078861{index + 1:04d}",
                position=f"{branch.name} Manager",
                department="Branch Administration",
                hire_date=date(2021, (index % 12) + 1, 10),
                branch=branch,
            )
            branch.manager = manager
            branch.save(update_fields=["manager"])
            branch_managers.append(manager)

        employee_names = [
            ("Alice", "Akamanzi"),
            ("David", "Bizimana"),
            ("Chantal", "Cyuzuzo"),
            ("Theoneste", "Dushimimana"),
            ("Vestine", "Gahongayire"),
            ("Olivier", "Hategekimana"),
            ("Jeannette", "Iradukunda"),
            ("Fabrice", "Kalisa"),
            ("Esperance", "Kayitesi"),
            ("Aimable", "Manirakiza"),
            ("Carine", "Mugisha"),
            ("Pascal", "Mutabazi"),
            ("Solange", "Mutesi"),
            ("Thierry", "Ngabonziza"),
            ("Beatrice", "Niyigena"),
            ("Innocent", "Niyitegeka"),
            ("Rosine", "Nsabimana"),
            ("Felix", "Nsengiyumva"),
            ("Delphine", "Ntakirutimana"),
            ("Emile", "Ntirenganya"),
            ("Yvonne", "Nyiransabimana"),
            ("Gilbert", "Rugamba"),
            ("Immaculee", "Rukundo"),
            ("Cedric", "Rutayisire"),
            ("Marie Claire", "Rwiririza"),
            ("Claude", "Sibomana"),
            ("Ange", "Tuyisenge"),
            ("Arnaud", "Twagirayezu"),
            ("Liliane", "Umutoni"),
            ("Moise", "Uwimana"),
            ("Dativa", "Uwimbabazi"),
            ("Etienne", "Bayingana"),
            ("Francine", "Byukusenge"),
            ("Gaspard", "Gakuba"),
            ("Helene", "Gatabazi"),
            ("Isaac", "Hakizimana"),
            ("Julienne", "Hitimana"),
            ("Kevin", "Ishimwe"),
            ("Lydia", "Kabagambe"),
            ("Martin", "Kamanzi"),
            ("Nadine", "Kankindi"),
            ("Oscar", "Karangwa"),
            ("Pascasie", "Karekezi"),
            ("Queen", "Kayiranga"),
            ("Robert", "Mbarushimana"),
            ("Sonia", "Mbonyinshuti"),
            ("Thomas", "Mugabo"),
            ("Ursule", "Mujawamariya"),
            ("Vincent", "Mukamurenzi"),
            ("Wivine", "Mukarugwiza"),
            ("Xavier", "Munyakazi"),
            ("Yvan", "Murangwa"),
            ("Zawadi", "Murekatete"),
            ("Albert", "Musabyimana"),
            ("Bella", "Mutamuliza"),
            ("Charles", "Mutangana"),
            ("Denise", "Muteteri"),
            ("Elias", "Muvunyi"),
            ("Flora", "Mwizerwa"),
            ("Gerard", "Ndagijimana"),
            ("Honorine", "Ndahimana"),
            ("Ignace", "Ndikumana"),
            ("Jacqueline", "Ndimubanzi"),
            ("Kenny", "Ndizeye"),
            ("Lea", "Ngabire"),
            ("Modeste", "Ngarambe"),
            ("Noella", "Ngendahayo"),
            ("Odette", "Ngiruwonsanga"),
            ("Philibert", "Ngoboka"),
            ("Rachel", "Niyibizi"),
            ("Serge", "Niyibikora"),
            ("Therese", "Niyigaba"),
            ("Urban", "Niyonkuru"),
            ("Valerie", "Nshimyumuremyi"),
            ("Wilson", "Nsengimana"),
            ("Yvette", "Nshuti"),
            ("Zacharie", "Ntambara"),
            ("Adrien", "Ntawukuriryayo"),
            ("Berthe", "Ntezimana"),
            ("Christian", "Nyandwi"),
            ("Dorothee", "Nyirabagenzi"),
            ("Elisee", "Nyirakamana"),
            ("Fiona", "Nyiramana"),
            ("Gisele", "Nyiransengiyumva"),
            ("Herve", "Nzabonimpa"),
            ("Irene", "Nzabonariba"),
            ("Jules", "Nzamwita"),
            ("Kellen", "Rugema"),
            ("Leon", "Ruhumuriza"),
            ("Mireille", "Rukazambuga"),
            ("Norbert", "Ruzindana"),
            ("Olive", "Rumanyika"),
            ("Prosper", "Rutagengwa"),
            ("Rebecca", "Rwabukumba"),
            ("Silas", "Ruterana"),
            ("Teta", "Sebahire"),
            ("Valens", "Sendegeya"),
            ("Winifrida", "Twahirwa"),
            ("Yolande", "Uwingeneye"),
            ("Zephyrin", "Uzaribara"),
        ]
        departments = ["Finance", "ICT", "Operations", "Procurement", "Customer Care"]
        positions = ["Finance Officer", "ICT Officer", "Operations Officer", "Procurement Officer", "Customer Care Officer"]

        employees = []
        name_index = 0
        for branch_index, branch in enumerate(branches):
            for employee_number in range(10):
                first_name, last_name = employee_names[name_index]
                employees.append(
                    self._create_employee_profile(
                        encoded_password=encoded_password,
                        email=f"{last_name.lower()}@asset.sc.rw",
                        role=User.Roles.EMPLOYEE,
                        first_name=first_name,
                        last_name=last_name,
                        phone=f"+250789{branch_index + 1:02d}{employee_number + 1:04d}",
                        position=positions[employee_number % len(positions)],
                        department=departments[employee_number % len(departments)],
                        hire_date=date(2022 + (employee_number % 3), ((employee_number + branch_index) % 12) + 1, 12),
                        branch=branch,
                    )
                )
                name_index += 1

        device_catalog = [
            ("Dell OptiPlex 7010", "computer", "Dell", "OptiPlex 7010"),
            ("HP ProDesk 400 G9", "computer", "HP", "ProDesk 400 G9"),
            ("Lenovo ThinkCentre M70q", "computer", "Lenovo", "ThinkCentre M70q"),
            ("Acer Veriton X", "computer", "Acer", "Veriton X"),
            ("Asus ExpertCenter D5", "computer", "Asus", "ExpertCenter D5"),
            ("Canon imageFORMULA R40", "scanner", "Canon", "imageFORMULA R40"),
            ("Epson WorkForce ES-580W", "scanner", "Epson", "WorkForce ES-580W"),
            ("Brother ADS-1700W", "scanner", "Brother", "ADS-1700W"),
            ("HP ScanJet Pro 2600", "scanner", "HP", "ScanJet Pro 2600"),
            ("Fujitsu ScanSnap iX1600", "scanner", "Fujitsu", "ScanSnap iX1600"),
            ("HP LaserJet Pro M404dn", "printer", "HP", "LaserJet Pro M404dn"),
            ("Canon i-SENSYS MF455dw", "printer", "Canon", "i-SENSYS MF455dw"),
            ("Epson EcoTank L3250", "printer", "Epson", "EcoTank L3250"),
            ("Brother DCP-L2550DW", "printer", "Brother", "DCP-L2550DW"),
            ("Kyocera ECOSYS M2040dn", "printer", "Kyocera", "ECOSYS M2040dn"),
            ("TP-Link Archer AX55", "wifi router", "TP-Link", "Archer AX55"),
            ("Ubiquiti UniFi Dream Router", "wifi router", "Ubiquiti", "UniFi Dream Router"),
            ("MikroTik hAP ac3", "wifi router", "MikroTik", "hAP ac3"),
            ("Cisco RV340W", "wifi router", "Cisco", "RV340W"),
            ("Huawei WiFi AX3", "wifi router", "Huawei", "WiFi AX3"),
        ]

        devices = []
        for index in range(50):
            branch = branches[index % len(branches)]
            name, device_type, brand, model = device_catalog[index % len(device_catalog)]
            devices.append(
                Device.objects.create(
                    name=f"{name} {index + 1:02d}",
                    device_type=device_type,
                    branch=branch if index % 5 else None,
                    serial_number=f"RW-{branch.name.split()[0].upper()[:3]}-{device_type.replace(' ', '').upper()[:3]}-{index + 1:03d}",
                    brand=brand,
                    model=model,
                    purchase_date=date(2023 + (index % 3), (index % 12) + 1, (index % 25) + 1),
                    assign_to_all_branches=index % 5 == 0,
                )
            )

        assignments = []
        now = timezone.now()
        for index, device in enumerate(devices):
            primary_employee = employees[(index * 2) % len(employees)]
            assignments.append(
                DeviceAssignment.objects.create(
                    device=device,
                    employee=primary_employee,
                    branch=primary_employee.branch,
                    assigned_at=now - timedelta(days=90 - index),
                )
            )
            if index % 3 == 0:
                secondary_employee = employees[(index * 2 + 1) % len(employees)]
                assignments.append(
                    DeviceAssignment.objects.create(
                        device=device,
                        employee=secondary_employee,
                        branch=secondary_employee.branch,
                        assigned_at=now - timedelta(days=60 - index),
                    )
                )

        requests = []
        request_statuses = [
            Request.Statuses.PENDING,
            Request.Statuses.APPROVED_BY_BRANCH,
            Request.Statuses.APPROVED_BY_HEAD_OFFICE,
            Request.Statuses.RESOLVED,
            Request.Statuses.REJECTED,
        ]
        for index, assignment in enumerate(assignments[:40]):
            employee = assignment.employee
            branch_manager = employee.branch.manager if employee.branch else None
            status = request_statuses[index % len(request_statuses)]
            req = Request.objects.create(
                employee=employee,
                device=assignment.device,
                issue_description=f"{assignment.device.name} needs technical support at {employee.branch.name}.",
                status=status,
                branch_manager=branch_manager if status != Request.Statuses.PENDING else None,
                head_office_manager=head_manager if status in [Request.Statuses.APPROVED_BY_HEAD_OFFICE, Request.Statuses.RESOLVED, Request.Statuses.REJECTED] else None,
                rejection_reason="Replacement required instead of repair." if status == Request.Statuses.REJECTED else "",
                resolution_notes="Device serviced and returned to user." if status == Request.Statuses.RESOLVED else "",
            )
            updates = {"created_at": now - timedelta(days=40 - index), "updated_at": now - timedelta(days=39 - index)}
            if status in [Request.Statuses.APPROVED_BY_BRANCH, Request.Statuses.APPROVED_BY_HEAD_OFFICE, Request.Statuses.RESOLVED]:
                updates["approved_by_branch_at"] = updates["created_at"] + timedelta(hours=2)
            if status in [Request.Statuses.APPROVED_BY_HEAD_OFFICE, Request.Statuses.RESOLVED]:
                updates["approved_by_head_office_at"] = updates["created_at"] + timedelta(hours=6)
            if status == Request.Statuses.RESOLVED:
                updates["resolved_at"] = updates["created_at"] + timedelta(days=2)
            if status == Request.Statuses.REJECTED:
                updates["rejected_at"] = updates["created_at"] + timedelta(hours=8)
            Request.objects.filter(pk=req.pk).update(**updates)
            requests.append(req)

        notifications = []
        for assignment in assignments:
            notifications.append(
                Notification.objects.create(
                    user=assignment.employee.user,
                    notification_type=Notification.NotificationTypes.DEVICE_ASSIGNED,
                    title="Device Assigned",
                    message=f"{assignment.device.name} was assigned to you.",
                    related_device=assignment.device,
                    related_employee=assignment.employee,
                )
            )
            if assignment.employee.branch and assignment.employee.branch.manager:
                notifications.append(
                    Notification.objects.create(
                        user=assignment.employee.branch.manager.user,
                        notification_type=Notification.NotificationTypes.DEVICE_ASSIGNED,
                        title="Branch Device Assignment",
                        message=f"{assignment.device.name} assigned to {assignment.employee.full_name}.",
                        related_device=assignment.device,
                        related_employee=assignment.employee,
                    )
                )

        for req in requests:
            recipients = {head_manager.user, req.employee.user}
            if req.employee.branch and req.employee.branch.manager:
                recipients.add(req.employee.branch.manager.user)
            for recipient in recipients:
                notifications.append(
                    Notification.objects.create(
                        user=recipient,
                        notification_type=Notification.NotificationTypes.REQUEST_CREATED,
                        title="Repair Request Activity",
                        message=f"Request #{req.id} for {req.device.name} is {req.get_status_display()}.",
                        related_device=req.device,
                        related_employee=req.employee,
                        related_request=req,
                    )
                )

        return {
            "head_offices": HeadOffice.objects.count(),
            "branches": Branch.objects.count(),
            "head_office_users": User.objects.filter(role=User.Roles.HEAD_OFFICE_MANAGER).count(),
            "branch_managers": User.objects.filter(role=User.Roles.BRANCH_MANAGER).count(),
            "employees": User.objects.filter(role=User.Roles.EMPLOYEE).count(),
            "devices": Device.objects.count(),
            "assignments": DeviceAssignment.objects.count(),
            "requests": Request.objects.count(),
            "notifications": Notification.objects.count(),
            "head_office_login": "admin@assert.ac.rw",
            "default_password": DEFAULT_PASSWORD,
        }
