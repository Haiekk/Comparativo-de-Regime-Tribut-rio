from .models import Premissas
from . import simples, presumido, real, contrato
from . import tabelas as t

PREFIXOS = ("simples", "presumido", "real")


def _formatar_reais(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def comparar(p: Premissas) -> dict:
    s = simples.calcular(p)
    pr = presumido.calcular(p)
    r = real.calcular(p)

    receita = p.fat_total
    desp = (p.desp_aluguel + p.desp_mat_consumo + p.desp_mat_limpeza + p.desp_energia
            + p.desp_financeiras + p.desp_combustivel + p.desp_alimentacao
            + p.outras_desp_dedutiveis + p.outras_desp_operacionais)

    lucros = {
        "simples": receita - s["total_impostos"] - s["folha"] - desp - p.compras_revenda,
        "presumido": receita - pr["total_impostos"] - pr["folha"] - desp - p.compras_revenda,
        "real": receita - r["total_impostos"] - r["folha"] - desp - p.compras_revenda,
    }

    avisos = []
    simples_elegivel = p.rbt12 <= t.LIMITE_SIMPLES
    if not simples_elegivel:
        avisos.append(
            f"RBT12 de R$ {_formatar_reais(p.rbt12)} ultrapassa o teto do Simples "
            f"Nacional (R$ {_formatar_reais(t.LIMITE_SIMPLES)}). O regime foi "
            "excluído da comparação."
        )
    elif p.rbt12 > t.SUBLIMITE_ICMS_ISS_SP:
        avisos.append(
            f"RBT12 acima do sublimite de R$ {_formatar_reais(t.SUBLIMITE_ICMS_ISS_SP)}: "
            "no Simples, ICMS e ISS passam a ser recolhidos por fora do DAS. "
            "A simulação ainda não considera esse recolhimento adicional."
        )

    elegiveis = [pfx for pfx in PREFIXOS if pfx != "simples" or simples_elegivel]
    vencedor = max(elegiveis, key=lambda pfx: lucros[pfx])
    recomendado = {pfx: (pfx == vencedor) for pfx in PREFIXOS}

    resultado = contrato.montar(p, s, pr, r, recomendado)
    resultado["meta"] = {
        "simples_elegivel": simples_elegivel,
        "regime_recomendado": vencedor,
        "avisos": avisos,
        "lucros": lucros,
    }
    return resultado