#!/usr/bin/env python3
"""
Script para diagnosticar problemas com o arquivo .env
Mostra exatamente o que está errado
"""
import os
import json
from pathlib import Path

print("\n" + "="*70)
print("🔍 DIAGNÓSTICO COMPLETO DO .env")
print("="*70 + "\n")

# ─────────────────────────────────────────────────────────────
# 1. Verificar se arquivo existe
# ─────────────────────────────────────────────────────────────
print("📁 PASSO 1: Verificar arquivo .env")
print("-" * 70)

env_path = Path(".env")
if env_path.exists():
    file_size = env_path.stat().st_size
    print(f"✅ Arquivo .env ENCONTRADO ({file_size} bytes)")
else:
    print(f"❌ Arquivo .env NÃO ENCONTRADO")
    print(f"   Caminho procurado: {env_path.absolute()}")
    print(f"   Solução: Copie .env.example para .env")
    exit(1)

# ─────────────────────────────────────────────────────────────
# 2. Ler arquivo manualmente
# ─────────────────────────────────────────────────────────────
print("\n📄 PASSO 2: Ler conteúdo do .env")
print("-" * 70)

with open(".env", "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total de linhas: {len(lines)}")

for i, line in enumerate(lines, 1):
    if "=" in line:
        key = line.split("=")[0].strip()
        value = line.split("=", 1)[1].strip()

        if key == "TELEGRAM_API_ID":
            print(f"  Linha {i}: {key} = {value}")
        elif key == "TELEGRAM_API_HASH":
            print(f"  Linha {i}: {key} = {value[:30]}...")
        elif key == "TELEGRAM_SESSION":
            print(f"  Linha {i}: {key} = {value[:30]}... ({len(value)} chars)")
        elif key == "GOOGLE_CREDS":
            print(f"  Linha {i}: {key} = {value[:40]}... ({len(value)} chars)")
        else:
            print(f"  Linha {i}: {key} = {value[:40]}...")

# ─────────────────────────────────────────────────────────────
# 3. Carregar com dotenv
# ─────────────────────────────────────────────────────────────
print("\n🔧 PASSO 3: Carregar com python-dotenv")
print("-" * 70)

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ python-dotenv carregado com sucesso")
except ImportError:
    print("❌ python-dotenv não está instalado")
    print("   Instale com: pip install python-dotenv")
    exit(1)

# ─────────────────────────────────────────────────────────────
# 4. Validar cada credencial
# ─────────────────────────────────────────────────────────────
print("\n🔐 PASSO 4: Validar credenciais carregadas")
print("-" * 70)

credentials_ok = True

# TELEGRAM_API_ID
api_id = os.getenv("TELEGRAM_API_ID")
if api_id:
    print(f"✅ TELEGRAM_API_ID: {api_id}")
else:
    print(f"❌ TELEGRAM_API_ID: NÃO CARREGADO")
    credentials_ok = False

# TELEGRAM_API_HASH
api_hash = os.getenv("TELEGRAM_API_HASH")
if api_hash:
    print(f"✅ TELEGRAM_API_HASH: {api_hash[:30]}... ({len(api_hash)} chars)")
else:
    print(f"❌ TELEGRAM_API_HASH: NÃO CARREGADO")
    credentials_ok = False

# TELEGRAM_SESSION
session = os.getenv("TELEGRAM_SESSION")
if session:
    print(f"✅ TELEGRAM_SESSION: {session[:30]}... ({len(session)} chars)")
else:
    print(f"❌ TELEGRAM_SESSION: NÃO CARREGADO")
    credentials_ok = False

# GOOGLE_CREDS
google_creds = os.getenv("GOOGLE_CREDS")
if google_creds:
    print(f"✅ GOOGLE_CREDS carregado ({len(google_creds)} chars)")

    # Tentar parsear JSON
    try:
        creds_dict = json.loads(google_creds)
        print(f"   ✅ JSON válido")

        # Verificar campos obrigatórios
        required = ["type", "project_id", "private_key", "client_email"]
        for field in required:
            if field in creds_dict:
                if field == "private_key":
                    pk = creds_dict[field]
                    print(f"   ✅ {field}: {pk[:40]}...{pk[-20:]}")
                else:
                    print(f"   ✅ {field}: {creds_dict[field]}")
            else:
                print(f"   ❌ {field}: FALTANDO")
                credentials_ok = False

    except json.JSONDecodeError as e:
        print(f"   ❌ JSON INVÁLIDO: {str(e)[:100]}")
        print(f"   Primeiro erro: Posição {e.pos}")
        print(f"   Contexto: ...{google_creds[max(0,e.pos-20):min(len(google_creds),e.pos+20)]}...")
        credentials_ok = False
else:
    print(f"❌ GOOGLE_CREDS: NÃO CARREGADO")
    credentials_ok = False

# ─────────────────────────────────────────────────────────────
# 5. Resultado Final
# ─────────────────────────────────────────────────────────────
print("\n" + "="*70)
if credentials_ok:
    print("✅ TUDO OK! Você pode iniciar o bot com:")
    print("   python layscore_local.py")
    print("   ou")
    print("   INICIAR_BOT.bat")
else:
    print("❌ PROBLEMAS ENCONTRADOS:")
    print("   1. Verifique se todas as linhas no .env estão completas")
    print("   2. Especialmente GOOGLE_CREDS deve ser uma única linha JSON")
    print("   3. Não deve haver quebras de linha no meio das credenciais")
    print("   4. Verifique se não há aspas extras ou caracteres invisíveis")

print("="*70 + "\n")
