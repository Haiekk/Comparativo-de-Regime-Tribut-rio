"""
Ponto de entrada do cálculo — substitui ExcelService().processar(dados).
Mesma assinatura (recebe o dict do formulário, devolve o dict de resultados),
para que a cirurgia no app.py seja mínima. Sem Excel, sem thread, sem trava:
é síncrono e instantâneo.

Retorna: {"comparativo": {...}, "detalhamento": {...}, "dre": {...}, "meta": {...}}
onde 'meta' traz simples_elegivel, regime_recomendado, avisos e lucros.
"""
from greentax_engine import comparar
from .premissas_adapter import montar_premissas


def processar(dados: dict) -> dict:
    premissas = montar_premissas(dados)
    return comparar(premissas)