from django.db import migrations
from django.utils import timezone

from legal.textos import PRIVACIDADE_V13, TERMOS_V13

VERSAO = "1.3"

DOCUMENTOS = (
    (
        "termos",
        "Termos de uso",
        TERMOS_V13,
        "Sem mudança de conteúdo: acompanha a nova versão da política de privacidade "
        "para que o aceite das duas fique na mesma data.",
    ),
    (
        "privacidade",
        "Política de privacidade",
        PRIVACIDADE_V13,
        "Nomeia os operadores de monitoramento (Sentry e Grafana Cloud), o que cada um "
        "recebe, onde ficam hospedados e o mascaramento do IP antes do envio.",
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
    dependencies = [("legal", "0005_documentos_v12")]
    operations = [migrations.RunPython(publicar, despublicar)]
