from .models import OpcaoPergunta, PerguntaTemplate, TemplateBriefing
from .templates_padrao import PADROES


def semear_templates_padrao(grupo, usuario=None):
    """Cria os roteiros que já vêm prontos para uma empresa que ainda não tem
    nenhum. Idempotente: rodar de novo não duplica."""
    criados = []
    for definicao in PADROES:
        if TemplateBriefing.objects.filter(empresa=grupo, nome=definicao["nome"]).exists():
            continue
        template = TemplateBriefing.objects.create(
            empresa=grupo,
            criado_por=usuario,
            nome=definicao["nome"],
            tipo_projeto=definicao.get("tipo_projeto", ""),
            descricao=definicao.get("descricao", ""),
        )
        for ordem, dados in enumerate(definicao["perguntas"]):
            pergunta = PerguntaTemplate.objects.create(
                empresa=grupo,
                template=template,
                bloco=dados.get("bloco", ""),
                texto=dados["texto"],
                tipo=dados.get("tipo", "opcao"),
                ajuda=dados.get("ajuda", ""),
                ordem=ordem,
            )
            OpcaoPergunta.objects.bulk_create(
                [
                    OpcaoPergunta(empresa=grupo, pergunta=pergunta, texto=texto, ordem=indice)
                    for indice, texto in enumerate(dados.get("opcoes", []))
                ]
            )
        criados.append(template)
    return criados


def perguntas_por_bloco(template):
    """Agrupa as perguntas na ordem em que os blocos aparecem."""
    blocos = []
    indice = {}
    for pergunta in template.perguntas.prefetch_related("opcoes"):
        nome = pergunta.bloco or "Geral"
        if nome not in indice:
            indice[nome] = {"nome": nome, "perguntas": []}
            blocos.append(indice[nome])
        indice[nome]["perguntas"].append(pergunta)
    return blocos
