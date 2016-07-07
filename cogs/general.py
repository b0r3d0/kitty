import discord
from discord.ext import commands
from .utils.chat_formatting import *
from random import randint
from random import choice as randchoice
import datetime
import time
import aiohttp
import asyncio

settings = {"POLL_DURATION" : 7200}

class General:
    """General commands."""

    def __init__(self, bot):
        self.bot = bot
        self.stopwatches = {}
        self.ball = ["As I see it, yes", "It is certain", "It is decidedly so", "Most likely", "Outlook good",
                     "Signs point to yes", "Without a doubt", "Yes", "Yes – definitely", "You may rely on it", "Reply hazy, try again",
                     "Ask again later", "Better not tell you now", "Cannot predict now", "Concentrate and ask again",
                     "Don't count on it", "My reply is no", "My sources say no", "Outlook not so good", "Very doubtful"]
        self.poll_sessions = []

    @commands.command(hidden=True)
    async def ping(self):
        """Pong."""
        await self.bot.say("Pong.")

    @commands.command()
    async def choose(self, *choices):
        """Chooses between multiple choices.

        To denote multiple choices, you should use double quotes.
        """
        choices = [escape_mass_mentions(choice) for choice in choices]
        if len(choices) < 2:
            await self.bot.say('Not enough choices to pick from.')
        else:
            await self.bot.say(randchoice(choices))

    @commands.command(pass_context=True)
    async def roll(self, ctx, number : int = 100):
        """Rolls random number (between 1 and user choice)

        Defaults to 100.
        """
        author = ctx.message.author
        if number > 1:
            n = str(randint(1, number))
            return await self.bot.say("{} :game_die: {} :game_die:".format(author.mention, n))
        else:
            return await self.bot.say("{} Maybe higher than 1? ;P".format(author.mention))

    @commands.command(pass_context=True)
    async def flip(self, ctx, user : discord.Member=None):
        """Flips a coin... or a user.

        Defaults to coin.
        """
        if user != None:
            msg = ""
            if user.id == self.bot.user.id:
                user = ctx.message.author
                msg = "Nice try. You think this is funny? How about *this* instead:\n\n"
            char = "abcdefghijklmnopqrstuvwxyz"
            tran = "ɐqɔpǝɟƃɥᴉɾʞlɯuodbɹsʇnʌʍxʎz"
            table = str.maketrans(char, tran)
            name = user.name.translate(table)
            char = char.upper()
            tran = "∀qƆpƎℲפHIſʞ˥WNOԀQᴚS┴∩ΛMX⅄Z"
            table = str.maketrans(char, tran)
            name = name.translate(table)
            return await self.bot.say(msg + "(╯°□°）╯︵ " + name[::-1])
        else:
            return await self.bot.say("*flips a coin and... " + randchoice(["HEADS!*", "TAILS!*"]))


    @commands.command(no_pm=True, hidden=True)
    async def hug(self, user : discord.Member, intensity : int=1):
        """Because everyone likes hugs

        Up to 10 intensity levels."""
        name = " *" + user.name + "*"
        if intensity <= 0:
            msg = "(っ˘̩╭╮˘̩)っ" + name
        elif intensity <= 3:
            msg = "(っ´▽｀)っ" + name
        elif intensity <= 6:
            msg = "╰(*´︶`*)╯" + name
        elif intensity <= 9:
            msg = "(つ≧▽≦)つ" + name
        elif intensity >= 10:
            msg = "(づ￣ ³￣)づ" + name + " ⊂(´・ω・｀⊂)"
        await self.bot.say(msg)

    @commands.command(no_pm= True, hidden=True)
    async def fo(self, user : discord.Member, intensity : int=1):
        """Because we need this command

        Up to 3 intensity levels"""
        name = " *" + user.name + "*"
        if intensity <= 0:
            msg = "(っ˘̩╭╮˘̩)っ" + name
        elif intensity <= 1:
            msg = "༼✿◕ᗜ◕༽┌∩┐ " + name
        elif intensity <= 2:
            msg = "(ಠ_ಠ)┌∩┐ " + name
        elif intensity <= 3:
            msg = "┌∩┐(◣_◢)┌∩┐ " + name
        elif intensity <= 4:
            msg = "凸ಠ益ಠ)凸 " + name
        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    async def poll(self, ctx, *text):
        """Starts/stops a poll

        Usage example:
        poll Is this a poll?;Yes;No;Maybe
        poll stop"""
        message = ctx.message
        if len(text) == 1:
            if text[0].lower() == "stop":
                await self.endpoll(message)
                return
        if not self.getPollByChannel(message):
            check = " ".join(text).lower()
            if "@everyone" in check or "@here" in check:
                await self.bot.say("Nice try.")
                return
            p = NewPoll(message, self)
            if p.valid:
                self.poll_sessions.append(p)
                await p.start()
            else:
                await self.bot.say("poll question;option1;option2 (...)")
        else:
            await self.bot.say("A poll is already ongoing in this channel.")

    async def endpoll(self, message):
        if self.getPollByChannel(message):
            p = self.getPollByChannel(message)
            if p.author == message.author.id: # or isMemberAdmin(message)
                await self.getPollByChannel(message).endPoll()
            else:
                await self.bot.say("Only admins and the author can stop the poll.")
        else:
            await self.bot.say("There's no poll ongoing in this channel.")

    def getPollByChannel(self, message):
        for poll in self.poll_sessions:
            if poll.channel == message.channel:
                return poll
        return False

    async def check_poll_votes(self, message):
        if message.author.id != self.bot.user.id:
            if self.getPollByChannel(message):
                    self.getPollByChannel(message).checkAnswer(message)

class NewPoll():
    def __init__(self, message, main):
        self.channel = message.channel
        self.author = message.author.id
        self.client = main.bot
        self.poll_sessions = main.poll_sessions
        msg = message.content[6:]
        msg = msg.split(";")
        if len(msg) < 2: # Needs at least one question and 2 choices
            self.valid = False
            return None
        else:
            self.valid = True
        self.already_voted = []
        self.question = msg[0]
        msg.remove(self.question)
        self.answers = {}
        i = 1
        for answer in msg: # {id : {answer, votes}}
            self.answers[i] = {"ANSWER" : answer, "VOTES" : 0}
            i += 1

    async def start(self):
        msg = "**POLL STARTED!**\n\n{}\n\n".format(self.question)
        for id, data in self.answers.items():
            msg += "{}. *{}*\n".format(id, data["ANSWER"])
        msg += "\nType the number to vote! \nThe default duration of a poll is 120 minutes. Remember to end the poll with ?poll stop"
        await self.client.send_message(self.channel, msg)
        await asyncio.sleep(settings["POLL_DURATION"])
        if self.valid:
            await self.endPoll()

    async def endPoll(self):
        self.valid = False
        msg = "**POLL ENDED!**\n\n{}\n\n".format(self.question)
        for data in self.answers.values():
            msg += "*{}* - {} votes\n".format(data["ANSWER"], str(data["VOTES"]))
        await self.client.send_message(self.channel, msg)
        self.poll_sessions.remove(self)

    def checkAnswer(self, message):
        try:
            i = int(message.content)
            if i in self.answers.keys():
                if message.author.id not in self.already_voted:
                    data = self.answers[i]
                    data["VOTES"] += 1
                    self.answers[i] = data
                    self.already_voted.append(message.author.id)
        except ValueError:
            pass


def setup(bot):
    n = General(bot)
    bot.add_listener(n.check_poll_votes, "on_message")
    bot.add_cog(n)
