import discord
import os
import datetime
import psycopg2
import sqlite3
from discord.ext import commands
from discord.ext import tasks
from flask import Flask
import threading

DATABASE_URL = os.environ.get("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS alko (
    nick VARCHAR(50) PRIMARY KEY,
    procenty REAL
)
""")
# Używamy Bot zamiast Client
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


GUILD_ID=1407035107189063844


client = commands.Bot(command_prefix="!", intents=intents)
def add_drink(user: str, etanol: float):
    cursor.execute("""
    INSERT INTO alko (nick, procenty)
    VALUES (%s, %s)
    ON CONFLICT (nick)
    DO UPDATE SET procenty = alko.procenty + EXCLUDED.procenty
    """, (user, etanol))
    conn.commit()

@client.event
async def on_ready():
    print(f'Logged on as {client.user}!')
    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await client.tree.sync(guild=guild)
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Sync error: {e}")
@client.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    guild = reaction.message.guild
    if not guild:
        return
    if hasattr(client, "pijok_rola_message_id") and reaction.message.id != client.pijok_rola_message_id:
        return

    if str(reaction.emoji) == "🍻":
        role_name = "🍻"  # upewnij się, że rola istnieje
        member = guild.get_member(user.id)  # <- ważne
        role = discord.utils.get(guild.roles, name=role_name)
        if role and member:
            await user.add_roles(role)
            print(f"✅ Assigned {role_name} to {user}")


@client.event
async def on_reaction_remove(reaction, user):
    if user.bot:
        return
    guild = reaction.message.guild
    if not guild:
        return
    if hasattr(client, "pijok_rola_message_id") and reaction.message.id != client.pijok_rola_message_id:
        return

    if str(reaction.emoji) == "🍻":
        role_name = "🍻"
        role = discord.utils.get(guild.roles, name=role_name)
        member = guild.get_member(user.id)
        if role and member:
            await user.remove_roles(role)
            print(f"❌ Removed {role_name} from {user}")
#Rola pijoka
@client.tree.command(name="pijokrola", description="Pobierz role pijoka", guild=discord.Object(id=GUILD_ID))
async def pijok_rola(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You must be admin to use this command", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    description = (
        "Zareaguj aby dołączyć do pijoków\n"
    )
    embed = discord.Embed(title="Rola pijoka🍻", description=description, color=discord.Color.blurple())
    message= await interaction.channel.send(embed=embed)
    await message.add_reaction("🍻")
    client.pijok_rola_message_id = message.id
    await interaction.followup.send("Pijok rola created!", ephemeral=True)
# Slash command (aplikacyjne)
@client.tree.command(name="gralko", description="Gienio dodaje twoją porcję alkoholu", guild=discord.Object(id=GUILD_ID))
async def gralkoo(interaction: discord.Interaction, ile: int, woltarz: int):
    etanol=ile*(woltarz/100)
    await interaction.response.send_message(f"wypiłxś {etanol} etanolu")
    add_drink(interaction.user.name, etanol)
@client.tree.command(name="pijoki", description="Gienio robi ranking pijoków", guild=discord.Object(id=GUILD_ID))
async def pijoki(interaction: discord.Interaction):
    cursor.execute("SELECT nick, procenty FROM alko ORDER BY procenty DESC LIMIT 4;")
    rows = cursor.fetchall()

    if not rows:
        await interaction.response.send_message("🚫 Jeszcze nikt nic nie wypił!")
        return

    ranking = "\n".join([f"{i+1}. {nick} — {procenty:.1f} ml etanolu"
                         for i, (nick, procenty) in enumerate(rows)])

    await interaction.response.send_message(f"🍻 **Ranking pijoków**:\n{ranking}")
@client.tree.command(name="cleardb", description="reset tabeli", guild=discord.Object(id=GUILD_ID))
async def cleardb(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You must be admin to use this command", ephemeral=True)
        return
    cursor.execute("DELETE FROM alko;")#czyszczenie tabeli tylko dla admina
    conn.commit()
    await interaction.response.send_message("wyczyszczona")
@client.tree.command(name="help", description="spis komend", guild=discord.Object(id=GUILD_ID))
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="Ranking alkoholowy",
                          description="Komendy i ich działanie:",
                          colour=0xff8040)

    embed.add_field(name="**/grajko <ile alkoholu w ml> <moc alkoholu w procentach>**",
                    value="Dodaje ilość wypitego alkoholu użytkownikowi",
                    inline=False)
    embed.add_field(name="**/pijoki**",
                    value="Wyświetla top 4 osoby które wypiły najwięcej alkoholu",
                    inline=False)

    await interaction.channel.send(embed=embed)

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot działa ✅"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# uruchamiamy Flask w osobnym wątku
threading.Thread(target=run_flask).start()

# Uruchomienie
client.run('MTQwNzAzODAwNDg4Njc2NTYzOQ.G1vG4y.U4Xvy3GLTfDbEAvq_D6tro3m1yV3eSYhib5pMc')
