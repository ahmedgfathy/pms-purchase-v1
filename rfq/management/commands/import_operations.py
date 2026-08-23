import datetime
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from access_parser import AccessParser

from rfq.models import RequestForQuotation
from tenders.models import PurchaseOrder
from vendors.models import Supplier, TenderInvitation, VendorOperation


def clean(v):
    if v is None:
        return ''
    s = str(v).strip()
    return '' if s in ('0', 'None') else s


def parse_date(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s == '0' or s == 'None':
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


ADMIN_MAP = {
    'المشتريات المحلية': 'local_purchasing',
    'المشتريات الخارجية': 'foreign_purchasing',
}
METHOD_MAP = {
    'أمر مباشر': 'direct_order',
    'مناقصة عامة': 'public_tender',
    'مناقصة محدودة': 'limited_tender',
    'استعلام سعر': 'price_inquiry',
}
STATUS_MAP = {
    'open': 'new',
    'closed': 'approved',
    'cancelled': 'cancelled',
}


def parse_num(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s in ('0', 'None'):
        return None
    # Arabic-Indic numerals → Western
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    for i, d in enumerate(arabic_digits):
        s = s.replace(d, str(i))
    s = s.replace(',', '').replace(' ', '')
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


class Command(BaseCommand):
    help = 'Import all tender operations from legacy Oprations table'

    def add_arguments(self, parser):
        parser.add_argument('--db', default='data/2026.accdb')

    @transaction.atomic
    def handle(self, *args, **opts):
        db = AccessParser(opts['db'])
        opr = db.parse_table('Oprations')
        n = len(opr['رقم العملية'])

        # Build existing operation numbers to skip
        existing_ops = set(
            RequestForQuotation.objects.exclude(seq=None).values_list('seq', flat=True)
        )
        self.stdout.write(f'Existing RFQs with seq: {len(existing_ops)}')

        # Import Oprations as RequestForQuotation
        imported = 0
        skipped = 0
        op_to_rfq = {}  # operation_no → rfq pk
        used_seqs = set(existing_ops)

        for i in range(n):
            op_no = opr['رقم العملية'][i]
            if op_no in used_seqs:
                skipped += 1
                continue

            year = opr['العام'][i]
            try:
                year_int = int(str(year).strip()) if year else 2026
            except (ValueError, TypeError):
                year_int = 2026

            # Generate rfq_no: OPR-{year}-{op_no:04d}
            rfq_no = f'OPR-{year_int}-{op_no:04d}'

            admin_raw = clean(opr['إدارة الملف'][i])
            method_raw = clean(opr['طريقة التنفيذ'][i])
            status_raw = clean(opr['الموقف العام'][i]).lower()

            rfq = RequestForQuotation(
                rfq_no=rfq_no,
                year=year_int,
                seq=op_no,
                title=clean(opr['بيان المهمات'][i]) or f'Operation {op_no}',
                technical_specs=clean(opr['المواصفات الفنية'][i]),
                requesting_entity=clean(opr['الجهة الطالبة'][i]),
                requester_contact=clean(opr['منفذ سجل الموردين'][i] or opr['أسم المتابع'][i]),
                request_date=parse_date(opr['تاريخ إستلام طلب المهمات'][i]),
                administration=ADMIN_MAP.get(admin_raw, 'local_purchasing'),
                execution_method=METHOD_MAP.get(method_raw, 'direct_order'),
                estimated_value=parse_num(opr['إجمالى القيمة التقديرية'][i]),
                currency=clean(opr['العملة'][i])[:3] or 'EGP',
                status=STATUS_MAP.get(status_raw, 'new'),
                notes=clean(opr['ملاحظات'][i]),
                # Milestone dates
                tender_issue_date=parse_date(opr['تاريخ الطرح'][i]),
                technical_opening_date=parse_date(opr['تاريخ الفض الفنى'][i]),
                technical_report_date=parse_date(opr['تاريخ التقرير الفنى النهائى'][i]),
                offers_to_requester_date=parse_date(opr['تاريخ إرسال العروض للجهة الطالبة'][i]),
                financial_opening_date=parse_date(opr['تاريخ الفض المالى'][i]),
                committee_presentation_date=parse_date(opr['تاريخ العرض على لجنة البت'][i]),
                committee_approval_date=parse_date(opr['تاريخ إعتماد لجنة البت'][i]),
            )
            rfq.save()
            op_to_rfq[op_no] = rfq.pk
            used_seqs.add(op_no)
            imported += 1

        self.stdout.write(f'Oprations → RFQ: imported {imported}, skipped {skipped}')

        # Link VendorOperation → TenderInvitation
        # First, build a map of operation_no → rfq pk
        all_rfq_by_seq = {rfq.seq: rfq.pk for rfq in RequestForQuotation.objects.all()}

        # Get existing invitations to skip
        existing_invites = set(
            TenderInvitation.objects.values_list('rfq_id', 'supplier_id')
        )

        invites_created = 0
        invites_skipped = 0
        vo_qs = VendorOperation.objects.all()

        # Group by operation_no for efficiency
        vo_by_op = defaultdict(list)
        for vo in vo_qs:
            vo_by_op[vo.operation_no].append(vo)

        for op_no, vos in vo_by_op.items():
            rfq_pk = all_rfq_by_seq.get(op_no)
            if not rfq_pk:
                invites_skipped += len(vos)
                continue

            for vo in vos:
                if (rfq_pk, vo.supplier_id) in existing_invites:
                    invites_skipped += 1
                    continue

                # Map legacy status values to our choices
                offer_map = {
                    'قدم': 'submitted',
                    'لم يقدم': 'not_submitted',
                    'قدم إعتذار': 'withdrew',
                }
                tech_map = {
                    'مطابق فنياً': 'passed',
                    'مطابق لبعض البنود': 'partial',
                    'غير مطابق فنياً': 'failed',
                }
                supply_map = {
                    'تم التوريد': 'on_time',
                    'لم يتم التوريد': 'not_yet',
                }

                inv = TenderInvitation(
                    rfq_id=rfq_pk,
                    supplier_id=vo.supplier_id,
                    seq=vo.seq or 0,
                    offer_status=offer_map.get(vo.offer_status, 'not_submitted'),
                    progress_status='submitted' if vo.offer_status == 'قدم' else 'not_yet',
                    technical_result=tech_map.get(vo.technical_result, 'pending'),
                    technical_rejection_reason=vo.technical_rejection_reason,
                    certificates_status='accepted' if 'مقبول' in vo.certificates_status else 'not_yet',
                    initial_bond_type=vo.initial_bond_type or 'none',
                    initial_bond_status='submitted' if vo.initial_bond_status not in ('', '0') else 'not_yet',
                    final_bond_status='submitted' if vo.final_bond_status not in ('', '0') else 'not_yet',
                    supply_status=supply_map.get(vo.supply_status, 'not_yet'),
                    late_penalty='due' if 'غرامة' in vo.late_penalty else 'none',
                    po_status='accepted' if 'مقبول' in vo.po_status else 'not_yet',
                    notes=vo.notes,
                )
                inv.save()
                invites_created += 1
                existing_invites.add((rfq_pk, vo.supplier_id))

        self.stdout.write(f'VendorOperation → TenderInvitation: created {invites_created}, skipped {invites_skipped}')

        # Link PurchaseOrder to RFQ via legacy_op_no
        po_linked = 0
        for po in PurchaseOrder.objects.exclude(legacy_op_no=''):
            try:
                op_no = int(po.legacy_op_no)
            except (ValueError, TypeError):
                continue
            rfq_pk = all_rfq_by_seq.get(op_no)
            if rfq_pk and not po.rfq_id:
                po.rfq_id = rfq_pk
                po.save(update_fields=['rfq_id'])
                po_linked += 1

        self.stdout.write(f'PurchaseOrder → RFQ: linked {po_linked}')

        # Summary
        self.stdout.write(f'\nFinal counts:')
        self.stdout.write(f'  RFQs: {RequestForQuotation.objects.count()}')
        self.stdout.write(f'  TenderInvitations: {TenderInvitation.objects.count()}')
        self.stdout.write(f'  PurchaseOrders: {PurchaseOrder.objects.count()}')
