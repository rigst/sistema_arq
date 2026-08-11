from typing import cast

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

from core.tenancy import VISITOR_GROUP_PREFIX, obter_grupo_empresa_usuario

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    add_fieldsets = (
        *UserAdmin.add_fieldsets,
        (
            "Identificação e acesso",
            {
                "fields": (
                    "nome_exibicao",
                    "email",
                    "perfil",
                    "groups",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
    )
    fieldsets = (
        # `or ()` porque a assinatura de ModelAdmin declara fieldsets como
        # opcional; o UserAdmin sempre define, mas o desempacotamento não sabe.
        *(UserAdmin.fieldsets or ()),
        (
            "Informações adicionais",
            {"fields": ("perfil", "nome_exibicao", "criado_em", "atualizado_em")},
        ),
    )
    readonly_fields = ("criado_em", "atualizado_em")
    list_display = ("username", "email", "perfil", "is_staff", "is_active", "empresa_atual")
    list_filter = ("perfil", "is_staff", "is_active", "groups")
    search_fields = ("username", "nome_exibicao", "email")
    filter_horizontal = ("groups", "user_permissions")

    def empresa_atual(self, obj):
        return obj.nome_empresa

    def grupos_empresa_queryset(self, request):
        queryset = Group.objects.exclude(name__startswith=VISITOR_GROUP_PREFIX).order_by("name")
        if request.user.is_superuser:
            return queryset
        grupo = obter_grupo_empresa_usuario(request.user)
        if grupo is None:
            return queryset.none()
        return queryset.filter(pk=grupo.pk)

    def get_form(self, request, obj=None, change=False, **kwargs):
        # `change` entra explícito só para casar com a assinatura de
        # ModelAdmin.get_form; segue sendo repassado por kwargs, como antes.
        form = super().get_form(request, obj, change=change, **kwargs)
        if "groups" in form.base_fields:
            # base_fields é dict[str, Field]; queryset só existe no campo de
            # relação que este de fato é.
            grupos = cast(forms.ModelMultipleChoiceField, form.base_fields["groups"])
            grupos.queryset = self.grupos_empresa_queryset(request)
            grupos.label = "Empresa"
        return form

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        grupo = request.user.groups.order_by("name", "id").first()
        if grupo is None:
            return queryset.none()
        return queryset.filter(groups=grupo)

    def has_module_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if request.user.is_superuser or form.instance.eh_visitante:
            return
        grupo = obter_grupo_empresa_usuario(request.user)
        if grupo is not None:
            form.instance.groups.set([grupo])
