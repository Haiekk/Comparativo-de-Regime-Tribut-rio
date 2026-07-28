"""
Adaptador form -> Premissas.

Reconcilia os nomes dos campos do formulário (que espelhavam as células da
planilha) com os nomes do motor. Toda conversão string->número passa pelo
parse_moeda. Campos não coletados pelo formulário (desp_alimentacao,
outras_desp_operacionais e as alíquotas ICMS/ISS/INSS/RAT/Sistema S) NÃO
aparecem aqui — assumem os valores-padrão definidos na dataclass Premissas.
"""
from greentax_engine import Premissas
from .utils import parse_moeda

# Bloco "Controle de Créditos" (B18:B28). Todas as linhas recebem
# PIS 1,65% + COFINS 7,6%, então somam numa base única de crédito.
# ATENÇÃO: 'mercadorias_revenda' (crédito, B18) é campo distinto de
# 'compras' (despesa/CMV, B32), mesmo que tenham o mesmo valor no exemplo.
CAMPOS_CREDITO = [
    "mercadorias_revenda", "aluguel_pj", "frete_compras", "frete_vendas",
    "servicos_terceiros", "combustiveis", "epis", "energia", "depreciacao",
    "ferramentas", "outras_despesas",
]

# {campo_da_Premissas: campo_do_formulario}
MAPA_NUMERICO = {
    "fat_comercio":           "receita_comercio",       # B10
    "fat_servicos":           "receita_servicos",       # B11
    "fat_sem_nota":           "receita_sem_nota",       # B12
    "rbt12":                  "rbt12",                  # B14
    "compras_revenda":        "compras",                # B32
    "outras_desp_dedutiveis": "despesas_operacionais",  # B33
    "desp_aluguel":           "despesas_aluguel",       # B34
    "desp_mat_consumo":       "materiais_consumo",      # B35
    "desp_mat_limpeza":       "materiais_limpeza",      # B36
    "desp_energia":           "despesas_energia",       # B37
    "desp_financeiras":       "despesas_financeiras",   # B38
    "desp_combustivel":       "despesas_combustivel",   # B39
    "salario_bruto":          "folha_pagamento",        # B45
    "ticket_alim":            "ticket_alimentacao",     # B46
}


def montar_premissas(dados: dict) -> Premissas:
    """Recebe o dicionário do formulário e devolve um objeto Premissas pronto."""
    numericos = {
        campo_premissa: parse_moeda(dados.get(campo_form))
        for campo_premissa, campo_form in MAPA_NUMERICO.items()
    }
    bases_credito = [parse_moeda(dados.get(c)) for c in CAMPOS_CREDITO]
    return Premissas(bases_credito=bases_credito, **numericos)