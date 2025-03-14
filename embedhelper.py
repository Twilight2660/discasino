import discord

twilight = "#4c16c9"

def genEmbed(title: str, description: str=None, footer: str=None) -> discord.Embed:
    if description:
        embed = discord.Embed(title=title, description=description, color=discord.Color.from_str(twilight))
    else:
        embed = discord.Embed(title=title, color=discord.Color.from_str(twilight))
    embed.set_author(name="Twilight Casino")
    if footer:
        embed.set_footer(text=footer)
    else:
        embed.set_footer(text="Twilight Casino, where fortunes are instantly earned!")
    return embed