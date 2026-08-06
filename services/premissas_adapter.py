from greentax_engine import Premissas
from .utils import parse_moeda

MAPA_DIRETO = {
    "fat_comercio":  "receita_comercio",
    "fat_servicos":  "receita_servicos",
    "fat_sem_nota":  "receita_sem_nota",
    "rbt12":         "rbt12",
    "salario_bruto": "folha_pagamento",
    "ticket_alim":   "ticket_alimentacao",
}

CUSTOS_DESPESAS = [
    ("compras_revenda",      "compras_revenda",          True),
    ("aluguel_pj",           "desp_aluguel",             True),
    ("frete_compras",        "outras_desp_operacionais", True),
    ("frete_vendas",         "outras_desp_operacionais", True),
    ("servicos_terceiros",   "outras_desp_operacionais", True),
    ("energia",              "desp_energia",             True),
    ("combustiveis",         "desp_combustivel",         True),
    ("epis",                 "outras_desp_operacionais", True),
    ("depreciacao",          "outras_desp_operacionais", True),
    ("ferramentas",          "outras_desp_operacionais", True),
    ("materiais_consumo",    "desp_mat_consumo",         False),
    ("materiais_limpeza",    "desp_mat_limpeza",         False),
    ("despesas_financeiras", "desp_financeiras",         False),
    ("outras_dedutiveis",    "outras_desp_dedutiveis",   True),
]

def montar_premissas(dados: dict) -> Premissas:
    valores = {
        campo_premissa: parse_moeda(dados.get(campo_form))
        for campo_premissa, campo_form in MAPA_DIRETO.items()
    }

    bases_credito = []
    for campo_form, premissa_dre, gera_credito in CUSTOS_DESPESAS:
        valor = parse_moeda(dados.get(campo_form))
        if premissa_dre is not None:
            valores[premissa_dre] = valores.get(premissa_dre, 0.0) + valor
        if gera_credito:
            bases_credito.append(valor)

    return Premissas(bases_credito=bases_credito, **valores)

CAMPOS_PREMISSAS = (
    ["receita_comercio", "receita_servicos", "receita_sem_nota", "rbt12"]
    + [campo for campo, _, _ in CUSTOS_DESPESAS]
    + ["folha_pagamento", "ticket_alimentacao"]
)