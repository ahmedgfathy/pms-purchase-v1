from django.core.management.base import BaseCommand

from access_parser import AccessParser

from audit.models import record
from rfq.models import Client, CostCenter, Location, Project


def val(row, key):
    v = row.get(key)
    if v is None or v == '' or v == b'':
        return ''
    return str(v).strip()


def access_rows(db, name):
    tab = db.parse_table(name)
    cols = [c for c in tab.keys() if c != 'rows']
    if not cols:
        return []
    return [{c: tab[c][i] for c in cols} for i in range(len(tab[cols[0]]))]


class Command(BaseCommand):
    help = 'Import reference data (clients, cost centers, locations, projects) from the legacy 2026.accdb.'

    def add_arguments(self, parser):
        parser.add_argument('--file', default='data/2026.accdb')

    def handle(self, *args, **options):
        db = AccessParser(options['file'])
        counts = {}

        rows = access_rows(db, 'Client Code')
        for r in rows:
            code = val(r, 'Client code')
            if not code:
                continue
            Client.objects.update_or_create(code=code, defaults={'name': val(r, 'Client name'), 'note': val(r, 'note')})
        counts['clients'] = Client.objects.count()

        rows = access_rows(db, 'Cost Center')
        for r in rows:
            code = val(r, 'Cost code')
            if not code:
                continue
            CostCenter.objects.update_or_create(code=code, defaults={'name': val(r, 'Cost name'), 'note': val(r, 'note')})
        counts['cost_centers'] = CostCenter.objects.count()

        rows = access_rows(db, 'Location Code')
        for r in rows:
            code = val(r, 'Location code')
            if not code:
                continue
            Location.objects.update_or_create(code=code, defaults={'name': val(r, 'Location name'), 'note': val(r, 'note')})
        counts['locations'] = Location.objects.count()

        clients_by_code = {c.code: c for c in Client.objects.all()}
        rows = access_rows(db, 'Project Code')
        for r in rows:
            code = val(r, 'project code')
            if not code:
                continue
            client = clients_by_code.get(val(r, 'Client name')) or None
            Project.objects.update_or_create(
                code=code,
                defaults={'name': val(r, 'project name'), 'client': client, 'note': val(r, 'note')})
        counts['projects'] = Project.objects.count()

        record('CREATE', module='rfq', model_label='legacy.import',
               object_repr=f"Imported lookups from {options['file']}: {counts}")
        self.stdout.write(self.style.SUCCESS(f"Imported from Access: {counts}"))
