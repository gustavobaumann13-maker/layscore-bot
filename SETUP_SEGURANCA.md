# 🔐 Configuração de Segurança - LAY_SCORE Bot

## ✅ O Que Foi Feito

### 1. **Removidas Credenciais do Código-Fonte**

**Antes** ❌ (Inseguro):
```python
# layscore_local.py
GOOGLE_CREDS = '{"type": "service_account", "private_key": "-----BEGIN PRIVATE KEY-----\\n..."}'
SESSION_STR  = "1AZWarzQBux..." # Token do Telegram
```

**Depois** ✅ (Seguro):
```python
# layscore_local.py
GOOGLE_CREDS = os.getenv("GOOGLE_CREDS")  # Lê de variável de ambiente
SESSION_STR  = os.getenv("TELEGRAM_SESSION")
API_HASH     = os.getenv("TELEGRAM_API_HASH")
```

### 2. **Criados Arquivos de Segurança**

| Arquivo | Propósito | Git |
|---------|-----------|-----|
| `.env` | **Suas credenciais reais** (NÃO compartilhar) | ❌ IGNORADO |
| `.env.example` | Modelo com placeholders | ✅ COMMITADO |
| `.gitignore` | Bloqueia upload de `.env` | ✅ COMMITADO |

### 3. **Atualizado Launcher do Bot**

`INICIAR_BOT.bat` agora:
- ✅ Lê arquivo `.env` antes de executar
- ✅ Passa credenciais via variáveis de ambiente
- ✅ Valida presença de `.env` (pede para copiar de `.env.example`)

### 4. **Histórico do Git Limpo**

```bash
# Antes: Credenciais expostas no commit inicial
# ❌ GitHub Push Protection bloqueava

# Depois: Novo repositório sem credenciais
# ✅ Push bem-sucedido para GitHub
```

## 🔑 Como Usar

### **Primeira Vez (Setup Inicial)**

```bash
# 1. Copie o template
copy .env.example .env

# 2. Abra .env em editor de texto
notepad .env

# 3. Preencha com suas credenciais:
TELEGRAM_API_ID=29422958
TELEGRAM_API_HASH=seu_api_hash_aqui
TELEGRAM_SESSION=sua_sessao_aqui
GOOGLE_CREDS={"type": "service_account", ...}

# 4. Salve e feche
```

### **Executar o Bot**

```bash
# Double-click em:
INICIAR_BOT.bat

# Ou via terminal:
cd "C:\Users\Gustavo\OneDrive\Desktop\Bots Cloude"
INICIAR_BOT.bat
```

## ⚠️ NUNCA FAÇA ISSO

```bash
# ❌ Não copie .env para GitHub
git add .env
git commit -m "adicionar credenciais"

# ❌ Não envie credenciais em commits
# GitHub Push Protection vai bloquear

# ❌ Não compartilhe o arquivo .env
# Alguém teria acesso à sua conta Google e Telegram

# ❌ Não revele TELEGRAM_SESSION em público
# É basicamente sua "senha" do Telegram
```

## 🛡️ Por Que Isso É Seguro

### Fluxo Seguro:

```
┌──────────────────────────────────┐
│  Seu Computador (Windows)        │
│  ┌────────────────────────────┐  │
│  │ .env (CREDENCIAIS REAIS)   │  │
│  │ ✅ Apenas no seu PC        │  │
│  │ ✅ Nunca no GitHub         │  │
│  └────────────────────────────┘  │
│            │                      │
│            ▼                      │
│  ┌────────────────────────────┐  │
│  │ INICIAR_BOT.bat            │  │
│  │ └─> Lê .env                │  │
│  │     └─> Python bot         │  │
│  │         └─> Usa credenciais│  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
          │
          │ (Criptografado via HTTPS)
          ▼
┌──────────────────────────────────┐
│  APIs Externas                   │
│  ├─ Telegram (privado)           │
│  ├─ Google Sheets (privado)      │
│  └─ ✅ Suas credenciais nunca    │
│     aparecem em logs públicos     │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│  GitHub (Código-Fonte Público)   │
│  ├─ layscore_local.py (✅ limpo) │
│  ├─ index.html (✅ sem secrets)  │
│  ├─ .env.example (template OK)   │
│  └─ ❌ NÃO contém credenciais    │
└──────────────────────────────────┘
```

## 📋 Checklist de Segurança

- [x] Credenciais removidas de `layscore_local.py`
- [x] Credenciais removidas de `preencher_gols.py`
- [x] `.env` adicionado ao `.gitignore`
- [x] `.env.example` criado como template
- [x] Código refatorado para usar `os.getenv()`
- [x] GitHub repositório limpo (sem secrets no histórico)
- [x] Push bem-sucedido para GitHub
- [x] README com instruções de segurança
- [x] Validação de credenciais no startup

## 🔄 Renovar Credenciais (se vazar)

Se acidentalmente compartilhar `.env`:

### 1. **Google Credentials**
```
1. Google Cloud Console
2. Service Accounts
3. Delete old account
4. Create new account
5. Download new JSON
6. Atualizar GOOGLE_CREDS em .env
```

### 2. **Telegram Session**
```
1. Abrir gerar_session.py
2. Executar para gerar nova SESSION_STR
3. Atualizar TELEGRAM_SESSION em .env
```

### 3. **Telegram API Hash**
```
1. Acessar https://my.telegram.org/apps
2. Gerar novo API_HASH
3. Atualizar TELEGRAM_API_HASH em .env
```

## 📞 Suporte

Se tiver dúvidas sobre segurança:

1. **GitHub Push Protection bloqueando?**
   - Verifique se `.env` está em `.gitignore`
   - Rode `git status` para ver arquivos unstaged

2. **Bot não inicia?**
   - Verifique se `.env` existe
   - Rode manualmente: `python layscore_local.py`
   - Veja mensagens de erro no console

3. **Credenciais vazaram?**
   - Regenere todas (Google + Telegram)
   - Update `.env`
   - Restart o bot

---

**Data**: Abril 2026  
**Status**: ✅ Seguro para produção  
**Próximo Passo**: Conectar Netlify para auto-deploy do dashboard
