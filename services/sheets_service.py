import os
import json
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def _client():
    creds_json = json.loads(os.environ["GOOGLE_SHEETS_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    return gspread.authorize(creds)

def registrar_lead(dados):
    sh = _client().open_by_key(os.environ["GOOGLE_SHEET_ID"]).sheet1
    sh.append_row([
        dados.get("razao_social"),
        dados.get("cnpj"),
        dados.get("email"),
        dados.get("telefone"),
        dados.get("celular"),
        dados.get("cidade"),
        dados.get("estado"),
    ])