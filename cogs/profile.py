import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO, fileIO
from collections import namedtuple, defaultdict
from datetime import datetime
from random import randint
from copy import deepcopy
from .utils import checks
from __main__ import send_cmd_help
import os
import time
import logging


class AccountError(Exception):
    pass

class AccountAlreadyExists(AccountError):
    pass

class NoAccount(AccountError):
    pass

class InsufficientBalance(AccountError):
    pass

class NegativeValue(AccountError):
    pass

class SameSenderAndReceiver(AccountError):
    pass

class Accounts:
    def __init__(self, bot):
        self.accounts = dataIO.load_json("data/fakin/profile.json")
        self.bot = bot

    def create_account(self, user):
        server = user.server
        if not self.account_exists(user):
            if server.id not in self.accounts:
                self.accounts[server.id] = {}
            if user.id in self.accounts: # Legacy account
                assets = self.accounts[user.id]["assets"]
            else:
                assets = 0
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            account = {"name" : user.name, "cmdr": "_____", "assets" : assets, "powerplay" : "_____",
                       "superpower":"_____","fedrank":"None", "emprank":"None", "combat":"_____","trade":"_____",
                       "explore":"_____","location":"____",
                       "ships": "None",
                        "created_at" : timestamp}
            self.accounts[server.id][user.id] = account

            self._save_profile()
            return self.get_account(user)
        else:
            raise AccountAlreadyExists

    def account_exists(self, user):
        try:
            self._get_account(user)
        except NoAccount:
            return False
        return True

    def set_credits(self, user, amount):
        server = user.server
        if amount < 0:
            raise NegativeValue
        account = self._get_account(user)
        account["assets"] = amount
        self.accounts[server.id][user.id] = account
        self._save_profile()

    def set_ships(self,user,ship):
        server = user.server
        account = self._get_account(user)
        account["ships"] = ship
        self.accounts[server.id][user.id] = account
        self._save_profile()

    def set_cmdr(self, user, cmdrname):
        server = user.server
        account = self._get_account(user)
        account["cmdr"] = cmdrname
        self.accounts[server.id][user.id] = account
        self._save_profile()

    def set_combat(self,user,combat):
        server = user.server
        account = self._get_account(user)
        account["combat"] = combat
        self.accounts[server.id][user.id] = account
        self._save_profile()

    def set_trade(self,user,trade):
        server = user.server
        account = self._get_account(user)
        account["trade"] = trade
        self.accounts[server.id][user.id] = account
        self._save_profile()

    def set_explore(self,user,explore):
        server = user.server
        account = self._get_account(user)
        account["explore"] = explore
        self.accounts[server.id][user.id] = account
        self._save_profile()

    def set_location(self,user,location):
        server = user.server
        account = self._get_account(user)
        account["location"] = location
        self.accounts[server.id][user.id] = account
        self._save_profile()

    def set_powerplay(self, user, powerplay):
        server = user.server
        account = self._get_account(user)
        account["powerplay"] = powerplay
        self.accounts[server.id][user.id] = account
        self._save_profile()

    def set_superpower(self,user,superpower):
        server = user.server
        account = self._get_account(user)
        account["superpower"] = superpower
        self.accounts[server.id][user.id] = account
        self._save_profile()

    def set_fedrank(self,user,fedrank):
        server = user.server
        account = self._get_account(user)
        account["fedrank"] = fedrank
        self.accounts[server.id][user.id] = account
        self._save_profile()

    def set_emprank(self,user,emprank):
        server = user.server
        account = self._get_account(user)
        account["emprank"] = emprank
        self.accounts[server.id][user.id] = account
        self._save_profile()

    def wipe_profile(self, server):
        self.accounts[server.id] = {}
        self._save_profile()

    def get_server_accounts(self, server):
        if server.id in self.accounts:
            raw_server_accounts = deepcopy(self.accounts[server.id])
            accounts = []
            for k, v in raw_server_accounts.items():
                v["id"] = k
                v["server"] = server
                acc = self._create_account_obj(v)
                accounts.append(acc)
            return accounts
        else:
            return []

    def get_all_accounts(self):
        accounts = []
        for server_id, v in self.accounts.items():
            server = self.bot.get_server(server_id)
            if server is None:# Servers that have since been left will be ignored
                continue      # Same for users_id from the old profile format
            raw_server_accounts = deepcopy(self.accounts[server.id])
            for k, v in raw_server_accounts.items():
                v["id"] = k
                v["server"] = server
                acc = self._create_account_obj(v)
                accounts.append(acc)
        return accounts

    def get_assets(self, user):
        account = self._get_account(user)
        return account["assets"]

    def get_cmdr(self,user):
        account = self._get_account(user)
        return account["cmdr"]

    def get_ships(self,user):
        account = self._get_account(user)
        return account["ships"]

    def get_powerplay(self,user):
        account = self._get_account(user)
        return account["powerplay"]

    def get_superpower(self,user):
        account = self._get_account(user)
        return account["superpower"]

    def get_fedrank(self,user):
        account = self._get_account(user)
        return account["fedrank"]

    def get_emprank(self,user):
        account = self._get_account(user)
        return account["emprank"]

    def get_combat(self,user):
        account = self._get_account(user)
        return account["combat"]

    def get_trade(self,user):
        account = self._get_account(user)
        return account["trade"]

    def get_explore(self,user):
        account = self._get_account(user)
        return account["explore"]

    def get_location(self,user):
        account = self._get_account(user)
        return account["location"]

    def get_ships(self,user):
        account = self._get_account(user)
        return account["ships"]

    def get_account(self, user):
        acc = self._get_account(user)
        acc["id"] = user.id
        acc["server"] = user.server
        return self._create_account_obj(acc)



    def _create_account_obj(self, account):
        Account = namedtuple("Account", "id name "
        "assets cmdr created_at server powerplay superpower fedrank emprank combat trade explore location ships")
        return Account(
            id = account["id"],
            name = account["name"],
            cmdr = account["cmdr"],
            assets = account["assets"],
            powerplay = account["powerplay"],
            superpower = account["superpower"],
            fedrank = account["fedrank"],
            emprank = account["emprank"],
            combat = account["combat"],
            trade = account["trade"],
            explore = account["explore"],
            location = account["location"],
            ships = account["ships"],
            created_at = datetime.strptime(account["created_at"], "%Y-%m-%d %H:%M:%S"),
            server = account["server"],)

    def _save_profile(self):
        dataIO.save_json("data/fakin/profile.json", self.accounts)

    def _get_account(self, user):
        server = user.server
        try:
            return deepcopy(self.accounts[server.id][user.id])
        except KeyError:
            raise NoAccount

class Profile:
    """Profile

    Get rich and have fun with imaginary currency!"""

    def __init__(self, bot):
        global default_settings
        self.bot = bot
        self.profile = Accounts(bot)
        self.settings = fileIO("data/fakin/settings.json", "load")
        if "PAYDAY_TIME" in self.settings: #old format
            default_settings = self.settings
            self.settings = {}
        self.settings = defaultdict(lambda: default_settings, self.settings)
        self.payday_register = defaultdict(dict)
        self.slot_register = defaultdict(dict)

    @commands.group(name="profile", pass_context=True)
    async def _profile(self, ctx):
        """Accounts operations"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_profile.command(pass_context=True, no_pm=True)
    async def register(self, ctx):
        """Registers an account at the Simbad profile"""
        user = ctx.message.author
        try:
            account = self.profile.create_account(user)
            await self.bot.say("{} Account opened.".format(user.mention))
        except AccountAlreadyExists:
            await self.bot.say("{} You already have an account at the Simbad profile.".format(user.mention))

    @_profile.command(pass_context=True)
    async def cmdr(self,ctx,user: discord.Member=None):
        """Shows cmdr name of users.

        Defaults to yours."""
        if not user:
            user = ctx.message.author
            try:
                await self.bot.say("{} Your CMDR name is: {}".format(user.mention, self.profile.get_cmdr(user)))
            except NoAccount:
                await self.bot.say("{} You don't have an account at the Simbad profile."
                 " Type {}profile register to open one.".format(user.mention, ctx.prefix))
        else:
            try:
                await self.bot.say("{}'s CMDR name is {}".format(user.name, self.profile.get_cmdr(user)))
            except NoAccount:
                await self.bot.say("That does not have a profile yet.")

    @_profile.command(pass_context=True)
    async def location(self,ctx,user: discord.Member = None):
        """Shows cmdr general location and timezone

        Default to yours"""
        if not user:
            user = ctx.message.author
            try:
                await self.bot.say("{} Your location/timezone is at: {}".format(user.mention,self.profile.get_location(user)))
            except NoAccount:
                await self.bot.say("{} You don't have an account at the Simbad profile."
                 " Type {}profile register to open one.".format(user.mention, ctx.prefix))
        else:
            try:
                await self.bot.say("{}'s location/timezone is {}".format(user.name, self.profile.get_location(user)))
            except NoAccount:
                await self.bot.say("That does not have a profile yet.")

    @_profile.command(pass_context=True)
    async def info(self,ctx,user: discord.Member= None):
        """Displays all info from user's profile."""
        if not user:
            user = ctx.message.author
            try:
                msg = "{} \n".format(user.mention)
                msg += "**CMDR Name: **{}".format(self.profile.get_cmdr(user)) + "\n"
                msg += "**Current Assets: **{:,d}".format(self.profile.get_assets(user)) + "\n"
                msg += "**Powerplay Allegiance: **{}".format(self.profile.get_powerplay(user) + "\n")
                msg += "**Superpower Allegiance: **{}".format(self.profile.get_superpower(user) + "\n")
                msg += "**Federal Navy Rank: ** {}".format(self.profile.get_fedrank(user) + "\n")
                msg += "**Empire Navy Rank: ** {}".format(self.profile.get_emprank(user) + "\n")
                msg += "**Combat Rank: ** {}".format(self.profile.get_combat(user) + "\n")
                msg += "**Trade Rank: ** {}".format(self.profile.get_trade(user) + "\n")
                msg += "**Exploration Rank: ** {}".format(self.profile.get_explore(user) + "\n")
                msg += "**Ships: ** {}".format(self.profile.get_ships(user) + "\n")
                await self.bot.say(msg)
            except NoAccount:
                await self.bot.say("That does not have a profile yet.")
        else:
            try:
                msg = "\n"
                msg += "**CMDR Name: **{}".format(self.profile.get_cmdr(user)) + "\n"
                msg += "**Current Assets: **{:,d}".format(self.profile.get_assets(user)) + "\n"
                msg += "**Powerplay Allegiance: **{}".format(self.profile.get_powerplay(user)) + "\n"
                msg += "**Superpower Allegiance: **{}".format(self.profile.get_superpower(user) + "\n")
                msg += "**Federal Navy Rank: ** {}".format(self.profile.get_fedrank(user) + "\n")
                msg += "**Empire Navy Rank: ** {}".format(self.profile.get_emprank(user) + "\n")
                msg += "**Combat Rank: ** {}".format(self.profile.get_combat(user) + "\n")
                msg += "**Trade Rank: ** {}".format(self.profile.get_trade(user) + "\n")
                msg += "**Exploration Rank: ** {}".format(self.profile.get_explore(user) + "\n")
                msg += "**Ships: ** {}".format(self.profile.get_ships(user) + "\n")
                await self.bot.say(msg)
            except NoAccount:
                await self.bot.say("User doesn't have an account yet.")

    @_profile.command(pass_context= True)
    async def superpower(self,ctx, user: discord.Member= None):
        """Shows user's superpower allegiance

        Defaults to yours"""
        if not user:
            user = ctx.message.author
            try:
                await self.bot.say(
                    "{} Your superpower allegiance is: {}".format(user.mention, self.profile.get_superpower(user)))
            except NoAccount:
                await self.bot.say("{} You don't have an account at the Simbad profile."
                                   " Type {}profile register to open one.".format(user.mention, ctx.prefix))
        else:
            try:
                await self.bot.say(
                    "{}'s superpower allegiance is {}".format(user.name, self.profile.get_superpower(user)))
            except NoAccount:
                await self.bot.say("That does not have a profile yet.")

    @_profile.command(pass_context=True)
    async def powerplay(self,ctx, user: discord.Member=None):
        """Shows user's powerplay allegiance

        Defaults to yours"""
        if not user:
            user = ctx.message.author
            try:
                await self.bot.say("{} Your powerplay allegiance is: {}".format(user.mention, self.profile.get_powerplay(user)))
            except NoAccount:
                await self.bot.say("{} You don't have an account at the Simbad profile."
                                   " Type {}profile register to open one.".format(user.mention, ctx.prefix))
        else:
            try:
                await self.bot.say("{}'s powerplay allegiance is {}".format(user.name, self.profile.get_powerplay(user)))
            except NoAccount:
                await self.bot.say("That does not have a profile yet.")

    @_profile.command(pass_context=True)
    async def assets(self, ctx, user : discord.Member=None):
        """Shows assets of user.

        Defaults to yours."""
        if not user:
            user = ctx.message.author
            try:
                await self.bot.say("{} Your current assets are at: {:,d}".format(user.mention, self.profile.get_assets(user)))
            except NoAccount:
                await self.bot.say("{} You don't have an account at the Simbad profile."
                 " Type {}profile register to open one.".format(user.mention, ctx.prefix))
        else:
            try:
                await self.bot.say("{}'s assets is {:,d}".format(user.name, self.profile.get_assets(user)))
            except NoAccount:
                await self.bot.say("That user does not have a profile yet.")

    @_profile.command(pass_context=True)
    async def combat(self, ctx, user : discord.Member=None):
        """Shows combat rank of user.

        Defaults to yours."""
        if not user:
            user = ctx.message.author
            try:
                await self.bot.say("{} Your combat rank is: {}".format(user.mention, self.profile.get_combat(user)))
            except NoAccount:
                await self.bot.say("{} You don't have an account at the Simbad profile."
                 " Type {}profile register to open one.".format(user.mention, ctx.prefix))
        else:
            try:
                await self.bot.say("{}'s combat rank is {}".format(user.name, self.profile.get_combat(user)))
            except NoAccount:
                await self.bot.say("That user does not have a profile yet.")

    @_profile.command(pass_context=True)
    async def trade(self, ctx, user : discord.Member=None):
        """Shows combat rank of user.

        Defaults to yours."""
        if not user:
            user = ctx.message.author
            try:
                await self.bot.say("{} Your trade rank is: {}".format(user.mention, self.profile.get_trade(user)))
            except NoAccount:
                await self.bot.say("{} You don't have an account at the Simbad profile."
                 " Type {}profile register to open one.".format(user.mention, ctx.prefix))
        else:
            try:
                await self.bot.say("{}'s trade rank is {}".format(user.name, self.profile.get_trade(user)))
            except NoAccount:
                await self.bot.say("That user does not have a profile yet.")

    @_profile.command(pass_context=True)
    async def explore(self, ctx, user : discord.Member=None):
        """Shows combat rank of user.

        Defaults to yours."""
        if not user:
            user = ctx.message.author
            try:
                await self.bot.say("{} Your exploration rank is: {}".format(user.mention, self.profile.get_explore(user)))
            except NoAccount:
                await self.bot.say("{} You don't have an account at the Simbad profile."
                 " Type {}profile register to open one.".format(user.mention, ctx.prefix))
        else:
            try:
                await self.bot.say("{}'s exploration rank is {}".format(user.name, self.profile.get_explore(user)))
            except NoAccount:
                await self.bot.say("That user does not have a profile yet.")

    @commands.group(name="proset",pass_context=True)
    async def _proset(self,ctx):
        """Profile settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_proset.command(name="cmdr", pass_context=True)
    async def _cmdr(self,ctx, cmdrname : str):
        """Sets CMDR name of user's profile account"""
        author = ctx.message.author
        try:
            self.profile.set_cmdr(author,cmdrname)
            logger.info("{}({}) set their CMDR name to {}".format(author.name,author.id,cmdrname))
            await self.bot.say("You've set your CMDR name to {}. **If you have more than one word in your CMDR name, put it in double quotes.**".format(cmdrname))
        except NoAccount:
            await self.bot.say("You do not have a profile yet.")

    @_proset.command(name="location", pass_context=True)
    async def _location(self,ctx,*,location):
        """Set your location/timezone.

        Never give out your address"""
        author = ctx.message.author
        try:
            self.profile.set_location(author,location)
            logger.info("{}({}) set their location to {}".format(author.name,author.id,location))
            await self.bot.say("You've set your location/timezone to {}. **Please only your state/country/timezone. Never give out your address. __I repeat: Never give out your address__**".format(location))
        except NoAccount:
            await self.bot.say("You do not have a profile yet.")

    @_proset.command(name="ships", pass_context=True)
    async def _ships(self,ctx,*,ship):
        """Set what ships you own!

        Even give them a nickname. Anything you type after the "shipadd" will be included in the list."""
        author = ctx.message.author
        try:
            self.profile.set_ships(author,ship)
            logger.info("{}({}) set their ship listing to {}".format(author.name,author.id,ship))
            await self.bot.say("You've set your ship list to: {}".format(ship))
        except NoAccount:
            await self.bot.say("You do not have a profile yet.")

    @_proset.command(name="combat", pass_context=True)
    async def _combat(self,ctx,combat_number):
        """
        Set combat rank.

        1. Harmless
        2. Mostly Harmless
        3. Novice
        4. Competent
        5. Expert
        6. Master
        7. Dangerous
        8. Deadly
        9. Elite
        """
        clist = [("1","Harmless"),
                 ("2","Mostly Harmless"),
                 ("3","Novice"),
                 ("4","Competent"),
                 ("5","Expert"),
                 ("6","Master"),
                 ("7","Dangerous"),
                 ("8","Deadly"),
                 ("9","Elite"),]
        author = ctx.message.author
        try:
            for x, y in clist:
                if combat_number == x:
                    self.profile.set_combat(author, y)
                    await self.bot.say("You've set your combat rank to {}.".format(y))
        except NoAccount:
            await self.bot.say("User does not have a profile account yet.")

    @_proset.command(name="trade", pass_context=True)
    async def _trade(self,ctx,trade_number):
        """
        Set combat rank.

        1. Penniless
        2. Mostly Penniless
        3. Peddler
        4. Dealer
        5. Merchant
        6. Broker
        7. Entrepreneur
        8. Tycoon
        9. Elite
        """
        tlist = [("1", "Penniless"),
                 ("2", "Mostly Penniless"),
                 ("3", "Peddler"),
                 ("4", "Dealer"),
                 ("5", "Merchant"),
                 ("6", "Broker"),
                 ("7", "Entrepreneur"),
                 ("8", "Tycoon"),
                 ("9", "Elite")]
        author = ctx.message.author
        try:
            for x, y in tlist:
                if trade_number == x:
                    self.profile.set_trade(author, y)
                    await self.bot.say("You've set your trade rank to {}.".format(y))
        except NoAccount:
            await self.bot.say("User does not have a profile account yet.")

    @_proset.command(name="explore", pass_context=True)
    async def _explore(self,ctx,explore_number):
        """
        Set combat rank.

        1. Aimless
        2. Mostly Aimless
        3. Scout
        4. Surveyor
        5. Trailblazer
        6. Pathfinder
        7. Ranger
        8. Pioneer
        9. Elite
        """
        elist = [("1","Aimless"),
                 ("2","Mostly Aimless"),
                 ("3","Scout"),
                 ("4","Surveyor"),
                 ("5","Trailblazer"),
                 ("6","Pathfinder"),
                 ("7","Ranger"),
                 ("8","Pioneer"),
                 ("9","Elite"),]
        author = ctx.message.author
        try:
            for x, y in elist:
                if explore_number == x:
                    self.profile.set_explore(author, y)
                    await self.bot.say("You've set your exploration rank to {}.".format(y))
        except NoAccount:
            await self.bot.say("User does not have a profile account yet.")

    @_proset.command(name="superpower", pass_context=True)
    async def _superpower(self,ctx,superpower_number):
        """
        Set superpower allegiance.

        1. Independent
        2. Alliance
        3. Empire
        4. Federation"""
        splist = [("1", "Independent"),("2","Alliance"),("3","Empire"),("4","Federation")]
        author = ctx.message.author
        try:
            for x,y in splist:
                if superpower_number == x:
                    self.profile.set_superpower(author,y)
                    await self.bot.say("You've set your superpower allegiance to {}.".format(y))
        except NoAccount:
            await self.bot.say("User does not have a profile account yet.")

    @_proset.command(name="fed",pass_context=True)
    async def _fed(self,ctx, fedrank_number):
        """Set Federal Navy Rank

        0. None
        1. Recruit
        2. Cadet
        3. Midshipman
        4. Petty Officer
        5. Chief Petty Officer
        6. Warrant Officer
        7. Ensign
        8. Lieutenant
        9. Lieutenant Commander
        10. Post Commander
        11. Post Captain
        12. Rear Admiral
        13. Vice Admiral
        14. Admiral"""
        fedlist = [("0","None"),("1","Recruit"),("2","Cadet"),("3","Midshipman"),("4","Petty Officer"),("5","Chief Petty Officer"),("6","Warrant Officer"),("7","Ensign"),("8","Lieutenant"),("9","Lieutenant Commander"),("10","Post Commander"),("11","Post Captain"),("12","Rear Admiral"),("13","Vice Admiral"),("14","Admiral")]
        author = ctx.message.author
        try:
            for x, y in fedlist:
                if fedrank_number == x:
                    self.profile.set_fedrank(author,y)
                    await self.bot.say("You've set your Federation Navy rank to {}.".format(y))
        except NoAccount:
            await self.bot.say("User does not have a profile yet.")

    @_proset.command(name = "emp", pass_context=True)
    async def _emp(self,ctx, emprank_number):
        """Set Empire Navy Rank

        0. None
        1. Outsider
        2. Serf
        3. Master
        4. Squire
        5. Knight
        6. Lord
        7. Baron
        8. Viscount
        9. Count
        10. Earl
        11. Marquis
        12. Duke
        13. Prince
        14. King"""
        fedlist = [("0","None"),("1","Outsider"),("2","Serf"),("3","Master"),("4","Squire"),("5","Knight"),("6","Lord"),("7","Baron"),("8","Viscount"),("9","Count"),("10","Earl"),("11","Marquis"),("12","Duke"),("13","Prince"),("14","King")]
        author = ctx.message.author
        try:
            for x, y in fedlist:
                if emprank_number == x:
                    self.profile.set_emprank(author,y)
                    await self.bot.say("You've set your Empire Navy rank to {}.".format(y))
        except NoAccount:
            await self.bot.say("User does not have a profile yet.")

    @_proset.command(name="powerplay", pass_context=True)
    async def _powerplay(self,ctx,powerplay_number):
        """Set powerplay allegiance.

        1. A. Lavigny-Duval
        2. Aisling Duval
        3. Archon Delaine
        4. Denton Patreus
        5. Edmund Mahon
        6. Felicia Winters
        7. Li Yong-Rui
        8. Pranav Antal
        9. Zachary Hudson
        10. Zemina Torval"""
        pplist = [("1","A Lavigny-Duval"),("2","Aisling Duval"),("3","Archon Delaine"),("4","Denton Patreus"),("5","Edmund Mahon"),("6","Felicia Winters"),("7","Li Yong-Rui"),("8", "Pranav Antal"),("9","Zachary Hudson"),("10","Zemina Torval")]
        author = ctx.message.author
        try:
            for x,y in pplist:
                if powerplay_number == x:
                    self.profile.set_powerplay(author, y)
                    await self.bot.say("You've set your powerplay allegiance to {}".format(y))
        except NoAccount:
            await self.bot.say("You do not have a profile yet.")

    @_proset.command(name="assets", pass_context=True)
    async def _assets(self, ctx, sum : int):
        """Sets current assets of user's profile account. Do not use commas."""
        author = ctx.message.author
        try:
            self.profile.set_credits(author, sum)
            logger.info("{}({}) set {} credits to {} ({})".format(author.name, author.id, sum, author.name, author.id))
            await self.bot.say("{}'s credits have been set to {:,d}".format(author.name, sum))
        except NoAccount:
            await self.bot.say("You do not have a profile yet.")

def check_folders():
    if not os.path.exists("data/economy"):
        print("Creating data/economy folder...")
        os.makedirs("data/economy")

def check_files():

    f = "data/fakin/settings.json"
    if not fileIO(f, "check"):
        print("Creating default economy's settings.json...")
        fileIO(f, "save", {})

    f = "data/fakin/profile.json"
    if not fileIO(f, "check"):
        print("Creating empty profile.json...")
        fileIO(f, "save", {})

def setup(bot):
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("simbad.economy")
    if logger.level == 0: # Prevents the logger from being loaded again in case of module reload
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename='data/fakin/economy.log', encoding='utf-8', mode='a')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    bot.add_cog(Profile(bot))