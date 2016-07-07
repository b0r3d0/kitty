import discord
from discord.ext import commands
from cogs.utils import checks
from __main__ import set_cog, send_cmd_help, settings
from .utils.dataIO import fileIO

import importlib
import traceback
import logging
import asyncio
import threading
import datetime
import glob
import os
import time
import aiohttp
import copy

log = logging.getLogger("simbad.owner")


class CogNotFoundError(Exception):
    pass


class CogLoadError(Exception):
    pass


class NoSetupError(CogLoadError):
    pass


class CogUnloadError(Exception):
    pass


class OwnerUnloadWithoutReloadError(CogUnloadError):
    pass


class Owner:
    """All owner-only commands that relate to debug bot operations.
    """

    def __init__(self, bot):
        super(Owner, self).__init__()
        self.bot = bot
        self.setowner_lock = False
        self.disabled_commands = fileIO("data/simbad/disabled_commands.json", "load")
        self.channels = fileIO("data/channellogger/channels.json", "load")
        self.session = aiohttp.ClientSession(loop=self.bot.loop)

    def __unload(self):
        self.session.close()

    @commands.command()
    @checks.is_owner()
    async def load(self, *, module: str):
        """Loads a module

        Example: load mod"""
        module = module.strip()
        if "cogs." not in module:
            module = "cogs." + module
        try:
            self._load_cog(module)
        except CogNotFoundError:
            await self.bot.say("That module could not be found.")
        except CogLoadError as e:
            log.exception(e)
            traceback.print_exc()
            await self.bot.say("There was an issue loading the module. Check"
                               " your console or logs for more information.")
        except Exception as e:
            log.exception(e)
            traceback.print_exc()
            await self.bot.say('Module was found and possibly loaded but '
                               'something went wrong. Check your console '
                               'or logs for more information.')
        else:
            set_cog(module, True)
            #await self.disable_commands()
            await self.bot.say("Module enabled.")

    @commands.group(invoke_without_command=True)
    @checks.is_owner()
    async def unload(self, *, module: str):
        """Unloads a module

        Example: unload mod"""
        module = module.strip()
        if "cogs." not in module:
            module = "cogs." + module
        if not self._does_cogfile_exist(module):
            await self.bot.say("That module file doesn't exist. I will not"
                               " turn off autoloading at start just in case"
                               " this isn't supposed to happen.")
        else:
            set_cog(module, False)
        try:  # No matter what we should try to unload it
            self._unload_cog(module)
        except OwnerUnloadWithoutReloadError:
            await self.bot.say("I cannot allow you to unload the Owner plugin"
                               " unless you are in the process of reloading.")
        except CogUnloadError as e:
            log.exception(e)
            traceback.print_exc()
            await self.bot.say('Unable to safely disable that module.')
        else:
            await self.bot.say("Module disabled.")

    @unload.command(name="all")
    @checks.is_owner()
    async def unload_all(self):
        """Unloads all modules"""
        cogs = self._list_cogs()
        still_loaded = []
        for cog in cogs:
            set_cog(cog, False)
            try:
                self._unload_cog(cog)
            except OwnerUnloadWithoutReloadError:
                pass
            except CogUnloadError as e:
                log.exception(e)
                traceback.print_exc()
                still_loaded.append(cog)
        if still_loaded:
            still_loaded = ", ".join(still_loaded)
            await self.bot.say("I was unable to unload some cogs: "
                "{}".format(still_loaded))
        else:
            await self.bot.say("All cogs are now unloaded.")

    @checks.is_owner()
    @commands.command(name="reload")
    async def _reload(self, module):
        """Reloads a module

        Example: reload audio"""
        if "cogs." not in module:
            module = "cogs." + module

        try:
            self._unload_cog(module, reloading=True)
        except:
            pass

        try:
            self._load_cog(module)
        except CogNotFoundError:
            await self.bot.say("That module cannot be found.")
        except NoSetupError:
            await self.bot.say("That module does not have a setup function.")
        except CogLoadError as e:
            log.exception(e)
            traceback.print_exc()
            await self.bot.say("That module could not be loaded. Check your"
                               " console or logs for more information.")
        else:
            set_cog(module, True)
            #await self.disable_commands()
            await self.bot.say("Module reloaded.")

    @commands.group(name="set", pass_context=True)
    async def _set(self, ctx):
        """Changes Simbad Bot's global settings."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @_set.command(pass_context=True)
    async def owner(self, ctx):
        """Sets owner"""
        if settings.owner != "id_here":
            await self.bot.say("Owner ID has already been set.")
            return

        if self.setowner_lock:
            await self.bot.say("A set owner command is already pending.")
            return

        await self.bot.say("Confirm in the console that you're the owner.")
        self.setowner_lock = True
        t = threading.Thread(target=self._wait_for_answer,
                             args=(ctx.message.author,))
        t.start()

    @_set.command()
    @checks.is_owner()
    async def prefix(self, *prefixes):
        """Sets prefixes

        Must be separated by a space. Enclose in double
        quotes if a prefix contains spaces."""
        if prefixes == ():
            await self.bot.say("Example: setprefix [ ! ^ .")
            return

        self.bot.command_prefix = sorted(prefixes, reverse=True)
        settings.prefixes = sorted(prefixes, reverse=True)
        log.debug("Setting prefixes to:\n\t{}".format(settings.prefixes))

        if len(prefixes) > 1:
            await self.bot.say("Prefixes set")
        else:
            await self.bot.say("Prefix set")

    @_set.command(pass_context=True)
    @checks.is_owner()
    async def name(self, ctx, *, name):
        """Sets Simbad Bot's name"""
        name = name.strip()
        if name != "":
            await self.bot.edit_profile(settings.password, username=name)
            await self.bot.say("Done.")
        else:
            await send_cmd_help(ctx)

    @_set.command(pass_context=True, no_pm=True)
    @checks.is_owner()
    async def nickname(self, ctx, *, nickname=""):
        """Sets Simbad Bot's nickname

        Leaving this empty will remove it."""
        nickname = nickname.strip()
        if nickname == "":
            nickname = None
        try:
            await self.bot.change_nickname(ctx.message.server.me, nickname)
            await self.bot.say("Done.")
        except discord.Forbidden:
            await self.bot.say("I cannot do that, I lack the "
                "\"Change Nickname\" permission.")

    @_set.command(pass_context=True)
    @checks.is_owner()
    async def status(self, ctx, *, status=None):
        """Sets Simbad Bot's status

        Leaving this empty will clear it."""

        if status:
            status = status.strip()
            await self.bot.change_status(discord.Game(name=status))
            log.debug('Status set to "{}" by owner'.format(status))
        else:
            await self.bot.change_status(None)
            log.debug('status cleared by owner')
        await self.bot.say("Done.")

    @_set.command()
    @checks.is_owner()
    async def avatar(self, url):
        """Sets Simbad Bot's avatar"""
        try:
            async with self.session.get(url) as r:
                data = await r.read()
            await self.bot.edit_profile(settings.password, avatar=data)
            await self.bot.say("Done.")
            log.debug("changed avatar")
        except Exception as e:
            await self.bot.say("Error, check your console or logs for "
                               "more information.")
            log.exception(e)
            traceback.print_exc()

    @_set.command(name="token")
    @checks.is_owner()
    async def _token(self, token):
        """Sets Simbad Bot's login token"""
        if len(token) < 50:
            await self.bot.say("Invalid token.")
        else:
            settings.login_type = "token"
            settings.email = token
            settings.password = ""
            await self.bot.say("Token set. Restart me.")
            log.debug("Just converted to a bot account.")

    @commands.command()
    @checks.is_owner()
    async def shutdown(self):
        """Shuts down Simbad Bot"""
        await self.bot.logout()

    @commands.group(pass_context=True, no_pm=True)
    @checks.is_owner()
    async def modset(self, ctx):
        """Manages server administration settings."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            msg = "```"
            for k, v in settings.get_server(ctx.message.server).items():
                msg += str(k) + ": " + str(v) + "\n"
            msg += "```"
            await self.bot.say(msg)

    @modset.command(name="adminrole", pass_context=True, no_pm=True)
    async def _modset_adminrole(self, ctx, role_name: str):
        """Sets the admin role for this server, case insensitive."""
        server = ctx.message.server
        if server.id not in settings.servers:
            await self.bot.say("Remember to set modrole too.")
        settings.set_server_admin(server, role_name)
        await self.bot.say("Admin role set to '{}'".format(role_name))

    @modset.command(name="modrole", pass_context=True, no_pm=True)
    async def _modset_modrole(self, ctx, role_name: str):
        """Sets the mod role for this server, case insensitive."""
        server = ctx.message.server
        if server.id not in settings.servers:
            await self.bot.say("Remember to set adminrole too.")
        settings.set_server_mod(server, role_name)
        await self.bot.say("Mod role set to '{}'".format(role_name))

    @commands.command()
    async def uptime(self):
        """Shows Simbad Bot's uptime"""
        up = abs(self.bot.uptime - int(time.perf_counter()))
        up = str(datetime.timedelta(seconds=up))
        await self.bot.say("`Uptime: {}`".format(up))

    def _load_cog(self, cogname):
        if not self._does_cogfile_exist(cogname):
            raise CogNotFoundError(cogname)
        try:
            mod_obj = importlib.import_module(cogname)
            importlib.reload(mod_obj)
            self.bot.load_extension(mod_obj.__name__)
        except SyntaxError as e:
            raise CogLoadError(*e.args)
        except:
            raise

    def _unload_cog(self, cogname, reloading=False):
        if not reloading and cogname == "cogs.owner":
            raise OwnerUnloadWithoutReloadError(
                "Can't unload the owner plugin :P")
        try:
            self.bot.unload_extension(cogname)
        except:
            raise CogUnloadError

    def _list_cogs(self):
        cogs = glob.glob("cogs/*.py")
        clean = []
        for c in cogs:
            c = c.replace("/", "\\")  # Linux fix
            clean.append("cogs." + c.split("\\")[1].replace(".py", ""))
        return clean

    def _does_cogfile_exist(self, module):
        if "cogs." not in module:
            module = "cogs." + module
        if module not in self._list_cogs():
            return False
        return True

    def _wait_for_answer(self, author):
        print(author.name + " requested to be set as owner. If this is you, "
              "type 'yes'. Otherwise press enter.")
        print()
        print("*DO NOT* set anyone else as owner.")

        choice = "None"
        while choice.lower() != "yes" and choice == "None":
            choice = input("> ")

        if choice == "yes":
            settings.owner = author.id
            print(author.name + " has been set as owner.")
            self.setowner_lock = False
            self.owner.hidden = True
        else:
            print("setowner request has been ignored.")
            self.setowner_lock = False

    def _get_version(self):
        getversion = os.popen(r'git show -s HEAD --format="%cr|%s|%h"')
        getversion = getversion.read()
        version = getversion.split('|')
        return 'Last updated: ``{}``\nCommit: ``{}``\nHash: ``{}``'.format(
            *version)

    @commands.command(pass_context=True, no_pm=True)
    @checks.is_owner()
    async def logger(self, ctx):
        """Toggles logging for a channel"""
        channel = ctx.message.channel
        if channel.id not in self.channels:
            self.channels[channel.id] = True
        else:
            self.channels[channel.id] = not self.channels[channel.id]
        if self.channels[channel.id]:
            await self.bot.say('Logging enabled'
                               ' for {}'.format(channel.mention))
        else:
            await self.bot.say('Logging disabled'
                               ' for {}'.format(channel.mention))
        self.save_channels()

    def save_channels(self):
        fileIO('data/channellogger/channels.json', 'save', self.channels)

    def log(self, message):
        serverid = message.server.id
        channelid = message.channel.id
        if not os.path.exists('data/channellogger/{}'.format(serverid)):
            os.mkdir('data/channellogger/{}'.format(serverid))
        fname = 'data/channellogger/{}/{}.log'.format(serverid, channelid)
        with open(fname, 'a', errors='backslashreplace') as f:
            message = ("{0.timestamp} #{1.name} @{2.name}#{2.discriminator}: "
                       "{0.clean_content}\n".format(message, message.channel,
                                                    message.author))
            f.write(message)

    async def message_logger(self, message):
        enabled = self.channels.get(message.channel.id, False)
        if enabled:
            self.log(message)

    async def message_edit_logger(self, before, after):
        new_message = copy.deepcopy(after)
        new_content = ("EDIT: \nBefore: "
                       "{}\nAfter: {}".format(before.clean_content,
                                              after.clean_content))
        new_message.content = new_content
        await self.message_logger(new_message)

def check_folders():
    if not os.path.exists("data/channellogger"):
        os.mkdir("data/channellogger")

def check_files():
    if not os.path.isfile("data/simbad/disabled_commands.json"):
        print("Creating empty disabled_commands.json...")
        fileIO("data/simbad/disabled_commands.json", "save", [])
    if not os.path.exists("data/channellogger/channels.json"):
        fileIO("data/channellogger/channels.json", "save", {})

def setup(bot):
    check_folders()
    check_files()
    n = Owner(bot)
    bot.add_cog(n)
    bot.add_listener(n.message_logger, "on_message")
    bot.add_listener(n.message_edit_logger, 'on_message_edit')
