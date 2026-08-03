from django.db import migrations
from django.utils import timezone

from legal.textos import PRIVACIDADE_V12, TERMOS_V12

VERSAO = "1.2"

DOCUMENTOS = (
    (
        "termos",
        "Termos de uso",
        TERMOS_V12,
        "Atualiza o serviço para a primeira implantação web e esclarece a revisão de "
        "propostas, contratos, PDFs e arquivos enviados.",
    ),
    (
        "privacidade",
        "Política de privacidade",
        PRIVACIDADE_V12,
        "Detalha prestadores, transferência internacional, retenção, controles de segurança "
        "e resposta a incidentes.",
    ),
)


def publicar(apps, schema_editor):
    Documento = apps.get_model("legal", "DocumentoLegal")
    agora = timezone.now()
    for tipo, titulo, conteudo, resumo in DOCUMENTOS:
        Documento.objects.update_or_create(
            tipo=tipo,
            versao=VERSAO,
            defaults={
                "titulo": titulo,
                "conteudo": conteudo,
                "resumo_mudancas": resumo,
                "vigente_desde": agora,
            },
        )


def despublicar(apps, schema_editor):
    Documento = apps.get_model("legal", "DocumentoLegal")
    Documento.objects.filter(versao=VERSAO, aceites__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("legal", "0004_documentos_v11")]
    operations = [migrations.RunPython(publicar, despublicar)]
