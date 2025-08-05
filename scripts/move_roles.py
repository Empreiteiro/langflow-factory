import os
from dotenv import load_dotenv

load_dotenv()  # Carrega as variáveis do arquivo .env

import discord
from discord.ext import commands

GUILD_ID = 1116803230643527710 
OLD_ROLE_NAME = "AI Devs India"
NEW_ROLE_NAME = "Competitors"

intents = discord.Intents.default()
intents.members = True  # Ative também no portal do Discord

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print("Guild não encontrada.")
        await bot.close()
        return

    old_role = discord.utils.get(guild.roles, name=OLD_ROLE_NAME)
    new_role = discord.utils.get(guild.roles, name=NEW_ROLE_NAME)

    if not old_role or not new_role:
        print("Cargo(s) não encontrado(s).")
        await bot.close()
        return

    count = 0
    async for member in guild.fetch_members(limit=None):
        if old_role in member.roles:
            await member.remove_roles(old_role)
            await member.add_roles(new_role)
            count += 1
            print(f"{member.name} movido.")

    print(f"Total movidos: {count}")
    await bot.close()

# Certifique-se de que DISCORD_TOKEN está definido no seu .env
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("Token não encontrado no .env. Verifique a variável DISCORD_TOKEN.")

bot.run(token)
