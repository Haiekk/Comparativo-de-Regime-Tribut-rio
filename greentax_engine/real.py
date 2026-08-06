from .models import Premissas
from .creditos import creditos_pis_cofins
from .folha import custo_folha_presumido_real
from . import tabelas as t

def _despesas_operacionais(p: Premissas) -> float:
    return (p.outras_desp_dedutiveis + p.desp_aluguel + p.desp_mat_consumo
            + p.desp_mat_limpeza + p.desp_energia + p.desp_financeiras
            + p.desp_combustivel + p.outras_desp_operacionais)

def calcular(p: Premissas) -> dict:
    cred_pis, cred_cofins = creditos_pis_cofins(p)

    pis_debito = p.fat_total * t.PIS_NAO_CUMULATIVO
    pis_recolher = max(pis_debito - cred_pis, 0)
    cofins_debito = p.fat_total * t.COFINS_NAO_CUMULATIVO
    cofins_recolher = max(cofins_debito - cred_cofins, 0)

    icms_debito = p.fat_comercio * p.icms
    icms_credito = p.compras_revenda * p.icms
    icms_recolher = max(icms_debito - icms_credito, 0)
    iss = (p.fat_servicos + p.fat_sem_nota) * p.iss

    receita_liquida = p.fat_total - (icms_debito + iss + pis_debito + cofins_debito)
    cmv_liquido = p.compras_revenda - icms_credito
    lucro_bruto = receita_liquida - cmv_liquido
    folha = custo_folha_presumido_real(p)
    lucro_real = lucro_bruto - folha - _despesas_operacionais(p)

    irpj = max(lucro_real, 0) * t.IRPJ_ALIQUOTA
    adicional_irpj = max(lucro_real - t.IRPJ_ADICIONAL_LIMITE, 0) * t.IRPJ_ADICIONAL
    irpj_total = irpj + adicional_irpj
    csll = max(lucro_real, 0) * t.CSLL_ALIQUOTA

    total = irpj_total + csll + pis_recolher + cofins_recolher + icms_recolher + iss
    return {
        "regime": "Lucro Real",
        "lucro_real": lucro_real,
        "irpj_total": irpj_total, "csll": csll,
        "pis_debito": pis_debito, "pis_credito": cred_pis, "pis_recolher": pis_recolher,
        "cofins_debito": cofins_debito, "cofins_credito": cred_cofins, "cofins_recolher": cofins_recolher,
        "icms_debito": icms_debito, "icms_credito": icms_credito, "icms_recolher": icms_recolher,
        "iss": iss,
        "total_impostos": total,                
        "carga": total / p.fat_total,           
        "folha": folha,
    }