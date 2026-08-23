from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from access_parser import AccessParser

from rfq.models import Client, CostCenter, Location, Project, RequestForQuotation


REGION_MAP = {
    'القاهرة': 'cairo',
    'الإسكندرية': 'alexandria',
    'الاسكندرية': 'alexandria',
    'السuez': 'suez',
    'السويس': 'suez',
    'البحر الأحمر': 'red_sea',
    'البحر الاحمر': 'red_sea',
    'سيناء': 'sinai',
    'الدلتا': 'delta',
}

METHOD_MAP = {
    'أمر مباشر': 'direct_order',
    'مناقصة عامة': 'public_tender',
    'مناقصة محدودة': 'limited_tender',
    'استعلام سعر': 'price_inquiry',
    'مناقصة محدودة عاجله': 'limited_tender',
    'مناقصة عامة عاجله': 'public_tender',
    'عاجله': 'direct_order',
    'استعجال': 'direct_order',
}


class Command(BaseCommand):
    help = 'Link RFQ records to Location/Client/Project/CostCenter via legacy codes'

    def handle(self, *args, **opts):
        db = AccessParser('data/2026.accdb')
        opr = db.parse_table('Oprations')

        loc_map = {loc.code: loc.pk for loc in Location.objects.all()}
        client_map = {c.code: c.pk for c in Client.objects.all()}
        proj_map = {p.code: p.pk for p in Project.objects.all()}
        cc_map = {cc.code: cc.pk for cc in CostCenter.objects.all()}

        rfq_by_seq = {rfq.seq: rfq for rfq in RequestForQuotation.objects.all()}

        updated = 0
        for i in range(len(opr['رقم العملية'])):
            op_no = opr['رقم العملية'][i]
            rfq = rfq_by_seq.get(op_no)
            if not rfq:
                continue

            changes = {}

            # Location Code
            loc_code = str(opr['Location Code'][i] or '').strip()
            if loc_code and not rfq.location_id and loc_code in loc_map:
                changes['location_id'] = loc_map[loc_code]

            # Client Code
            client_code = str(opr['Client Code'][i] or '').strip()
            if client_code and not rfq.client_id and client_code in client_map:
                changes['client_id'] = client_map[client_code]

            # Project Code
            proj_code = str(opr['project code'][i] or '').strip()
            if proj_code and not rfq.project_id and proj_code in proj_map:
                changes['project_id'] = proj_map[proj_code]

            # Cost code
            cc_code = str(opr['Cost code'][i] or '').strip()
            if cc_code and not rfq.cost_center_id and cc_code in cc_map:
                changes['cost_center_id'] = cc_map[cc_code]

            # Region (Arabic → English key)
            region_ar = str(opr['المنطقة'][i] or '').strip()
            if region_ar and not rfq.region:
                for ar, en in REGION_MAP.items():
                    if ar in region_ar:
                        changes['region'] = en
                        break

            # Execution method
            method_ar = str(opr['طريقة التنفيذ'][i] or '').strip()
            if method_ar and rfq.execution_method == 'direct_order':
                for ar, en in METHOD_MAP.items():
                    if ar == method_ar:
                        changes['execution_method'] = en
                        break

            # Estimated value (might be None/0 for some)
            val = opr['إجمالى القيمة التقديرية'][i]
            if val and not rfq.estimated_value:
                try:
                    changes['estimated_value'] = float(str(val).replace(',', ''))
                except (ValueError, TypeError):
                    pass

            # Currency
            currency_ar = str(opr['العملة'][i] or '').strip()
            if currency_ar and rfq.currency == 'EGP':
                if 'دولار' in currency_ar or 'USD' in currency_ar.upper():
                    changes['currency'] = 'USD'
                elif 'يورو' in currency_ar or 'EUR' in currency_ar.upper():
                    changes['currency'] = 'EUR'

            if changes:
                for k, v in changes.items():
                    setattr(rfq, k, v)
                rfq.save(update_fields=list(changes.keys()))
                updated += 1

        self.stdout.write(f'Updated {updated} RFQs with FK links + region + method')
        self.stdout.write(f'  With location: {RequestForQuotation.objects.exclude(location=None).count()}')
        self.stdout.write(f'  With client: {RequestForQuotation.objects.exclude(client=None).count()}')
        self.stdout.write(f'  With project: {RequestForQuotation.objects.exclude(project=None).count()}')
        self.stdout.write(f'  With cost_center: {RequestForQuotation.objects.exclude(cost_center=None).count()}')
        self.stdout.write(f'  With region: {RequestForQuotation.objects.exclude(region="").count()}')
