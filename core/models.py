from django.conf import settings
from django.db import models


class Agency(models.Model):
    """Agência dona dos dados. Todo dado de negócio pertence a uma agência (multi-agência, D1=B)."""

    name = models.CharField("nome", max_length=120)
    slug = models.SlugField(unique=True)
    timezone = models.CharField(max_length=64, default="America/Sao_Paulo")
    whatsapp_support = models.CharField("WhatsApp de suporte", max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "agência"

    def __str__(self):
        return self.name


class AgencySettings(models.Model):
    """Regras editáveis por agência (nada fixo no código)."""

    agency = models.OneToOneField(Agency, on_delete=models.CASCADE, related_name="settings")
    first_month_days = models.PositiveIntegerField("dias do grupo Primeiro Mês", default=30)
    onboarding_window_days = models.PositiveIntegerField("janela da meta de onboarding (dias)", default=14)
    onboarding_valid_days = models.PositiveIntegerField("dias válidos da meta de onboarding", default=5)
    onboarding_hours = models.PositiveIntegerField("horas da meta de onboarding", default=15)
    monthly_min_valid_days = models.PositiveIntegerField("dias válidos mínimos no mês", default=5)
    monthly_min_hours = models.PositiveIntegerField("horas mínimas no mês", default=15)
    free_exit_days = models.PositiveIntegerField("dias de saída livre", default=15)
    return_wait_days = models.PositiveIntegerField("carência para voltar (dias)", default=90)
    stale_data_days = models.PositiveIntegerField("alerta de importação atrasada após (dias sem importar)", default=2)
    auto_import_deadline_hour = models.PositiveSmallIntegerField(
        "leitura automática: avisar se não chegar até as (hora de Brasília)", default=10,
        help_text="Depois dessa hora, sem a leitura do dia, o painel pede o plano B (subir a planilha).")
    auto_import_max_exits = models.PositiveSmallIntegerField(
        "leitura automática: segurar para conferência com mais saídas que", default=5,
        help_text="Uma leitura com muitas saídas de uma vez não é gravada sozinha: fica esperando alguém conferir.")
    drop_alert_pct = models.PositiveIntegerField("alerta de queda maior que (%)", default=30)
    near_tier_pct = models.PositiveIntegerField("perto do próximo Tier a partir de (%)", default=85)
    no_live_alert_days = models.PositiveIntegerField("alerta sem LIVE após (dias)", default=7)
    no_live_steps = models.CharField("régua sem LIVE (dias, separados por vírgula)", max_length=40, default="4,14,21,30",
                                     help_text="Em cada um desses dias sem LIVE, o criador entra na fila com a mensagem da régua.")
    contact_limit_days = models.PositiveIntegerField("rodízio: dias sem mensagem individual (segunda a sábado)", default=4)
    daily_message_cap = models.PositiveIntegerField("teto de mensagens individuais por gestora por dia", default=30,
                                                    help_text="O que passa do teto fica para o dia seguinte, começando pelo rodízio.")
    restriction_escalate_days = models.PositiveIntegerField("restrição na conta: sobe para as sócias no dia", default=4)
    visit_suggestions_per_day = models.PositiveIntegerField("sugestões de visita por gestora por dia", default=3)
    pause_after_days = models.PositiveIntegerField("fase Pausa: dias sem LIVE", default=4,
                                                   help_text="Quem já fez LIVE e fica esse número de dias sem abrir entra na fase Pausa.")
    academy_all_open_level = models.PositiveSmallIntegerField(
        "Hera Academy: nível que abre todos os módulos", default=3,
        help_text="Quem chega a este nível (inclusive quem vem de outra agência) abre todos os módulos de uma vez. Cursos extras continuam só com liberação da gestão.")
    battle_notice_days = models.PositiveSmallIntegerField(
        "batalha oficial: antecedência mínima do pedido (dias)", default=7,
        help_text="O criador escolhe datas a partir de hoje + este número de dias. É o tempo de a Hera achar o oponente e os dois lados divulgarem.")
    graduation_diamonds = models.PositiveIntegerField("graduação: diamantes em um mês (regra do TikTok)", default=80_000)
    graduation_window_days = models.PositiveIntegerField("graduação: janela a partir da entrada (dias)", default=90,
                                                         help_text="Os 3 primeiros meses de casa. Cada mês com o mínimo de diamantes dentro da janela vale uma graduação.")
    anonymize_after_days = models.PositiveIntegerField("anonimizar dados após saída (dias)", default=180)
    access_code_days = models.PositiveIntegerField("validade do código de acesso ao app (dias)", default=7)
    whatsapp_api_trigger = models.PositiveIntegerField(
        "gatilho para testar API do WhatsApp (mensagens em lote/semana)", null=True, blank=True
    )
    community_brand_posts_per_month = models.PositiveIntegerField(default=1)
    # Teste do app com poucos criadores (etapa 3, passo 3.7): datas e a trava do código de acesso
    app_test_start = models.DateField("teste do app: início", null=True, blank=True)
    app_test_end = models.DateField("teste do app: fim", null=True, blank=True)
    app_test_only_testers = models.BooleanField(
        "teste do app: só quem participa recebe código de acesso", default=False,
        help_text="Ligado, a gestão só consegue gerar código de acesso para os criadores marcados no teste.")
    # Indique e ganhe (passo 4.7; regulamento de novembro de 2026). As faixas de cada mês ficam em "Faixas do Indique e ganhe".
    referral_referrer_min_hours = models.PositiveSmallIntegerField(
        "Indique e ganhe: horas de LIVE de quem indicou no mês", default=25,
        help_text="Para receber o bônus de um mês, quem indicou precisa ter feito estas horas e os dias válidos abaixo naquele mês.")
    referral_referrer_min_days = models.PositiveSmallIntegerField("Indique e ganhe: dias válidos de quem indicou no mês", default=8)
    referral_entry_cutoff_day = models.PositiveSmallIntegerField(
        "Indique e ganhe: entrada até o dia (Mês 1 = mês da entrada)", default=15,
        help_text="Se a pessoa indicada entrar depois deste dia, o Mês 1 passa a ser o mês seguinte.")
    referral_m2_min_diamonds = models.PositiveIntegerField("Indique e ganhe: diamantes mínimos no Mês 2", default=10_000)
    referral_m3_min_diamonds = models.PositiveIntegerField("Indique e ganhe: diamantes mínimos no Mês 3", default=25_000)
    legal_name = models.CharField("razão social (recibos)", max_length=160, blank=True, default="HERA AGÊNCIA E MARKETING DIGITAL")
    cnpj = models.CharField("CNPJ (recibos)", max_length=20, blank=True)
    referral_graduation_bonus = models.DecimalField(
        "Indique e ganhe: bônus único de graduação (R$)", max_digits=8, decimal_places=2, default=50,
        help_text="A pessoa indicada graduou (a mesma regra da graduação acima).")

    class Meta:
        verbose_name = "configurações da agência"
        verbose_name_plural = "configurações da agência"

    def __str__(self):
        return f"Configurações · {self.agency}"


class PartnerGroup(models.Model):
    """Grupo/rede parceira (coluna 'Grupo' do Backstage). 'Não está em um grupo' = Hera direta."""

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="partner_groups")
    name = models.CharField("nome no Backstage", max_length=120)
    is_direct = models.BooleanField("é a própria agência (sem grupo)", default=False)
    streamer_access_enabled = models.BooleanField("streamers deste grupo acessam o app", default=False)

    class Meta:
        unique_together = [("agency", "name")]
        verbose_name = "grupo parceiro"
        verbose_name_plural = "grupos parceiros"

    def __str__(self):
        return self.name


class Role(models.TextChoices):
    ADMIN = "admin", "Admin/CEO"
    GESTORA = "gestora", "Gestora de creators"
    RECRUTADORA = "recrutadora", "Recrutadora"
    CONTEUDO = "conteudo", "Conteúdo"
    FINANCEIRO = "financeiro", "Financeiro"
    ANALISTA = "analista", "Analista (somente leitura)"
    GESTOR_PARCEIRA = "gestor_parceira", "Gestor de parceira (V2)"
    STREAMER = "streamer", "Streamer"


STAFF_ROLES = {Role.ADMIN, Role.GESTORA, Role.RECRUTADORA, Role.CONTEUDO, Role.FINANCEIRO, Role.ANALISTA, Role.GESTOR_PARCEIRA}


class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=Role.choices)
    partner_group = models.ForeignKey(PartnerGroup, null=True, blank=True, on_delete=models.SET_NULL)
    phone = models.CharField("WhatsApp", max_length=30, blank=True)
    active = models.BooleanField(default=True)
    # Só no papel Gestora: quem recebe os itens que não podem esperar quando ela avisa "Hoje não trabalho".
    # Vazio = as sócias. Definido pelas sócias na tela Carteiras (uma sócia ou uma recrutadora).
    covered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
                                   verbose_name="quem cobre quando não trabalha")

    class Meta:
        unique_together = [("user", "agency", "role")]
        verbose_name = "papel"
        verbose_name_plural = "papéis"

    def __str__(self):
        return f"{self.user} · {self.get_role_display()}"


class Consent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="consents")
    version = models.CharField(max_length=20)
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "version")]


class AuditLog(models.Model):
    """Log de ações administrativas (LGPD)."""

    agency = models.ForeignKey(Agency, null=True, blank=True, on_delete=models.SET_NULL)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    target = models.CharField(max_length=200, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-at"]


class AppEvent(models.Model):
    """Eventos de uso (ex.: app_open) para medir streamers ativos por semana."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event = models.CharField(max_length=40)
    at = models.DateTimeField(auto_now_add=True, db_index=True)


class Outbox(models.Model):
    """Fila de envios futuros (WhatsApp API, e-mail, push). No MVP só registra; o envio é ligado na V2."""

    agency = models.ForeignKey(Agency, on_delete=models.CASCADE)
    channel = models.CharField(max_length=20, choices=[("whatsapp", "WhatsApp"), ("email", "E-mail"), ("push", "Push")])
    to = models.CharField(max_length=200)
    template_code = models.CharField(max_length=40, blank=True)
    body = models.TextField()
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
