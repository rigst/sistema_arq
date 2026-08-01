"""Projetos que existem desde antes das fases precisam ganhar as suas.

Sem isso a ficha deles abriria vazia — e um projeto sem fase nenhuma parece um
projeto quebrado, não um projeto antigo.
"""

from django.db import migrations

PRINCIPAIS = ["briefing", "proposta", "estudo_preliminar", "anteprojeto", "executivo"]


def criar(apps, schema_editor):
    Projeto = apps.get_model("projetos", "Projeto")
    Fase = apps.get_model("fases", "Fase")
    novas = []
    for projeto in Projeto.objects.all():
        ja_tem = set(Fase.objects.filter(projeto=projeto).values_list("chave", flat=True))
        for ordem, chave in enumerate(PRINCIPAIS):
            if chave not in ja_tem:
                novas.append(
                    Fase(empresa_id=projeto.empresa_id, projeto=projeto, chave=chave, ordem=ordem)
                )
    Fase.objects.bulk_create(novas)


def remover(apps, schema_editor):
    apps.get_model("fases", "Fase").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("fases", "0001_initial"), ("projetos", "0007_tipologias_novas")]
    operations = [migrations.RunPython(criar, remover)]
