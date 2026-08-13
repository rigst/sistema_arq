from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

# Os três clientes da demonstração, referenciados em cadastro, projetos e
# lançamentos — o nome precisa bater exatamente entre eles.
CLIENTE_RESIDENCIAL = "Marina e Lucas Almeida"
CLIENTE_COMERCIAL = "Café Horizonte Ltda."
CLIENTE_INSTITUCIONAL = "Instituto Caminhos"


class Command(BaseCommand):
    help = "Cria dados de demonstração idempotentes na empresa de um usuário."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", default="admin")

    @transaction.atomic
    def handle(self, *args, **options):
        from agenda.models import Compromisso
        from contratos.models import Contrato, Parcela
        from core.tenancy import obter_grupo_empresa_usuario
        from crm.models import Cliente, Interacao
        from fases.models import Fase, montar_fases
        from fases.services import garantir_tarefas_da_fase
        from financeiro.models import ContaBancaria, Lancamento
        from fornecedores.models import Fornecedor
        from obras.models import Obra, criar_etapas_obra_padrao
        from orcamentos.models import ItemOrcamento, Orcamento
        from precificacao.models import ConfiguracaoPrecificacao, CustoFixo, FatorPrecificacao
        from projetos.models import Projeto, Tag
        from propostas.models import ItemProposta, Proposta
        from tarefas.models import Tarefa
        from usuarios.models import Usuario

        username = options["usuario"]
        try:
            usuario = Usuario.objects.get(username=username)
        except Usuario.DoesNotExist as exc:
            raise CommandError(f"Usuário {username!r} não encontrado.") from exc
        grupo = obter_grupo_empresa_usuario(usuario)
        if grupo is None:
            raise CommandError(f"Usuário {username!r} não possui empresa.")

        hoje = timezone.localdate()
        timezone.localtime()

        ConfiguracaoPrecificacao.objects.update_or_create(
            empresa=grupo,
            defaults={
                "horas_uteis_mes": 160,
                "hora_tecnica_manual": Decimal("185.00"),
                "margem_seguranca_percent": Decimal("10.00"),
                "imposto_percent": Decimal("6.00"),
            },
        )
        for descricao, valor in (
            ("Pró-labore", "6500.00"),
            ("Aluguel e condomínio", "2400.00"),
            ("Softwares e licenças", "890.00"),
            ("Internet, energia e telefone", "620.00"),
        ):
            CustoFixo.objects.update_or_create(
                empresa=grupo,
                descricao=descricao,
                defaults={"valor_mensal": Decimal(valor), "ativo": True, "criado_por": usuario},
            )
        for nome, percentual in (
            ("Urgência", "20.00"),
            ("Alta complexidade", "15.00"),
            ("Cliente recorrente", "-8.00"),
        ):
            FatorPrecificacao.objects.update_or_create(
                empresa=grupo,
                nome=nome,
                defaults={"percentual": Decimal(percentual), "ativo": True},
            )

        clientes = {}
        dados_clientes = (
            (CLIENTE_RESIDENCIAL, "marina.almeida@example.com", "ganho", "indicacao"),
            (CLIENTE_COMERCIAL, "contato@cafehorizonte.example", "ganho", "instagram"),
            (CLIENTE_INSTITUCIONAL, "projetos@caminhos.example", "proposta", "site"),
            ("Incorporadora Parque Sul", "urbanismo@parquesul.example", "negociacao", "evento"),
        )
        for nome, email, fase, origem in dados_clientes:
            clientes[nome], _ = Cliente.objects.update_or_create(
                empresa=grupo,
                nome=nome,
                defaults={
                    "email": email,
                    "telefone": "(51) 99999-0000",
                    "fase": fase,
                    "origem": origem,
                    "ativo": True,
                    "criado_por": usuario,
                    "observacoes": "Cadastro demonstrativo para validação do fluxo comercial.",
                },
            )
        Interacao.objects.update_or_create(
            empresa=grupo,
            cliente=clientes[CLIENTE_INSTITUCIONAL],
            descricao="Apresentação inicial realizada; cliente solicitou proposta por etapas.",
            defaults={"tipo": "reuniao", "autor": usuario},
        )

        tags = {}
        for nome, cor in (
            ("Prioridade", "#111827"),
            ("Em aprovação", "#6b7280"),
            ("Obra", "#374151"),
        ):
            tags[nome], _ = Tag.objects.update_or_create(
                empresa=grupo, nome=nome, defaults={"cor": cor}
            )

        projetos = {}
        dados_projetos = (
            (
                "Residência Alameda",
                CLIENTE_RESIDENCIAL,
                "residencial",
                "ativo",
                "42000.00",
                280,
                True,
            ),
            (
                "Café Horizonte — Loja Centro",
                CLIENTE_COMERCIAL,
                "comercial",
                "ativo",
                "28500.00",
                190,
                True,
            ),
            (
                "Centro Educacional Caminhos",
                CLIENTE_INSTITUCIONAL,
                "institucional",
                "ativo",
                "68000.00",
                420,
                False,
            ),
            (
                "Loteamento Parque Sul",
                "Incorporadora Parque Sul",
                "urbanismo",
                "pausado",
                "95000.00",
                560,
                False,
            ),
        )
        for indice, (nome, cliente_nome, tipo, status, valor, horas, execucao) in enumerate(
            dados_projetos
        ):
            projeto, _ = Projeto.objects.update_or_create(
                empresa=grupo,
                nome=nome,
                defaults={
                    "cliente": clientes[cliente_nome],
                    "tipo": tipo,
                    "status": status,
                    "valor_contratado": Decimal(valor),
                    "horas_estimadas": Decimal(horas),
                    "tem_execucao": execucao,
                    "cidade": "Porto Alegre",
                    "uf": "RS",
                    "endereco": f"Rua de Demonstração, {120 + indice * 35}",
                    "area_construida": Decimal(str(145 + indice * 180)),
                    "data_inicio": hoje - timedelta(days=45 - indice * 8),
                    "data_prevista": hoje + timedelta(days=100 + indice * 30),
                    "criado_por": usuario,
                },
            )
            projeto.tags.add(tags["Prioridade"] if indice == 0 else tags["Em aprovação"])
            montar_fases(
                projeto, complementares=("comp_estrutural", "comp_eletrica", "comp_hidraulica")
            )
            projetos[nome] = projeto

        residencia = projetos["Residência Alameda"]
        fases_residencia = list(residencia.fases.order_by("ordem"))
        for indice, fase_projeto in enumerate(fases_residencia):
            if indice < 4:
                novo_status = Fase.APROVADA
            elif indice == 4:
                novo_status = Fase.EM_ELABORACAO
            else:
                novo_status = Fase.NAO_INICIADA
            Fase.objects.filter(pk=fase_projeto.pk).update(
                status=novo_status,
                prazo=hoje + timedelta(days=14 + indice * 9),
            )
        fase_ativa = residencia.fases.order_by("ordem")[4]
        garantir_tarefas_da_fase(fase_ativa, usuario)
        # A primeira tarefa entra concluída e a segunda em andamento, para a
        # demo abrir com a fase em movimento em vez de tudo por fazer.
        status_por_indice = {0: "concluida", 1: "andamento"}
        for indice, tarefa in enumerate(fase_ativa.tarefas.order_by("ordem")):
            tarefa.responsavel = usuario
            tarefa.status = status_por_indice.get(indice, "aberta")
            tarefa.prazo = hoje + timedelta(days=indice + 2)
            tarefa.save(update_fields=["responsavel", "status", "prazo"])
        Tarefa.objects.update_or_create(
            empresa=grupo,
            projeto=residencia,
            fase=fase_ativa,
            titulo="Revisar compatibilização da cozinha",
            defaults={
                "descricao": "Conferir arquitetura, elétrica e hidráulica antes da apresentação.",
                "responsavel": usuario,
                "prazo": hoje + timedelta(days=3),
                "horas_previstas": Decimal("4"),
                "status": "andamento",
                "criado_por": usuario,
            },
        )

        proposta, _ = Proposta.objects.update_or_create(
            empresa=grupo,
            titulo="Proposta — Centro Educacional Caminhos",
            defaults={
                "cliente": clientes[CLIENTE_INSTITUCIONAL],
                "tipo_projeto": "institucional",
                "hora_tecnica_aplicada": Decimal("185.00"),
                "status": "enviada",
                "validade_dias_uteis": 10,
                "observacoes": "Honorários divididos conforme a sequência das etapas.",
                "criado_por": usuario,
            },
        )
        itens_proposta = (
            (
                0,
                "Levantamento e diagnóstico",
                32,
                "Visita técnica, levantamento cadastral e diagnóstico das necessidades.",
            ),
            (
                1,
                "Estudo preliminar",
                64,
                "Partido arquitetônico, implantação, plantas e apresentação ao cliente.",
            ),
            (
                2,
                "Anteprojeto",
                96,
                "Desenvolvimento das soluções aprovadas e compatibilização inicial.",
            ),
            (
                3,
                "Projeto executivo",
                180,
                "Detalhamentos, especificações e documentação para execução.",
            ),
        )
        from precificacao.services import precificar_etapa

        for ordem, descricao, horas, inclusoes in itens_proposta:
            ItemProposta.objects.update_or_create(
                empresa=grupo,
                proposta=proposta,
                descricao=descricao,
                defaults={
                    "ordem": ordem,
                    "horas_estimadas": Decimal(horas),
                    "inclusoes": inclusoes,
                    "valor": precificar_etapa(grupo, horas, hora_tecnica=Decimal("185.00"))[
                        "total"
                    ],
                },
            )

        contrato, _ = Contrato.objects.update_or_create(
            empresa=grupo,
            projeto=residencia,
            numero="DEMO-2026-001",
            defaults={
                "titulo": "Contrato de serviços — Residência Alameda",
                "valor_total": Decimal("42000.00"),
                "data_assinatura": hoje - timedelta(days=40),
                "status": "ativo",
                "parcelas_lancadas": True,
                "criado_por": usuario,
                "corpo": "Contrato demonstrativo de prestação de serviços de arquitetura, com escopo, prazos e condições comerciais.",
            },
        )

        conta, _ = ContaBancaria.objects.update_or_create(
            empresa=grupo,
            nome="Conta empresarial — demonstração",
            defaults={"saldo_inicial": Decimal("12500.00"), "pessoal": False},
        )
        for numero, (dias, paga) in enumerate(
            ((-30, True), (0, True), (30, False), (60, False)), 1
        ):
            valor_parcela = Decimal("10500.00")
            lancamento, _ = Lancamento.objects.update_or_create(
                empresa=grupo,
                descricao=f"Contrato DEMO-2026-001 — parcela {numero}",
                defaults={
                    "conta": conta,
                    "tipo": "entrada",
                    "projeto": residencia,
                    "valor": valor_parcela,
                    "data": hoje + timedelta(days=dias),
                    "status": "realizado" if paga else "previsto",
                    "criado_por": usuario,
                },
            )
            Parcela.objects.update_or_create(
                empresa=grupo,
                contrato=contrato,
                numero=numero,
                defaults={
                    "descricao": f"Parcela {numero}/4",
                    "valor": valor_parcela,
                    "vencimento": hoje + timedelta(days=dias),
                    "paga": paga,
                    "lancamento": lancamento,
                },
            )
        extras = (
            ("Consultoria avulsa de layout", "entrada", "1800.00", -8),
            ("Assinatura de biblioteca técnica", "saida", "349.90", -5),
            ("Impressões e plotagens", "saida", "486.50", -2),
            ("Workshop de representação", "entrada", "2400.00", 5),
        )
        for descricao, tipo, valor, dias in extras:
            Lancamento.objects.update_or_create(
                empresa=grupo,
                descricao=descricao,
                defaults={
                    "conta": conta,
                    "tipo": tipo,
                    "projeto": None,
                    "categoria": None,
                    "valor": Decimal(valor),
                    "data": hoje + timedelta(days=dias),
                    "status": "realizado" if dias <= 0 else "previsto",
                    "criado_por": usuario,
                },
            )

        fornecedores = {}
        for nome, categoria, contato in (
            ("Traço Comunicação Visual", "comunicacao_visual", "Ana Ribeiro"),
            ("Eixo Engenharia", "servicos_engenharia", "Carlos Mendes"),
            ("Studio Render Freelancer", "freelancer", "Bianca Luz"),
            ("Madeira Sul Marcenaria", "marcenaria", "Paulo Nunes"),
        ):
            fornecedores[nome], _ = Fornecedor.objects.update_or_create(
                empresa=grupo,
                nome=nome,
                defaults={
                    "categoria": categoria,
                    "contato": contato,
                    "telefone": "(51) 3333-2026",
                    "email": f"contato@{nome.lower().replace(' ', '')[:18]}.example",
                    "cidade": "Porto Alegre",
                    "prazo_medio_dias": 18,
                    "avaliacao": 5,
                    "ativo": True,
                    "criado_por": usuario,
                },
            )

        cafe = projetos["Café Horizonte — Loja Centro"]
        orcamento, _ = Orcamento.objects.update_or_create(
            empresa=grupo,
            projeto=cafe,
            titulo="Orçamento de execução — Loja Centro",
            defaults={
                "versao": "1",
                "status": "rascunho",
                "bdi_percent": Decimal("12.00"),
                "validade": hoje + timedelta(days=20),
                "criado_por": usuario,
            },
        )
        for (
            ordem,
            ambiente,
            categoria,
            descricao,
            unidade,
            quantidade,
            unitario,
            fornecedor_nome,
        ) in (
            (
                0,
                "Salão",
                "marcenaria",
                "Balcão de atendimento sob medida",
                "un",
                1,
                "18500.00",
                "Madeira Sul Marcenaria",
            ),
            (
                1,
                "Fachada",
                "outro",
                "Letreiro e sinalização externa",
                "vb",
                1,
                "6800.00",
                "Traço Comunicação Visual",
            ),
            (
                2,
                "Salão",
                "instalacoes",
                "Adequações elétricas e luminotécnicas",
                "vb",
                1,
                "12400.00",
                "Eixo Engenharia",
            ),
        ):
            ItemOrcamento.objects.update_or_create(
                empresa=grupo,
                orcamento=orcamento,
                descricao=descricao,
                defaults={
                    "ordem": ordem,
                    "ambiente": ambiente,
                    "categoria": categoria,
                    "unidade": unidade,
                    "quantidade": Decimal(quantidade),
                    "valor_unitario": Decimal(unitario),
                    "fornecedor": fornecedores[fornecedor_nome],
                },
            )

        obra, criada = Obra.objects.get_or_create(
            empresa=grupo,
            projeto=residencia,
            defaults={
                "endereco": residencia.endereco,
                "responsavel_tecnico": "Arq. Rodrigo Stolben",
                "status": "andamento",
                "data_inicio": hoje - timedelta(days=25),
                "data_prevista_fim": hoje + timedelta(days=150),
                "criado_por": usuario,
            },
        )
        if criada or not obra.etapas.exists():
            criar_etapas_obra_padrao(obra)
        for indice, etapa in enumerate(obra.etapas.order_by("ordem")):
            etapa.percentual_previsto = Decimal(min(100, 80 - indice * 12))
            etapa.percentual_real = Decimal(min(100, 72 - indice * 12))
            etapa.valor = Decimal("35000.00") + Decimal(indice * 12000)
            etapa.save(update_fields=["percentual_previsto", "percentual_real", "valor"])

        compromissos = (
            (
                "Apresentação — Centro Educacional",
                "apresentacao",
                2,
                14,
                clientes[CLIENTE_INSTITUCIONAL],
                projetos["Centro Educacional Caminhos"],
            ),
            (
                "Visita técnica — Residência Alameda",
                "visita",
                4,
                9,
                clientes[CLIENTE_RESIDENCIAL],
                residencia,
            ),
            (
                "Reunião com engenharia — Café Horizonte",
                "reuniao",
                7,
                16,
                clientes[CLIENTE_COMERCIAL],
                cafe,
            ),
        )
        for titulo, tipo, dias, hora, cliente, projeto in compromissos:
            inicio = timezone.make_aware(
                datetime.combine(hoje + timedelta(days=dias), time(hora, 0))
            )
            Compromisso.objects.update_or_create(
                empresa=grupo,
                titulo=titulo,
                defaults={
                    "tipo": tipo,
                    "inicio": inicio,
                    "fim": inicio + timedelta(hours=1),
                    "local": "Escritório / videoconferência",
                    "cliente": cliente,
                    "projeto": projeto,
                    "criado_por": usuario,
                },
            )

        totais = {
            "clientes": Cliente.objects.filter(empresa=grupo).count(),
            "projetos": Projeto.objects.filter(empresa=grupo).count(),
            "propostas": Proposta.objects.filter(empresa=grupo).count(),
            "lancamentos": Lancamento.objects.filter(empresa=grupo).count(),
        }
        self.stdout.write(
            self.style.SUCCESS(f"Dados de demonstração disponíveis para {username}: {totais}")
        )
