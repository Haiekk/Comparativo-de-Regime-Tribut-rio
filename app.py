import logging
import os
import uuid
import threading

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_session import Session

from SERVICES.excel_service import ExcelService, ErroPlanilha, num, texto

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-troque-em-producao")

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_FILE_DIR"] = os.path.join(app.root_path, "flask_session")
Session(app)

TAREFAS_EXCEL = {}

def executar_calculo_background(task_id, dados):
    try:
        resultado = ExcelService().processar(dados)
        TAREFAS_EXCEL[task_id] = {"status": "concluido", "resultado": resultado}
    except ErroPlanilha as erro:
        TAREFAS_EXCEL[task_id] = {"status": "erro", "mensagem": str(erro)}
    except Exception as erro:
        app.logger.exception("Falha na thread de background")
        TAREFAS_EXCEL[task_id] = {"status": "erro", "mensagem": "Erro inesperado ao calcular."}

logging.basicConfig(level=logging.INFO)

LIMITE_SIMPLES = 4_800_000.0
SUBLIMITE_ICMS_ISS = 3_600_000.0

PREFIXOS = ["simples", "presumido", "real"]
NOMES_REGIMES = {
    "simples": "Simples Nacional",
    "presumido": "Lucro Presumido",
    "real": "Lucro Real",
}

CAMPOS_PREMISSAS = [
    "receita_comercio", "receita_servicos", "receita_sem_nota", "rbt12",
    "mercadorias_revenda", "aluguel_pj", "frete_compras", "frete_vendas",
    "servicos_terceiros", "combustiveis", "epis", "energia", "depreciacao",
    "ferramentas", "outras_despesas",
    "compras", "despesas_operacionais", "despesas_aluguel", "materiais_consumo",
    "materiais_limpeza", "despesas_energia", "despesas_financeiras",
    "despesas_combustivel",
    "folha_pagamento", "ticket_alimentacao",
]


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


def validar_premissas(form):
    erros, avisos = [], []

    from SERVICES.excel_service import parse_moeda

    receita = sum(parse_moeda(form.get(c)) for c in
                  ("receita_comercio", "receita_servicos", "receita_sem_nota"))
    rbt12 = parse_moeda(form.get("rbt12"))

    if receita <= 0:
        erros.append("Informe ao menos uma receita (comércio, serviços ou sem nota).")
    if rbt12 <= 0:
        erros.append("O RBT12 é obrigatório e deve ser maior que zero — ele define a faixa de alíquota do Simples Nacional.")
    elif rbt12 < receita:
        avisos.append("O RBT12 informado é menor que o faturamento do mês. Confira: ele deve somar os últimos 12 meses.")

    return erros, avisos


@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/novo", methods=["GET", "POST"])
def novo_planejamento():
    if request.method == "POST":
        razao_social = (request.form.get("razao_social") or "").strip()
        if not razao_social:
            return render_template(
                "novo_planejamento.html",
                erro="Informe a razão social.",
                form=request.form,
            )

        session["empresa"] = {
            "razao_social": razao_social,
            "cnpj": (request.form.get("cnpj") or "").strip(),
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

    if request.method == "GET":
        return render_template("premissas.html", form={})

    erros, avisos = validar_premissas(request.form)
    if erros:
        return render_template("premissas.html", erros=erros, form=request.form)

    session["premissas"] = {c: request.form.get(c) for c in CAMPOS_PREMISSAS}
    session["avisos_iniciais"] = avisos

    dados = {**session["empresa"], **session["premissas"]}

    task_id = str(uuid.uuid4())
    TAREFAS_EXCEL[task_id] = {"status": "processando"}

    thread = threading.Thread(target=executar_calculo_background, args=(task_id, dados))
    thread.start()

    return redirect(url_for("processando", task_id=task_id))

@app.route("/processando/<task_id>")
def processando(task_id):
    """Renderiza a tela de loading enquanto o Excel trabalha"""
    if task_id not in TAREFAS_EXCEL:
        return redirect(url_for("premissas"))
    return render_template("processando.html", task_id=task_id)

@app.route("/status/<task_id>")
def status_processamento(task_id):
    """Endpoint que o navegador consulta a cada 2 segundos via JS"""
    tarefa = TAREFAS_EXCEL.get(task_id)
    
    if not tarefa:
        return jsonify({"status": "erro", "mensagem": "Tarefa não encontrada ou expirada."})
        
    if tarefa["status"] == "concluido":
        resultado_excel = tarefa["resultado"]
        avisos = session.get("avisos_iniciais", [])
        
        session["resultado"] = montar_resumo(resultado_excel, avisos)
        session["tabela_comparativo"], session["tabela_recomendado"] = montar_tabela_comparativo(resultado_excel)
        session["tabela_dre"] = montar_tabela_dre(resultado_excel)
        
        del TAREFAS_EXCEL[task_id] 
        return jsonify({"status": "concluido", "redirect": url_for("resultado")})
        
    elif tarefa["status"] == "erro":
        mensagem = tarefa["mensagem"]
        del TAREFAS_EXCEL[task_id]
        return jsonify({"status": "erro", "mensagem": mensagem})
        
    return jsonify({"status": "processando"})

def montar_resumo(resultado_excel, avisos=None):
    comparativo = resultado_excel.get("comparativo", {})
    dre = resultado_excel.get("dre", {})
    avisos = list(avisos or [])

    prefixo_atual = identificar_regime_atual(session["empresa"].get("regime_atual"))

    rbt12 = num(session["premissas"].get("rbt12"))
    if isinstance(session["premissas"].get("rbt12"), str):
        from SERVICES.excel_service import parse_moeda
        rbt12 = parse_moeda(session["premissas"]["rbt12"])

    simples_elegivel = rbt12 <= LIMITE_SIMPLES
    if not simples_elegivel:
        avisos.append(
            f"RBT12 de R$ {formatar_moeda(rbt12)} ultrapassa o teto do Simples Nacional "
            f"(R$ {formatar_moeda(LIMITE_SIMPLES)}). O regime foi excluído da comparação."
        )
    elif rbt12 > SUBLIMITE_ICMS_ISS:
        avisos.append(
            f"RBT12 acima do sublimite de R$ {formatar_moeda(SUBLIMITE_ICMS_ISS)}: "
            "no Simples, ICMS e ISS passam a ser recolhidos por fora do DAS. "
            "A simulação ainda não considera esse recolhimento adicional."
        )

    candidatos = [p for p in PREFIXOS if p != "simples" or simples_elegivel]
    prefixo_novo = max(candidatos, key=lambda p: num(comparativo.get(f"{p}_lucro")))

    marcado = [p for p in PREFIXOS if texto(comparativo.get(f"{p}_recomendado"))]
    if marcado and marcado[0] != prefixo_novo:
        app.logger.warning(
            "Divergência de recomendação: planilha aponta %s, cálculo aponta %s",
            marcado[0], prefixo_novo,
        )

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

def montar_tabela_comparativo(resultado_excel):
    origens = {
        "detalhamento": resultado_excel.get("detalhamento", {}),
        "comparativo": resultado_excel.get("comparativo", {}),
    }
    comparativo = origens["comparativo"]

    tabela = []
    for rotulo, sufixo, grupo, tipo in LINHAS_COMPARATIVO:
        origem = origens[grupo]
        linha = {"rotulo": rotulo}
        for p in PREFIXOS:
            valor = origem.get(f"{p}_{sufixo}")
            linha[p] = f"{percentual(valor)}%" if tipo == "pct" else formatar_moeda(num(valor))
        tabela.append(linha)

    recomendado = {p: bool(texto(comparativo.get(f"{p}_recomendado"))) for p in PREFIXOS}
    return tabela, recomendado


def montar_tabela_dre(resultado_excel):
    dre = resultado_excel.get("dre", {})
    linhas = []
    
    tributos_simples = ["icms", "iss", "pis", "cofins", "irpj", "csll"]
    
    for rotulo, sufixo, tipo in LINHAS_DRE:
        linha = {"rotulo": rotulo}
        for p in PREFIXOS:
            valor = dre.get(f"{p}_{sufixo}")
            
            if p == "simples" and sufixo in tributos_simples and num(valor) == 0:
                linha[p] = {"is_das": True, "valor": ""}
            elif tipo == "pct":
                linha[p] = {"is_das": False, "valor": f"{percentual(valor)}%"}
            else:
                linha[p] = {"is_das": False, "valor": f"R$ {formatar_moeda(num(valor))}"}
        
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