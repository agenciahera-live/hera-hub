"""Cadastros de conteúdo e configurações (Admin e Conteúdo)."""
from django import forms
from django.contrib import admin

from core.access import get_agency
from core.models import Agency, AgencySettings, AuditLog, Membership, PartnerGroup
from crm.models import OnboardingItem, ReferralBand
from data.models import GroupRule, ImportTemplate, TierRule
from engage import models as M
from engage.services import publish_announcement

GROUP_CHOICES = [(g, g) for g in ["Primeiro Mês", "Bronze", "Prata", "Ouro", "Diamante"]]
TIER_CHOICES = [(str(t), f"Tier {t}") for t in range(1, 11)]


class AudienceForm(forms.ModelForm):
    audience_groups = forms.MultipleChoiceField(label="Grupos (vazio = todos)", choices=GROUP_CHOICES, required=False, widget=forms.CheckboxSelectMultiple)
    audience_tiers = forms.MultipleChoiceField(label="Tiers (vazio = todos)", choices=TIER_CHOICES, required=False, widget=forms.CheckboxSelectMultiple)

    def clean_audience_tiers(self):
        return [int(t) for t in self.cleaned_data["audience_tiers"]]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        if self.instance.pk:
            self.initial["audience_tiers"] = [str(t) for t in (self.instance.audience_tiers or [])]


class AgencyScopedAdmin(admin.ModelAdmin):
    """Mostra e grava sempre na agência do usuário logado."""

    agency_field = "agency"
    exclude = ("agency",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        ag = get_agency(request.user)
        return qs.filter(**{self.agency_field: ag}) if ag else qs.none()

    def save_model(self, request, obj, form, change):
        if not change and hasattr(obj, "agency_id") and not obj.agency_id:
            obj.agency = get_agency(request.user)
        super().save_model(request, obj, form, change)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "audience_partners":
            kwargs["queryset"] = PartnerGroup.objects.filter(agency=get_agency(request.user))
            kwargs["widget"] = forms.CheckboxSelectMultiple
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class ParticipantInline(admin.TabularInline):
    model = M.CampaignParticipant
    extra = 1
    verbose_name = "participante (lista fechada)"
    verbose_name_plural = "participantes (deixe vazio para usar o público acima)"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "creator":
            from crm.models import Creator

            kwargs["queryset"] = Creator.objects.filter(agency=get_agency(request.user)).exclude(status__in=["saiu", "anonimizado"]).order_by("username")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(M.Campaign)
class CampaignAdmin(AgencyScopedAdmin):
    form = AudienceForm
    inlines = [ParticipantInline]
    list_display = ("name", "source", "start", "end", "metric", "published")
    list_filter = ("source", "published")
    exclude = ("agency",)


@admin.register(M.Announcement)
class AnnouncementAdmin(AgencyScopedAdmin):
    form = AudienceForm
    list_display = ("title", "publish_at", "pinned", "notified")
    exclude = ("agency", "created_by")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        from django.utils import timezone

        if form.instance.publish_at <= timezone.now():
            publish_announcement(form.instance)


class LessonInline(admin.TabularInline):
    model = M.Lesson
    extra = 1


@admin.register(M.Course)
class CourseAdmin(AgencyScopedAdmin):
    form = AudienceForm
    inlines = [LessonInline]
    list_display = ("title", "order", "opens_on", "opens_level", "published")
    fields = ("title", "description", "order", "opens_on", "opens_level", "published",
              "audience_groups", "audience_tiers", "audience_partners", "only_first_month")


@admin.register(M.Tip)
class TipAdmin(AgencyScopedAdmin):
    form = AudienceForm
    list_display = ("text", "active")


@admin.register(M.PartnerOffer)
class OfferAdmin(AgencyScopedAdmin):
    form = AudienceForm
    list_display = ("brand", "title", "category", "coupon", "affiliate", "active", "valid_until")


class QuestionInline(admin.TabularInline):
    model = M.SurveyQuestion
    extra = 1


@admin.register(M.Survey)
class SurveyAdmin(AgencyScopedAdmin):
    form = AudienceForm
    inlines = [QuestionInline]
    list_display = ("title", "opens_at", "closes_at", "anonymous")


@admin.register(M.FaqItem)
class FaqAdmin(AgencyScopedAdmin):
    list_display = ("question", "category", "helpful", "not_helpful", "active")
    list_filter = ("category", "active")
    search_fields = ("question", "keywords", "answer")


@admin.register(M.MessageTemplate)
class TemplateAdmin(AgencyScopedAdmin):
    """A tela própria da biblioteca é /gestao/mensagens/. Aqui vale a mesma regra: verificador de tom e histórico de versões."""

    list_display = ("code", "variant", "stage", "title", "source")
    list_filter = ("stage", "source")
    search_fields = ("code", "title", "body")
    exclude = ("agency", "marketing")

    def save_model(self, request, obj, form, change):
        obj._editor = request.user  # o sinal em engage/apps.py guarda a versão anterior com quem mudou
        super().save_model(request, obj, form, change)


@admin.register(TierRule)
class TierRuleAdmin(AgencyScopedAdmin):
    list_display = ("tier", "min_diamonds", "phase")


@admin.register(GroupRule)
class GroupRuleAdmin(AgencyScopedAdmin):
    list_display = ("name", "tier_min", "tier_max", "order")


@admin.register(OnboardingItem)
class OnboardingItemAdmin(AgencyScopedAdmin):
    list_display = ("order", "day", "label", "anchor", "auto_rule")


@admin.register(PartnerGroup)
class PartnerGroupAdmin(AgencyScopedAdmin):
    list_display = ("name", "is_direct", "streamer_access_enabled")


@admin.register(ReferralBand)
class ReferralBandAdmin(AgencyScopedAdmin):
    """Faixas do Indique e ganhe (passo 4.7): mês da pessoa indicada, horas e dias válidos mínimos e o bônus."""

    list_display = ("program_month", "min_hours", "min_valid_days", "amount")
    list_filter = ("program_month",)


@admin.register(AgencySettings)
class AgencySettingsAdmin(AgencyScopedAdmin):
    def has_add_permission(self, request):
        return False


@admin.register(Membership)
class MembershipAdmin(AgencyScopedAdmin):
    exclude = ("agency", "covered_by")  # "quem cobre" é definido na tela Carteiras (só sócia ou recrutadora)
    list_display = ("user", "role", "phone", "active")
    list_filter = ("role", "active")
    search_fields = ("user__email",)


@admin.register(ImportTemplate)
class ImportTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "agency")


@admin.register(AuditLog)
class AuditLogAdmin(AgencyScopedAdmin):
    list_display = ("at", "actor", "action", "target")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
