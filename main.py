import discord
import os
import datetime
import psycopg2
import sqlite3
from discord.ext import commands
from discord.ext import tasks
from flask import Flask
import threading
import subprocess
import time
import sys  # potrzebne do restartu

# --- KONFIGURACJA POLLINGU GIT ---
REPO_DIR = "/home/none/gienio/Gienio"  # katalog Twojego repo
POLL_INTERVAL = 300  # co 5 minut

def git_poller():
    last_commit = None
    while True:
        try:
            os.chdir(REPO_DIR)
            # Pobranie najnowszych informacji z GitHub
            subprocess.run(["git", "fetch", "origin", "master"], check=True)

            # Odczyt HEAD aktualnej gałęzi
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
            )
            current_commit = result.stdout.strip()

            # Jeśli commit się zmienił, robimy pull i restartujemy bota
            if last_commit and current_commit != last_commit:
                print("🔄 Zmiana w repo wykryta! Aktualizuję bota...")
                subprocess.run(["git", "pull", "origin", "master"], check=True)
                os.execv(sys.executable, ["python3"] + sys.argv)  # restart procesu

            last_commit = current_commit

        except Exception as e:
            print(f"❌ Błąd podczas sprawdzania repo: {e}")

        time.sleep(POLL_INTERVAL)

# --- POZOSTAŁY KOD BOTA ---

DATABASE_URL = os.environ.get("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS alko (
    nick VARCHAR(50) PRIMARY KEY,
    procenty REAL
)
""")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

GUILD_ID=os.environ.get("SERVER_ID")
client = commands.Bot(command_prefix="!", intents=intents)

def add_drink(user: str, etanol: float):
    cursor.execute("""
    INSERT INTO alko (nick, procenty)
    VALUES (%s, %s)
    ON CONFLICT (nick)
    DO UPDATE SET procenty = alko.procenty + EXCLUDED.procenty
    """, (user, etanol))
    conn.commit()

def update_value(user: str, etanol: float):
    cursor.execute("""
        UPDATE alko
        SET procenty = %s
        WHERE nick = %s
        """, (etanol, user))
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
async def on_message(message):
    if message.author.bot:
        return
    if message.content.startswith('@Gienio#6365'):
        await message.channel.send(f'Elo {message.author.mention}')
    await client.process_commands(message)

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
        role_name = "🍻"
        member = guild.get_member(user.id)
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

# --- KOMENDY SLASH ---
@client.tree.command(name="pijokrola", description="Pobierz role pijoka", guild=discord.Object(id=GUILD_ID))
async def pijok_rola(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You must be admin to use this command", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    description = "Zareaguj aby dołączyć do pijoków\n"
    embed = discord.Embed(title="Rola pijoka🍻", description=description, color=discord.Color.blurple())
    message = await interaction.channel.send(embed=embed)
    await message.add_reaction("🍻")
    client.pijok_rola_message_id = message.id
    await interaction.followup.send("Pijok rola created!", ephemeral=True)

@client.tree.command(name="gralko", description="Gienio dodaje twoją porcję alkoholu", guild=discord.Object(id=GUILD_ID))
async def gralkoo(interaction: discord.Interaction, ile: int, woltarz: int):
    etanol=ile*(woltarz/100)
    await interaction.response.send_message(f"wypiłxś {etanol} etanolu użytkowniku {interaction.user.name}")
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
    cursor.execute("DELETE FROM alko;")
    conn.commit()
    await interaction.response.send_message("wyczyszczona")

@client.tree.command(name="update", description="update'uje wartość dla użytkownika x", guild=discord.Object(id=GUILD_ID))
async def update(interaction: discord.Interaction, kto: str, ile: float):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You must be admin to use this command", ephemeral=True)
        return
    await interaction.response.send_message(f"wartość dla użytkownika {kto} zmieniona")
    update_value(kto, ile)

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
    await interaction.response.send_message(embed=embed)
app = Flask(__name__)
@app.route("/")
def home():
    return "Bot działa ✅"

if __name__ == "__main__":
    # Uruchom polling Git w osobnym wątku
    threading.Thread(target=git_poller, daemon=True).start()

    # Bot w tle
    threading.Thread(target=lambda: client.run(os.environ["DISCORD_TOKEN"])).start()

    # Flask
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
