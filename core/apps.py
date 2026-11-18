from django.apps import AppConfig


def on_membership(sender, instance, **kwargs):
    """Papel salvo: Admin vira superusuário do painel de cadastros e Conteúdo ganha acesso aos cadastros de conteúdo."""
    from .bootstrap import sync_user_flags

    sync_user_flags(instance)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Agência e acessos"

    def ready(self):
        from . import checks  # noqa: F401
        from django.db.models.signals import post_save

        from .models import Membership

        # weak=False: o receptor precisa continuar vivo. Com a referência fraca (padrão do Django) ele podia ser
        # descartado da memória, e em produção as sócias criadas pelo criar_admin ficavam sem acesso aos cadastros.
        post_save.connect(on_membership, sender=Membership, dispatch_uid="hera_membership_flags", weak=False)
