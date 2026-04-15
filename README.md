# LAY_SCORE Bot - Automated Sports Betting Monitor

Monitoramento automático de alertas de Lay em canais do Telegram, com integração Google Sheets e dashboard em tempo real.

## 🚀 Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│             LAY_SCORE Bot System                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Windows Local Machine:                                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ INICIAR_BOT.bat                                      │  │
│  │ └─> Loads .env file (credentials)                   │  │
│  │     └─> layscore_local.py (24/7 bot)               │  │
│  │         ├─> Telegram API (coletar alerts)           │  │
│  │         └─> Google Sheets (atualizar dados)         │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Google Sheets (LAY_SCORE_ALERTAS)                  │  │
│  │  Data Storage: Estratégia, Times, Resultados, Gols  │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
└─────────────────────────────────────────────────────────────┘
          │
          │ (Netlify Auto-Deploy)
          ▼
┌─────────────────────────────────────────────────────────────┐
│  GitHub Repository (layscore-bot)                          │
│  ├─ layscore_local.py (bot code)                           │
│  ├─ index.html (dashboard code)                            │
│  ├─ .env.example (config template)                         │
│  └─ Code versioning + CI/CD trigger                        │
└─────────────────────────────────────────────────────────────┘
          │
          │ (GitHub webhook → Netlify)
          ▼
┌─────────────────────────────────────────────────────────────┐
│  Netlify (Public Dashboard)                                │
│  URL: https://meek-speculoos-d061e6.netlify.app/           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ index.html + JavaScript                             │  │
│  │ ├─ Fetches data from Google Sheets (public access)  │  │
│  │ ├─ Real-time calculations (placares, momentos)      │  │
│  │ └─ Interactive filters & reports                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Public URL for viewing results                            │
└─────────────────────────────────────────────────────────────┘
```

## 📋 Pré-requisitos

- Python 3.8+
- Git
- Conta Telegram (para API)
- Google Cloud Project (Service Account)
- Conta GitHub
- Netlify (free tier OK)

## 🔧 Instalação & Configuração

### 1. **Configurar Variáveis de Ambiente**

```bash
# No diretório do projeto, copie o template:
cp .env.example .env

# Edite .env com seus valores:
# - TELEGRAM_API_ID
# - TELEGRAM_API_HASH
# - TELEGRAM_SESSION
# - GOOGLE_CREDS (JSON string)
```

⚠️ **IMPORTANTE**: O arquivo `.env` NÃO é commitado (está em .gitignore). Isso protege suas credenciais.

### 2. **Iniciar o Bot Localmente**

```bash
# Double-click em:
INICIAR_BOT.bat

# Ou via terminal:
python layscore_local.py
```

O bot executará indefinidamente:
- A cada 5 minutos: coleta mensagens do Telegram
- A cada 3 horas: atualiza placares e resultados

### 3. **Ver o Dashboard**

Acesse: `https://meek-speculoos-d061e6.netlify.app/`

O dashboard lê os dados do Google Sheets em tempo real (via API pública).

## 🔑 Credenciais & Segurança

### Onde as credenciais estão armazenadas:

| Credencial | Onde Armazenar | Onde NÃO armazenar |
|------------|---------------|--------------------|
| TELEGRAM_API_HASH | `.env` (local) | ❌ GitHub |
| TELEGRAM_SESSION | `.env` (local) | ❌ GitHub |
| GOOGLE_CREDS | `.env` (local) | ❌ GitHub |

### Por que isso funciona:

1. **Código no GitHub** é publicamente visível
2. **Credenciais locais** em `.env` ficam APENAS na sua máquina
3. **GitHub .gitignore** bloqueia upload de `.env`
4. **Python** carrega credenciais via `os.getenv()` em tempo de execução

### Fluxo de Autenticação:

```
INICIAR_BOT.bat lê .env
    ↓
layscore_local.py recebe variáveis de ambiente
    ↓
Conecta ao Telegram API (usa TELEGRAM_API_HASH, TELEGRAM_SESSION)
    ↓
Conecta ao Google Sheets (usa GOOGLE_CREDS JSON)
    ↓
Coleta e atualiza dados
```

## 📁 Arquivos Importantes

```
Bots Cloude/
├── .env                          ⚠️ NUNCA commitar (credenciais)
├── .env.example                  ✅ Template para copiar
├── .gitignore                    ✅ Protege .env do git
├── layscore_local.py            ✅ Bot principal (24/7)
├── preencher_gols.py            ✅ Script auxiliar (opcional)
├── index.html                    ✅ Dashboard (Netlify)
├── INICIAR_BOT.bat              ✅ Launcher para bot
├── SUBIR_GITHUB.bat             ✅ Setup inicial Git
└── README.md                     ✅ Documentação
```

## 🔄 Fluxo de Atualização de Código

### Para atualizar o dashboard (index.html):

```bash
# 1. Faça alterações no index.html
# 2. Commit localmente:
git add index.html
git commit -m "Atualizar dashboard com novo filtro"

# 3. Push para GitHub:
git push origin main

# 4. Netlify fará deploy automaticamente!
# (webhook automático)
```

### Para atualizar a lógica do bot (layscore_local.py):

```bash
# ⚠️ NÃO contém credenciais → seguro commitar
git add layscore_local.py
git commit -m "Melhorar coleta de gols"
git push origin main

# Depois reinicie o bot localmente:
# (feche e abra INICIAR_BOT.bat novamente)
```

## ⚙️ Variáveis de Ambiente

### TELEGRAM_API_ID
- Tipo: Integer
- Fonte: https://my.telegram.org/apps
- Exemplo: `29422958`

### TELEGRAM_API_HASH
- Tipo: String (32 caracteres hex)
- Fonte: https://my.telegram.org/apps
- Exemplo: `f5c8a457728681f29b60e99eecddcc06`

### TELEGRAM_SESSION
- Tipo: String (token base64 longo)
- Gerado por: `gerar_session.py` (Telethon StringSession)
- Contém: Autenticação persistente da sessão Telegram

### GOOGLE_CREDS
- Tipo: JSON string (válido e escapado)
- Fonte: Google Cloud Console → Service Account → Download JSON
- **Formato obrigatório**: Uma única linha, tudo em JSON
- Exemplo: `{"type": "service_account", "project_id": "...", ...}`

## 🐛 Troubleshooting

### Bot não inicia

```
ERRO: Python não encontrado
→ Instale Python de https://python.org

ERRO: TELEGRAM_SESSION not set
→ Verifique se .env existe e está preenchido

ERRO: GOOGLE_CREDS JSON invalid
→ Copie o JSON da Service Account direto do Google Cloud
  (sem quebras de linha)
```

### Dashboard não atualiza

```
→ Verifique se Google Sheets é público (qualquer um pode ver)
→ Verifique permissões da Service Account no Sheets
→ Abra console do navegador (F12) para ver erros
```

### Credenciais vazadas por acidente?

```
1. Resete sua Service Account no Google Cloud
2. Regenere o TELEGRAM_SESSION rodando gerar_session.py
3. Atualize .env com novas credenciais
4. Restart o bot
```

## 📊 Estrutura de Dados

### Google Sheets - Colunas (LAY_SCORE_ALERTAS)

| Col | Nome | Tipo | Descrição |
|-----|------|------|-----------|
| A | data | texto | DD/MM/YYYY |
| B | mes | texto | MM |
| C | estrategia | texto | "Lay 1x0" |
| D | casa | texto | "Time A" |
| E | visitante | texto | "Time B" |
| F | liga | texto | "Liga Name" |
| G | resultado_final | texto | "1x1" |
| H | resultado_entrada | texto | "GREEN\|RED" |
| I | odd | número | 2.45 |
| J | gols | texto | "23'C,45'V,89'V" |

## 🔗 URLs & Links

- **GitHub**: https://github.com/gustavobaumann13-maker/layscore-bot
- **Dashboard**: https://meek-speculoos-d061e6.netlify.app/
- **Google Sheets**: LAY_SCORE_ALERTAS (deve estar público)
- **Telegram Channel**: BOT de Lay CS - Baumann

## 📝 Licença

Projeto pessoal para automação de análise de apostas.

---

**Última atualização**: Abril 2026  
**Status**: ✅ Produção (Seguro - sem credenciais no GitHub)
