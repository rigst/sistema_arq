"""As tipologias passaram a ser residencial, comercial, empresarial e
institucional. Os dois valores antigos que sumiram precisam de destino:

- "corporativo" vira "empresarial", que é o mesmo trabalho com outro nome;
- "interiores" vira "residencial", porque é onde a maioria dos projetos de
  interiores do escritório cai. Não é uma tradução perfeita — interiores
  comercial existe — mas escolher um padrão e deixar o arquiteto corrigir os
  poucos casos é melhor do que deixar o campo com um valor fora da lista.
"""

from django.db import migrations

DE_PARA = {"corporativo": "empresarial", "interiores": "residencial"}


def para_frente(apps, schema_editor):
    Projeto = apps.get_model("projetos", "Projeto")
    for antigo, novo in DE_PARA.items():
        Projeto.objects.filter(tipo=antigo).update(tipo=novo)


def para_tras(apps, schema_editor):
    """Sem volta possível: "empresarial" e "residencial" agora abrigam projetos
    que vieram de origens diferentes, e não há como separá-los de novo."""


class Migration(migrations.Migration):
    dependencies = [("projetos", "0006_remove_disciplina_disciplina_unica_por_projeto_and_more")]
    operations = [migrations.RunPython(para_frente, para_tras)]
