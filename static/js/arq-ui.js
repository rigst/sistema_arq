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

    function iniciar() { contarNumeros(); preencherBarras(); marcarEnvio(); }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", iniciar);
    } else {
        iniciar();
    }
})();
