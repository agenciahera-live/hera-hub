from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView

admin.site.site_header = "Hera Creator Hub · Conteúdo e configurações"
admin.site.site_title = "Hera Creator Hub"
admin.site.index_title = "Cadastros"

urlpatterns = [
    path("gestao/admin/", admin.site.urls),
    # Senha nova só com o código que a gestão envia no grupo: o e-mail do criador não é conferido,
    # então "esqueci a senha" por e-mail fica bloqueado (ver config/settings.py, seção Login).
    re_path(r"^accounts/password/reset/", RedirectView.as_view(url="/primeiro-acesso/")),
    path("accounts/", include("allauth.urls")),
    path("", include("web.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
