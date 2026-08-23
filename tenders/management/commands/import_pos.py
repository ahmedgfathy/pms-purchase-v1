from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from access_parser import AccessParser

from audit.models import record
from tenders.models import PurchaseOrder
from vendors.models import Supplier


def s(v, limit=None):
    if v is None or v == '' or v == b'':
        return ''
    out = str(v).strip()
    return out[:limit] if limit else out


def dt(v):
    txt = s(v)
    if not txt:
        return None
    try:
        return datetime.strptime(txt, '%Y-%m-%d %H:%M:%S').date()
    except ValueError:
        return None


def num(v):
    txt = s(v).replace(',', '')
    try:
        return float(txt) if txt else None
    except ValueError:
        return None


def integer(v):
    n = num(v)
    return int(n) if n is not None else None


PAYMENT_MAP = {
    'شيك مقابل الفحص و الإستلام': 'cheque_on_inspection',
    'شيك بعد الفحص و الإستلام': 'cheque_after_receipt',
}
CURRENCY_MAP = {'جنيه مصرى': 'EGP', 'دولار أمريكى': 'USD', 'يورو': 'EUR'}


class Command(BaseCommand):
    help = 'Import legacy purchase orders (46 rows) from 2026.accdb.'

    def add_arguments(self, parser):
        parser.add_argument('--file', default='data/2026.accdb')

    def handle(self, *args, **options):
        db = AccessParser(options['file'])
        tab = db.parse_table('Perchase Orders')
        cols = [c for c in tab.keys() if c != 'rows']
        rows = [{c: tab[c][i] for c in cols} for i in range(len(tab[cols[0]]))]

        rfq_model = PurchaseOrder._meta.get_field('rfq').related_model
        rfqs_by_op = {r.rfq_no: r for r in rfq_model.objects.all()}
        sup_by_no = dict(Supplier.objects.values_list('supplier_no', 'id'))

        created = updated = 0
        with transaction.atomic():
            for i, r in enumerate(rows):
                op_no = s(r.get('رقم العملية'))
                defaults = {
                    'legacy_op_no': op_no,
                    'po_no': s(r.get('رقم أمر التوريد')) or f"LEGACY-{i + 1}",
                    'po_date': dt(r.get('تاريخ أمر التوريد')),
                    'year': integer(r.get('العام')) or 2026,
                    'items_description': s(r.get('بيان المهمات بامر التوريد')),
                    'value': num(r.get('قيمة أمر التوريد')),
                    'currency': CURRENCY_MAP.get(s(r.get('العملة')), 'EGP'),
                    'payment_method': PAYMENT_MAP.get(s(r.get('طريقة الدفع')), ''),
                    'cheque_no': s(r.get('رقم الشيك'), 40),
                    'cheque_date': dt(r.get('تاريخ  الشيك')),
                    'lc_open_date': dt(r.get('تاريخ فتح الإعتماد')),
                    'lc_receipt_date': dt(r.get('تاريخ إستلام الــ L / C')),
                    'bank_name': s(r.get('أسم البنك'), 100),
                    'amount_egp': num(r.get('المبلغ بالجنيه')),
                    'amount_usd': num(r.get('المبلغ بالدولار')),
                    'delivery_days': integer(r.get('مدة التوريد')),
                    'delivery_start_date': dt(r.get('بداية إحتساب مدة التوريد')),
                    'expected_delivery_date': dt(r.get('التاريخ المتوقع للتوريد')),
                    'actual_delivery_date': dt(r.get('تاريخ التوريد الفعلى')),
                    'delivery_place': s(r.get('مكان التوريد'), 200),
                    'shipping_method': s(r.get('طريقة الشحن'), 100),
                    'goods_receipt_no': s(r.get('رقم إذن الإضافة'), 40),
                    'shipping_docs_date': dt(r.get('تاريخ إستلام مستندات الشحن')),
                    'customs_clearance_date': dt(r.get('تاريخ التخليص')),
                    'disbursement_request_date': dt(r.get('تاريخ طلب الصرف')),
                    'bond_refund_date': dt(r.get('تاريخ رد التأمين')),
                    'followup_by': s(r.get('أسم المتابع'), 150),
                    'sap_no': s(r.get('SAP NO'), 30),
                    'notes': s(r.get('ملاحظات')),
                }
                rfq = rfqs_by_op.get(op_no)
                if rfq:
                    defaults['rfq'] = rfq
                sup = sup_by_no.get(s(r.get('Supplier ID')))
                if sup:
                    defaults['supplier_id'] = sup

                obj, was_created = PurchaseOrder.objects.update_or_create(
                    po_no=defaults['po_no'], year=defaults['year'], defaults=defaults)
                created += was_created
                updated += not was_created

        record('CREATE', module='tender', model_label='legacy.import',
               object_repr=f"Imported {created} POs ({updated} updated) from data/2026.accdb")
        self.stdout.write(self.style.SUCCESS(f'POs: {created} created, {updated} updated, total {PurchaseOrder.objects.count()}'))
