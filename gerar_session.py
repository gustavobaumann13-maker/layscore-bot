import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID   = 29422958
API_HASH = "f5c8a457728681f29b60e99eecddcc06"

async def gerar():
    async with TelegramClient(StringSession(), API_ID, API_HASH) as client:
        print("\n" + "="*60)
        print("SUA SESSION STRING (copie tudo abaixo):")
        print("="*60)
        print(client.session.save())
        print("="*60)

asyncio.run(gerar())
