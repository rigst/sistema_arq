from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tarefas", "0005_apontamentohora_pausado_em_and_more")]

    operations = [
        migrations.AddField(
            model_name="tarefa",
            name="horas_previstas",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name="horas previstas"),
        ),
        migrations.AddField(
            model_name="tarefa",
            name="ordem",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterModelOptions(
            name="tarefa",
            options={"ordering": ["ordem", "id"], "verbose_name": "tarefa", "verbose_name_plural": "tarefas"},
        ),
    ]
