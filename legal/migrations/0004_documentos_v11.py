from django.db import migrations
from django.utils import timezone

from legal.textos import PRIVACIDADE_V11, TERMOS_V11

VERSAO = "1.1"

DOCUMENTOS = (
    (
        "termos",
        "Termos de uso",
        TERMOS_V11,
        "Acrescenta a licença de uso do software, o que ela cobre e quem responde "
        "pelo sistema, com site e e-mail de contato.",
    ),
    (
        "privacidade",
        "Política de privacidade",
        PRIVACIDADE_V11,
        "Identifica o controlador dos dados pelo nome e informa o e-mail para "
        "exercer seus direitos.",
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
    dependencies = [("legal", "0003_alter_aceitelegal_usuario")]
    operations = [migrations.RunPython(publicar, despublicar)]
