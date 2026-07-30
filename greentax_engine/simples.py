from .models import Premissas
from .tabelas import ANEXO_I, ANEXO_III, faixa_simples
from .folha import custo_folha_simples


def _das_anexo(rbt12, receita_mensal, tabela):
    aliq_nom, deduzir = faixa_simples(tabela, rbt12)
    aliq_efetiva = (rbt12 * aliq_nom - deduzir) / rbt12
    das = receita_mensal * aliq_efetiva
    return {"aliq_nominal": aliq_nom, "parcela_deduzir": deduzir,
            "aliq_efetiva": aliq_efetiva, "das": das}


def calcular(p: Premissas) -> dict:
    anexo_i = _das_anexo(p.rbt12, p.fat_comercio, ANEXO_I)      
    anexo_iii = _das_anexo(p.rbt12, p.fat_servicos, ANEXO_III)  
    das_total = anexo_i["das"] + anexo_iii["das"]               
    return {
        "regime": "Simples Nacional",
        "anexo_i": anexo_i,
        "anexo_iii": anexo_iii,
        "das_total": das_total,
        "total_impostos": das_total,
        "carga": das_total / p.fat_total,          
        "folha": custo_folha_simples(p),
    }