from pathlib import Path
import logging
import re
import shutil
import threading
import time
import uuid

import xlwings as xw

from SERVICES import excel_map

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
MODELO = BASE_DIR / "EXCEL" / "Greentax_Planejamento_Tributario_Compressores(Recuperado Automaticamente).xlsx"
TEMP = BASE_DIR / "TEMP"

ERROS_EXCEL = {
    -2146826288: "#NULL!",
    -2146826281: "#DIV/0!",
    -2146826273: "#VALUE!",
    -2146826265: "#REF!",
    -2146826259: "#NAME?",
    -2146826252: "#NUM!",
    -2146826246: "#N/A",
}

_TRAVA = threading.Lock()

try:
    import pythoncom
except ImportError:
    pythoncom = None


class ErroPlanilha(RuntimeError):
    """A planilha não pôde ser processada ou devolveu resultado inválido."""


def parse_moeda(valor):
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

        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif virgulas == 1:
        texto = texto.replace(",", ".")          
    elif pontos == 1:

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

    if valor is None or valor == "":
        return padrao
    if isinstance(valor, bool):
        return float(valor)
    if isinstance(valor, int) and valor in ERROS_EXCEL:
        raise ErroPlanilha(f"Célula com erro de cálculo: {ERROS_EXCEL[valor]}")
    if isinstance(valor, (int, float)):
        return float(valor)
    return parse_moeda(valor)


def texto(valor, padrao=""):
    if valor is None:
        return padrao
    if isinstance(valor, int) and valor in ERROS_EXCEL:
        return padrao
    return str(valor).strip()


def limpar_temporarios(idade_minima_segundos=3600):
    TEMP.mkdir(parents=True, exist_ok=True)
    limite = time.time() - idade_minima_segundos
    removidos = 0
    for arquivo in TEMP.glob("*.xlsx"):
        try:
            if arquivo.stat().st_mtime < limite:
                arquivo.unlink()
                removidos += 1
        except OSError:
            logger.warning("Não foi possível remover %s", arquivo)
    if removidos:
        logger.info("Removidas %d cópias temporárias órfãs", removidos)


class ExcelService:
    def __init__(self, modelo=None):
        self.modelo = Path(modelo) if modelo else MODELO
        if not self.modelo.exists():
            raise ErroPlanilha(
                f"Planilha modelo não encontrada em {self.modelo}. "
                "Confira o nome do arquivo e o caso das letras da pasta."
            )
        TEMP.mkdir(parents=True, exist_ok=True)

        problemas = excel_map.validar(self.modelo)
        if problemas:
            raise ErroPlanilha(
                "O mapa não bate com a planilha:\n  - " + "\n  - ".join(problemas)
            )

        self.arquivo = None
        self.app = None
        self.wb = None
    def criar_copia(self):
        self.arquivo = TEMP / f"{uuid.uuid4()}.xlsx"
        shutil.copy(self.modelo, self.arquivo)
        return self.arquivo

    def abrir(self):
        self.app = xw.App(visible=False, add_book=False)
        self.app.display_alerts = False
        self.app.screen_updating = False
        self.wb = self.app.books.open(str(self.arquivo))

    def preencher(self, dados):
        for grupo in excel_map.INPUTS.values():
            for campo, (aba, celula) in grupo.items():
                valor = dados.get(campo)
                if campo not in excel_map.CAMPOS_TEXTO:
                    valor = parse_moeda(valor)
                self.wb.sheets[aba].range(celula).value = valor

        for campo, alvos in excel_map.CAMPOS_ESPELHADOS.items():
            valor = dados.get(campo)
            if campo not in excel_map.CAMPOS_TEXTO:
                valor = parse_moeda(valor)
            for aba, celula in alvos:
                self.wb.sheets[aba].range(celula).value = valor

    def recalcular(self):
        try:
            self.app.api.CalculateFullRebuild()
        except Exception:
            logger.debug("CalculateFullRebuild indisponível, usando calculate()")
            self.app.calculate()

    def ler(self):
        resultados = {}
        for grupo, campos in excel_map.OUTPUTS.items():
            resultados[grupo] = {}
            for nome, (aba, celula) in campos.items():
                bruto = self.wb.sheets[aba].range(celula).value
                if isinstance(bruto, int) and bruto in ERROS_EXCEL:
                    raise ErroPlanilha(
                        f"{aba}!{celula} devolveu {ERROS_EXCEL[bruto]}. "
                        "Verifique as premissas informadas (RBT12 zerado, por exemplo)."
                    )
                if isinstance(bruto, str):
                    bruto = bruto.strip()
                resultados[grupo][nome] = bruto
        return resultados

    def fechar(self):

        if self.wb is not None:
            try:
                self.wb.close()
            except Exception:
                logger.exception("Falha ao fechar a pasta de trabalho")
            self.wb = None

        if self.app is not None:
            try:
                self.app.quit()
            except Exception:
                logger.exception("Falha no quit(); tentando kill()")
                try:
                    self.app.kill()
                except Exception:
                    logger.exception("Falha também no kill()")
            self.app = None

        if self.arquivo is not None:
            try:
                self.arquivo.unlink(missing_ok=True)
            except OSError:
                logger.warning("Não foi possível remover %s", self.arquivo)
            self.arquivo = None

    def processar(self, dados):
        with _TRAVA:
            if pythoncom is not None:
                pythoncom.CoInitialize()
            try:
                self.criar_copia()
                try:
                    self.abrir()
                    self.preencher(dados)
                    self.recalcular()
                    return self.ler()
                finally:
                    self.fechar()
            finally:
                if pythoncom is not None:
                    pythoncom.CoUninitialize()


limpar_temporarios()