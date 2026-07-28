/* =====================================================
   dvolv · Simulador Tributário
   Comportamentos de interface. Nenhuma regra de cálculo
   é executada aqui — os valores seguem para o backend
   exatamente no mesmo formato de antes.
   ===================================================== */

/* --- Máscara de CNPJ (inalterada) --- */

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
}

/* --- Máscara monetária (inalterada) --- */

document.querySelectorAll(".money").forEach(function(input){
    input.addEventListener("input", function(e){
        let value = e.target.value.replace(/\D/g,'');
        value = (value/100).toLocaleString('pt-BR',{
            minimumFractionDigits:2
        });
        e.target.value = value;
    });
});

/* --- Estado visual do campo preenchido (só CSS) --- */

document.querySelectorAll(".money").forEach(function(input){
    const marcar = () => input.classList.toggle("preenchido", input.value.trim() !== "");
    input.addEventListener("input", marcar);
    input.addEventListener("blur", marcar);
    marcar();
});

/* --- Botão de envio: evita duplo clique enquanto calcula --- */

document.querySelectorAll("form").forEach(function(form){
    form.addEventListener("submit", function(){
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