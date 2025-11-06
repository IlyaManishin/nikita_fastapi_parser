import os
from typing import List

from googleapiclient.discovery import build
from google.oauth2 import service_account

TOKEN_SHEET_NAME = "Токен"
TOKEN_RANGE = "A1:A10"

this_dir = os.path.dirname(os.path.realpath(__file__))
spreadsheets_id = None
with open(f"{this_dir}/data/main_spreadsheets_id.txt") as file:
    spreadsheets_id = file.read().strip("\n ")


creds_path = f"{this_dir}/data/credentials.json"

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

KEYFILE = 'google_api_keyfile.json'
credentials = service_account.Credentials.from_service_account_file(
    creds_path, scopes=scope)
service = build('sheets', 'v4', credentials=credentials)


def raw_read_table(spreadsheets_id, name, table_range):
    tryings = 3
    values = None
    for i in range(tryings):
        try:
            values = service.spreadsheets().values().get(spreadsheetId=spreadsheets_id,
                                                         range=f"{name}!{table_range}").execute()["values"]
            break
        except Exception as err:
            continue
    if not values:
        return []
    return values


def get_wb_tokens() -> List[str]:
    data = raw_read_table(spreadsheets_id, TOKEN_SHEET_NAME, TOKEN_RANGE)
    if not data:
        return None
    tokens = []
    for row in data:
        try:
            if row[0]:
                tokens.append(row[0])
        except:
            continue
    return tokens
