import asyncio
import re
import requests
import pandas as pd
from telethon import TelegramClient
from telethon.sessions import StringSession
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Credenciais ────────────────────────────────────────────────────────────────
API_ID          = int(os.environ["TELEGRAM_API_ID"])
API_HASH        = os.environ["TELEGRAM_API_HASH"]
SESSION_STR     = os.environ["TELEGRAM_SESSION_STRING"]
GOOGLE_CREDS    = os.environ["GOOGLE_CREDENTIALS_JSON"]
SPORTMONKS_KEY  = os.environ.get("SPORTMONKS_API_KEY", "sE4bwh57jhrMnm9sPMg4kvAob9fwGIce7CPRgtFpCgxyAur3KPPNTrCslBAc")
SPREADSHEET     = os.environ.get("SPREADSHEET_NAME", "LAY_SCORE_ALERTAS")
CANAL_NOME      = os.environ.get("TELEGRAM_CANAL",   "BOT de Lay CS - Baumann")
INTERVALO_SEG   = int(os.environ.get("INTERVALO_SEG",   "300"))
INTERVALO_PLAC  = int(os.environ.get("INTERVALO_PLACAR", "10800"))

ANO_MINIMO      = 2026   # só processa jogos de 2026 em diante

COLUNAS = ["data", "mes", "estrategia", "casa", "visitante", "liga",
           "resultado_final", "resultado_entrada", "odd"]

MESES_PT = {
    "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
    "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
    "09": "Set", "10": "Out", "11": "Nov", "12": "Dez"
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def limpar(texto):
    if not texto:
        return ""
    return texto.replace("*", "").replace("_", "").strip()

def limpar_time(nome):
    if not nome:
        return ""
    return re.sub(r'\s*\(\d+[°º]?\)', '', nome).strip()

def nome_aba(mes_str, ano_str):
    return f"{MESES_PT.get(mes_str, mes_str)}/{ano_str}"

def extrair_placar_estrategia(estrategia):
    m = re.search(r'Lay\s+(\d+)[xX](\d+)', estrategia or "")
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None

def calcular_resultado(estrategia, resultado_final):
    if not resultado_final or resultado_final.strip() in ("", "-"):
        return ""
    gols_esp_casa, gols_esp_vis = extrair_placar_estrategia(estrategia)
    if gols_esp_casa is None:
        return ""
    m = re.match(r'(\d+)[xX\-:](\d+)', resultado_final.strip())
    if not m:
        return ""
    if int(m.group(1)) == gols_esp_casa and int(m.group(2)) == gols_esp_vis:
        return "RED"
    return "GREEN"

# ── Sportmonks: busca todos os jogos de uma data (com paginação) ───────────────
_cache_jogos = {}  # cache global: data_api → lista de fixtures

def buscar_jogos_do_dia(data_api):
    if data_api in _cache_jogos:
        return _cache_jogos[data_api]

    todos = []
    page  = 1
    while True:
        try:
            resp = requests.get(
                f"https://api.sportmonks.com/v3/football/fixtures/date/{data_api}",
                params={
                    "api_token": SPORTMONKS_KEY,
                    "include":   "participants;scores",
                    "per_page":  100,
                    "page":      page,
                },
                timeout=15
            )
            data = resp.json()
            jogos = data.get("data", [])
            todos.extend(jogos)

            if not data.get("pagination", {}).get("has_more", False):
                break
            page += 1

        except Exception as e:
            log.warning(f"Erro ao buscar página {page} da data {data_api}: {e}")
            break

    log.info(f"[{data_api}] {len(todos)} jogos carregados da Sportmonks.")
    _cache_jogos[data_api] = todos
    return todos

def buscar_placar(casa, visitante, data_str):
    try:
        dt       = datetime.strptime(data_str, "%d/%m/%Y")
        data_api = dt.strftime("%Y-%m-%d")
        casa_l   = limpar_time(casa).lower()
        visit_l  = limpar_time(visitante).lower()

        for fixture in buscar_jogos_do_dia(data_api):
            home_name = away_name = ""
            for p in fixture.get("participants", []):
                loc = p.get("meta", {}).get("location", "")
                if loc == "home":
                    home_name = p["name"].lower()
                elif loc == "away":
                    away_name = p["name"].lower()

            if not (casa_l[:5] in home_name or home_name[:5] in casa_l):
                continue
            if not (visit_l[:5] in away_name or away_name[:5] in visit_l):
                continue

            home_goals = away_goals = None
            for s in fixture.get("scores", []):
                if s.get("description") == "CURRENT":
                    if s["score"]["participant"] == "home":
                        home_goals = s["score"]["goals"]
                    elif s["score"]["participant"] == "away":
                        away_goals = s["score"]["goals"]

            if home_goals is not None and away_goals is not None:
                log.info(f"✓ {casa} {home_goals}x{away_goals} {visitante}")
                return f"{home_goals}x{away_goals}"

        return "-"

    except Exception as e:
        log.warning(f"Erro placar {casa} x {visitante}: {e}")
        return "-"

# ── Coleta mensagens do Telegram ───────────────────────────────────────────────
async def coletar_dados(telegram_client):
    canal = None
    async for dialog in telegram_client.iter_dialogs():
        if CANAL_NOME in dialog.name:
            canal = dialog.entity
            break

    if not canal:
        log.warning(f"Canal '{CANAL_NOME}' não encontrado.")
        return None

    dados = []
    vistos = set()

    async for message in telegram_client.iter_messages(canal, limit=1000):
        if not message.text:
            continue

        # Ignora mensagens de anos anteriores ao ANO_MINIMO
        if message.date.year < ANO_MINIMO:
            continue

        texto = message.text

        m_est = re.search(r'Lay\s+\d+[xX]\d+', texto)
        if not m_est:
            m_par = re.search(r'\(Lay\s+\d+[xX]\d+\)', texto)
            if m_par:
                m_est = re.search(r'Lay\s+\d+[xX]\d+', m_par.group(0))
        estrategia_val = m_est.group(0) if m_est else ""

        if not estrategia_val:
            continue

        jogo = re.search(r'Jogo:\s*(.*)', texto)
        liga = re.search(r'Competi[çc][ãa]o:\s*(.*)', texto)

        jogo_limpo = limpar(jogo.group(1)) if jogo else ""
        casa = visitante = ""
        if " x " in jogo_limpo:
            partes    = jogo_limpo.split(" x ", 1)
            casa      = limpar_time(partes[0].strip())
            visitante = limpar_time(partes[1].strip())

        if not casa or not visitante:
            continue

        data_str = message.date.strftime("%d/%m/%Y")
        chave = f"{estrategia_val}|{casa}|{visitante}|{data_str}"
        if chave in vistos:
            continue
        vistos.add(chave)

        ano = message.date.strftime("%Y")
        mes = message.date.strftime("%m")

        dados.append({
            "data":              data_str,
            "mes":               mes,
            "estrategia":        estrategia_val,
            "casa":              casa,
            "visitante":         visitante,
            "liga":              limpar(liga.group(1)) if liga else "",
            "resultado_final":   "",
            "resultado_entrada": "",
            "odd":               "",
            "_dt_sort":          message.date,
            "_msg_id":           message.id,
            "_chave":            chave,
            "_aba":              nome_aba(mes, ano),
        })

    log.info(f"{len(dados)} mensagens válidas coletadas (só {ANO_MINIMO}+).")
    df = pd.DataFrame(dados)
    df = df.sort_values(["_dt_sort", "_msg_id"], ascending=[True, True]).reset_index(drop=True)
    df = df.drop(columns=["_dt_sort", "_msg_id"])
    return df

# ── Conecta ao Google Sheets ───────────────────────────────────────────────────
def conectar_planilha():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS), scope)
    return gspread.authorize(creds).open(SPREADSHEET)

def obter_ou_criar_aba(planilha, nome):
    try:
        return planilha.worksheet(nome)
    except gspread.exceptions.WorksheetNotFound:
        sheet = planilha.add_worksheet(title=nome, rows=2000, cols=len(COLUNAS))
        sheet.append_row(COLUNAS)
        log.info(f"Aba '{nome}' criada.")
        return sheet

# ── Aplica cores em lote numa aba ──────────────────────────────────────────────
def aplicar_cores_lote(sheet, updates):
    """updates: lista de (row_num, valor) onde valor é GREEN ou RED"""
    if not updates:
        return
    col_re = COLUNAS.index("resultado_entrada")  # 0-indexed
    requests_body = []
    for row_num, valor in updates:
        if valor == "GREEN":
            bg = {"red": 0.2,  "green": 0.78, "blue": 0.35}
            fg = {"red": 1.0,  "green": 1.0,  "blue": 1.0}
        elif valor == "RED":
            bg = {"red": 0.9,  "green": 0.2,  "blue": 0.2}
            fg = {"red": 1.0,  "green": 1.0,  "blue": 1.0}
        else:
            continue
        requests_body.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet.id,
                    "startRowIndex": row_num - 1,
                    "endRowIndex":   row_num,
                    "startColumnIndex": col_re,
                    "endColumnIndex":   col_re + 1,
                },
                "cell": {"userEnteredFormat": {
                    "backgroundColor": bg,
                    "textFormat": {"foregroundColor": fg, "bold": True},
                    "horizontalAlignment": "CENTER",
                }},
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
            }
        })
    if requests_body:
        sheet.spreadsheet.batch_update({"requests": requests_body})

# ── Atualiza abas mensais ──────────────────────────────────────────────────────
def atualizar_sheets(df):
    planilha = conectar_planilha()

    for aba_nome, grupo in df.groupby("_aba"):
        sheet = obter_ou_criar_aba(planilha, aba_nome)
        dados_existentes = sheet.get_all_records(expected_headers=COLUNAS)

        chaves_existentes = {
            f"{l.get('estrategia')}|{l.get('casa')}|{l.get('visitante')}|{l.get('data')}"
            for l in dados_existentes
        }

        df_novas = grupo[~grupo["_chave"].isin(chaves_existentes)].copy()

        if df_novas.empty:
            log.info(f"[{aba_nome}] Nenhuma nova entrada.")
            continue

        if dados_existentes:
            df_exist = pd.DataFrame(dados_existentes)
            for col in COLUNAS:
                if col not in df_exist.columns:
                    df_exist[col] = ""
            df_exist["_chave"] = (df_exist["estrategia"].astype(str) + "|" +
                                  df_exist["casa"].astype(str) + "|" +
                                  df_exist["visitante"].astype(str) + "|" +
                                  df_exist["data"].astype(str))
            df_completo = pd.concat([df_exist[COLUNAS + ["_chave"]], df_novas[COLUNAS + ["_chave"]]], ignore_index=True)
        else:
            df_completo = df_novas[COLUNAS + ["_chave"]].copy()

        df_completo["_sort"] = pd.to_datetime(df_completo["data"], format="%d/%m/%Y", errors="coerce")
        df_completo = df_completo.sort_values("_sort").reset_index(drop=True)
        df_completo = df_completo.drop(columns=["_sort", "_chave"])

        sheet.clear()
        sheet.append_row(COLUNAS)
        sheet.append_rows(df_completo.fillna("").values.tolist())

        # Aplica cores em lote
        updates = [(i + 2, row["resultado_entrada"])
                   for i, row in df_completo.iterrows()
                   if row["resultado_entrada"] in ("GREEN", "RED")]
        aplicar_cores_lote(sheet, updates)

        log.info(f"[{aba_nome}] {len(df_novas)} novas entradas. Total: {len(df_completo)}.")

# ── Atualiza placares (batch — sem update_cell) ────────────────────────────────
def atualizar_placares():
    log.info("Buscando placares via Sportmonks (só 2026+)...")
    planilha = conectar_planilha()
    hoje     = datetime.now().date()
    col_rf   = COLUNAS.index("resultado_final") + 1   # 1-indexed para gspread
    col_re   = COLUNAS.index("resultado_entrada") + 1
    total    = 0

    for sheet in planilha.worksheets():
        # Só abas mensais de 2026+  (ex: "Mar/2026")
        if "/" not in sheet.title:
            continue
        try:
            ano_aba = int(sheet.title.split("/")[1])
        except:
            continue
        if ano_aba < ANO_MINIMO:
            log.info(f"[{sheet.title}] Pulando (ano < {ANO_MINIMO}).")
            continue

        dados = sheet.get_all_records(expected_headers=COLUNAS)
        if not dados:
            continue

        # Acumula updates de valor e de cor para aplicar em lote
        batch_valores = []   # [{"range": "G5", "values": [["2x1"]]}, ...]
        updates_cores = []   # [(row_num, valor)]

        for i, linha in enumerate(dados):
            if str(linha.get("resultado_final", "")).strip() not in ("", "-"):
                continue

            data_str   = linha.get("data", "")
            casa       = linha.get("casa", "")
            visitante  = linha.get("visitante", "")
            estrategia = linha.get("estrategia", "")

            if not data_str or not casa:
                continue
            try:
                dt = datetime.strptime(data_str, "%d/%m/%Y")
                if dt.date() > hoje or dt.year < ANO_MINIMO:
                    continue
            except:
                continue

            placar = buscar_placar(casa, visitante, data_str)
            if placar == "-":
                continue

            resultado = calcular_resultado(estrategia, placar)
            row_num   = i + 2  # +2 porque linha 1 é cabeçalho

            # Notação A1 para batch_update de valores
            batch_valores.append({
                "range":  f"{sheet.title}!G{row_num}:H{row_num}",
                "values": [[placar, resultado]]
            })
            updates_cores.append((row_num, resultado))
            total += 1

        # Grava todos os valores de uma vez
        if batch_valores:
            sheet.spreadsheet.values_batch_update({
                "valueInputOption": "RAW",
                "data": batch_valores
            })
            # Aplica cores em lote
            aplicar_cores_lote(sheet, updates_cores)
            log.info(f"[{sheet.title}] {len(batch_valores)} placares atualizados em lote.")

        # Pequena pausa para não estourar cota entre abas
        time.sleep(1)

    log.info(f"Total de placares atualizados: {total}.")

# ── Loop principal ─────────────────────────────────────────────────────────────
async def main():
    async with TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH) as tg:
        log.info("Conectado ao Telegram.")
        ultimo_placar = datetime.now() - timedelta(seconds=INTERVALO_PLAC)

        while True:
            try:
                log.info("Coletando mensagens...")
                df = await coletar_dados(tg)
                if df is not None and not df.empty:
                    atualizar_sheets(df)

                if (datetime.now() - ultimo_placar).total_seconds() >= INTERVALO_PLAC:
                    _cache_jogos.clear()  # limpa cache antes de cada rodada
                    atualizar_placares()
                    ultimo_placar = datetime.now()

                log.info(f"Ciclo concluído. Próximo em {INTERVALO_SEG // 60} min.\n")

            except Exception as e:
                log.error(f"Erro: {e}", exc_info=True)

            await asyncio.sleep(INTERVALO_SEG)

if __name__ == "__main__":
    asyncio.run(main())
