from .models import Premissas
from . import simples, presumido, real, contrato
from . import tabelas as t

PREFIXOS = ("simples", "presumido", "real")

def _formatar_reais(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def comparar(p: Premissas, incluir_simples: bool = True) -> dict:
    pr = presumido.calcular(p)
    r = real.calcular(p)

    receita = p.fat_total
    desp = (p.desp_aluguel + p.desp_mat_consumo + p.desp_mat_limpeza + p.desp_energia
            + p.desp_financeiras + p.desp_combustivel
            + p.outras_desp_dedutiveis + p.outras_desp_operacionais)

    lucros = {
        "presumido": receita - pr["total_impostos"] - pr["folha"] - desp - p.compras_revenda,
        "real": receita - r["total_impostos"] - r["folha"] - desp - p.compras_revenda,
    }

    avisos = []

    acima_do_teto = p.rbt12 > t.LIMITE_SIMPLES
    rbt12_informado = p.rbt12 > 0
    simples_incluido = incluir_simples and rbt12_informado and not acima_do_teto

    s = None
    if simples_incluido:
        s = simples.calcular(p)
        lucros["simples"] = (
            receita - s["total_impostos"] - s["folha"] - desp - p.compras_revenda
        )
        if p.rbt12 > t.SUBLIMITE_ICMS_ISS_SP:
            avisos.append(
                f"RBT12 acima do sublimite de R$ {_formatar_reais(t.SUBLIMITE_ICMS_ISS_SP)}: "
                "no Simples, ICMS e ISS passam a ser recolhidos por fora do DAS. "
                "A simulação ainda não considera esse recolhimento adicional."
            )
    else:
        avisos.append("Simples não incluído na comparação.")

    candidatos = [pfx for pfx in PREFIXOS if pfx in lucros]
    vencedor = max(candidatos, key=lambda pfx: lucros[pfx])
    recomendado = {pfx: (pfx == vencedor) for pfx in PREFIXOS}

    resultado = contrato.montar(p, s, pr, r, recomendado)
    resultado["meta"] = {
        "simples_incluido": simples_incluido,
        "acima_do_teto": acima_do_teto,
        "regime_recomendado": vencedor,
        "avisos": avisos,
        "lucros": lucros,
    }
    return resultado