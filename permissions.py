import discord

adminid = 1348204850248286260
logid = 1348204821286621184

async def checkEmployeePerms(interaction: discord.Interaction, message: str) -> bool:
    allowed_roles = ["Owner", "Pitboss", "Dealer"]
    user_roles = [role.name for role in interaction.user.roles]
    user = interaction.user.name
    print(f"{user} has roles: {user_roles}")
    if any(role.name in allowed_roles for role in interaction.user.roles):
        return True
    else:
        await interaction.response.send_message(content=f"You **do not have permission** to {message}.", ephemeral=True)

async def checkAdminPerms(interaction: discord.Interaction, message: str) -> bool:
    allowed_roles = ["Owner", "Pitboss"]
    user_roles = [role.name for role in interaction.user.roles]
    user = interaction.user.name
    print(f"{user} has roles: {user_roles}")
    if any(role.name in allowed_roles for role in interaction.user.roles):
        return True
    else:
        await interaction.response.send_message(content=f"You **do not have permission** to {message}.", ephemeral=True)
