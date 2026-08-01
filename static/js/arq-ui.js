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
    function marcarEnvio() {
        document.addEventListener("submit", function (e) {
            var form = e.target;
            if (!(form instanceof HTMLFormElement) || form.hasAttribute("data-sem-espera")) return;
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

    function iniciar() { contarNumeros(); preencherBarras(); marcarEnvio(); aberturaEmPassos(); }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", iniciar);
    } else {
        iniciar();
    }
})();
