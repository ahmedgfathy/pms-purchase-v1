from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from organization.models import Department, EmployeeProfile, JobTitle, Section
from rbac.models import AppModule, FieldPermission, ModulePermission, Role, UserRole

User = get_user_model()

DEMO_PASSWORD = 'Purchase@123'

MODULES = [
    ('rfq', 'RFQ — Purchase Requests'),
    ('purchases', 'Purchasing'),
    ('suppliers', 'Suppliers'),
    ('tender', 'Tender Evaluation & POs'),
    ('reports', 'Reports & Analytics'),
    ('audit_trail', 'Audit Trail'),
    ('administration', 'Administration'),
]

PERMISSIONS = {
    'super_admin': {'rfq': 'VACD', 'purchases': 'VACD', 'suppliers': 'VACD', 'tender': 'VACD', 'reports': 'VACD', 'audit_trail': 'V', 'administration': 'V'},
    'purchase_manager': {'rfq': 'VACD', 'purchases': 'VACD', 'suppliers': 'VACD', 'tender': 'VACD', 'reports': 'V', 'audit_trail': 'V'},
    'purchase_assistant': {'rfq': 'VAC', 'purchases': 'VAC', 'suppliers': 'VAC', 'tender': 'VAC', 'reports': 'V'},
    'dept_head': {'rfq': 'VC', 'purchases': 'VC', 'suppliers': 'V', 'tender': 'VC', 'reports': 'V', 'audit_trail': 'V'},
    'section_head': {'rfq': 'VA', 'purchases': 'VA', 'suppliers': 'V', 'tender': 'VAC'},
    'procurement_officer': {'rfq': 'VA', 'purchases': 'VA', 'suppliers': 'V', 'tender': 'VA'},
}

FIELD_PERMISSIONS = [
    ('procurement_officer', 'purchases.PurchaseRequest', 'unit_price', FieldPermission.HIDDEN),
    ('procurement_officer', 'purchases.PurchaseRequest', 'budget_code', FieldPermission.HIDDEN),
    ('purchase_assistant', 'purchases.PurchaseRequest', 'budget_code', FieldPermission.READONLY),
]

ROLE_DEFS = [
    ('Super Admin', 'super_admin', True),
    ('Purchase Manager', 'purchase_manager', False),
    ('Purchase Manager Assistant', 'purchase_assistant', False),
    ('Department Head', 'dept_head', False),
    ('Section Head', 'section_head', False),
    ('Procurement Officer', 'procurement_officer', False),
]

USERS = [
    {
        'username': 'xinreal', 'password': 'ZeroCall20!@H', 'first': 'System', 'last': 'Administrator',
        'email': 'xinreal@pmsoffshore.local', 'superuser': True, 'staff': True,
        'no': 'PMS-0001', 'job': 'IT System Administrator',
        'dept': 'corporate_admin', 'section': None, 'manager': None,
        'roles': ['super_admin'],
        'job_desc': 'Full system authority: manages users, roles, module access, field-level permissions and the audit trail.',
    },
    {
        'username': 'pms.manager', 'password': DEMO_PASSWORD, 'first': 'Ahmed', 'last': 'Rahman',
        'email': 'ahmed.rahman@pmsoffshore.local',
        'no': 'PMS-1001', 'job': 'Purchase Manager',
        'dept': 'purchase', 'section': None, 'manager': None,
        'roles': ['purchase_manager'],
        'job_desc': 'Owns the procurement cycle: approves and rejects purchase requests, manages suppliers, monitors department spend and KPIs.',
    },
    {
        'username': 'pms.assistant', 'password': DEMO_PASSWORD, 'first': 'Laila', 'last': 'Hassan',
        'email': 'laila.hassan@pmsoffshore.local',
        'no': 'PMS-1002', 'job': 'Purchase Manager Assistant',
        'dept': 'purchase', 'section': None, 'manager': 'pms.manager',
        'roles': ['purchase_assistant'],
        'job_desc': 'Supports the Purchase Manager: prepares RFQs, creates and updates purchase requests, follows up deliveries. Budget codes are view-only for this role.',
    },
    {
        'username': 'pms.dhead', 'password': DEMO_PASSWORD, 'first': 'Omar', 'last': 'Farouk',
        'email': 'omar.farouk@pmsoffshore.local',
        'no': 'PMS-1003', 'job': 'Department Head',
        'dept': 'purchase', 'section': None, 'manager': 'pms.manager',
        'roles': ['dept_head'],
        'job_desc': 'Heads the Purchase Department: reviews requests for policy compliance, approves within delegated limits, oversees section heads.',
    },
    {
        'username': 'pms.shead', 'password': DEMO_PASSWORD, 'first': 'Yousef', 'last': 'Karim',
        'email': 'yousef.karim@pmsoffshore.local',
        'no': 'PMS-1004', 'job': 'Section Head - Procurement Operations',
        'dept': 'purchase', 'section': 'proc_ops', 'manager': 'pms.dhead',
        'roles': ['section_head'],
        'job_desc': 'Runs the Procurement Operations section: assigns workload to buyers, validates request quality, first-line approval of operational purchases.',
    },
    {
        'username': 'buyer1', 'password': DEMO_PASSWORD, 'first': 'Dana', 'last': 'Salem',
        'email': 'dana.salem@pmsoffshore.local',
        'no': 'PMS-2001', 'job': 'Procurement Officer',
        'dept': 'purchase', 'section': 'proc_ops', 'manager': 'pms.shead',
        'roles': ['procurement_officer'],
        'job_desc': 'Raises purchase requests, obtains quotations and negotiates prices. Pricing and budget fields are hidden from this role.',
    },
    {
        'username': 'buyer2', 'password': DEMO_PASSWORD, 'first': 'Tariq', 'last': 'Nabil',
        'email': 'tariq.nabil@pmsoffshore.local',
        'no': 'PMS-2002', 'job': 'Buyer',
        'dept': 'purchase', 'section': 'contracts', 'manager': 'pms.shead',
        'roles': ['procurement_officer'],
        'job_desc': 'Executes purchase orders for assigned categories, tracks order status and coordinates with vessels on delivery schedules.',
    },
]


class Command(BaseCommand):
    help = 'Seed PMS org structure, RBAC configuration and users.'

    def handle(self, *args, **options):
        purchase_dept, _ = Department.objects.get_or_create(
            code='purchase', defaults={'name': 'Purchase Department'})
        admin_dept, _ = Department.objects.get_or_create(
            code='corporate_admin', defaults={'name': 'Corporate Administration'})
        proc_ops, _ = Section.objects.get_or_create(
            code='proc_ops', defaults={'name': 'Procurement Operations', 'department': purchase_dept})
        contracts, _ = Section.objects.get_or_create(
            code='contracts', defaults={'name': 'Contracts & Tenders', 'department': purchase_dept})

        titles = {}
        for u in USERS:
            titles[u['job']], _ = JobTitle.objects.get_or_create(
                name=u['job'], defaults={'job_description': u['job_desc']})

        roles = {}
        for name, code, manage in ROLE_DEFS:
            roles[code], _ = Role.objects.update_or_create(
                code=code,
                defaults={'name': name, 'can_manage_rbac': manage, 'is_system': True})

        modules = {}
        for code, name in MODULES:
            modules[code], _ = AppModule.objects.update_or_create(code=code, defaults={'name': name})

        for role_code, mod_map in PERMISSIONS.items():
            for mod_code, flags in mod_map.items():
                ModulePermission.objects.update_or_create(
                    role=roles[role_code], module=modules[mod_code],
                    defaults={
                        'can_view': 'V' in flags, 'can_add': 'A' in flags,
                        'can_change': 'C' in flags, 'can_delete': 'D' in flags})

        for role_code, label, field, mode in FIELD_PERMISSIONS:
            FieldPermission.objects.update_or_create(
                role=roles[role_code], model_label=label, field_name=field,
                defaults={'mode': mode})

        profiles = {}
        sections = {'proc_ops': proc_ops, 'contracts': contracts}
        for u in USERS:
            user, created = User.objects.get_or_create(username=u['username'], defaults={'email': u['email']})
            if created:
                user.set_password(u['password'])
            user.first_name = u['first']
            user.last_name = u['last']
            user.email = u['email']
            user.is_superuser = u.get('superuser', False)
            user.is_staff = u.get('staff', False)
            user.is_active = True
            user.save()

            profile, _ = EmployeeProfile.objects.update_or_create(
                user=user,
                defaults={
                    'employee_no': u['no'],
                    'job_title': titles[u['job']],
                    'department': admin_dept if u['dept'] == 'corporate_admin' else purchase_dept,
                    'section': sections.get(u['section']),
                    'direct_manager': profiles.get(u['manager']),
                })
            profiles[u['username']] = profile

            for role_code in u['roles']:
                UserRole.objects.get_or_create(user=user, role=roles[role_code])

        self.stdout.write(self.style.SUCCESS(
            f"Seeded: 2 departments, 2 sections, {len(titles)} job titles, {len(roles)} roles, "
            f"{len(modules)} modules, {len(USERS)} users. Super admin: xinreal"))
