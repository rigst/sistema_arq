from django.db import migrations
from django.utils import timezone

from legal.textos import PRIVACIDADE_V1, TERMOS_V1

VERSAO = "1.0"


def publicar(apps, schema_editor):
    Documento = apps.get_model("legal", "DocumentoLegal")
    agora = timezone.now()
    for tipo, titulo, conteudo in (
        ("termos", "Termos de uso", TERMOS_V1),
        ("privacidade", "Política de privacidade", PRIVACIDADE_V1),
    ):
        Documento.objects.update_or_create(
            tipo=tipo,
            versao=VERSAO,
            defaults={"titulo": titulo, "conteudo": conteudo, "vigente_desde": agora},
        )


def despublicar(apps, schema_editor):
    Documento = apps.get_model("legal", "DocumentoLegal")
    Documento.objects.filter(versao=VERSAO, aceites__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("legal", "0001_initial")]
    operations = [migrations.RunPython(publicar, despublicar)]
