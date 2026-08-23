from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from access_parser import AccessParser

from audit.models import record
from vendors.models import Supplier, SupplierQualification, TaskMain, TaskSub


def rows(db, name):
    tab = db.parse_table(name)
    cols = [c for c in tab.keys() if c != 'rows']
    return [{c: tab[c][i] for c in cols} for i in range(len(tab[cols[0]]))] if cols else []


def s(v, limit=None):
    if v is None or v == '' or v == b'':
        return ''
    out = str(v).strip()
    return out[:limit] if limit else out


def b(v):
    return s(v).lower() == 'true'


def d(v):
    txt = s(v)
    if not txt:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            continue
    return None


def dec(v):
    txt = s(v).replace(',', '')
    try:
        return txt or None
    except ValueError:
        return None


REG_STATUS_MAP = {
    'مسجل': 'local', 'إستبعاد': 'excluded', 'استبعاد': 'excluded',
    'موقوف': 'suspended', 'مشطوب': 'struck_off',
}

REG_TYPE_MAP = {'توريد فقط': 'supply_only', 'توريد و تركيب': 'supply_install', 'تقديم خدمة': 'service', 'تأجير': 'rental'}
REG_CAP_MAP = {
    'مصنع أصلى': 'original_manufacturer', 'وكيل حصرى': 'sole_agent',
    'ممثل تجارى': 'commercial_agent', 'موزع معتمد': 'authorized_distributor', 'أخرى': 'other',
}


class Command(BaseCommand):
    help = 'Import activities + suppliers + qualifications from legacy 2026.accdb.'

    def add_arguments(self, parser):
        parser.add_argument('--file', default='data/2026.accdb')
        parser.add_argument('--skip-quals', action='store_true')

    def handle(self, *args, **options):
        db = AccessParser(options['file'])

        with transaction.atomic():
            self.stdout.write('Importing tasks...')
            for r in rows(db, 'Tasks'):
                TaskMain.objects.update_or_create(
                    code=s(r.get('كود النشاط الرئيسى')),
                    defaults={'name_ar': s(r.get('أسم النشاط الرئيسى A')), 'name_en': s(r.get('أسم النشاط الرئيسى E'))})

            main_by_code = {m.code: m for m in TaskMain.objects.all()}
            for r in rows(db, 'Tasks sub'):
                code = s(r.get('كود النشاط الفرعى'))
                if not code:
                    continue
                TaskSub.objects.update_or_create(
                    code=code,
                    defaults={
                        'main': main_by_code.get(s(r.get('كود النشاط الرئيسى'))),
                        'name_ar': s(r.get('أسم النشاط الفرعى A')),
                        'name_en': s(r.get('أسم النشاط الفرعى E'))})
            self.stdout.write(self.style.SUCCESS(f"tasks: {TaskMain.objects.count()} main / {TaskSub.objects.count()} sub"))

            self.stdout.write('Importing suppliers (this takes a while)...')
            for i, r in enumerate(rows(db, 'Vendors')):
                supplier_no = s(r.get('Supplier ID'))
                if not supplier_no:
                    continue
                status_old = s(r.get('موقف  التسجيل')) or s(r.get('موقف التسجيل'))
                status_new = s(r.get('موقف التسجيل جديد'))
                reg_status = REG_STATUS_MAP.get(status_new) or REG_STATUS_MAP.get(status_old, '')
                if not reg_status and status_new.startswith('مسجل'):
                    reg_status = 'local'
                suspended = b(r.get('موقوف'))
                struck = b(r.get('مشطوب'))
                if suspended:
                    reg_status = 'suspended'
                elif struck:
                    reg_status = 'struck_off'

                Supplier.objects.update_or_create(
                    supplier_no=supplier_no,
                    defaults={
                        'legacy_id': s(r.get('ID')),
                        'name_ar': s(r.get('أسم المورد A'), 255),
                        'name_en': s(r.get('أسم المورد E'), 255),
                        'registration_status': reg_status,
                        'registered_local': b(r.get('مسجل محلي')),
                        'registered_foreign': b(r.get('مسجل خارجى')),
                        'suspended': suspended,
                        'struck_off': struck,
                        'dossier_no': s(r.get('رقم الكراسة')),
                        'dossier_type': s(r.get('نوع الكراسة')),
                        'committee_no': s(r.get('رقم اللجنة')),
                        'committee_date': d(r.get('تاريخ اللجنة')),
                        'commercial_registry_no': s(r.get('السجل التجارى')),
                        'commercial_registry_expiry': d(r.get('تاريخ انتهاء السجل التجاري')),
                        'tax_card_no': s(r.get('البطاقه الضريبيه')),
                        'tax_card_expiry': d(r.get('تاريخ انتهاء البطاقة الضريبية')),
                        'vat_no': s(r.get('القيمة المضافه')),
                        'vat_expiry': d(r.get('تاريخ انتهاء ضريبة القيمة المضافة')),
                        'capital_amount': dec(r.get('مبلغ رأس المال')),
                        'capital_currency': s(r.get('عملة رأس المال'), 40),
                        'country': s(r.get('البلد')),
                        'address': s(r.get('العنوان')),
                        'phone1': s(r.get('التليفون 1'), 40),
                        'phone2': s(r.get('التليفون 2'), 40),
                        'mobile1': s(r.get('المحمول 1'), 40),
                        'mobile2': s(r.get('المحمول 2'), 40),
                        'fax': s(r.get('الفاكس 1'), 40),
                        'email1': s(r.get('E_mail 1').split('#')[0] if r.get('E_mail 1') else '', 120),
                        'email2': s(r.get('E_mail 2'), 120),
                        'website': s(r.get('الموقع الالكترونى'), 150),
                        'contact_person': s(r.get('الشخص المتصل'), 150),
                        'owner_name': s(r.get('أسم صاحب المنشأة'), 150),
                        'agent_name': s(r.get('الوكيل'), 200),
                        'agent_phone': s(r.get('تليفون الوكيل 1'), 80),
                        'agent_mobile': s(r.get('محمول الوكيل 1'), 80),
                        'agent_fax': s(r.get('فاكس الوكيل 1'), 80),
                        'agent_email': s(r.get('E_mail الوكيل 1'), 120),
                        'agent_address': s(r.get('عنوان الوكيل')),
                        'agency_documents': s(r.get('مستندات الوكالة'), 200),
                        'category': s(r.get('Categry'), 100),
                        'free_zone': s(r.get('منطقة حرة')).lower() in ('true', 'yes', 'نعم'),
                        'certified': s(r.get('A certified')).lower() == 'yes',
                        'previous_no': s(r.get('رقم الساب'), 30),
                        'notes': s(r.get('ملاحظات')),
                        'private_notes': s(r.get('ملاحظات خاصة')),
                    })
                if i % 1000 == 0:
                    self.stdout.write(f'  {i} suppliers...')
            self.stdout.write(self.style.SUCCESS(f'suppliers: {Supplier.objects.count()}'))

            if not options['skip_quals']:
                self.stdout.write('Importing vendor-vs-tasks qualifications...')
                subs_by_code = {t.code: t for t in TaskSub.objects.all()}
                sup_by_no = dict(Supplier.objects.values_list('supplier_no', 'id'))
                batch = []
                total_skipped = 0
                for r in rows(db, 'Vendor VS Tasks'):
                    sup = sup_by_no.get(s(r.get('Supplier ID')))
                    sub = subs_by_code.get(s(r.get('كود النشاط الفرعى')))
                    if not sup or not sub:
                        total_skipped += 1
                        continue
                    batch.append(SupplierQualification(
                        supplier_id=sup, task_sub=sub,
                        registration_type=REG_TYPE_MAP.get(s(r.get('نوع التسجيل')), ''),
                        registration_capacity=REG_CAP_MAP.get(s(r.get('صفة التسجيل')), ''),
                        brand=s(r.get('الماركة'), 120),
                        original_maker=s(r.get('مصنع أصلى'), 120),
                        origin_country=s(r.get('بلد المنشأ'), 80),
                        notes=s(r.get('ملاحظات')),
                    ))
                    if len(batch) >= 1000:
                        SupplierQualification.objects.bulk_create(batch, ignore_conflicts=True)
                        batch = []
                if batch:
                    SupplierQualification.objects.bulk_create(batch, ignore_conflicts=True)
                self.stdout.write(self.style.SUCCESS(
                    f"qualifications: {SupplierQualification.objects.count()} (skipped unmatched: {total_skipped})"))

        record('CREATE', module='vendors', model_label='legacy.import',
               object_repr=f"Vendors import: {Supplier.objects.count()} suppliers, {SupplierQualification.objects.count()} quals")
        self.stdout.write(self.style.SUCCESS('Done.'))
