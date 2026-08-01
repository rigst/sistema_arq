from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.forms import ArqForm
from core.tenancy import obter_grupo_empresa_ou_erro, queryset_da_empresa
from crm.models import Cliente
from projetos.models import Projeto

from .roteiro import montar_roteiro, percentual, proxima_etapa


class AberturaForm(ArqForm):
    """Um formulário só para tirar o projeto do papel: cliente (existente ou
    novo) e o nome do projeto. Todo o resto vem depois, no roteiro."""

    cliente_existente = forms.ModelChoiceField(
        queryset=Cliente.objects.none(),
        required=False,
        label="Cliente já cadastrado",
        empty_label="— cadastrar um novo —",
    )
    cliente_nome = forms.CharField(label="Nome do novo cliente", max_length=150, required=False)
    cliente_email = forms.EmailField(label="E-mail", required=False)
    cliente_telefone = forms.CharField(label="Telefone", max_length=40, required=False)

    nome = forms.CharField(label="Nome do projeto", max_length=200)
    tipo = forms.ChoiceField(label="Tipo de projeto", choices=Projeto.TIPO_CHOICES)
    data_prevista = forms.DateField(
        label="Entrega prevista",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cliente_existente"].queryset = queryset_da_empresa(
            Cliente.objects.all(), user
        )

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
                data_prevista=form.cleaned_data["data_prevista"],
            )
            messages.success(request, "Projeto aberto. Siga o roteiro abaixo.")
            return redirect("jornada_roteiro", projeto_pk=projeto.pk)
    else:
        form = AberturaForm(user=request.user)

    return render(request, "jornada/abrir.html", {"form": form})


@login_required
def roteiro(request, projeto_pk):
    projeto = get_object_or_404(
        queryset_da_empresa(Projeto.objects.select_related("cliente"), request.user),
        pk=projeto_pk,
    )
    etapas = montar_roteiro(projeto)
    return render(
        request,
        "jornada/roteiro.html",
        {
            "projeto": projeto,
            "etapas": etapas,
            "proxima": proxima_etapa(etapas),
            "percentual": percentual(etapas),
        },
    )
