from django.contrib import admin

from .models import ConfiguracaoPrecificacao, CustoFixo, FatorPrecificacao


@admin.register(CustoFixo)
class CustoFixoAdmin(admin.ModelAdmin):
    list_display = ("descricao", "valor_mensal", "ativo", "empresa")
    list_filter = ("ativo",)
    search_fields = ("descricao",)


@admin.register(FatorPrecificacao)
class FatorPrecificacaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "percentual", "ativo", "empresa")
    list_filter = ("ativo",)
    search_fields = ("nome",)


@admin.register(ConfiguracaoPrecificacao)
class ConfiguracaoPrecificacaoAdmin(admin.ModelAdmin):
    list_display = (
        "empresa", "horas_uteis_mes", "hora_tecnica_manual",
        "margem_seguranca_percent", "imposto_percent",
    )
