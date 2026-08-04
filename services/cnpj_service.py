import logging
import re

import requests

logger = logging.getLogger(__name__)

URL_BASE = "https://api.opencnpj.org/"
TIMEOUT = 8

_PESOS_DV1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_PESOS_DV2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

def _limpar_cnpj(cnpj):
    return re.sub(r"[^0-9A-Za-z]", "", cnpj or "").upper()

def _valor_caractere(c):
    return ord(c) - 48

def _dv_modulo11(base, pesos):
    soma = sum(_valor_caractere(c) * p for c, p in zip(base, pesos))
    resto = soma % 11
    return 0 if resto < 2 else 11 - resto

def cnpj_valido(cnpj):
    c = _limpar_cnpj(cnpj)
    if len(c) != 14:
        return False
    if not re.fullmatch(r"[0-9A-Z]{12}[0-9]{2}", c):
        return False
    if len(set(c)) == 1:
        return False

    base = c[:12]
    dv1 = _dv_modulo11(base, _PESOS_DV1)
    dv2 = _dv_modulo11(base + str(dv1), _PESOS_DV2)
    return c[12] == str(dv1) and c[13] == str(dv2)

def consultar_cnpj(cnpj_bruto):
    cnpj = _limpar_cnpj(cnpj_bruto)

    if len(cnpj) != 14:
        return {"ok": False, "erro": "CNPJ deve conter 14 caracteres."}

    if not cnpj_valido(cnpj):
        return {"ok": False, "erro": "CNPJ inválido."}

    try:
        resp = requests.get(URL_BASE + cnpj, timeout=TIMEOUT)
    except requests.Timeout:
        logger.warning("Timeout ao consultar CNPJ %s", cnpj)
        return {"ok": False, "erro": "A consulta demorou demais. Tente novamente."}
    except requests.RequestException:
        logger.exception("Falha de rede ao consultar CNPJ %s", cnpj)
        return {"ok": False, "erro": "Não foi possível consultar o CNPJ agora. Preencha manualmente."}

    if resp.status_code == 404:
        return {"ok": False, "erro": "CNPJ não encontrado na base da Receita."}
    if resp.status_code == 400:
        return {"ok": False, "erro": "CNPJ inválido."}
    if resp.status_code == 429:
        logger.warning("Rate limit da OpenCNPJ atingido ao consultar CNPJ %s", cnpj)
        return {"ok": False, "erro": "Muitas consultas em pouco tempo. Aguarde alguns instantes e tente novamente."}
    if resp.status_code != 200:
        logger.warning("OpenCNPJ status %s para CNPJ %s", resp.status_code, cnpj)
        return {"ok": False, "erro": "Serviço de consulta indisponível no momento. Preencha manualmente."}

    try:
        d = resp.json()
    except ValueError:
        logger.exception("Resposta não-JSON da OpenCNPJ para CNPJ %s", cnpj)
        return {"ok": False, "erro": "Resposta inesperada do serviço de consulta."}

    municipio = (d.get("municipio") or "").strip()
    uf = (d.get("uf") or "").strip()

    dados = {
        "razao_social": (d.get("razao_social") or "").strip(),
        "cidade": municipio,
        "estado": uf,
        "email": (d.get("email") or "").strip(),
    }
    return {"ok": True, "dados": dados}