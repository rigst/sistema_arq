from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("arquivos", "0003_arquivo_fase"),
    ]

    operations = [
        migrations.AddField(
            model_name="arquivo",
            name="favorito",
            field=models.BooleanField(
                default=False,
                help_text="Exibe este arquivo entre os documentos principais do projeto.",
                verbose_name="arquivo principal",
            ),
        ),
    ]
