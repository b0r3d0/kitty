import discord
from discord.ext import commands

class Info:
    """Commands to express information"""
    def __init__(self,bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    async def userinfo(self, ctx, user : discord.Member = None):
        """Shows users's informations"""
        author = ctx.message.author
        if not user:
            user = author
        roles = [x.name for x in user.roles if x.name != "@everyone"]
        if not roles: roles = ["None"]
        data = "```python\n"
        data += "Name: {}\n".format(user.name)
        data += "ID: {}\n".format(user.id)
        passed = (ctx.message.timestamp - user.created_at).days
        data += "Created: {} ({} days ago)\n".format(user.created_at, passed)
        passed = (ctx.message.timestamp - user.joined_at).days
        data += "Joined: {} ({} days ago)\n".format(user.joined_at, passed)
        data += "Roles: {}\n".format(", ".join(roles))
        data += "Avatar: {}\n".format(user.avatar_url)
        data += "```"
        await self.bot.say(data)


    @commands.command(pass_context=True, no_pm=True)
    async def serverinfo(self, ctx):
        """Shows server's informations"""
        server = ctx.message.server
        online = str(len([m.status for m in server.members if str(m.status) == "online" or str(m.status) == "idle"]))
        total_users = str(len(server.members))
        text_channels = len([x for x in server.channels if str(x.type) == "text"])
        voice_channels = len(server.channels) - text_channels

        data = "```python\n"
        data += "Name: {}\n".format(server.name)
        data += "ID: {}\n".format(server.id)
        data += "Region: {}\n".format(server.region)
        data += "Users: {}/{}\n".format(online, total_users)
        data += "Text channels: {}\n".format(text_channels)
        data += "Voice channels: {}\n".format(voice_channels)
        data += "Roles: {}\n".format(len(server.roles))
        passed = (ctx.message.timestamp - server.created_at).days
        data += "Created: {} ({} days ago)\n".format(server.created_at, passed)
        data += "Owner: {}\n".format(server.owner)
        data += "Icon: {}\n".format(server.icon_url)
        data += "```"
        await self.bot.say(data)


    @commands.command()
    async def simbad(self):
        """Provides a link to our website and forums."""
        await self.bot.say(
            "\nOur website is http://simbadelite.com/"
            "\nOur forum is http://forums.simbadelite.com/")

    @commands.command()
    async def mvp(self,name):
        """Indicates whether a CMDR has achieved MVP (ex. ?mvp Leavism)"""
        name = name.lower()
        list = ["smidget", "leavism", "marsharpe", "blacksabre","dangofett" ,"havoc235"]
        if name == "list":
            await self.bot.say(', '.join(list))
        if name in list:
            await self.bot.say("Yes, " + name + " has been a recognized as valuable member of our group!")
        elif name not in list and name != "list":
            await self.bot.say("This CMDR has yet to be recognized for their activity. Please make sure you've spelled the CMDR name correctly.")

def setup(bot):
    n = Info(bot)
    bot.add_cog(n)