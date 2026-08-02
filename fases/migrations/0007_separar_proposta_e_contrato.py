from django.db import migrations, models


def criar_fase_contrato(apps, schema_editor):
    Fase = apps.get_model("fases", "Fase")
    for proposta in Fase.objects.filter(chave="proposta").select_related("projeto"):
        Fase.objects.filter(projeto=proposta.projeto, ordem__gt=proposta.ordem).update(
            ordem=models.F("ordem") + 1
        )
        Fase.objects.get_or_create(
            empresa=proposta.empresa,
            projeto=proposta.projeto,
            chave="contrato",
            defaults={"ordem": proposta.ordem + 1},
        )


class Migration(migrations.Migration):
    dependencies = [("fases", "0006_lembrete_so_do_usuario")]

    operations = [
        migrations.AlterField(
            model_name="fase",
            name="chave",
            field=models.CharField(
                choices=[
                    ("briefing", "Briefing"),
                    ("proposta", "Proposta"),
                    ("contrato", "Contrato"),
                    ("estudo_preliminar", "Estudo preliminar"),
                    ("anteprojeto", "Anteprojeto"),
                    ("executivo", "Projeto executivo"),
                    ("comp_estrutural", "Projeto estrutural"),
                    ("comp_eletrica", "Projeto elétrico"),
                    ("comp_hidraulica", "Projeto hidrossanitário"),
                    ("comp_outro", "Complementar"),
                    ("comp_paisagismo", "Paisagismo"),
                ],
                max_length=30,
            ),
        ),
        migrations.RunPython(criar_fase_contrato, migrations.RunPython.noop),
    ]
