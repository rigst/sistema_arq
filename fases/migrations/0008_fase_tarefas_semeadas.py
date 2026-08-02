from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fases", "0007_separar_proposta_e_contrato")]

    operations = [
        migrations.AddField(
            model_name="fase",
            name="tarefas_semeadas",
            field=models.BooleanField(default=False),
        ),
    ]
