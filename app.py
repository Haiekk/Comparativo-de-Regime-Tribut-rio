import logging
import os

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_session import Session

from services.calculo_service import processar
from services.cnpj_service import consultar_cnpj, cnpj_valido
from services.premissas_adapter import CAMPOS_PREMISSAS
from services.utils import parse_moeda, num, texto

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-troque-em-producao")

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_FILE_DIR"] = os.path.join(app.root_path, "flask_session")
Session(app)

logging.basicConfig(level=logging.INFO)

PREFIXOS = ["simples", "presumido", "real"]
NOMES_REGIMES = {
    "simples": "Simples Nacional",
    "presumido": "Lucro Presumido",
    "real": "Lucro Real",
}

def formatar_moeda(valor):
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        valor = 0.0
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def percentual(valor):
    v = num(valor)
    return round(v * 100 if abs(v) <= 1 else v, 2)

def identificar_regime_atual(rotulo):
    rotulo = (rotulo or "").lower()
    if "presumido" in rotulo:
        return "presumido"
    if "real" in rotulo:
        return "real"
    return "simples"

def validar_premissas(form, prefixo_regime, incluir_simples):
    erros, avisos = [], []

    receita = sum(parse_moeda(form.get(c)) for c in
                  ("receita_comercio", "receita_servicos", "receita_sem_nota"))
    rbt12 = parse_moeda(form.get("rbt12"))

    if receita <= 0:
        erros.append("Informe ao menos uma receita (comércio, serviços ou sem nota).")

    if prefixo_regime != "simples" and form.get("comparar_simples") not in ("sim", "nao"):
        erros.append("Informe se deseja comparar com o Simples Nacional.")

    if incluir_simples:
        if rbt12 <= 0:
            erros.append("O RBT12 é obrigatório e deve ser maior que zero — ele define a faixa de alíquota do Simples Nacional.")
        elif rbt12 < receita:
            erros.append("O RBT12 informado é menor que o faturamento do mês. Confira: ele deve somar os últimos 12 meses.")

    return erros, avisos

@app.route("/")
def dashboard():
    return render_template("index.html")

@app.route("/consulta-cnpj/<cnpj>")
def consulta_cnpj(cnpj):
    resultado = consultar_cnpj(cnpj)
    status = 200 if resultado.get("ok") else 422
    return jsonify(resultado), status


@app.route("/novo", methods=["GET", "POST"])
def novo_planejamento():
    if request.method == "POST":
        razao_social = (request.form.get("razao_social") or "").strip()
        cnpj = (request.form.get("cnpj") or "").strip()

        erros = []
        if not razao_social:
            erros.append("Informe a razão social.")
        if not cnpj:
            erros.append("Informe o CNPJ.")
        elif not cnpj_valido(cnpj):
            erros.append("CNPJ inválido. Confira os dígitos informados.")

        if erros:
            return render_template(
                "novo_planejamento.html",
                erros=erros,
                form=request.form,
            )

        session["empresa"] = {
            "razao_social": razao_social,
            "cnpj": cnpj,
            "email": (request.form.get("email") or "").strip(),
            "cidade": (request.form.get("cidade") or "").strip(),
            "estado": (request.form.get("estado") or "").strip(),
            "atividade": (request.form.get("atividade") or "").strip(),
            "regime_atual": (request.form.get("regime_atual") or "").strip(),
        }
        return redirect(url_for("premissas"))

    return render_template("novo_planejamento.html", form={})


@app.route("/premissas", methods=["GET", "POST"])
def premissas():
    if "empresa" not in session:
        return redirect(url_for("novo_planejamento"))

    prefixo_regime = identificar_regime_atual(session["empresa"].get("regime_atual"))

    if request.method == "GET":
        return render_template("premissas.html", form={}, prefixo_regime=prefixo_regime)

    if prefixo_regime == "simples":
        incluir_simples = True
    else:
        incluir_simples = request.form.get("comparar_simples") == "sim"

    erros, avisos = validar_premissas(request.form, prefixo_regime, incluir_simples)
    if erros:
        return render_template("premissas.html", erros=erros, form=request.form,
                               prefixo_regime=prefixo_regime)

    session["premissas"] = {c: request.form.get(c) for c in CAMPOS_PREMISSAS}
    session["incluir_simples"] = incluir_simples

    dados = {**session["empresa"], **session["premissas"]}

    try:
        resultado_calc = processar(dados, incluir_simples=incluir_simples)
    except Exception:
        app.logger.exception("Falha no cálculo do comparativo")
        return render_template(
            "premissas.html",
            erros=["Não foi possível concluir o cálculo. Revise as premissas e tente novamente."],
            form=request.form,
            prefixo_regime=prefixo_regime,
        )

    avisos = avisos + resultado_calc["meta"]["avisos"]

    session["resultado"] = montar_resumo(resultado_calc, avisos)
    session["tabela_comparativo"], session["tabela_recomendado"] = montar_tabela_comparativo(resultado_calc)
    session["tabela_dre"] = montar_tabela_dre(resultado_calc)

    return redirect(url_for("resultado"))


def montar_resumo(resultado_calc, avisos=None):
    comparativo = resultado_calc.get("comparativo", {})
    dre = resultado_calc.get("dre", {})
    meta = resultado_calc.get("meta", {})
    avisos = list(avisos or [])

    prefixo_atual = identificar_regime_atual(session["empresa"].get("regime_atual"))
    prefixo_novo = meta.get("regime_recomendado")

    tributo_atual = num(comparativo.get(f"{prefixo_atual}_total_impostos"))
    tributo_novo = num(comparativo.get(f"{prefixo_novo}_total_impostos"))
    lucro_atual = num(comparativo.get(f"{prefixo_atual}_lucro"))
    lucro_novo = num(comparativo.get(f"{prefixo_novo}_lucro"))

    ganho_lucro = lucro_novo - lucro_atual
    economia_tributaria = tributo_atual - tributo_novo
    ja_otimizado = prefixo_novo == prefixo_atual

    reducao = (economia_tributaria / tributo_atual * 100) if tributo_atual > 0 else 0.0

    return {
        "receita": formatar_moeda(num(dre.get("receita_bruta_mensal"))),
        "regime_atual": NOMES_REGIMES[prefixo_atual],
        "regime_novo": NOMES_REGIMES[prefixo_novo],
        "ja_otimizado": ja_otimizado,
        "tributo_atual": formatar_moeda(tributo_atual),
        "tributo_novo": formatar_moeda(tributo_novo),
        "lucro_atual": formatar_moeda(lucro_atual),
        "lucro_novo": formatar_moeda(lucro_novo),
        "percentual_atual": percentual(comparativo.get(f"{prefixo_atual}_carga")),
        "percentual_novo": percentual(comparativo.get(f"{prefixo_novo}_carga")),
        "economia": formatar_moeda(max(economia_tributaria, 0.0)),
        "ganho_lucro": formatar_moeda(max(ganho_lucro, 0.0)),
        "reducao": round(max(reducao, 0.0), 2),
        "avisos": avisos,
    }

LINHAS_COMPARATIVO = [
    ("DAS / IRPJ", "das_irpj", "detalhamento", "moeda"),
    ("CSLL", "csll", "detalhamento", "moeda"),
    ("PIS", "pis", "detalhamento", "moeda"),
    ("COFINS", "cofins", "detalhamento", "moeda"),
    ("ISS + ICMS", "iss_icms", "detalhamento", "moeda"),
    ("Total de Impostos", "total_impostos", "comparativo", "moeda"),
    ("Carga Tributária", "carga", "comparativo", "pct"),
    ("Custo Total de Folha", "folha", "comparativo", "moeda"),
    ("Custo Total", "custo_total", "comparativo", "moeda"),
    ("Lucro Líquido", "lucro", "comparativo", "moeda"),
]

LINHAS_DRE = [
    ("Receita Bruta de Vendas e Serviços", "receita_bruta", "moeda"),
    ("(-) DAS (tributo único — Simples)", "das", "moeda"),
    ("(-) ICMS sobre vendas", "icms", "moeda"),
    ("(-) ISS sobre serviços", "iss", "moeda"),
    ("(-) PIS sobre a receita", "pis", "moeda"),
    ("(-) COFINS sobre a receita", "cofins", "moeda"),
    ("(=) RECEITA LÍQUIDA", "receita_liquida", "moeda"),
    ("(-) CMV — Compras de peças", "cmv", "moeda"),
    ("(=) LUCRO BRUTO", "lucro_bruto", "moeda"),
    ("(-) Despesas com Pessoal", "pessoal", "moeda"),
    ("(-) Despesas Aluguel", "aluguel", "moeda"),
    ("(-) Despesas Mat. Consumo e Embalagens", "consumo", "moeda"),
    ("(-) Despesas Mat. Conserv. E Limpeza", "limpeza", "moeda"),
    ("(-) Despesas Energia Elétrica", "energia", "moeda"),
    ("(-) Despesas Financeiras", "financeiras", "moeda"),
    ("(-) Despesas Combustível", "combustivel", "moeda"),
    ("(-) Despesas Alimentação", "alimentacao", "moeda"),
    ("(-) Outras Despesas Operacionais", "outras", "moeda"),
    ("(=) RESULTADO ANTES DE IRPJ/CSLL", "resultado_antes", "moeda"),
    ("(-) IRPJ (+ adicional)", "irpj", "moeda"),
    ("(-) CSLL", "csll", "moeda"),
    ("(=) LUCRO LÍQUIDO DO PERÍODO", "lucro_liquido", "moeda"),
    ("Margem Líquida (% sobre a Receita)", "margem", "pct"),
]

def montar_tabela_comparativo(resultado_calc):
    origens = {
        "detalhamento": resultado_calc.get("detalhamento", {}),
        "comparativo": resultado_calc.get("comparativo", {}),
    }
    comparativo = origens["comparativo"]

    tabela = []
    for rotulo, sufixo, grupo, tipo in LINHAS_COMPARATIVO:
        origem = origens[grupo]
        linha = {"rotulo": rotulo}
        for p in PREFIXOS:
            valor = origem.get(f"{p}_{sufixo}")
            if valor is None:                     
                linha[p] = "—"
            elif tipo == "pct":
                linha[p] = f"{percentual(valor)}%"
            else:
                linha[p] = formatar_moeda(num(valor))
        tabela.append(linha)

    recomendado = {p: bool(texto(comparativo.get(f"{p}_recomendado"))) for p in PREFIXOS}
    return tabela, recomendado

def montar_tabela_dre(resultado_calc):
    dre = resultado_calc.get("dre", {})
    linhas = []

    tributos_simples = ["icms", "iss", "pis", "cofins", "irpj", "csll"]

    for rotulo, sufixo, tipo in LINHAS_DRE:
        linha = {"rotulo": rotulo}
        eh_abatimento = rotulo.strip().startswith("(-)")
        for p in PREFIXOS:
            valor = dre.get(f"{p}_{sufixo}")

            if valor is None:                     
                linha[p] = {"is_das": False, "valor": "—"}
            elif p == "simples" and sufixo in tributos_simples and num(valor) == 0:
                linha[p] = {"is_das": True, "valor": ""}
            elif tipo == "pct":
                linha[p] = {"is_das": False, "valor": f"{percentual(valor)}%"}
            else:
                v = num(valor)
                if eh_abatimento:
                    v = abs(v)
                linha[p] = {"is_das": False, "valor": f"R$ {formatar_moeda(v)}"}

        linhas.append(linha)

    return {
        "receita_bruta_mensal": formatar_moeda(num(dre.get("receita_bruta_mensal"))),
        "linhas": linhas
    }

@app.route("/resultado")
def resultado():
    if "resultado" not in session:
        return redirect(url_for("novo_planejamento"))
    return render_template(
        "resultado.html",
        empresa=session.get("empresa"),
        resultado=session.get("resultado"),
        tabela_comparativo=session.get("tabela_comparativo"),
        tabela_recomendado=session.get("tabela_recomendado"),
        tabela_dre=session.get("tabela_dre"),
        nomes_regimes=NOMES_REGIMES,
        prefixos=PREFIXOS,
    )

@app.route("/novo-processo")
def novo_processo():
    session.clear()
    return redirect(url_for("novo_planejamento"))

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)