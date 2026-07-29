from greentax_engine import comparar
from .premissas_adapter import montar_premissas


def processar(dados: dict) -> dict:
    premissas = montar_premissas(dados)
    return comparar(premissas)