const cnpj = document.getElementById("cnpj");
if (cnpj) {
  cnpj.addEventListener("input", (e) => {
    let v = e.target.value.replace(/[^A-Za-z0-9]/g, "").toUpperCase().substring(0, 14);
    v = v.replace(/^([A-Z0-9]{2})([A-Z0-9])/, "$1.$2");
    v = v.replace(/^([A-Z0-9]{2})\.([A-Z0-9]{3})([A-Z0-9])/, "$1.$2.$3");
    v = v.replace(/\.([A-Z0-9]{3})([A-Z0-9])/, ".$1/$2");
    v = v.replace(/\/([A-Z0-9]{4})([A-Z0-9])/, "/$1-$2");
    e.target.value = v;
  });

  const PESOS_DV1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const PESOS_DV2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

  function limparCnpj(valor) {
    return (valor || "").replace(/[^0-9A-Za-z]/g, "").toUpperCase();
  }

  function dvModulo11(base, pesos) {
    let soma = 0;
    for (let i = 0; i < pesos.length; i++) {
      soma += (base.charCodeAt(i) - 48) * pesos[i];
    }
    const resto = soma % 11;
    return resto < 2 ? 0 : 11 - resto;
  }

  function cnpjValido(valor) {
    const c = limparCnpj(valor);
    if (c.length !== 14) return false;
    if (!/^[0-9A-Z]{12}[0-9]{2}$/.test(c)) return false;
    if (new Set(c).size === 1) return false;
    const base = c.substring(0, 12);
    const dv1 = dvModulo11(base, PESOS_DV1);
    const dv2 = dvModulo11(base + dv1, PESOS_DV2);
    return c[12] === String(dv1) && c[13] === String(dv2);
  }

  function erroCnpj(valor) {
    const limpo = limparCnpj(valor);
    if (limpo.length === 0) return "Informe o CNPJ.";
    if (limpo.length < 14) return "O CNPJ deve conter 14 dígitos.";
    if (!cnpjValido(limpo)) return "CNPJ inválido. Confira os dígitos informados.";
    return "";
  }

  const consultarCnpj = () => {
    const limpo = limparCnpj(cnpj.value);
    if (limpo.length === 0) {
      definirStatusCnpj("", "info");
      return;
    }
    const erro = erroCnpj(limpo);
    if (erro) {
      definirStatusCnpj(erro, "erro");
      return;
    }

    definirStatusCnpj("Consultando Receita…", "info");

    fetch("/consulta-cnpj/" + limpo)
      .then((resp) => resp.json())
      .then((data) => {
        if (data.ok) {
          preencherCampo("razao_social", data.dados.razao_social);
          preencherCampo("cidade", data.dados.cidade);
          preencherCampo("email", data.dados.email);
          selecionarEstado(data.dados.estado);
          definirStatusCnpj("Dados encontrados e preenchidos.", "sucesso");
        } else {
          definirStatusCnpj(data.erro || "Não foi possível consultar o CNPJ.", "erro");
        }
      })
      .catch(() => {
        definirStatusCnpj("Falha ao consultar o CNPJ. Preencha manualmente.", "erro");
      });
  };

  cnpj.addEventListener("blur", consultarCnpj);

  const formCnpj = cnpj.closest("form");
  if (formCnpj) {
    formCnpj.addEventListener("submit", function (e) {
      const erro = erroCnpj(cnpj.value);
      if (erro) {
        e.preventDefault();
        e.stopImmediatePropagation(); 
        definirStatusCnpj(erro, "erro");
        cnpj.focus();
      }
    });
  }

  function preencherCampo(id, valor) {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = valor || "";
    el.classList.toggle("preenchido", el.value.trim() !== "");
  }

  function selecionarEstado(uf) {
    const el = document.getElementById("estado");
    if (!el || !uf) return;
    for (const opt of el.options) {
      if (opt.value === uf || opt.text === uf) {
        el.value = opt.value || opt.text;
        break;
      }
    }
  }

  function definirStatusCnpj(mensagem, tipo) {
    let alvo = document.getElementById("cnpj-status");
    if (!alvo) {
      alvo = document.createElement("small");
      alvo.id = "cnpj-status";
      alvo.className = "d-block mt-1";
      cnpj.parentNode.appendChild(alvo);
    }
    const cores = { info: "text-muted", sucesso: "text-success", erro: "text-danger" };
    alvo.className = "d-block mt-1 " + (cores[tipo] || "text-muted");
    alvo.textContent = mensagem;
  }
}

(function () {
  const radios = document.querySelectorAll('input[name="comparar_simples"]');
  const container = document.getElementById("rbt12-container");
  if (radios.length === 0 || !container) return;

  function atualizar() {
    let escolha = "";
    radios.forEach((r) => {
      if (r.checked) escolha = r.value;
    });
    container.style.display = escolha === "sim" ? "" : "none";
  }

  radios.forEach((r) => r.addEventListener("change", atualizar));
  atualizar(); 
})();

document.querySelectorAll(".money").forEach(function (input) {
  input.addEventListener("input", function (e) {
    let value = e.target.value.replace(/\D/g, "");
    value = (value / 100).toLocaleString("pt-BR", {
      minimumFractionDigits: 2,
    });
    e.target.value = value;
  });
});

document.querySelectorAll(".money").forEach(function (input) {
  const marcar = () => input.classList.toggle("preenchido", input.value.trim() !== "");
  input.addEventListener("input", marcar);
  input.addEventListener("blur", marcar);
  marcar();
});

document.querySelectorAll("form").forEach(function (form) {
  form.addEventListener("submit", function () {
    const botao = form.querySelector('button[type="submit"]');
    if (!botao || botao.dataset.enviando) return;
    botao.dataset.enviando = "1";
    if (botao.dataset.carregando) {
      botao.textContent = botao.dataset.carregando;
    }
    botao.classList.add("disabled");
    botao.setAttribute("aria-disabled", "true");
  });
});