from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from access_parser import AccessParser

from rfq.models import RequestForQuotation
from vendors.models import Supplier, TenderInvitation, VendorOperation


class Command(BaseCommand):
    help = 'Import vendor lists from Vendor VS Tasks via Oprations.ALL → Tasks sub link'

    def add_arguments(self, parser):
        parser.add_argument('--db', default='data/2026.accdb')

    @transaction.atomic
    def handle(self, *args, **opts):
        db = AccessParser(opts['db'])
        opr = db.parse_table('Oprations')
        tasks_sub = db.parse_table('Tasks sub')
        vt = db.parse_table('Vendor VS Tasks')

        # Build Tasks sub lookup: ID sub → sub code
        sub_code_map = {}
        for j in range(len(tasks_sub['ID sub'])):
            sub_code_map[tasks_sub['ID sub'][j]] = tasks_sub['كود النشاط الفرعى'][j]

        # Build Vendor VS Tasks lookup: sub code → [supplier_ids]
        vt_by_sub = defaultdict(set)
        for k in range(len(vt['كود النشاط الفرعى'])):
            sc = vt['كود النشاط الفرعى'][k]
            supplier_id = vt['Supplier ID'][k]
            if supplier_id:
                vt_by_sub[sc].add(supplier_id)

        # Build existing RFQ seq → pk map
        rfq_by_seq = {rfq.seq: rfq.pk for rfq in RequestForQuotation.objects.all()}

        # Build existing invitation set to avoid duplicates
        existing_invites = set(
            TenderInvitation.objects.values_list('rfq_id', 'supplier_id')
        )

        # Get valid supplier_no → pk map (convert string supplier_nos to int for matching)
        supplier_no_to_pk = {}
        for s in Supplier.objects.all():
            try:
                supplier_no_to_pk[int(s.supplier_no)] = s.pk
            except (ValueError, TypeError):
                supplier_no_to_pk[s.supplier_no] = s.pk

        created = 0
        skipped = 0
        no_rfq = 0
        no_suppliers = 0

        for i in range(len(opr['رقم العملية'])):
            op_no = opr['رقم العملية'][i]
            all_val = opr['ALL'][i]

            rfq_pk = rfq_by_seq.get(op_no)
            if not rfq_pk:
                no_rfq += 1
                continue

            if all_val not in sub_code_map:
                skipped += 1
                continue

            sub_code = sub_code_map[all_val]
            supplier_ids = vt_by_sub.get(sub_code, set())

            if not supplier_ids:
                no_suppliers += 1
                continue

            for sid in supplier_ids:
                supplier_pk = supplier_no_to_pk.get(sid)
                if not supplier_pk:
                    continue
                if (rfq_pk, supplier_pk) not in existing_invites:
                    inv = TenderInvitation(
                        rfq_id=rfq_pk,
                        supplier_id=supplier_pk,
                        offer_status='not_submitted',
                        progress_status='not_yet',
                        technical_result='pending',
                        certificates_status='not_yet',
                        initial_bond_type='none',
                        initial_bond_status='not_yet',
                        final_bond_status='not_yet',
                        supply_status='not_yet',
                        late_penalty='none',
                        po_status='not_yet',
                    )
                    inv.save()
                    existing_invites.add((rfq_pk, supplier_pk))
                    created += 1

        self.stdout.write(f'VendorVS Tasks → TenderInvitation: created {created}')
        self.stdout.write(f'  Skipped (no ALL link): {skipped}')
        self.stdout.write(f'  Skipped (no RFQ): {no_rfq}')
        self.stdout.write(f'  Skipped (no suppliers): {no_suppliers}')
        self.stdout.write(f'Total TenderInvitations: {TenderInvitation.objects.count()}')
