from django.apps import AppConfig


class EngageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "engage"

    def ready(self):
        from django.db.models.signals import pre_save

        from .models import MessageTemplate, MessageVersion

        def keep_previous_version(sender, instance, **kwargs):
            """Antes de gravar um modelo de mensagem com texto ou título novo, guarda a versão que estava valendo."""
            if not instance.pk:
                return
            old = sender.objects.filter(pk=instance.pk).values("title", "body").first()
            if old and (old["body"] != instance.body or old["title"] != instance.title):
                MessageVersion.objects.create(template_id=instance.pk, title=old["title"], body=old["body"],
                                              saved_by=getattr(instance, "_editor", None))

        pre_save.connect(keep_previous_version, sender=MessageTemplate, dispatch_uid="hera_message_versions")
