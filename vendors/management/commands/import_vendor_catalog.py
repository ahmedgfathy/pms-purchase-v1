from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from access_parser import AccessParser

from vendors.models import ActivityProduct, Supplier, TaskSub, VendorActivity, VendorOperation


def clean(v):
    if v is None:
        return ''
    s = str(v).strip()
    return '' if s in ('0', 'None') else s


class Command(BaseCommand):
    help = 'Import activities catalogue, vendor activity positions and archived vendor operations'

    def add_arguments(self, parser):
        parser.add_argument('--db', default='data/2026.accdb')

    @transaction.atomic
    def handle(self, *args, **opts):
        db = AccessParser(opts['db'])

        # ---- 1) الأنشطة : activities + products/services catalogue ----
        tab = db.parse_table('الأنشطة')
        n = len(tab['ID'])
        objs = []
        seen = set()
        for i in range(n):
            row = (
                clean(tab['كود الرئيسي'][i]), clean(tab['الرئيسي'][i]),
                clean(tab['كود النشاط'][i]), clean(tab['أسم النشاط'][i]),
                clean(tab['كود المنتج'][i]), clean(tab['المنتج-الخدمة'][i]),
                clean(tab['حالة المنتج'][i]),
            )
            if row in seen:
                continue
            seen.add(row)
            objs.append(ActivityProduct(
                main_code=row[0], main_name=row[1], activity_code=row[2],
                activity_name=row[3], product_code=row[4], product_service=row[5],
                product_status=row[6],
            ))
        ActivityProduct.objects.all().delete()
        ActivityProduct.objects.bulk_create(objs, batch_size=500)
        self.stdout.write(f'ActivityProduct: {len(objs)} rows')

        # ---- 2) موقف الموردين من الأنشطة ----
        mo = db.parse_table('موقف الموردين من الأنشطة')
        m = len(mo['ID'])

        name2id = defaultdict(list)
        for sup in Supplier.objects.all():
            for key in (sup.name_ar.strip(), sup.name_en.strip()):
                if key:
                    name2id[key].append(sup.pk)
        subnames = {t.name_ar.strip(): t.pk for t in TaskSub.objects.all()}

        act_objs = []
        linked = 0
        for i in range(m):
            nm = clean(mo['أسم المورد'][i])
            an = clean(mo['أسم النشاط'][i])
            if not nm and not an:
                continue
            sid = name2id.get(nm, [None])[0]
            if sid:
                linked += 1
            key = (nm, an, clean(mo['المنتج-الخدمة'][i]))
            act_objs.append(VendorActivity(
                supplier_id=sid,
                vendor_name_raw=nm,
                activity_name=an,
                main_name=clean(mo['الرئيسي'][i]),
                registration_position=clean(mo['موقف التسجيل'][i]),
                product_service=key[2],
                ptype=clean(mo['النوع'][i]),
                model=clean(mo['موديل'][i]),
                details=clean(mo['تفصيلي'][i]),
            ))
        VendorActivity.objects.all().delete()
        VendorActivity.objects.bulk_create(act_objs, batch_size=1000)
        self.stdout.write(f'VendorActivity: {len(act_objs)} rows ({linked} supplier-linked)')

        # ---- 3) Vendor Opration : archived participation ----
        vo = db.parse_table('Vendor Opration')
        v = len(vo['id'])
        sup_by_legacy = {s.legacy_id: s.pk for s in Supplier.objects.exclude(legacy_id='')}
        sup_by_no = {s.supplier_no: s.pk for s in Supplier.objects.all()}
        op_objs = []
        skipped = 0
        for i in range(v):
            legacy = str(vo['Supplier ID'][i])
            sid = sup_by_no.get(legacy) or sup_by_legacy.get(legacy)
            if not sid:
                skipped += 1
                continue
            op_objs.append(VendorOperation(
                operation_no=int(vo['رقم العملية'][i] or 0),
                year=clean(vo['العام'][i]),
                supplier_id=sid,
                seq=int(vo['مسلسل'][i]) if vo['مسلسل'][i] not in (None, '') else None,
                offer_status=clean(vo['موقف التقدم'][i]),
                progress_status=clean(vo['موقف التقدم'][i]),
                technical_result=clean(vo['موقف الدراسة الفنية'][i]),
                technical_rejection_reason=clean(vo['سبب الرفض الفنى'][i]),
                certificates_status=clean(vo['موقف الشهادات'][i]),
                compliance=clean(vo['المطابقة الفنية'][i]),
                initial_bond_type=clean(vo['نوع التأمين الإبتدائى'][i]),
                initial_bond_status=clean(vo['موقف التأمين الإبتدائى'][i]),
                final_bond_status=clean(vo['موقف التأمين النهائى'][i]),
                supply_status=clean(vo['موقف التوريد'][i]),
                late_penalty=clean(vo['موقف غرامة التأخير'][i]),
                po_status=clean(vo['موقف إصدار أمر التوريد'][i]),
                notes=clean(vo['ملاحظات'][i]),
            ))
        VendorOperation.objects.all().delete()
        VendorOperation.objects.bulk_create(op_objs, batch_size=1000)
        self.stdout.write(f'VendorOperation: {len(op_objs)} rows (skipped {skipped})')
