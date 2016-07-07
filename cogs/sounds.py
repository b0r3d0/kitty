from discord.ext import commands
from __main__ import send_cmd_help
from .utils import checks
import random
from os import listdir
from os.path import isfile, join
import asyncio

class Animalsounds:
    def __init__(self, bot):
        self.bot = bot
        self.audio_player = False
        self.sound_base = 'data/sounds'
        #self.sound_base = 'data/sounds/'

    def voice_connected(self, server):
        if self.bot.is_voice_connected(server):
            return True
        return False

    def voice_client(self, server):
        return self.bot.voice_client_in(server)

    @commands.group(pass_context=True, no_pm=True, name='voice', aliases=['vc'],hidden=True)
    async def _vc(self, context):
        """[join/leave]"""
        if context.invoked_subcommand is None:
            await send_cmd_help(context)

    @_vc.command(hidden=True, pass_context=True, no_pm=True, name='join', aliases=['connect'],hidden=True)
    #@checks.serverowner_or_permissions()
    async def _join(self, context):
        """Joins your voice channel"""
        author = context.message.author
        server = context.message.server
        channel = author.voice_channel
        if not self.voice_connected(server):
            await self.bot.join_voice_channel(channel)

    @_vc.command(hidden=True, pass_context=True, no_pm=True, name='leave', aliases=['disconnect'],hidden=True)
    #@checks.serverowner_or_permissions()
    async def _leave(self, context):
        """Leaves your voice channel"""
        server = context.message.server
        if not self.voice_connected(server):
            return
        voice_client = self.voice_client(server)
        if self.audio_player:
            self.audio_player.stop()
        await voice_client.disconnect()

    @_vc.command(no_pm=True, name='stop')
    async def _stop(self):
        if self.audio_player:
            self.audio_player.stop()

    @commands.command(no_pm=True, pass_context=True, name='johncena', aliases=['cena'],hidden=True)
    async def _cena(self, context):
        animal = 'cena'
        kill = 8
        await self.sound_play(context, animal,kill)

    @commands.command(no_pm=True, pass_context=True, name='nootnoot', aliases=['pingu'],hidden=True)
    async def _meow(self, context):
        animal = 'pingu'
        kill = 1
        await self.sound_play(context, animal,kill)

    async def sound_init(self, server, path):
        sound = [f for f in listdir(path) if isfile(join(path, f))]
        path = '{}{}'.format(path, random.choice(sound))
        voice_client = self.voice_client(server)
        self.audio_player = voice_client.create_ffmpeg_player(path)

    async def sound_play(self, context, animal,kill:int):
        path = '{}/{}/'.format(self.sound_base, animal)
        server = context.message.server
        author = context.message.author
        channel = author.voice_channel
        if not self.voice_connected(server):
            await self.bot.join_voice_channel(channel)
        if not context.message.channel.is_private:
            if self.voice_connected(server) and not self.audio_player:
                await self.sound_init(server, path)
                self.audio_player.start()
                await asyncio.sleep(kill)
            elif self.audio_player:
                if not self.audio_player.is_playing():
                    await self.sound_init(server, path)
                    self.audio_player.start()
                    await asyncio.sleep(kill)
        if not self.voice_connected(server):
            return
        voice_client = self.voice_client(server)
        if self.audio_player:
            self.audio_player.stop()
        await voice_client.disconnect()

def setup(bot):
    n = Animalsounds(bot)
    bot.add_cog(n)