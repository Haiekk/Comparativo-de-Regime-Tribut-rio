from greentax_engine import comparar
from .premissas_adapter import montar_premissas


def processar(dados: dict, incluir_simples: bool = True) -> dict:
    premissas = montar_premissas(dados)
    return comparar(premissas, incluir_simples=incluir_simples)