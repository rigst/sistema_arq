"""Auxiliares de teste: criam um tenant (empresa + grupo + usuário) mínimo."""

import secrets

from django.contrib.auth import get_user_model

from core.tenancy import obter_grupo_empresa_usuario

# Sorteadas a cada processo de teste, e não escritas no código. Duas razões:
# nenhum literal de credencial fica versionado (o que os scanners acusam, com
# razão, porque um dia alguém copia o literal para produção), e nenhum teste
# consegue depender do valor — se depender, quebra no processo seguinte.
SENHA_TESTE = secrets.token_urlsafe(16)

# Qualquer senha diferente de SENHA_TESTE serve para exercitar o caminho de
# falha de login. Sortear é mais honesto do que um "errada" fixo: garante que
# não coincide com a senha válida.
SENHA_ERRADA = secrets.token_urlsafe(16)


def criar_empresa_e_usuario(username="arq", senha=SENHA_TESTE):
    """Cria um usuário já vinculado à sua empresa (grupo padrão criado pelo
    signal de usuários). Retorna (user, grupo) — o grupo é a empresa ativa,
    exatamente o que o app usa para escopo por tenant."""
    modelo_usuario = get_user_model()
    user = modelo_usuario.objects.create_user(username=username, password=senha)
    grupo = obter_grupo_empresa_usuario(user)
    return user, grupo
