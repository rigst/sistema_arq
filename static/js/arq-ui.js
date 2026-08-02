/* =================================================================
   A.R.Q. — comportamentos de interface
   Três coisas, todas opcionais: números que contam, barras que
   preenchem e botões que mostram que o envio começou.
   Nada aqui é necessário para a página funcionar.
   ================================================================= */
(function () {
    "use strict";

    var semMovimento = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    /* --- Números do painel contam até o valor, mantendo o formato --- */
    function contarNumeros() {
        document.querySelectorAll(".kpi-value").forEach(function (el) {
            var partes = /^(\D*?)([\d.,]+)(\D*)$/.exec(el.textContent.trim());
            if (!partes) return;

            var prefixo = partes[1];
            var bruto = partes[2];
            var sufixo = partes[3];
            var decimais = /,(\d+)$/.exec(bruto);
            decimais = decimais ? decimais[1].length : 0;
            var alvo = parseFloat(bruto.replace(/\./g, "").replace(",", "."));
            if (!isFinite(alvo) || alvo === 0) return;

            var fmt = new Intl.NumberFormat("pt-BR", {
                minimumFractionDigits: decimais,
                maximumFractionDigits: decimais,
            });
            var escrever = function (v) { el.textContent = prefixo + fmt.format(v) + sufixo; };

            if (semMovimento) return;

            var duracao = 750;
            var inicio = null;
            escrever(0);
            requestAnimationFrame(function passo(agora) {
                if (inicio === null) inicio = agora;
                var t = Math.min(1, (agora - inicio) / duracao);
                var suave = 1 - Math.pow(1 - t, 3);
                escrever(t === 1 ? alvo : alvo * suave);
                if (t < 1) requestAnimationFrame(passo);
            });
        });
    }

    /* --- Barras de progresso crescem a partir do zero --- */
    function preencherBarras() {
        if (semMovimento) return;
        var barras = document.querySelectorAll(".ds-progress-fill");
        if (!barras.length) return;
        barras.forEach(function (b) {
            b.dataset.alvo = b.style.width || "0%";
            b.style.width = "0%";
        });
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                barras.forEach(function (b) { b.style.width = b.dataset.alvo; });
            });
        });
    }

    /* --- Botão de envio mostra que já foi clicado (e não aceita dois cliques) --- */
    /* Trava de duplo envio: o segundo clique no mesmo botão não repete o POST.
       Formulário method="dialog" fica de fora — ele não envia nada, só fecha o
       modal, e travá-lo fazia o X parar de funcionar depois do primeiro uso.
       Modal preso aberto deixa o resto da página inerte, e era isso que
       parecia "a roda do mouse não rola". */
    function marcarEnvio() {
        document.addEventListener("submit", function (e) {
            var form = e.target;
            if (!(form instanceof HTMLFormElement)) return;
            if (form.method === "dialog" || form.hasAttribute("data-sem-espera")) return;
            /* Botão com formmethod="dialog" (o Cancelar) também só fecha. */
            if (e.submitter && e.submitter.formMethod === "dialog") return;
            if (form.dataset.enviando === "1") { e.preventDefault(); return; }
            form.dataset.enviando = "1";
            var botao = form.querySelector('button[type="submit"], button:not([type])');
            if (botao) botao.classList.add("is-busy");
        });
    }

    /* Abertura de projeto em dois passos.
       Sem JavaScript o formulário aparece inteiro e funciona igual — o que o
       script faz é esconder o que ainda não interessa, não habilitar nada. */
    function aberturaEmPassos() {
        var form = document.querySelector("[data-abertura]");
        if (!form) return;

        var seletor = form.querySelector("#id_cliente_existente");
        var ficha = form.querySelector("[data-cliente-ficha]");
        var blocoNovo = form.querySelector("[data-cliente-novo]");
        var passoProjeto = form.querySelector("[data-passo-projeto]");
        if (!seletor || !ficha || !blocoNovo || !passoProjeto) return;

        var campoNome = form.querySelector("#id_cliente_nome");

        function clienteResolvido() {
            return Boolean(seletor.value) || Boolean(campoNome && campoNome.value.trim());
        }

        function pintar() {
            var opcao = seletor.options[seletor.selectedIndex];
            var existente = Boolean(seletor.value);

            ficha.hidden = !existente;
            blocoNovo.hidden = existente;
            /* Campo escondido não pode continuar exigindo preenchimento. */
            if (campoNome) campoNome.disabled = existente;

            if (existente && opcao) {
                ["nome", "email", "telefone"].forEach(function (campo) {
                    var alvo = ficha.querySelector('[data-ficha="' + campo + '"]');
                    if (alvo) alvo.textContent = opcao.getAttribute("data-" + campo) || "—";
                });
                var link = ficha.querySelector("[data-ficha-link]");
                if (link) link.href = opcao.getAttribute("data-url") || "#";
            }

            passoProjeto.hidden = !clienteResolvido();
        }

        seletor.addEventListener("change", pintar);
        if (campoNome) campoNome.addEventListener("input", pintar);
        pintar();
    }

    /* Avisos do canto: fecham no clique e somem sozinhos.
       Erro NÃO some sozinho — quem precisa reler o que deu errado não deve
       correr contra um cronômetro. */
    function avisos() {
        var caixa = document.querySelector("[data-avisos]");
        if (!caixa) return;

        function fechar(aviso) {
            aviso.classList.add("is-saindo");
            window.setTimeout(function () {
                aviso.remove();
                if (!caixa.querySelector(".ds-aviso")) caixa.remove();
            }, 260);
        }

        Array.prototype.forEach.call(caixa.querySelectorAll(".ds-aviso"), function (aviso, i) {
            var botao = aviso.querySelector(".ds-aviso-fechar");
            if (botao) botao.addEventListener("click", function () { fechar(aviso); });

            if (aviso.classList.contains("ds-aviso--error")) return;
            var prazo = 5000 + i * 600;
            var relogio = window.setTimeout(function () { fechar(aviso); }, prazo);
            /* Com o ponteiro em cima, o aviso espera: quem está lendo não
               quer ver o texto sumir no meio da frase. */
            aviso.addEventListener("mouseenter", function () { window.clearTimeout(relogio); });
        });
    }

    /* Modais de criação. O botão traz data-abre="id-do-dialog".
       Sem JavaScript o <dialog> não abre — por isso todo modal do sistema é
       para CRIAR algo, nunca para ler: quem não tem script continua vendo a
       lista inteira, que é o conteúdo da página. */
    function modais() {
        document.querySelectorAll("[data-abre]").forEach(function (botao) {
            var alvo = document.getElementById(botao.getAttribute("data-abre"));
            if (!alvo || typeof alvo.showModal !== "function") return;
            botao.hidden = false;
            botao.addEventListener("click", function () {
                alvo.showModal();
                var primeiro = alvo.querySelector(
                    "input:not([type=hidden]), select, textarea"
                );
                if (primeiro) primeiro.focus();
            });
        });

        /* Clique fora fecha: o backdrop é o próprio <dialog>, então basta
           conferir se o ponto do clique caiu fora da caixa. */
        document.querySelectorAll("dialog.ds-modal").forEach(function (dlg) {
            /* Fechar sem enviar destrava o formulário: senão, reabrir o modal
               e tentar de novo esbarraria na marca do envio anterior. */
            dlg.addEventListener("close", function () {
                dlg.querySelectorAll("form").forEach(function (f) {
                    delete f.dataset.enviando;
                    f.querySelectorAll(".is-busy").forEach(function (b) {
                        b.classList.remove("is-busy");
                    });
                });
            });
            dlg.addEventListener("click", function (e) {
                if (e.target !== dlg) return;
                var r = dlg.getBoundingClientRect();
                var dentro = e.clientX >= r.left && e.clientX <= r.right &&
                             e.clientY >= r.top && e.clientY <= r.bottom;
                if (!dentro) dlg.close();
            });
        });
    }

    function iniciar() { contarNumeros(); preencherBarras(); marcarEnvio(); aberturaEmPassos(); avisos(); modais(); }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", iniciar);
    } else {
        iniciar();
    }
})();
