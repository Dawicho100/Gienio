import discord
import sqlite3
from discord.ext import commands

conn = sqlite3.connect("mydatabase.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS alko (
    nick VARCHAR(50) PRIMARY KEY,
    procenty INT
)
""")
# Używamy Bot zamiast Client
intents = discord.Intents.default()
intents.message_content = True
GUILD_ID="1407035107189063844"
client = commands.Bot(command_prefix="!", intents=intents)

def add_drink(user: str, etanol: float):
    cursor.execute("""
    INSERT INTO alko (nick, procenty) 
    VALUES (?, ?)
    ON CONFLICT(nick) DO UPDATE SET procenty = procenty + excluded.procenty
    """, (user, etanol))
    conn.commit()

@client.event
async def on_ready():
    print(f'Logged on as {client.user}!')
    try:
        synced = await client.tree.sync()  # synchronizuje globalne komendy
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Sync error: {e}")

# Slash command (aplikacyjne)
@client.tree.command(name="gralko", description="Gienio dodaje twoją porcję alkoholu", guild=GUILD_ID)
async def gralkoo(interaction: discord.Interaction, ile: int, woltarz: int):
    etanol=ile*(woltarz/100)
    await interaction.response.send_message(f"wypiłxś {etanol} etanolu")
    add_drink(interaction.user.name, etanol)
@client.tree.command(name="pijoki", description="Gienio robi ranking pijoków", guild=GUILD_ID)
async def pijoki(interaction: discord.Interaction):
    cursor.execute("SELECT nick, procenty FROM alko ORDER BY procenty DESC LIMIT 4;")
    rows = cursor.fetchall()

    if not rows:
        await interaction.response.send_message("🚫 Jeszcze nikt nic nie wypił!")
        return

    ranking = "\n".join([f"{i+1}. {nick} — {procenty:.1f} ml etanolu"
                         for i, (nick, procenty) in enumerate(rows)])

    await interaction.response.send_message(f"🍻 **Ranking pijoków**:\n{ranking}")


# Uruchomienie
client.run("MTQwNzAzODAwNDg4Njc2NTYzOQ.G1vG4y.U4Xvy3GLTfDbEAvq_D6tro3m1yV3eSYhib5pMc")
