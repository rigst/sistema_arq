"""Auxiliares de teste: criam um tenant (empresa + grupo + usuário) mínimo."""

from django.contrib.auth import get_user_model

from core.tenancy import obter_grupo_empresa_usuario


def criar_empresa_e_usuario(username="arq", senha="senha-teste-123"):
    """Cria um usuário já vinculado à sua empresa (grupo padrão criado pelo
    signal de usuários). Retorna (user, grupo) — o grupo é a empresa ativa,
    exatamente o que o app usa para escopo por tenant."""
    User = get_user_model()
    user = User.objects.create_user(username=username, password=senha)
    grupo = obter_grupo_empresa_usuario(user)
    return user, grupo
