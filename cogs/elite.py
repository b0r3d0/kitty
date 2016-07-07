from discord.ext import commands
import urllib.request
import json
import math
from .utils import checks
from __main__ import send_cmd_help, settings
from .utils.dataIO import fileIO, dataIO

class Elite():
    def __init__(self,bot):
        self.bot = bot
        self.cmdr_list = dataIO.load_json("data/mod/cmdr.json")

    @commands.command()
    async def dist(self, *, everything):
        """Indicates distance between two systems. (ex. ?dist HR 1257, HR 1254)"""
        try:
            sys1, sys2 = everything.split(", ")
            sys1plus = sys1.replace(" ", "+")
            sys2plus = sys2.replace(" ", "+")
            base1 = 'https://www.edsm.net/api-v1/system?sysname=' + sys1plus + '&coords=1'
            base2 = 'https://www.edsm.net/api-v1/system?sysname=' + sys2plus + '&coords=1'
            readit1 = urllib.request.urlopen(base1)
            readit2 = urllib.request.urlopen(base2)
            dataedsm1 = json.loads(readit1.read().decode('utf-8'))
            dataedsm2 = json.loads(readit2.read().decode('utf-8'))
            datax1, datay1, dataz1 = dataedsm1['coords']['x'], dataedsm1['coords']['y'], dataedsm1['coords']['z']
            datax2, datay2, dataz2 = dataedsm2['coords']['x'], dataedsm2['coords']['y'], dataedsm2['coords']['z']
            x = float(datax2 - datax1)
            y = float(datay2 - datay1)
            z = float(dataz2 - dataz1)
            distance = math.sqrt(x * x + y * y + z * z)
            await self.bot.say("The distance between " + sys1 + " and " + sys2 + " is " + "{0:.2F}".format(distance) + "ly.")
            readit1.close()
            readit2.close()
        except TypeError:
            await self.bot.say("**ERROR!** Please make sure you spelled the systems correctly. Not every system has been recorded, so not every system will work with this command. ")
        except ValueError:
            await self.bot.say("**ERROR!** There needs to be a space after the comma!")

    @commands.group(pass_context=True)
    async def member(self, ctx):
        """Checks if a CMDR is part of Simbad"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @member.command(name="check")
    async def _member_check(self, cmdr: str):
        cmdr = cmdr.lower()
        if cmdr not in self.cmdr_list["members"]:
            await self.bot.say("Nope. Make sure you've spelled the CMDR name correctly and that CMDR names with more than one word are put into double quotes."
                               "(ex. ?member check \"b. horn\") **If your CMDR name isn't added to the command yet, contact an admin.**")
        else:
            await self.bot.say("Yes. " +cmdr +" is a member of Simbad!")

    @member.command(name="add")
    @checks.recruiter_or_permissions(manage_messages=True)
    async def _member_add(self, cmdra: str):
        if cmdra.lower() not in self.cmdr_list["members"]:
            self.cmdr_list["members"].append(cmdra)
            fileIO("data/mod/cmdr.json","save", self.cmdr_list)
            await self.bot.say("CMDR " + cmdra + " has been added to the command.")


    @commands.command()
    async def ship(self,*,shipname):
        """Provides ship price and coriolis link (ex. ?ship federal corvette)"""
        shipname = shipname.lower()
        corio = [("adder", "87,810", "https://coriolis.io/outfit/adder/"),
                 ("anaconda", "146,969,450", "https://coriolis.io/outfit/anaconda/"),
                 ("conda", "146,969,450", "https://coriolis.io/outfit/anaconda/"),
                 ("asp explorer", "6,661,150", "https://coriolis.io/outfit/asp/"),
                 ("asp e", "6,661,150", "https://coriolis.io/outfit/asp/"),
                 ("aspe", "6,661,150", "https://coriolis.io/outfit/asp/"),
                 ("asp scout", "3,961,150", "https://coriolis.io/outfit/asp_scout/"),
                 ("cobra mk iii", "349,720", "https://coriolis.io/outfit/cobra_mk_iii/"),
                 ("cobra mkiii", "349,720", "https://coriolis.io/outfit/cobra_mk_iii/"),
                 ("cobra mk iv", "747,660", "https://coriolis.io/outfit/cobra_mk_iv/"),
                 ("cobra mkiv", "747,660", "https://coriolis.io/outfit/cobra_mk_iv/"),
                 ("diamondback explorer", "1,894,760", "https://coriolis.io/outfit/diamondback_explorer/"),
                 ("dbe", "1,894,760", "https://coriolis.io/outfit/diamondback_explorer/"),
                 ("diamondbacke", "1,894,760", "https://coriolis.io/outfit/diamondback_explorer/"),
                 ("diamondback scout", "564,330", "https://coriolis.io/outfit/diamondback/"),
                 ("dbs", "564,330", "https://coriolis.io/outfit/diamondback/"),
                 ("diamondbacks", "564,330", "https://coriolis.io/outfit/diamondback/"),
                 ("eagle", "44,800", "https://coriolis.io/outfit/eagle/"),
                 ("federal assault ship", "19,814,210", "https://coriolis.io/outfit/federal_assault_ship/"),
                 ("fas", "19,814,210", "https://coriolis.io/outfit/federal_assault_ship/"),
                 ("assault ship", "19,814,210", "https://coriolis.io/outfit/federal_assault_ship/"),
                 ("federal corvette", "187,969,450", "https://coriolis.io/outfit/federal_corvette/"),
                 ("corvette", "187,969,450", "https://coriolis.io/outfit/federal_corvette/"),
                 ("federal dropship", "14,314,210", "https://coriolis.io/outfit/federal_dropship/"),
                 ("dropship", "14,314,210", "https://coriolis.io/outfit/federal_dropship/"),
                 ("federal gunship", "35,814,210", "https://coriolis.io/outfit/federal_gunship/"),
                 ("gunship", "35,814,210", "https://coriolis.io/outfit/federal_gunship/"),
                 ("fer de lance", "51,703,780", "https://coriolis.io/outfit/fer_de_lance/"),
                 ("fer-de-lance", "51,703,780", "https://coriolis.io/outfit/fer_de_lance/"),
                 ("fdl", "51,703,780", "https://coriolis.io/outfit/fer_de_lance/"),
                 ("hauler", "52,730", "https://coriolis.io/outfit/hauler/"),
                 ("imperial clipper", "22,296,450", "https://coriolis.io/outfit/imperial_clipper/"),
                 ("iclipper", "22,296,450", "https://coriolis.io/outfit/imperial_clipper/"),
                 ("clipper", "22,296,450", "https://coriolis.io/outfit/imperial_clipper/"),
                 ("imperial courier", "2,542,930", "https://coriolis.io/outfit/imperial_courier/"),
                 ("icourier", "2,542,930", "https://coriolis.io/outfit/imperial_courier/"),
                 ("courier", "2,542,930", "https://coriolis.io/outfit/imperial_courier/"),
                 ("imperial cutter", "208,969,860", "https://coriolis.io/outfit/imperial_cutter/"),
                 ("icutter", "208,969,860", "https://coriolis.io/outfit/imperial_cutter/"),
                 ("cutter", "208,969,860", "https://coriolis.io/outfit/imperial_cutter/"),
                 ("imperial eagle", "110,830", "https://coriolis.io/outfit/imperial_eagle/"),
                 ("ieagle", "110,830", "https://coriolis.io/outfit/imperial_eagle/"),
                 ("keelback", "3,126,150", "https://coriolis.io/outfit/keelback/"),
                 ("orca", "48,539,890", "https://coriolis.io/outfit/orca/"),
                 ("python", "56,978,180", "https://coriolis.io/outfit/python/"),
                 ("sidewinder", "40,800", "https://coriolis.io/outfit/sidewinder/"),
                 ("type-6", "1,045,950", "https://coriolis.io/outfit/type_6_transporter/"),
                 ("type 6", "1,045,950", "https://coriolis.io/outfit/type_6_transporter/"),
                 ("type6", "1,045,950", "https://coriolis.io/outfit/type_6_transporter/"),
                 ("type-7", "17,472,250", "https://coriolis.io/outfit/type_7_transport/"),
                 ("type 7", "17,472,250", "https://coriolis.io/outfit/type_7_transport/"),
                 ("type7", "17,472,250", "https://coriolis.io/outfit/type_7_transport/"),
                 ("type-9", "76,555,840", "https://coriolis.io/outfit/type_9_heavy/"),
                 ("type 9", "76,555,840", "https://coriolis.io/outfit/type_9_heavy/"),
                 ("type9", "76,555,840", "https://coriolis.io/outfit/type_9_heavy/"),
                 ("cow", "76,555,840", "https://coriolis.io/outfit/type_9_heavy/"),
                 ("viper", "142,930", "https://coriolis.io/outfit/viper/"),
                 ("viper mk iii", "142,930", "https://coriolis.io/outfit/viper/"),
                 ("viper mk iv", "437,930", "https://coriolis.io/outfit/viper_mk_iv/"),
                 ("vulture", "4,925,620", "https://coriolis.io/outfit/vulture/")]
        for x, y, z in corio:
            if shipname == x:
                await self.bot.say("The " + x + " costs " + y + "cr. \n" + z)
                break


def setup(bot):
    bot.add_cog(Elite(bot))
