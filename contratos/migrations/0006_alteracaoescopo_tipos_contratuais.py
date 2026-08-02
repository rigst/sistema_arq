from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contratos", "0005_contrato_fluxo_cliente"),
    ]

    operations = [
        migrations.AlterField(
            model_name="alteracaoescopo",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("alteracao", "Alteração de escopo"),
                    ("aditivo", "Aditivo contratual"),
                    ("prazo", "Alteração de prazo"),
                    ("condicoes", "Condições contratuais"),
                    ("aprovacao", "Aprovação registrada"),
                ],
                default="alteracao",
                max_length=20,
            ),
        ),
    ]
