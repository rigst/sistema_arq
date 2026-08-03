from django.db import migrations


def reativar_itens(apps, schema_editor):
    CustoFixo = apps.get_model("precificacao", "CustoFixo")
    FatorPrecificacao = apps.get_model("precificacao", "FatorPrecificacao")
    CustoFixo.objects.filter(ativo=False).update(ativo=True)
    FatorPrecificacao.objects.filter(ativo=False).update(ativo=True)


class Migration(migrations.Migration):

    dependencies = [
        ("precificacao", "0003_alter_configuracaoprecificacao_hora_tecnica_manual_and_more"),
    ]

    operations = [
        migrations.RunPython(reativar_itens, migrations.RunPython.noop),
    ]
