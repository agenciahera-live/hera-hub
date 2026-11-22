"""Indique e ganhe (passo 4.7): faixas do regulamento de novembro de 2026 para as agências que já existem, e uma
indicação "em andamento" para cada "indicado por" já preenchido na ficha (as sócias validam na tela Indicações)."""
from django.db import migrations
from django.utils import timezone

BANDS = [
    (1, 25, 8, 20), (1, 40, 14, 30), (1, 60, 17, 40), (1, 80, 20, 50), (1, 100, 22, 65),
    (2, 40, 14, 10), (2, 60, 17, 15), (2, 80, 20, 20), (2, 100, 22, 30),
    (3, 40, 14, 5), (3, 60, 17, 10), (3, 80, 20, 15), (3, 100, 22, 20),
]


def forward(apps, schema_editor):
    schema_editor.execute("SELECT set_config('app.system', 'on', false)")
    Agency = apps.get_model("core", "Agency")
    Band = apps.get_model("crm", "ReferralBand")
    Creator = apps.get_model("crm", "Creator")
    Referral = apps.get_model("crm", "Referral")
    for ag in Agency.objects.all():
        if not Band.objects.filter(agency=ag).exists():
            Band.objects.bulk_create([Band(agency=ag, program_month=m, min_hours=h, min_valid_days=d, amount=v) for m, h, d, v in BANDS])
    now = timezone.now()
    for c in Creator.objects.filter(referred_by__isnull=False):
        if not Referral.objects.filter(referred=c).exists():
            Referral.objects.create(agency_id=c.agency_id, referred=c, referrer_id=c.referred_by_id, registered_at=now)
    schema_editor.execute("SELECT set_config('app.system', 'off', false)")


class Migration(migrations.Migration):
    dependencies = [("crm", "0014_indique_e_ganhe"), ("core", "0014_indique_e_ganhe")]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
