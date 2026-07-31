from django.contrib.auth.models import AbstractUser
from django.db import models

from core.tenancy import VISITOR_GROUP_PREFIX, obter_empresa_ativa_usuario


class Usuario(AbstractUser):
    PERFIL_CHOICES = [
        ("admin", "Administrador"),
        ("equipe", "Equipe"),
        ("visualizador", "Visualizador"),
        ("visitante", "Visitante"),
    ]

    perfil = models.CharField(max_length=20, choices=PERFIL_CHOICES, default="equipe")
    nome_exibicao = models.CharField(max_length=150, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    @property
    def eh_admin_perfil(self):
        return self.is_superuser or self.perfil == "admin"

    @property
    def eh_equipe(self):
        return self.perfil == "equipe"

    @property
    def eh_visualizador(self):
        return self.perfil == "visualizador"

    @property
    def eh_visitante(self):
        return self.perfil == "visitante"

    @property
    def pode_editar(self):
        """Quem pode criar/alterar dados. Visitante pode (é uma sandbox descartável)."""
        return self.eh_admin_perfil or self.eh_equipe or self.eh_visitante

    @property
    def nome_empresa(self):
        empresa = obter_empresa_ativa_usuario(self)
        grupo = empresa.grupo if empresa else self.groups.order_by("name", "id").first()
        if self.eh_visitante and grupo and grupo.name.startswith(VISITOR_GROUP_PREFIX):
            return "Escritório Visitante"
        return empresa.nome if empresa else (grupo.name if grupo else "Sem empresa")

    def __str__(self):
        if self.eh_visitante:
            return "Visitante"
        return self.nome_exibicao or self.get_full_name() or self.username
