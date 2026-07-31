from django.contrib import admin

from .models import ConfiguracaoPrecificacao, CustoFixo


@admin.register(CustoFixo)
class CustoFixoAdmin(admin.ModelAdmin):
    list_display = ("descricao", "valor_mensal", "ativo", "empresa")
    list_filter = ("ativo",)
    search_fields = ("descricao",)


@admin.register(ConfiguracaoPrecificacao)
class ConfiguracaoPrecificacaoAdmin(admin.ModelAdmin):
    list_display = ("empresa", "horas_uteis_mes", "margem_seguranca_percent", "reserva_percent")
