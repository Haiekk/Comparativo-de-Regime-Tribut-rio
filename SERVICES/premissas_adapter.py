from greentax_engine import Premissas
from .utils import parse_moeda

CAMPOS_CREDITO = [
    "mercadorias_revenda", "aluguel_pj", "frete_compras", "frete_vendas",
    "servicos_terceiros", "combustiveis", "epis", "energia", "depreciacao",
    "ferramentas", "outras_despesas",
]

MAPA_NUMERICO = {
    "fat_comercio":           "receita_comercio",       
    "fat_servicos":           "receita_servicos",      
    "fat_sem_nota":           "receita_sem_nota",       
    "rbt12":                  "rbt12",                  
    "compras_revenda":        "compras",                
    "outras_desp_dedutiveis": "despesas_operacionais",  
    "desp_aluguel":           "despesas_aluguel",       
    "desp_mat_consumo":       "materiais_consumo",      
    "desp_mat_limpeza":       "materiais_limpeza",      
    "desp_energia":           "despesas_energia",       
    "desp_financeiras":       "despesas_financeiras",   
    "desp_combustivel":       "despesas_combustivel",   
    "salario_bruto":          "folha_pagamento",        
    "ticket_alim":            "ticket_alimentacao",     
}

def montar_premissas(dados: dict) -> Premissas:
    numericos = {
        campo_premissa: parse_moeda(dados.get(campo_form))
        for campo_premissa, campo_form in MAPA_NUMERICO.items()
    }
    bases_credito = [parse_moeda(dados.get(c)) for c in CAMPOS_CREDITO]
    return Premissas(bases_credito=bases_credito, **numericos)