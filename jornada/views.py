from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.estados import UF_CHOICES
from core.forms import ArqForm
from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa
from crm.models import Cliente
from fases.models import criar_complementares_avulsos, montar_fases
from projetos.models import Projeto


class SelectCliente(forms.Select):
    """Carrega os dados do cliente na própria <option>.

    Assim a ficha de conferência é preenchida sem uma segunda ida ao servidor,
    e a página continua funcionando (com o formulário inteiro visível) se o
    JavaScript não rodar.
    """

    def create_option(self, name, value, *args, **kwargs):
        opcao = super().create_option(name, value, *args, **kwargs)
        cliente = getattr(value, "instance", None)
        if cliente is not None:
            opcao["attrs"].update(
                {
                    "data-nome": cliente.nome,
                    "data-email": cliente.email or "—",
                    "data-telefone": cliente.telefone or "—",
                    "data-url": reverse("crm_detalhe", kwargs={"pk": cliente.pk}),
                }
            )
        return opcao


class AberturaForm(ArqForm):
    """Um formulário só para tirar o projeto do papel.

    Os campos aparecem em duas partes: primeiro quem é o cliente, e só depois
    o projeto. Se o cliente já existe, os dados dele são exibidos para conferir
    e não para editar — corrigir cadastro é assunto da tela de clientes, e
    deixar dois lugares editarem a mesma coisa é como um vira cópia velha do
    outro. Status não se pergunta: projeto novo nasce ativo.
    """

    cliente_existente = forms.ModelChoiceField(
        queryset=Cliente.objects.none(),
        required=False,
        label="Cliente",
        empty_label="— cadastrar um novo cliente —",
        widget=SelectCliente,
    )
    cliente_nome = forms.CharField(label="Nome do cliente", max_length=150, required=False)
    cliente_email = forms.EmailField(label="E-mail", required=False)
    cliente_telefone = forms.CharField(label="Telefone", max_length=40, required=False)

    nome = forms.CharField(label="Nome do projeto", max_length=200)
    tipo = forms.ChoiceField(label="Tipo de projeto", choices=Projeto.TIPO_CHOICES)
    cidade = forms.CharField(label="Cidade", max_length=120, required=False)
    uf = forms.ChoiceField(label="Estado", required=False, choices=[("", "—")] + UF_CHOICES)
    endereco = forms.CharField(label="Endereço ou referência do terreno", max_length=200, required=False)
    complementares = forms.MultipleChoiceField(
        label="Projetos complementares",
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Opcionais, e podem ser ligados depois. Cada um começa a partir do anteprojeto.",
    )
    complementar_outro = forms.CharField(
        label="Outro complementar",
        max_length=120,
        required=False,
        help_text="Para o que não está na lista — acústico, luminotécnico, automação. "
                  "Separe por vírgula se for mais de um.",
    )
    tem_execucao = forms.BooleanField(
        label="O escritório também acompanha a execução da obra",
        required=False,
        help_text="Marque só se o contrato inclui obra. Dá para mudar depois.",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cliente_existente"].queryset = queryset_da_empresa(
            Cliente.objects.filter(ativo=True), user
        )
        from fases.catalogo import COMPLEMENTARES_NOMEADOS as COMPLEMENTARES

        self.fields["complementares"].choices = [(p.chave, p.nome) for p in COMPLEMENTARES]

    def clean(self):
        dados = super().clean()
        if not dados.get("cliente_existente") and not (dados.get("cliente_nome") or "").strip():
            raise forms.ValidationError(
                "Escolha um cliente já cadastrado ou informe o nome de um novo."
            )
        return dados


@login_required
def abrir(request):
    """Ponto de entrada do fluxo: cria cliente (se preciso) e projeto, e cai
    direto no roteiro."""
    if request.method == "POST":
        form = AberturaForm(request.POST, user=request.user)
        if form.is_valid():
            grupo = obter_grupo_empresa_ou_erro(request.user)
            cliente = form.cleaned_data["cliente_existente"]
            if cliente is None:
                cliente = Cliente.objects.create(
                    empresa=grupo,
                    criado_por=request.user,
                    nome=form.cleaned_data["cliente_nome"].strip(),
                    email=form.cleaned_data["cliente_email"],
                    telefone=form.cleaned_data["cliente_telefone"],
                    fase="em_contato",
                )
            projeto = Projeto.objects.create(
                empresa=grupo,
                criado_por=request.user,
                cliente=cliente,
                nome=form.cleaned_data["nome"],
                tipo=form.cleaned_data["tipo"],
                tem_execucao=form.cleaned_data["tem_execucao"],
                cidade=form.cleaned_data["cidade"],
                uf=form.cleaned_data["uf"],
                endereco=form.cleaned_data["endereco"],
                status="ativo",
            )
            montar_fases(projeto, complementares=form.cleaned_data["complementares"])
            criar_complementares_avulsos(projeto, form.cleaned_data["complementar_outro"])
            messages.success(
                request, "Projeto aberto. O próximo passo é o briefing — está aberto abaixo."
            )
            # Cai direto no briefing: é o primeiro trabalho real do projeto, e
            # obrigar a passar pela ficha antes só adiciona um clique.
            return redirect("briefing_responder", projeto_pk=projeto.pk)
    else:
        form = AberturaForm(user=request.user)

    return render(request, "jornada/abrir.html", {"form": form})


@login_required
def roteiro(request, projeto_pk):
    """O roteiro passou a morar na página do projeto.

    A rota continua de pé porque links antigos e o histórico do navegador
    apontam para cá; ela só encaminha para o lugar novo.
    """
    projeto = get_object_or_404(
        queryset_da_empresa(Projeto.objects.all(), request.user), pk=projeto_pk
    )
    return redirect("projeto_detalhe", pk=projeto.pk)
