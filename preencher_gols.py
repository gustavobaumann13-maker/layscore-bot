import asyncio, re, json, time, logging, os
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Load credentials from environment variables (see .env file)
API_ID       = int(os.getenv("TELEGRAM_API_ID", "29422958"))
API_HASH     = os.getenv("TELEGRAM_API_HASH")
SESSION_STR  = os.getenv("TELEGRAM_SESSION")
GOOGLE_CREDS = os.getenv("GOOGLE_CREDS")

if not API_HASH or not SESSION_STR or not GOOGLE_CREDS:
    raise ValueError("Missing required environment variables. Set TELEGRAM_API_HASH, TELEGRAM_SESSION, and GOOGLE_CREDS")

SPREADSHEET  = "LAY_SCORE_ALERTAS"
CANAL_NOME   = "BOT de Lay CS - Baumann"
ANO_MINIMO   = 2026

COLUNAS = ["data","mes","estrategia","casa","visitante","liga",
           "resultado_final","resultado_entrada","odd","gols"]
IDX = {c: i for i, c in enumerate(COLUNAS)}
COL_GOLS_LETRA = "J"  # coluna J = índice 9

MESES_PT = {"01":"Jan","02":"Fev","03":"Mar","04":"Abr","05":"Mai","06":"Jun",
             "07":"Jul","08":"Ago","09":"Set","10":"Out","11":"Nov","12":"Dez"}

def limpar(t):
    return (t or "").replace("*","").replace("_","").strip()

def limpar_time(n):
    return re.sub(r'\s*\(\d+[°º]?\)', '', n or "").strip()

def conectar_planilha():
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_CREDS)

    # FIX: Decode escape sequences in private_key (\\n -> actual newline)
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].encode('utf-8').decode('unicode_escape')

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds).open(SPREADSHEET)

def detectar_jogo_finalizado(texto):
    """Detecta se há ⚽ ✖️ ou equivalente no texto (jogo finalizou sem mais gols)"""
    if re.search(r'⚽\s*[❌✖️×x]', texto):
        return True
    return False

def extrair_placar_do_alerta(texto):
    """Extrai o placar que estava no alerta (para jogos finalizados com ⚽ ✖️)"""
    m = re.search(r'Placar[:\s]+(\d+)[xX](\d+)', texto)
    if m:
        return f"{m.group(1)}x{m.group(2)}"
    for linha in texto.split('\n'):
        if 'Resultado:' in linha:
            m = re.search(r'(\d+)[xX](\d+)', linha)
            if m:
                return f"{m.group(1)}x{m.group(2)}"
    return None

def extrair_gols(texto, casa, visitante):
    """Extrai gols da mensagem Telegram. Retorna string '45\'C,58\'V' ou ''."""
    casa_l  = limpar_time(casa).lower()
    visit_l = limpar_time(visitante).lower()
    gols = []
    for linha in texto.split("\n"):
        if "⚽" not in linha:
            continue
        m = re.search(r'(\d+)[\'′]', linha)
        if not m:
            continue
        minuto = m.group(1)
        resto  = linha[m.end():].strip().strip("()").lower()
        resto  = re.sub(r'[⚽\s]+', ' ', resto).strip()
        if casa_l[:5] and (resto[:5] in casa_l or casa_l[:5] in resto):
            lado = "C"
        elif visit_l[:5] and (resto[:5] in visit_l or visit_l[:5] in resto):
            lado = "V"
        else:
            lado = "?"
        gols.append(f"{minuto}'{lado}")
    return ",".join(gols)

async def main():
    async with TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH) as tg:
        log.info("Conectado ao Telegram.")

        # ── PASSO 1: Ler TODAS as mensagens e montar mapa chave→gols ──────────
        log.info("Lendo mensagens do Telegram (até 5000)...")
        canal = None
        async for dialog in tg.iter_dialogs():
            if CANAL_NOME in dialog.name:
                canal = dialog.entity
                break
        if not canal:
            log.error("Canal não encontrado!")
            return

        mapa_gols = {}   # chave → gols_str
        total_msg = 0

        async for msg in tg.iter_messages(canal, limit=5000):
            if not msg.text or msg.date.year < ANO_MINIMO:
                continue
            texto = msg.text

            m_est = re.search(r'Lay\s+\d+[xX]\d+', texto)
            if not m_est:
                m_par = re.search(r'\(Lay\s+\d+[xX]\d+\)', texto)
                if m_par:
                    m_est = re.search(r'Lay\s+\d+[xX]\d+', m_par.group(0))
            if not m_est:
                continue

            estrategia = m_est.group(0)
            jogo_m = re.search(r'Jogo:\s*(.*)', texto)
            jogo   = limpar(jogo_m.group(1)) if jogo_m else ""
            casa = visitante = ""
            if " x " in jogo:
                p = jogo.split(" x ", 1)
                casa      = limpar_time(p[0].strip())
                visitante = limpar_time(p[1].strip())
            if not casa or not visitante:
                continue

            data_str = msg.date.strftime("%d/%m/%Y")
            chave    = f"{estrategia}|{casa}|{visitante}|{data_str}"
            gols_str = extrair_gols(texto, casa, visitante)

            # Guarda mesmo sem gols (para saber que a mensagem existe)
            if chave not in mapa_gols or (not mapa_gols[chave] and gols_str):
                mapa_gols[chave] = gols_str
            total_msg += 1

        com_gols = sum(1 for v in mapa_gols.values() if v)
        log.info(f"{total_msg} msgs lidas | {len(mapa_gols)} entradas únicas | {com_gols} com gols")

        # ── PASSO 2: Percorrer planilha e atualizar coluna J ──────────────────
        log.info("Conectando na planilha...")
        planilha = conectar_planilha()
        total_atualizados = 0

        for sheet in planilha.worksheets():
            if "/" not in sheet.title:
                continue
            try:
                ano = int(sheet.title.split("/")[1])
            except:
                continue
            if ano < ANO_MINIMO:
                continue

            todas = sheet.get_all_values()
            dados = todas[1:] if len(todas) > 1 else []
            if not dados:
                log.info(f"[{sheet.title}] vazia, pulando.")
                continue

            batch = []
            sem_gol = 0
            for i, linha in enumerate(dados):
                def get(col):
                    ix = IDX.get(col, -1)
                    return linha[ix] if 0 <= ix < len(linha) else ""

                # Só atualiza linhas onde gols está vazio
                if get("gols").strip():
                    continue
                sem_gol += 1

                chave = f"{get('estrategia')}|{get('casa')}|{get('visitante')}|{get('data')}"
                gols  = mapa_gols.get(chave, "")
                if not gols:
                    continue

                row_num = i + 2  # +1 cabeçalho +1 base-1
                batch.append({
                    "range":  f"{sheet.title}!{COL_GOLS_LETRA}{row_num}",
                    "values": [[gols]]
                })

            log.info(f"[{sheet.title}] {len(dados)} linhas | {sem_gol} sem gol | {len(batch)} para atualizar")

            if batch:
                # Expandir para 10 colunas se necessário (Jan/Fev/2026 foram criadas com 9)
                if sheet.col_count < 10:
                    sheet.resize(cols=10)
                    if not sheet.cell(1, 10).value:
                        sheet.update_cell(1, 10, "gols")
                    time.sleep(0.5)

                # Envia em lotes de 500 para não estourar limite da API
                for i in range(0, len(batch), 500):
                    lote = batch[i:i+500]
                    sheet.spreadsheet.values_batch_update({
                        "valueInputOption": "RAW",
                        "data": lote
                    })
                    log.info(f"  → {len(lote)} gravados")
                    time.sleep(0.5)
                total_atualizados += len(batch)

            time.sleep(1)

        log.info(f"\n✅ CONCLUÍDO — {total_atualizados} gols gravados na planilha.")

if __name__ == "__main__":
    asyncio.run(main())
