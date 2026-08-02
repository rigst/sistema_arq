from core.tenancy import obter_empresa_ativa_usuario, obter_empresas_usuario


def empresa_context(request):
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return {}

    from tarefas.views import cronometro_aberto

    return {
        "empresas_usuario": list(obter_empresas_usuario(user)),
        "empresa_ativa": obter_empresa_ativa_usuario(user),
        # O cronômetro acompanha a pessoa por todas as telas: quem começa a
        # contar e navega para outra página não pode perder o relógio de vista,
        # senão a hora fica aberta a noite inteira.
        "cronometro": cronometro_aberto(user),
    }
