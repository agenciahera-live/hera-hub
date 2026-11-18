from django.conf import settings
from django.db import models

from core.models import Agency
from crm.models import Creator

User = settings.AUTH_USER_MODEL


class ImportTemplate(models.Model):
    """Mapeamento reutilizável cabeçalho → campo (ex.: 'Backstage PT', 'Task EN')."""

    KINDS = [("backstage", "Dados do criador (Backstage)"), ("task", "Task (fechamento)")]
    agency = models.ForeignKey(Agency, null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    kind = models.CharField(max_length=20, choices=KINDS)
    signature = models.JSONField(default=list, help_text="cabeçalhos que identificam este formato")
    column_map = models.JSONField(default=dict, help_text="{cabeçalho: campo}")

    def __str__(self):
        return self.name


class ImportKey(models.Model):
    """Chave da porta de importação (leitura automática do Backstage enviada pelo Claude).

    Identifica a agência quando o arquivo chega sem login. O banco guarda só o resumo (hash) da chave:
    o texto aparece uma vez, na hora em que as sócias geram. Uma chave ativa por agência."""

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="import_keys")
    key_hash = models.CharField(max_length=64, unique=True)
    hint = models.CharField("começo da chave", max_length=12)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ImportBatch(models.Model):
    STATUS = [("preview", "Pré-visualização"), ("committed", "Gravado"), ("reverted", "Desfeito"), ("failed", "Falhou")]
    VIAS = [("tela", "Enviado pela tela"), ("porta", "Leitura automática")]
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    via = models.CharField("como chegou", max_length=10, choices=VIAS, default="tela")
    template = models.ForeignKey(ImportTemplate, null=True, on_delete=models.SET_NULL)
    kind = models.CharField(max_length=20)
    filename = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64, db_index=True)
    file = models.FileField(upload_to="imports/", null=True, blank=True)
    period_start = models.DateField(null=True)
    period_end = models.DateField(null=True)
    exported_at = models.DateTimeField(null=True)
    uploaded_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=STATUS, default="preview")
    counts = models.JSONField(default=dict)
    mapping = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    committed_at = models.DateTimeField(null=True, blank=True)
    reverted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ImportRow(models.Model):
    ACTIONS = [("new", "Novo"), ("updated", "Atualizado"), ("unchanged", "Sem mudança"), ("exit", "Saída detectada"), ("error", "Erro"), ("skip", "Ignorado")]
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="rows")
    row_number = models.PositiveIntegerField()
    raw = models.JSONField()
    parsed = models.JSONField(default=dict)
    creator = models.ForeignKey(Creator, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=20, choices=ACTIONS)
    errors = models.TextField(blank=True)
    previous = models.JSONField(null=True, blank=True, help_text="snapshot anterior, para desfazer")


class CreatorSnapshot(models.Model):
    """Foto acumulada do período, uma por creator × período. Base de todas as métricas."""

    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="snapshots")
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="snapshots")
    period_start = models.DateField()
    period_end = models.DateField()
    exported_at = models.DateTimeField()
    username_at = models.CharField(max_length=120, blank=True)
    group_name = models.CharField(max_length=120, blank=True)
    agent_email = models.CharField(max_length=200, blank=True)
    diamonds = models.BigIntegerField(default=0)
    live_seconds = models.BigIntegerField(default=0)
    valid_days = models.IntegerField(default=0)
    new_followers = models.IntegerField(default=0)
    streams = models.IntegerField(default=0)
    lm_diamonds = models.BigIntegerField(null=True)
    lm_live_seconds = models.BigIntegerField(null=True)
    lm_valid_days = models.IntegerField(null=True)
    lm_new_followers = models.IntegerField(null=True)
    lm_streams = models.IntegerField(null=True)
    pct_diamonds = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    pct_hours = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    pct_valid_days = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    pct_followers = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    pct_streams = models.DecimalField(max_digits=12, decimal_places=6, null=True)
    battles = models.IntegerField(default=0)
    battle_diamonds = models.BigIntegerField(default=0)
    guest_diamonds = models.BigIntegerField(default=0)
    new_fans = models.IntegerField(null=True)
    graduation_status = models.CharField(max_length=120, blank=True)
    level_status = models.CharField(max_length=60, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("creator", "period_start", "period_end")]
        ordering = ["period_end"]
        indexes = [models.Index(fields=["creator", "period_start"])]

    @property
    def hours(self):
        return self.live_seconds / 3600


class MonthlyResult(models.Model):
    """Mês fechado por creator (Tier oficial sai daqui — D5)."""

    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="monthly")
    month = models.DateField()
    diamonds = models.BigIntegerField(default=0)
    live_seconds = models.BigIntegerField(default=0)
    valid_days = models.IntegerField(default=0)
    streams = models.IntegerField(null=True)
    battles = models.IntegerField(null=True)
    source = models.CharField(max_length=20)  # task | backstage | last_month
    tier = models.PositiveSmallIntegerField(null=True)

    class Meta:
        unique_together = [("creator", "month")]
        ordering = ["month"]


class TaskResult(models.Model):
    """Exportação Task. Colunas de bônus são ignoradas por decisão (29/09)."""

    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="task_results")
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="task_results")
    month = models.DateField()
    diamonds = models.BigIntegerField()
    valid_days = models.IntegerField()
    live_hours = models.DecimalField(max_digits=10, decimal_places=3)
    is_violative = models.BooleanField(default=False)
    rookie_at_join = models.BooleanField(null=True)

    class Meta:
        unique_together = [("creator", "month")]


class TierRule(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="tier_rules")
    tier = models.PositiveSmallIntegerField()
    min_diamonds = models.BigIntegerField()
    phase = models.CharField(max_length=60)

    class Meta:
        unique_together = [("agency", "tier")]
        ordering = ["tier"]

    def __str__(self):
        return f"Tier {self.tier} (≥ {self.min_diamonds:,})".replace(",", ".")


class GroupRule(models.Model):
    """Grupo de comunidade exibido ao streamer (Bronze, Prata...). 'Primeiro Mês' vem do tempo de casa."""

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="group_rules")
    name = models.CharField(max_length=40)
    tier_min = models.PositiveSmallIntegerField()
    tier_max = models.PositiveSmallIntegerField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.name} (Tier {self.tier_min}–{self.tier_max})"


class CreatorGroupHistory(models.Model):
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="group_history")
    group_name = models.CharField(max_length=40)
    since = models.DateField()
    until = models.DateField(null=True, blank=True)
    reason = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["-since"]
