import logging
import re

logger = logging.getLogger(__name__)


def parse_moeda(valor):
    """Interpreta valores monetários em formato BR ('1.234,56') ou US ('1234.56')."""
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)

    texto = re.sub(r"[^\d,.\-]", "", str(valor))
    if not texto or texto in {"-", ".", ","}:
        return 0.0

    virgulas = texto.count(",")
    pontos = texto.count(".")

    if virgulas and pontos:
        # o separador mais à direita é o decimal
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif virgulas == 1:
        texto = texto.replace(",", ".")
    elif pontos == 1:
        # um único ponto seguido de 3 dígitos é milhar (1.234), não decimal
        inteiro, _, fracao = texto.partition(".")
        if len(fracao) == 3 and fracao.isdigit():
            texto = inteiro + fracao
    else:
        texto = texto.replace(",", "").replace(".", "")

    try:
        return float(texto)
    except ValueError:
        logger.warning("Valor monetário não reconhecido: %r", valor)
        return 0.0


def num(valor, padrao=0.0):
    """Coage qualquer coisa para float com segurança (usado nas funções montar_*)."""
    if valor is None or valor == "":
        return padrao
    if isinstance(valor, bool):
        return float(valor)
    if isinstance(valor, (int, float)):
        return float(valor)
    return parse_moeda(valor)


def texto(valor, padrao=""):
    if valor is None:
        return padrao
    return str(valor).strip()