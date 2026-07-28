from .models import Premissas


def _despesas_dre(p: Premissas) -> dict:
    """Linhas de despesa da DRE — idênticas nos três regimes (B/C/D iguais)."""
    return {
        "aluguel": p.desp_aluguel,
        "consumo": p.desp_mat_consumo,
        "limpeza": p.desp_mat_limpeza,
        "energia": p.desp_energia,
        "financeiras": p.desp_financeiras,
        "combustivel": p.desp_combustivel,
        "alimentacao": p.desp_alimentacao,
        "outras": p.outras_desp_dedutiveis + p.outras_desp_operacionais,
    }


def montar(p: Premissas, s: dict, pr: dict, r: dict, recomendado: dict) -> dict:
    """
    s  = resultado do Simples   (simples.calcular)
    pr = resultado do Presumido (presumido.calcular)
    r  = resultado do Real      (real.calcular)
    recomendado = {"simples": bool, "presumido": bool, "real": bool}
    """
    receita = p.fat_total
    desp = _despesas_dre(p)
    soma_desp = sum(desp.values())

    # -------- lucro líquido por regime (= LUCRO LÍQUIDO da DRE) --------
    lucro_simples = receita - s["total_impostos"] - s["folha"] - soma_desp - p.compras_revenda
    lucro_presumido = receita - pr["total_impostos"] - pr["folha"] - soma_desp - p.compras_revenda
    lucro_real = receita - r["total_impostos"] - r["folha"] - soma_desp - p.compras_revenda

    def flag(pfx):
        return "✅ RECOMENDADO" if recomendado.get(pfx) else ""

    comparativo = {
        "simples_total_impostos": s["total_impostos"],
        "presumido_total_impostos": pr["total_impostos"],
        "real_total_impostos": r["total_impostos"],

        "simples_carga": s["carga"],
        "presumido_carga": pr["carga"],
        "real_carga": r["carga"],

        "simples_folha": s["folha"],
        "presumido_folha": pr["folha"],
        "real_folha": r["folha"],

        "simples_custo_total": s["total_impostos"] + s["folha"],
        "presumido_custo_total": pr["total_impostos"] + pr["folha"],
        "real_custo_total": r["total_impostos"] + r["folha"],

        "simples_lucro": lucro_simples,
        "presumido_lucro": lucro_presumido,
        "real_lucro": lucro_real,

        "simples_recomendado": flag("simples"),
        "presumido_recomendado": flag("presumido"),
        "real_recomendado": flag("real"),
    }

    # -------- detalhamento (LÍQUIDO a recolher) --------
    detalhamento = {
        "simples_das_irpj": s["das_total"],
        "presumido_das_irpj": pr["irpj_total"],
        "real_das_irpj": r["irpj_total"],

        "simples_csll": 0.0,
        "presumido_csll": pr["csll"],
        "real_csll": r["csll"],

        "simples_pis": 0.0,
        "presumido_pis": pr["pis"],
        "real_pis": r["pis_recolher"],

        "simples_cofins": 0.0,
        "presumido_cofins": pr["cofins"],
        "real_cofins": r["cofins_recolher"],

        "simples_iss_icms": 0.0,
        "presumido_iss_icms": pr["iss"] + pr["icms_recolher"],
        "real_iss_icms": r["iss"] + r["icms_recolher"],
    }

    # -------- DRE (débito bruto; sinais conforme planilha) --------
    dre = {"receita_bruta_mensal": receita}

    # Simples: DAS negativo, demais tributos zerados, CMV negativo
    dre.update({
        "simples_receita_bruta": receita,
        "simples_das": -s["das_total"],
        "simples_icms": 0.0, "simples_iss": 0.0, "simples_pis": 0.0, "simples_cofins": 0.0,
    })
    simples_rec_liq = receita + (-s["das_total"])  # = receita + SUM(tributos negativos)
    dre["simples_receita_liquida"] = simples_rec_liq
    dre["simples_cmv"] = -p.compras_revenda
    simples_lucro_bruto = simples_rec_liq + (-p.compras_revenda)
    dre["simples_lucro_bruto"] = simples_lucro_bruto
    dre["simples_pessoal"] = s["folha"]

    # Presumido / Real: ICMS em débito bruto, CMV positivo (líquido de crédito ICMS)
    for pfx, res in (("presumido", pr), ("real", r)):
        dre[f"{pfx}_receita_bruta"] = receita
        dre[f"{pfx}_das"] = 0.0
        dre[f"{pfx}_icms"] = res["icms_debito"]
        dre[f"{pfx}_iss"] = res["iss"]
        if pfx == "presumido":
            pis_dre, cofins_dre = res["pis"], res["cofins"]
        else:  # real: PIS/COFINS líquidos na DRE
            pis_dre, cofins_dre = res["pis_recolher"], res["cofins_recolher"]
        dre[f"{pfx}_pis"] = pis_dre
        dre[f"{pfx}_cofins"] = cofins_dre
        rec_liq = receita - 0.0 - res["icms_debito"] - res["iss"] - pis_dre - cofins_dre
        dre[f"{pfx}_receita_liquida"] = rec_liq
        cmv = p.compras_revenda - res["icms_credito"]
        dre[f"{pfx}_cmv"] = cmv
        dre[f"{pfx}_lucro_bruto"] = rec_liq - cmv
        dre[f"{pfx}_pessoal"] = res["folha"]

    # Linhas de despesa (iguais nos três) + resultado antes + IRPJ/CSLL + lucro líquido + margem
    lucros = {"simples": lucro_simples, "presumido": lucro_presumido, "real": lucro_real}
    irpj_map = {"simples": 0.0, "presumido": -pr["irpj_total"], "real": -r["irpj_total"]}
    csll_map = {"simples": 0.0, "presumido": -pr["csll"], "real": -r["csll"]}

    for pfx in ("simples", "presumido", "real"):
        for nome, valor in desp.items():
            dre[f"{pfx}_{nome}"] = valor
        resultado_antes = dre[f"{pfx}_lucro_bruto"] - dre[f"{pfx}_pessoal"] - soma_desp
        dre[f"{pfx}_resultado_antes"] = resultado_antes
        dre[f"{pfx}_irpj"] = irpj_map[pfx]
        dre[f"{pfx}_csll"] = csll_map[pfx]
        dre[f"{pfx}_lucro_liquido"] = resultado_antes + irpj_map[pfx] + csll_map[pfx]
        dre[f"{pfx}_margem"] = dre[f"{pfx}_lucro_liquido"] / receita

    return {"comparativo": comparativo, "detalhamento": detalhamento, "dre": dre}