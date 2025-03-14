import discord
from discord import app_commands
import sqlite3
import permissions
from embedhelper import genEmbed

# Main Method
def initBank(client, serverid):
    tokensgroup = app_commands.Group(name="tokens", description="Twlight Casino tokens commands.", guild_ids=[serverid])
    client.tree.add_command(tokensgroup)

    @tokensgroup.command(name="balance", description="Display your tokens balance!")
    @app_commands.describe(user="The user whose balance you wish to check. (Optional)")
    async def showTokensBalance(interaction: discord.Interaction, user: discord.Member = None):
        conn = sqlite3.connect("twilightcasino.db")
        cursor = conn.cursor()
        if user == None:
            user = interaction.user.id
            cursor.execute("SELECT balance FROM balances WHERE user = ?", (user,))
            result = cursor.fetchone()
            if result:
                balance = result[0]
                await interaction.response.send_message(content=f"You have **{balance:,}** tokens.", ephemeral=True)
            else:
                await interaction.response.send_message(content=f"You do not have a balance. Request a deposit to get started.", ephemeral=True)
        else:
            if await permissions.checkEmployeePerms(interaction, "check the balance of other users") == True:
                user2 = user.id
                cursor.execute("SELECT balance FROM balances WHERE user = ?", (user2,))
                result = cursor.fetchone()
                if result:
                    balance = result[0]
                    await interaction.response.send_message(content=f"{user.mention} has **{balance:,}** tokens.", ephemeral=True)
                else:
                    await interaction.response.send_message(content=f"{user.mention} does not have an account with Twilight Casino.", ephemeral=True)
        conn.close()
    
    @tokensgroup.command(name="deposit", description="Buy tokens and add them to your balance!")
    @app_commands.describe(quantity="The amount you wish to deposit.", proof="Attach proof of your deposit to Twilight Casino. See our policies for supported payment methods.")
    async def depositTokens(interaction: discord.Interaction, quantity: int, proof: discord.Attachment):
        if quantity > 0:
            if not proof or not proof.content_type.startswith("image/"):
                await interaction.response.send_message(content="You must attach a valid image file as evidence of your deposit. If you believe this message is an error, please open a support ticket.", ephemeral=True)
            else:
                print(f"Attempting to request a deposit for user {interaction.user.id} with amount {quantity:,}")
                # Database
                conn = sqlite3.connect("twilightcasino.db")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO transactions (user, type, amount, status, proof)
                    VALUES (?, 'deposit', ?, 'pending', ?)
                    """, (interaction.user.id, quantity, proof.url)
                )
                transaction = cursor.lastrowid
                conn.commit()
                conn.close()
                # Embed
                embed = genEmbed("Deposit Request", None, "Review this request:")
                embed.add_field(name="User", value=interaction.user.mention)
                embed.add_field(name="Amount", value=f"{quantity:,} tokens")
                embed.set_image(url=proof.url)
                # Admin Approval
                admin = interaction.client.get_channel(permissions.adminid)
                if admin:
                    view = DepositAdminView(interaction.user.id, quantity, transaction)
                    await admin.send(embed=embed, view=view)
                # Confirmation
                await interaction.response.send_message(content=f"You have submitted a deposit request for **{quantity:,}** tokens. It will be reviewed by staff as soon as possible.\n{proof}", ephemeral=True)
        else:
            await interaction.response.send_message(content="You must deposit an amount greater than zero.", ephemeral=True)
    
    @tokensgroup.command(name="withdraw", description="Cash tokens out to a supported currency and location!")
    @app_commands.describe(quantity="The amount you wish to withdraw.", currency="The currency you wish to cash your tokens out to. See our policies for the most current exchange rates.", location="The location you wish to have your money sent to.")
    @app_commands.choices(currency=[app_commands.Choice(name="Redmont Dollars", value="dollars"), app_commands.Choice(name="Alexandria Pounds", value="pounds")], location=[app_commands.Choice(name="In-Game Balance", value="ingame"), app_commands.Choice(name="Vanguard Bank", value="vanguard"), app_commands.Choice(name="Volt Bank", value="volt")])
    async def withdrawTokens(interaction: discord.Interaction, quantity: int, currency: app_commands.Choice[str], location: app_commands.Choice[str]):
        if quantity > 0:
            user = interaction.user.id
            conn = sqlite3.connect("twilightcasino.db")
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM balances WHERE user = ?", (user,))
            result = cursor.fetchone()
            if result:
                balance = result[0]
                if quantity > balance:
                    await interaction.response.send_message(content=f"Your balance is only **{balance:,}** tokens, so you may not withdraw **{quantity:,}** tokens!", ephemeral=True)
                else:
                    # Database
                    cursor.execute("""
                        INSERT INTO transactions (user, type, amount, status)
                        VALUES (?, 'withdrawal', ?, 'pending')
                        """, (user, quantity)
                    )
                    transaction = cursor.lastrowid
                    conn.commit()
                    conn.close()
                    # Embed
                    embed = discord.Embed(title="Deposit Request", color=discord.Color.blurple())
                    embed.add_field(name="User", value=interaction.user.mention)
                    embed.add_field(name="Amount", value=f"{quantity:,} tokens")
                    embed.set_footer(text="Review this request:")
                    embed.set_author(name="Twilight Casino")
                    # Admin Approval
                    admin = interaction.client.get_channel(permissions.adminid)
                    if admin:
                        view = DepositAdminView(interaction.user.id, quantity, transaction)
                        await admin.send(embed=embed, view=view)
                    # Confirmation
                    await interaction.response.send_message(content=f"You have submitted a withdraw request for **{quantity:,}** tokens to {currency.name} at {location.name}. It will be actioned by a manager as soon as possible.", ephemeral=True)
                    conn.commit()
            else:
                await interaction.response.send_message(content=f"You do not have a balance. Make a deposit to open an account.", ephemeral=True)
            conn.close()
        else:
            await interaction.response.send_message(content="You must withdraw an amount greater than zero.", ephemeral=True)

    @tokensgroup.command(name="mint", description="Mint a number of tokens to someone's balance!")
    @app_commands.describe(quantity="The amount you wish to mint.", user="The person to tokens tokens to.")
    @app_commands.default_permissions(view_audit_log=True)
    async def mintTokens(interaction: discord.Interaction, quantity: int, user: discord.Member):
        if await permissions.checkEmployeePerms(interaction, "mint tokens to someone's balance") == True:
            userid = user.id
            conn = sqlite3.connect("twilightcasino.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO balances (user, balance) VALUES (?, ?)
                ON CONFLICT(user) DO UPDATE SET balance = balance + ?
            """, (userid, quantity, quantity))
            conn.commit()
            cursor.execute("SELECT balance FROM balances WHERE user = ?", (userid,))
            result = cursor.fetchone()
            balance = result[0]
            conn.close()
            await interaction.response.send_message(content=f"You have minted **{quantity:,}** tokens to {user.mention}. They now have **{balance:,}** tokens.", ephemeral=True)

    @tokensgroup.command(name="delete", description="Delete a number of tokens from someone's balance!")
    @app_commands.describe(quantity="The amount you wish to delete.", user="The person to delete tokens from.")
    @app_commands.default_permissions(ban_members=True)
    async def deleteTokens(interaction: discord.Interaction, quantity: int, user: discord.Member):
        if await permissions.checkAdminPerms(interaction, "delete tokens from someone's balance") == True:
            userid = user.id
            conn = sqlite3.connect("twilightcasino.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO balances (user, balance) VALUES (?, 0)
                ON CONFLICT(user) DO UPDATE SET balance = balance - ?
            """, (userid, quantity))
            conn.commit()
            cursor.execute("SELECT balance FROM balances WHERE user = ?", (userid,))
            result = cursor.fetchone()
            balance = result[0]
            conn.close()
            await interaction.response.send_message(content=f"You have deleted **{quantity:,}** tokens from {user.mention}. They now have **{balance:,}** tokens.", ephemeral=True)

    @tokensgroup.command(name="set", description="Set someone's tokens balance to a certain value!")
    @app_commands.describe(quantity="The amount you wish to set the user\'s balance to.", user="The person to adjust the balance of.")
    @app_commands.default_permissions(ban_members=True)
    async def setTokens(interaction: discord.Interaction, quantity: int, user: discord.Member):
        if await permissions.checkAdminPerms(interaction, "set someone's tokens balance") == True:
            userid = user.id
            conn = sqlite3.connect("twilightcasino.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO balances (user, balance) VALUES (?, ?)
                ON CONFLICT(user) DO UPDATE SET balance = ?
            """, (userid, quantity, quantity))
            conn.commit()
            cursor.execute("SELECT balance FROM balances WHERE user = ?", (userid,))
            result = cursor.fetchone()
            balance = result[0]
            conn.close()
            await interaction.response.send_message(content=f"You have set {user.mention}\'s balance to **{quantity:,}** tokens. They now have **{balance:,}** tokens.", ephemeral=True)

    @tokensgroup.command(name="history", description="View your transaction history!")
    async def transactionHistory(interaction: discord.Interaction):
        conn = sqlite3.connect("twilightcasino.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE user = ?", (interaction.user.id,))
        total_transactions = cursor.fetchone()[0]

        if total_transactions == 0:
            await interaction.response.send_message("You have no transaction history.", ephemeral=True)
            return

        page = 1
        per_page = 5
        total_pages = (total_transactions + per_page - 1) // per_page

        view = TransactionHistoryView(interaction.user.id, page, total_pages)
        embed = await view.get_page_embed(page)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class DepositAdminView(discord.ui.View):
    def __init__(self, user: int, amount: int, transaction: int):
        super().__init__(timeout=None)
        self.user = user
        self.amount = amount
        self.transaction = transaction
        print(f"Attempting to create transaction {self.transaction} for user {self.user} with amount {self.amount:,}")

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_approval(interaction, approved=True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_approval(interaction, approved=False)

    async def handle_approval(self, interaction: discord.Interaction, approved: bool):
        conn = sqlite3.connect("twilightcasino.db")
        cursor = conn.cursor()
        print(f"Attempting to handle transaction {self.transaction} for user {self.user} with amount {self.amount:,}. The transaction was approved: {approved}")
        cursor.execute("""
            SELECT status FROM transactions 
            WHERE user = ? AND amount = ? AND status = 'pending' AND id = ?
        """, (self.user, self.amount, self.transaction))
        result = cursor.fetchone()
        if result is None:
            await interaction.response.send_message("This transaction no longer exists or was already processed.", ephemeral=True)
            return
        if approved:
            print(f"Attempting to approve transaction {self.transaction} for user {self.user} with amount {self.amount:,}")
            cursor.execute("""
                UPDATE transactions
                SET status = 'approved'
                WHERE user = ? AND amount = ? AND status = 'pending' AND id = ?
            """, (self.user, self.amount, self.transaction))
            cursor.execute("SELECT balance FROM balances WHERE user = ?", (self.user,))
            current_balance = cursor.fetchone()
            if current_balance:
                balance = current_balance[0]
                print(f"{self.user}\'s balance is {balance}")
            else:
                print(f"No balance found for user {self.user}")
            cursor.execute("""
                INSERT INTO balances (user, balance) VALUES (?, ?)
                ON CONFLICT(user) DO UPDATE SET balance = balance + ?
            """, (self.user, self.amount, self.amount))
            cursor.execute("SELECT balance FROM balances WHERE user = ?", (self.user,))
            current_balance = cursor.fetchone()
            if current_balance:
                balance = current_balance[0]
                print(f"{self.user}\'s balance is {balance}")
            else:
                print(f"No balance found for user {self.user}")
            conn.commit()
            conn.close()
            user = interaction.client.get_user(self.user)
            if user:
                await user.send(f"Your deposit of **{self.amount:,}** tokens has been **approved**!")
            await interaction.response.edit_message(content="Deposit approved.", view=None)
        else:
            cursor.execute("""
                UPDATE transactions
                SET status = 'denied'
                WHERE user = ? AND amount = ? AND status = 'pending' AND id = ?
            """, (self.user, self.amount, self.transaction))
            conn.commit()
            conn.close()
            user = interaction.client.get_user(self.user)
            if user:
                await user.send(f"Your deposit of **{self.amount:,}** tokens has been **denied**.")
            await interaction.response.edit_message(content="Deposit denied.", view=None)


class TransactionHistoryView(discord.ui.View):
    def __init__(self, user_id, current_page, total_pages):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.current_page = current_page
        self.total_pages = total_pages
        self.per_page = 5

        if self.total_pages > 1:
            self.add_item(discord.ui.Button(label="Previous", style=discord.ButtonStyle.primary, disabled=(self.current_page == 1), custom_id=f"prev_{self.user_id}"))
            self.add_item(discord.ui.Button(label="Next", style=discord.ButtonStyle.primary, disabled=(self.current_page == self.total_pages), custom_id=f"next_{self.user_id}"))

    async def get_page_embed(self, page):
        conn = sqlite3.connect("twilightcasino.db")
        cursor = conn.cursor()
        cursor.execute("""SELECT type, amount, status, datetime FROM transactions WHERE user = ? ORDER BY datetime DESC LIMIT ? OFFSET ?""", (self.user_id, self.per_page, (page - 1) * self.per_page))
        transactions = cursor.fetchall()
        conn.close()

        embed = discord.Embed(title=f"Transaction History (Page {page}/{self.total_pages})", color=discord.Color.blurple())
        if transactions:
            for type, amount, status, datetime in transactions:
                embed.add_field(name=f"{type.capitalize()} - {datetime}", value=f"Amount: {amount:,} Tokens\nStatus: {status.capitalize()}", inline=False)
        else:
            embed.description = "No transactions found for this page."
        return embed

    @discord.ui.button(style=discord.ButtonStyle.primary, label="Previous", disabled=True, custom_id="prev")
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 1:
            self.current_page -= 1
            button.disabled = self.current_page == 1
            embed = await self.get_page_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("You are already on the first page!", ephemeral=True)


    @discord.ui.button(style=discord.ButtonStyle.primary, label="Next", disabled=True, custom_id="next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages:
            self.current_page += 1
            button.disabled = self.current_page == self.total_pages
            embed = await self.get_page_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)

        else:
            await interaction.response.send_message("You are already on the last page!", ephemeral=True)