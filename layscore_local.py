import asyncio
import re
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

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Credenciais (via variáveis de ambiente) ────────────────────────────────────
# Load credentials from environment variables for security
# See .env.example for required variables
API_ID          = int(os.getenv("TELEGRAM_API_ID", "29422958"))
API_HASH        = os.getenv("TELEGRAM_API_HASH")
SESSION_STR     = os.getenv("TELEGRAM_SESSION")
GOOGLE_CREDS    = os.getenv("GOOGLE_CREDS")

# Validate that required credentials are set
if not API_HASH:
    raise ValueError("TELEGRAM_API_HASH not set. Please set environment variables from .env file.")
if not SESSION_STR:
    raise ValueError("TELEGRAM_SESSION not set. Please set environment variables from .env file.")
if not GOOGLE_CREDS:
    raise ValueError("GOOGLE_CREDS not set. Please set environment variables from .env file.")

SPREADSHEET     = "LAY_SCORE_ALERTAS"
CANAL_NOME      = "BOT de Lay CS - Baumann"
INTERVALO_SEG   = 300
INTERVALO_PLAC  = 10800

ANO_MINIMO      = 2026   # só processa jogos de 2026 em diante

COLUNAS = ["data", "mes", "estrategia", "casa", "visitante", "liga",
           "resultado_final", "resultado_entrada", "odd", "gols"]

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

def calcular_placar_dos_gols(gols_str):
    """Calcula placar final a partir da string de gols do Telegram. Ex: '23'C,45'V' → '1x1'"""
    if not gols_str:
        return None
    partes = [g for g in gols_str.split(",") if g.strip() and "?" not in g]
    if not partes:
        return None
    c = sum(1 for g in partes if "'C" in g)
    v = sum(1 for g in partes if "'V" in g)
    return f"{c}x{v}"

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

        # Extrair gols da mensagem Telegram
        # Formato: "⚽ 45' (AFC Bournemouth U21)" ou "⚽ 45' AFC Bournemouth"
        gols_msg  = []
        casa_l    = limpar_time(casa).lower()
        visit_l   = limpar_time(visitante).lower()
        for linha in texto.split("\n"):
            if "⚽" not in linha:
                continue
            m_min = re.search(r'(\d+)[\'′]', linha)
            if not m_min:
                continue
            minuto   = m_min.group(1)
            # Pegar nome do time na linha (após o minuto)
            resto    = linha[m_min.end():].strip().strip("()").strip()
            resto_l  = resto.lower()
            if casa_l[:5] and (resto_l[:5] in casa_l or casa_l[:5] in resto_l):
                lado = "C"
            elif visit_l[:5] and (resto_l[:5] in visit_l or visit_l[:5] in resto_l):
                lado = "V"
            else:
                lado = "?"
            gols_msg.append(f"{minuto}'{lado}")
        gols_str = ",".join(gols_msg)

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
            "gols":              gols_str,
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
        todas_linhas = sheet.get_all_values()
        dados_existentes = todas_linhas[1:] if len(todas_linhas) > 1 else []
        IDX = {c: i for i, c in enumerate(COLUNAS)}

        chaves_existentes = {
            f"{l[IDX['estrategia']]}|{l[IDX['casa']]}|{l[IDX['visitante']]}|{l[IDX['data']]}"
            for l in dados_existentes if len(l) > IDX['data']
        }

        df_novas = grupo[~grupo["_chave"].isin(chaves_existentes)].copy()

        if df_novas.empty:
            log.info(f"[{aba_nome}] Nenhuma nova entrada.")
            continue

        if dados_existentes:
            ncols = len(dados_existentes[0]) if dados_existentes else len(COLUNAS)
            df_exist = pd.DataFrame(dados_existentes, columns=COLUNAS[:ncols])
            for col in COLUNAS:
                if col not in df_exist.columns:
                    df_exist[col] = ""
            df_exist["_chave"] = (df_exist["estrategia"].astype(str) + "|" +
                                  df_exist["casa"].astype(str) + "|" +
                                  df_exist["visitante"].astype(str) + "|" +
                                  df_exist["data"].astype(str))
            # Atualizar gols vazios nas entradas existentes com dados novos do Telegram
            gols_novos = grupo[["_chave", "gols"]].set_index("_chave")["gols"]
            mask_sem_gol = (df_exist["gols"].fillna("") == "") & df_exist["_chave"].isin(gols_novos.index)
            if mask_sem_gol.any():
                df_exist.loc[mask_sem_gol, "gols"] = df_exist.loc[mask_sem_gol, "_chave"].map(gols_novos)
                log.info(f"[{aba_nome}] {mask_sem_gol.sum()} entradas com gols atualizados.")
            df_completo = pd.concat([df_exist[COLUNAS + ["_chave"]], df_novas[COLUNAS + ["_chave"]]], ignore_index=True)
        else:
            df_completo = df_novas[COLUNAS + ["_chave"]].copy()

        # Deduplicar pelo campo _chave (garante sem duplicatas mesmo se planilha já tinha)
        df_completo = df_completo.drop_duplicates(subset=["_chave"], keep="first")
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

# ── Atualiza placares calculando dos gols do Telegram ─────────────────────────
def atualizar_placares():
    log.info("Calculando placares dos gols do Telegram (2026+)...")
    planilha = conectar_planilha()
    hoje     = datetime.now().date()
    total    = 0

    for sheet in planilha.worksheets():
        if "/" not in sheet.title:
            continue
        try:
            ano_aba = int(sheet.title.split("/")[1])
        except:
            continue
        if ano_aba < ANO_MINIMO:
            continue

        todas = sheet.get_all_values()
        dados = todas[1:] if len(todas) > 1 else []
        if not dados:
            continue

        IDX2 = {c: i for i, c in enumerate(COLUNAS)}
        batch_valores = []
        updates_cores = []

        for i, linha in enumerate(dados):
            def get_col(col):
                idx = IDX2.get(col, -1)
                return linha[idx] if 0 <= idx < len(linha) else ""

            # Pula linhas que já têm placar
            if str(get_col("resultado_final")).strip() not in ("", "-"):
                continue

            data_str   = get_col("data")
            estrategia = get_col("estrategia")
            gols_str   = get_col("gols")

            if not data_str or not estrategia or not gols_str:
                continue
            try:
                dt = datetime.strptime(data_str, "%d/%m/%Y")
                if dt.date() > hoje or dt.year < ANO_MINIMO:
                    continue
            except:
                continue

            placar = calcular_placar_dos_gols(gols_str)
            if not placar:
                continue

            resultado = calcular_resultado(estrategia, placar)
            row_num   = i + 2

            batch_valores.append({
                "range":  f"{sheet.title}!G{row_num}:H{row_num}",
                "values": [[placar, resultado]]
            })
            updates_cores.append((row_num, resultado))
            total += 1
            log.info(f"  ✓ {get_col('casa')} x {get_col('visitante')} → {placar} ({resultado})")

        if batch_valores:
            if sheet.col_count < 10:
                sheet.resize(cols=10)
                time.sleep(0.5)
            sheet.spreadsheet.values_batch_update({
                "valueInputOption": "RAW",
                "data": batch_valores
            })
            aplicar_cores_lote(sheet, updates_cores)
            log.info(f"[{sheet.title}] {len(batch_valores)} placares gravados.")

        time.sleep(1)

    log.info(f"Total de placares atualizados: {total}.")


# ── Atualiza gols nas entradas existentes lendo mensagens do Telegram ──────────
async def atualizar_gols_telegram(telegram_client, planilha):
    """Percorre abas mensais, encontra linhas sem gols e preenche lendo o Telegram."""
    log.info("Atualizando gols das entradas existentes via Telegram...")

    # Indexar todas as mensagens do canal por chave
    canal = None
    async for dialog in telegram_client.iter_dialogs():
        if CANAL_NOME in dialog.name:
            canal = dialog.entity
            break
    if not canal:
        log.warning("Canal não encontrado para atualizar gols.")
        return

    # Construir mapa: chave → gols_str
    mapa_gols = {}
    async for message in telegram_client.iter_messages(canal, limit=5000):
        if not message.text or message.date.year < ANO_MINIMO:
            continue
        texto = message.text

        m_est = re.search(r'Lay\s+\d+[xX]\d+', texto)
        if not m_est:
            m_par = re.search(r'\(Lay\s+\d+[xX]\d+\)', texto)
            if m_par:
                m_est = re.search(r'Lay\s+\d+[xX]\d+', m_par.group(0))
        if not m_est:
            continue

        estrategia_val = m_est.group(0)
        jogo = re.search(r'Jogo:\s*(.*)', texto)
        jogo_limpo = limpar(jogo.group(1)) if jogo else ""
        casa = visitante = ""
        if " x " in jogo_limpo:
            partes = jogo_limpo.split(" x ", 1)
            casa      = limpar_time(partes[0].strip())
            visitante = limpar_time(partes[1].strip())
        if not casa or not visitante:
            continue

        data_str  = message.date.strftime("%d/%m/%Y")
        chave     = f"{estrategia_val}|{casa}|{visitante}|{data_str}"
        casa_l    = casa.lower()
        visit_l   = visitante.lower()

        gols_msg = []
        for linha in texto.split("\n"):
            if "⚽" not in linha:
                continue
            m_min = re.search(r'(\d+)[\'′]', linha)
            if not m_min:
                continue
            minuto  = m_min.group(1)
            resto_l = linha[m_min.end():].strip().strip("()").lower()
            if casa_l[:5] and (resto_l[:5] in casa_l or casa_l[:5] in resto_l):
                lado = "C"
            elif visit_l[:5] and (resto_l[:5] in visit_l or visit_l[:5] in resto_l):
                lado = "V"
            else:
                lado = "?"
            gols_msg.append(f"{minuto}\'{lado}")

        if gols_msg and chave not in mapa_gols:
            mapa_gols[chave] = ",".join(gols_msg)

    log.info(f"Mapa de gols: {len(mapa_gols)} entradas com gols encontradas.")

    # Percorrer planilha e atualizar linhas sem gols
    IDX = {c: i for i, c in enumerate(COLUNAS)}
    col_gols_letra = "J"  # coluna J = índice 9 = "gols"
    total = 0

    for sheet in planilha.worksheets():
        if "/" not in sheet.title:
            continue
        try:
            ano_aba = int(sheet.title.split("/")[1])
        except:
            continue
        if ano_aba < ANO_MINIMO:
            continue

        todas = sheet.get_all_values()
        dados = todas[1:] if len(todas) > 1 else []
        if not dados:
            continue

        batch = []
        for i, linha in enumerate(dados):
            def get(col):
                idx = IDX.get(col, -1)
                return linha[idx] if 0 <= idx < len(linha) else ""

            # Só atualiza se gols estiver vazio
            if get("gols").strip():
                continue

            chave = f"{get('estrategia')}|{get('casa')}|{get('visitante')}|{get('data')}"
            if chave in mapa_gols:
                row_num = i + 2
                batch.append({
                    "range":  f"{sheet.title}!{col_gols_letra}{row_num}",
                    "values": [[mapa_gols[chave]]]
                })
                total += 1

        if batch:
            # Expandir para 10 colunas se necessário (Jan/Fev/2026 foram criadas com 9)
            if sheet.col_count < 10:
                sheet.resize(cols=10)
                time.sleep(0.5)
            sheet.spreadsheet.values_batch_update({
                "valueInputOption": "RAW",
                "data": batch
            })
            log.info(f"[{sheet.title}] {len(batch)} gols atualizados.")
        time.sleep(1)

    log.info(f"Total de gols atualizados na planilha: {total}.")

# ── Loop principal ─────────────────────────────────────────────────────────────
async def main():
    async with TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH) as tg:
        log.info("Conectado ao Telegram.")
        ultimo_placar = datetime.now() - timedelta(seconds=INTERVALO_PLAC)

        # Atualiza gols retroativos uma vez ao iniciar
        planilha_init = conectar_planilha()
        await atualizar_gols_telegram(tg, planilha_init)

        while True:
            try:
                log.info("Coletando mensagens...")
                df = await coletar_dados(tg)
                if df is not None and not df.empty:
                    atualizar_sheets(df)

                if (datetime.now() - ultimo_placar).total_seconds() >= INTERVALO_PLAC:
                    atualizar_placares()
                    ultimo_placar = datetime.now()

                log.info(f"Ciclo concluído. Próximo em {INTERVALO_SEG // 60} min.\n")

            except Exception as e:
                log.error(f"Erro: {e}", exc_info=True)

            await asyncio.sleep(INTERVALO_SEG)

if __name__ == "__main__":
    asyncio.run(main())
