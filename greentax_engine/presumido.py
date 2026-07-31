from .models import Premissas
from .folha import custo_folha_presumido_real
from . import tabelas as t

def calcular(p: Premissas) -> dict:
    base_irpj = (p.fat_comercio * t.PRESUMIDO_BASE_IRPJ_COMERCIO
                 + p.fat_servicos * t.PRESUMIDO_BASE_IRPJ_SERVICOS)
    irpj = base_irpj * t.IRPJ_ALIQUOTA
    adicional_irpj = max(base_irpj - t.IRPJ_ADICIONAL_LIMITE, 0) * t.IRPJ_ADICIONAL
    irpj_total = irpj + adicional_irpj

    base_csll = (p.fat_comercio * t.PRESUMIDO_BASE_CSLL_COMERCIO
                 + p.fat_servicos * t.PRESUMIDO_BASE_CSLL_SERVICOS)
    csll = base_csll * t.CSLL_ALIQUOTA

    pis = p.fat_total * t.PIS_CUMULATIVO
    cofins = p.fat_total * t.COFINS_CUMULATIVO

    icms_debito = p.fat_comercio * p.icms
    icms_credito = p.compras_revenda * p.icms
    icms_recolher = max(icms_debito - icms_credito, 0)

    iss = (p.fat_servicos + p.fat_sem_nota) * p.iss

    total = irpj_total + csll + pis + cofins + icms_recolher + iss
    return {
        "regime": "Lucro Presumido",
        "irpj_total": irpj_total, "csll": csll,
        "pis": pis, "cofins": cofins,
        "icms_debito": icms_debito, "icms_credito": icms_credito,
        "icms_recolher": icms_recolher, "iss": iss,
        "total_impostos": total,                
        "carga": total / p.fat_total,           
        "folha": custo_folha_presumido_real(p),
    }