#!/usr/bin/env python3
"""
Script para testar se o arquivo .env está sendo carregado corretamente
"""
import os
from dotenv import load_dotenv
import json

print("=" * 60)
print("TESTE DE CARREGAMENTO DO .env")
print("=" * 60)
print()

# Load environment variables
load_dotenv()

# Check each variable
variables = {
    "TELEGRAM_API_ID": "API ID do Telegram",
    "TELEGRAM_API_HASH": "API Hash do Telegram",
    "TELEGRAM_SESSION": "Sessão do Telegram (muito longo)",
    "GOOGLE_CREDS": "Credenciais do Google (JSON)"
}

all_ok = True

for var_name, description in variables.items():
    value = os.getenv(var_name)

    if value:
        if var_name == "TELEGRAM_API_ID":
            print(f"✅ {var_name}: {value}")
        elif var_name == "TELEGRAM_API_HASH":
            print(f"✅ {var_name}: {value[:20]}...")
        elif var_name == "TELEGRAM_SESSION":
            print(f"✅ {var_name}: {value[:30]}... (comprimento: {len(value)} chars)")
        elif var_name == "GOOGLE_CREDS":
            try:
                creds_dict = json.loads(value)
                if "private_key" in creds_dict and "client_email" in creds_dict:
                    print(f"✅ {var_name}: JSON válido")
                    print(f"   - Projeto: {creds_dict.get('project_id', 'N/A')}")
                    print(f"   - Email: {creds_dict.get('client_email', 'N/A')}")
                    print(f"   - Private Key: {'Presente' if creds_dict.get('private_key') else 'FALTANDO'}")
                else:
                    print(f"❌ {var_name}: JSON inválido (faltam campos)")
                    all_ok = False
            except json.JSONDecodeError as e:
                print(f"❌ {var_name}: Erro ao parsear JSON - {str(e)[:50]}")
                all_ok = False
    else:
        print(f"❌ {var_name}: NÃO CARREGADO")
        all_ok = False

print()
print("=" * 60)

if all_ok:
    print("✅ TUDO OK! O .env está carregado corretamente.")
    print("   Você pode iniciar o bot com: python layscore_local.py")
else:
    print("❌ ERRO! Verifique o arquivo .env")
    print("   Passos:")
    print("   1. Verifique se .env existe neste diretório")
    print("   2. Verifique se as credenciais estão preenchidas")
    print("   3. Verifique se GOOGLE_CREDS é um JSON válido")

print("=" * 60)
