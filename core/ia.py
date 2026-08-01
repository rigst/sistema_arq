"""Apoio de IA — opcional e desligado por padrão.

O A.R.Q. funciona inteiro sem isto. Quando `ANTHROPIC_API_KEY` está no
ambiente, algumas telas ganham um botão que pede a Claude um rascunho:
resumo do briefing e minuta de contrato. O texto volta como rascunho para o
arquiteto revisar — nunca é gravado direto no documento final.

Tudo o que sai daqui vai para a API da Anthropic. Por isso o prompt carrega
só o que a tarefa exige, e as telas avisam o usuário disso antes de enviar.
"""

import logging
import os

logger = logging.getLogger(__name__)

MODELO = "claude-opus-5"


class IAIndisponivel(RuntimeError):
    """A IA não está configurada ou a chamada falhou. Sempre com texto para a tela."""


def disponivel() -> bool:
    """A IA só aparece na interface quando há chave e biblioteca instaladas."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def _cliente():
    if not disponivel():
        raise IAIndisponivel(
            "Apoio de IA desligado. Defina ANTHROPIC_API_KEY no ambiente e "
            "instale a biblioteca `anthropic` para habilitar."
        )
    import anthropic

    return anthropic.Anthropic()


def _pedir(system: str, prompt: str, max_tokens: int = 4000) -> str:
    """Uma volta na API, devolvendo texto. Erros viram IAIndisponivel com
    mensagem apresentável — nenhuma view precisa conhecer o SDK."""
    import anthropic

    cliente = _cliente()
    try:
        resposta = cliente.beta.messages.create(
            model=MODELO,
            max_tokens=max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.AuthenticationError:
        raise IAIndisponivel("Chave da API recusada. Confira ANTHROPIC_API_KEY.") from None
    except anthropic.RateLimitError:
        raise IAIndisponivel("Limite de uso da API atingido. Tente de novo em instantes.") from None
    except anthropic.APIConnectionError:
        raise IAIndisponivel("Não foi possível falar com a API. Verifique a conexão.") from None
    except anthropic.APIStatusError as erro:
        logger.warning("Falha na API da Anthropic", extra={"status": erro.status_code})
        raise IAIndisponivel(f"A API respondeu com erro {erro.status_code}.") from None

    if resposta.stop_reason == "refusal":
        raise IAIndisponivel(
            "O modelo recusou este pedido. Reveja o conteúdo enviado e tente de novo."
        )

    texto = "\n".join(bloco.text for bloco in resposta.content if bloco.type == "text").strip()
    if not texto:
        raise IAIndisponivel("A resposta veio vazia. Tente de novo.")
    return texto


# --- Briefing -------------------------------------------------------------

SYSTEM_BRIEFING = """\
Você apoia um escritório brasileiro de arquitetura e design de interiores.
Recebe as respostas de um briefing e devolve uma leitura curta e útil para o
arquiteto — não para o cliente.

Escreva em português do Brasil, em prosa, sem markdown e sem títulos numerados.
Três parágrafos, nesta ordem:
1. O que o cliente quer, em uma frase, e o que isso implica de partido.
2. Os pontos de atenção: contradições entre desejo, orçamento e prazo; o que
   ficou vago e precisa ser perguntado antes de projetar.
3. O que já dá para tratar como escopo fechado.

Não invente dados que não estejam no briefing. Se algo essencial faltar, diga
que falta em vez de supor.
"""


def resumir_briefing(projeto_nome: str, tipo: str, respostas: list[tuple[str, str]]) -> str:
    """Lê as respostas do briefing e devolve a leitura do arquiteto."""
    linhas = "\n".join(f"- {pergunta}: {resposta}" for pergunta, resposta in respostas if resposta)
    if not linhas:
        raise IAIndisponivel("Responda ao menos uma pergunta do briefing antes de pedir a leitura.")
    prompt = (
        f"Projeto: {projeto_nome}\nTipo: {tipo}\n\nRespostas do briefing:\n{linhas}"
    )
    return _pedir(SYSTEM_BRIEFING, prompt, max_tokens=2000)


# --- Contrato -------------------------------------------------------------

SYSTEM_CONTRATO = """\
Você redige minutas de contrato de prestação de serviços de arquitetura para
um escritório brasileiro, seguindo a praxe do setor e o Código Civil.

Devolva o texto do contrato em cláusulas numeradas, em português do Brasil,
sem markdown. Cubra: objeto e escopo, etapas e entregáveis, prazo, honorários
e forma de pagamento, reajuste, obrigações de cada parte, alterações de escopo
e aditivos, propriedade intelectual e direito autoral (Lei 9.610/98), rescisão,
responsabilidade técnica (ART/RRT) e foro.

Escreva apenas as cláusulas — sem preâmbulo, sem comentários seus, sem
explicações. Onde faltar um dado, deixe um campo entre colchetes em CAIXA ALTA
para o escritório preencher, por exemplo [PRAZO DE ENTREGA].
"""


def redigir_contrato(dados: dict, instrucoes: str = "") -> str:
    """Minuta a partir dos dados do projeto. `instrucoes` é o que o arquiteto
    quer de diferente nesta minuta."""
    campos = "\n".join(f"- {chave}: {valor}" for chave, valor in dados.items() if valor)
    prompt = f"Dados do contrato:\n{campos}"
    if instrucoes.strip():
        prompt += f"\n\nAjustes pedidos pelo escritório:\n{instrucoes.strip()}"
    return _pedir(SYSTEM_CONTRATO, prompt, max_tokens=8000)
