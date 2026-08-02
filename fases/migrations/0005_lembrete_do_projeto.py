"""RegistroFase vira Lembrete e passa a servir também ao projeto.

Nasceu preso à fase, mas o projeto tem recado que não é de fase nenhuma. Em vez
de um segundo modelo quase igual, a fase virou opcional e o projeto entrou como
obrigatório — os registros que já existem herdam o projeto da própria fase.
"""

from django.db import migrations, models
import django.db.models.deletion


def herdar_projeto_da_fase(apps, schema_editor):
    Lembrete = apps.get_model("fases", "Lembrete")
    for lembrete in Lembrete.objects.select_related("fase").all():
        lembrete.projeto_id = lembrete.fase.projeto_id
        lembrete.save(update_fields=["projeto"])


class Migration(migrations.Migration):
    dependencies = [
        ("fases", "0004_registrofase_fixado"),
        ("projetos", "0007_tipologias_novas"),
    ]

    operations = [
        migrations.RenameModel(old_name="RegistroFase", new_name="Lembrete"),
        migrations.AlterModelOptions(
            name="lembrete",
            options={
                "ordering": ["-criado_em", "-id"],
                "verbose_name": "lembrete",
                "verbose_name_plural": "lembretes",
            },
        ),
        migrations.AlterField(
            model_name="lembrete",
            name="fase",
            field=models.ForeignKey(
                blank=True, null=True,
                help_text="Vazio quando o lembrete é do projeto inteiro.",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="registros", to="fases.fase",
            ),
        ),
        migrations.AddField(
            model_name="lembrete",
            name="projeto",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name="lembretes", to="projetos.projeto",
            ),
        ),
        migrations.RunPython(herdar_projeto_da_fase, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="lembrete",
            name="projeto",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="lembretes", to="projetos.projeto",
            ),
        ),
    ]
