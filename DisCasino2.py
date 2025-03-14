import discord
from discord.ext import commands
import sqlite3
from sqlite3 import Error
import centralbank
import permissions
import security

# Database Engine
def initDatabase():
    conn = sqlite3.connect("twilightcasino.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lottotickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user INTEGER,
            num1 INTEGER,
            num2 INTEGER,
            num3 INTEGER,
            num4 INTEGER,
            num5 INTEGER,
            special INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lottodraws (
            draw_id INTEGER PRIMARY KEY AUTOINCREMENT,
            jackpot INTEGER,
            total_pot INTEGER DEFAULT 0,
            winning_num1 INTEGER,
            winning_num2 INTEGER,
            winning_num3 INTEGER,
            winning_num4 INTEGER,
            winning_num5 INTEGER,
            special_num INTEGER,
            winner INTEGER,
            draw_date TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS balances (
            user INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            totalwon INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            user INTEGER,
            type TEXT CHECK(type IN ('deposit', 'withdrawal')),
            amount INTEGER,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT CHECK(status IN ('pending', 'approved', 'denied')),
            proof TEXT DEFAULT NULL
        )
    """)

    conn.commit()  # Save changes
    conn.close()  # Close connection


# Main Engine
class Client(commands.Bot):
    async def on_ready(self):
        print(f'{self.user} is now online!')
        try:
            guild = discord.Object(id=serverid)
            synced = await self.tree.sync(guild=guild)
            print(f'{len(synced)} commands are now synced.')
        except Exception as e:
            print(f'There was an error syncing commands: {e}.')
        await client.change_presence(activity=discord.Activity(name="the blackjack tables.", type=discord.ActivityType.watching))
        try:
            initDatabase()
            print("The database has been successfully initialized.")
        except Error as e:
            print(f'There was an error initializing the database: {e}.')
        conn = sqlite3.connect("twilightcasino.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, user, amount, proof FROM transactions WHERE status = 'pending' AND type = 'deposit'")
        pending_transactions = cursor.fetchall()
        conn.close()

        admin_channel = client.get_channel(permissions.adminid)

        if admin_channel:
            for transaction, user, amount, proof in pending_transactions:
                view = centralbank.DepositAdminView(user, amount, transaction)

                embed = discord.Embed(title="Deposit Request", color=discord.Color.blurple())
                embed.add_field(name="User", value=f"<@{user}>")
                embed.add_field(name="Amount", value=f"{amount:,} tokens")
                embed.set_footer(text="Review this request:")
                embed.set_author(name="Twilight Casino")
                if proof:
                    embed.set_image(url=proof)

                await admin_channel.send(embed=embed, view=view)
     
intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="%", intents=intents)
serverid = 1347631647658610768


centralbank.initBank(client, serverid)

client.run(security.token)