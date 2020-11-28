print(f"Starting bot...")

import time
startTime = time.time()
print(f"Importing modules...")

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from random import randint
import asyncio
from datetime import datetime
from os import path

#to write
import gspread
import gspread_formatting as gsf

print(f"Importing .env configuration...")
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
goldEmoji = "<:gold:779842822441795615>"
skullEmoji = "💀"
doomedEmoji = "<:Doomed:770934108485582858>"
doomedUrl = "https://cdn.discordapp.com/attachments/743499472851435642/770686971147583528/doomed-logo-downsized.png"
cancelEmoji = "🚫"
checkEmoji = "✅"
bot = commands.Bot(command_prefix='.')

masterId = "201769563912667147"
officerID = "747680647409041428"

print("Initializing Google Authentication...")
#For writing
gc = gspread.service_account(filename='botCreds.json')
sh = gc.open("Doomed")
moneyLog = sh.worksheet("Money Log")
shBot = gc.open("Bot / Gold")
transSheet = shBot.worksheet("Transactions")
archiveSheet = shBot.worksheet("Archived Transactions")
nillBotSheet = shBot.worksheet("BOTNill")


print(f"Startup complete!\t[ {(time.time()-startTime):.2f}s ]")
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    userData = await getUserData(user.id)
    currentBal = userData[1]
    #If user is too poor
    bet = drStatus["bet"]
    if int(bet) > int(currentBal):
        await reaction.message.channel.send(user.name + " does not have enough balance to enter.")
        return
    if user.id == drStatus["playerA"]:
        await reaction.remove(user)
        return

    #do a ton of checks, is user same, does user have funds..
    if reaction.emoji == skullEmoji:# and not drStatus["gameStarted"]:
        drStatus["playerB"] = user.id
        drStatus["nickB"] = user.display_name
        drStatus["gameStarted"] = True
        #Post the game has started
        await reaction.message.channel.send('<@' + str(drStatus["playerB"]) +'> joined the session!')
        await reaction.message.channel.send('Let the game begin! <@' + str(drStatus["playerA"]) + '> you have to type `roll` first.')
        await autoRoll(reaction.message.channel)

@bot.event
async def on_message(message):
    if message.content == (".b"):
        await requestBalance(message)

    elif message.content.startswith(".b") and len(message.mentions) == 1:
        await RequestBalanceOfUser(message)

    elif message.content == ".dr on":
        await turnOnDR(message)

    elif message.content == ".dr off":
        await turnOffDR(message)

    elif message.content == ".dr status":
        await statusOfDR(message)

    elif message.content.startswith(".dr"):
        await gambleDR(message)

    elif message.content == "roll":
        await drRoll(message)

    elif message.content.startswith(".addBal"):
        await addBoost(message)

    elif message.content.startswith(".performPayout"):
        await doPayOut(message)

    elif message.content.startswith(".register"):
        await registerUser(message)

    elif message.content == ".help":
        await postHelp(message)


async def postHelp(message):
    str = ""
    str += "**Commands for raiders:**\n"
    str += "`.b` will post your own balance.\n"
    str += "`.b @mention` will post balance of tagged person.\n"
    str += "`.dr GOLD` will initialise a DEATHROLL for inserted GOLD value. Value can be inserted either as raw value i.e. `.dr 5000` or shorthand `.dr 5k`. **Works but is risk-free atm.**\n"
    str += "`.dr status` will post status of deathroll. Officers can turn this off."
    if isOfficer(message.author):
        str += "\n**Commands for officers:**\n"
        str += "`.register @user` will add mentioned users to the sheet.\n"
        str += "`.dr on/off` will turn on/off the deathrolling, i.e. `.dr on` to turn on.\n"
        str += "`.addBal VALUE @mention1 @mention2 noteNoteNote` will add the value to every tagged person's balance. Example:\n"
        str += "`.addBal 10k @Nill @Peach For boost in heroic Nathria` -- adds 10k balance to Nill and Peach.\n"
        str += "`.performPayout` will archive the current transactions, reset balance and post a list of payment to every member."
    await message.channel.send(str)

def hasPerm(message):
    if isOfficer(message.author):
        log(message)
        return True
    else:
        return false

def isOfficer(user):
    if str(user.id) == masterId:
        return True
    for role in user.roles:
        if str(role.id) == officerID or str(role.id) == raidLeadID:
            return True
    return False

def log(message):
    file = open("officer.log", "a")
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    logMsg = "\n" + now + "\t" + str(message.author.id) + "\t" + message.content
    file.write(logMsg)

def hasRole(user,roleID):

    if roleID in [y.id for y in user.roles]:
        return True
    return False

async def addBoost(message):
    if not hasPerm(message):
        return
    splitMsg = message.content.split(" ")
    participants = message.mentions
    noOfParts = len(participants)

    balance = splitMsg[1].replace("k","000")
    if not RepresentsInt(balance):
        await message.channel.send("Check that gold value is after `.addBal`. Use `.help` for commands.")

    #check if a space is missing in any mentions. Cancels if there is more than one space.
    for i in splitMsg:
        if splitMsg.count('@') > 1:
            await message.channel.send("Don't remove space between mentions. Action aborted.")

    #if there is a note
    if len(splitMsg) <= (noOfParts + 2):
        noteArray = ''
    else:
        noteArray = message.content.split()[noOfParts+2:]
    note = ' '.join(str(e) for e in noteArray)

    for user in participants:
        await addTransEntry(user.id, balance, balance, note, message.author.id, message.channel) #channel for posting error
    await message.add_reaction(checkEmoji)

async def addTransEntry(id, addedBalance, totalBalance, note, creatorID, channel):
    userData = await getUserData(id)

    if not userData: #if id doesn't exist in sheet
        await channel.send("<@"+ str(id) +"> was not found in the sheet. Balance to this user has not been added.\n<@"+str(masterId)+"> fix")
        return

    nickname = userData[0]
    currentBalance = userData[1]

    creator = await getUserData(creatorID)
    if not creator: #If creator ID is not in sheet
        #report on error
        creatorNick = str(creatorID)
    else:
        creatorNick = creator[0]

    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    balanceEntry = [now, str(nickname), str(id), str(addedBalance), str(int(currentBalance)+int(addedBalance)), str(note), creatorNick]
    nextRow = len(list(filter(None, transSheet.col_values(1))))+1  #####NEXT ROW
    transSheet.insert_row(balanceEntry, nextRow)
    await updateBalanceAdded(id, addedBalance, totalBalance)

async def updateBalanceAdded(id, addedCurrentBalance, addedTotalBalance):
    findRow = nillBotSheet.find(str(id)).row
    data = nillBotSheet.row_values(findRow)
    cellCurrentBalance = int(data[1])
    cellCurrentTotal = int(data[2])
    newCurrent = str(cellCurrentBalance + int(addedCurrentBalance))
    newTotal = str(cellCurrentTotal + int(addedTotalBalance))
    nillBotSheet.update_cell(findRow,2, newCurrent)
    nillBotSheet.update_cell(findRow,3, newTotal)

    moneyLog.update_cell(findRow+1,4, newCurrent)
    moneyLog.update_cell(findRow+1,5, newTotal)


async def doPayOut(message):
    if not hasPerm(message):
        return
    if len(message.content.split(" ")) == 1:
        note = "Archiving, blank note"
    else:
        note = message.content.split(" ", 1)[1]

    await postCurrentBalances(message.channel)
    await archiveTransactions(message.author, note)
    await clearTransactions()
    await resetCurrentBalance()
    await message.add_reaction(checkEmoji)

async def postCurrentBalances(channel):
    allEntries = nillBotSheet.get_all_values()
    stringToPrint = ""
    stringWithEmptyUsers = ""
    for user in allEntries:
        if user[1] == "Current Balance":
            continue
        if user[1] == str(0): #users WITHOUT balance
            stringWithEmptyUsers += user[0] + "\n"
        else: #users WITH balance
            stringToPrint += user[0] + ": " + user[1] + goldEmoji +"\n"
    stringToPrint = stringToPrint.replace("-","**----**")

    embed = discord.Embed(title = "Payout balances", color=0x00ff00)
    embed.add_field(name = "Current Balances", value = stringToPrint, inline=False)
    embed.add_field(name = "Users with no balance", value = stringWithEmptyUsers, inline = False)
    embed.set_thumbnail(url = doomedUrl)
    await channel.send(embed=embed)

async def archiveTransactions(user, note):

    trans = transSheet.get_all_values()
    del trans[0] #delete first element
    header = [datetime.now().strftime("%d/%m/%Y %H:%M:%S"), str(user.id), "", "", "", note, ""]
    #add header to values
    trans.insert(0,header)
    #find row to add transactions
    nextRow = len(list(filter(None, archiveSheet.col_values(1))))+1
    shBot.values_update('Archived Transactions!A'+str(nextRow), params = {'valueInputOption': 'RAW'}, body={'values': trans})
    #Format background of header
    fmt = gsf.cellFormat(backgroundColor=gsf.color(50,50,50))
    #apply header
    gsf.format_cell_range(archiveSheet,'A'+str(nextRow)+':G'+str(nextRow),fmt)

    #clear transSheet
    rows = len(trans)

async def clearTransactions():
    rows = len(list(filter(None, transSheet.col_values(1))))
    transSheet.delete_rows(2, rows)

async def resetCurrentBalance():
    rows = len(list(filter(None, nillBotSheet.col_values(1))))
    zeros = ["0" for i in range(rows)]
    #nillBotSheet.update(2,2,0)
    for i in range(rows-1):
        nillBotSheet.update('B'+str(i+2),0)
    #nillBotSheet.update('B2:B'+str(rows),zeros) #make array of zeros

async def registerUser(message):
    if not hasPerm(message):
        return
    ments = message.mentions
    noOfRegs = len(message.mentions)
    if noOfRegs == 0:
        await message.channel.send("Remember to tag a user")
        return
    for i in range(noOfRegs):
        name = str(ments[i].name)
        id = str(ments[i].id)
        data = [name, 0, 0, id]
        try:
            cell = nillBotSheet.find(id)
            await message.channel.send("<@"+id+"> is already in the sheet.")
        except:
            nillBotSheet.append_row(data)
            moneyLogData = [data[3], data[0], data[1], data[2]]
            moneyLog.append_row(moneyLogData)
            await message.add_reaction(checkEmoji)


async def turnOnDR(message):
    user = message.author
    channel = message.channel
    roleID = 747681150469931189 #raider

    if hasRole(user,roleID) and not drStatus["turnedOn"]:
        drStatus["turnedOn"] = True
        await channel.send("DeathRolling is now enabled.")

async def turnOffDR(message):
    user = message.author
    channel = message.channel
    roleID = 747681150469931189 #raider

    if hasRole(user,roleID) and drStatus["turnedOn"]:
        drStatus["turnedOn"] = False
        await channel.send("Deathrolling is now disabled.")

async def statusOfDR(message):
    if drStatus["turnedOn"]:
        await message.channel.send("Deathrolling is on.")
    else:
        await message.channel.send("Deathrolling is off.")

async def gambleDR(message):
    if not drStatus["turnedOn"]: #If an officer has turned the bot off
        await message.channel.send("An officer has turned off the deathrolling.")
        return
    if drStatus["gameInit"]:
        await message.channel.send("Let the other players finish first, <@"+str(message.author.id)+">")
        message.delete()
        return




    value = message.content.split(".dr ")
    bet = value[1].replace("k","000")
    if not RepresentsInt(bet):
        return

    userData = await getUserData(message.author.id)
    currentBal = userData[1]
    #If user is too poor
    if int(bet) > int(currentBal):
        await cancelGame(message.channel, "You don't have enough balance.")
        return

    if int(bet) < 5000:
        await cancelGame(message.channel, "Minimum 5k.")
        return

    drStatus["gameInit"] = True
    drStatus["bet"] = bet
    drStatus["currentRoll"] = bet
    drStatus["playerA"] = message.author.id
    drStatus["nickA"] = message.author.display_name
    drStatus["nextRoller"] = 0
    drStatus["userTimedOut"] = []
    #Do some checks

    embed = discord.Embed(title=skullEmoji+" Death Roll | Roll: "+ bet + " " + skullEmoji)
    embed.add_field(name="Session Creator", value = message.author.name)
    embed.set_thumbnail(url = doomedUrl)
    embed.set_footer(text = message.id) #Footer is set to
    msg = await message.channel.send(embed = embed)

    await msg.add_reaction(skullEmoji)
    await message.channel.send("**Death roll** | Session started! Click on the " + skullEmoji + " reaction to join!")
    await message.channel.send("**Death Roll** | Session will cancel in 30s.")
    await asyncio.sleep(30) #if no one else has joined
    if not drStatus["gameStarted"]:
        await cancelGame(message.channel, "No one joined.")
        drStatus["gameInit"] = False

async def drRoll(message):
    drStatus["userTimedOut"][-1] = False #user DID roll before timing out (did NOT time out)
    if not drStatus["gameStarted"]:
        return
    if drStatus["nextRoller"] == 0:
        if not message.author.id == drStatus["playerA"] and not message.author.bot:
            return
        rollerID = drStatus["playerA"]
        drStatus["nextRoller"] = 1  #for next round
    elif drStatus["nextRoller"] == 1:
        if not message.author.id == drStatus["playerB"] and not message.author.bot:
            return
        rollerID = drStatus["playerB"]
        drStatus["nextRoller"] = 0 #for next round
    ceil = int(drStatus["currentRoll"])
    rolled = randint(1,ceil)
    drStatus["currentRoll"] = rolled
    await message.channel.send("**Death Roll** | <@"+str(rollerID)+"> rolled a **" + str(rolled) + "**!")
    if rolled == 1:
        await drRolledOne(message.channel)
        await message.delete()
        return
    await message.delete()
    await autoRoll(message.channel)

async def drRolledOne(channel):
    drStatus["gameInit"] = False
    drStatus["gameStarted"] = False
    if drStatus["nextRoller"] == 0:
        winner = drStatus["nickA"]
        winnerId = drStatus["playerA"]
        loser = drStatus["nickB"]
        loserId = drStatus["playerB"]
    else:
        winner = drStatus["nickB"]
        winnerId = drStatus["playerB"]
        loser = drStatus["nickA"]
        loserId = drStatus["playerA"]
    bet = drStatus["bet"]
    embed = discord.Embed(title = "Game is over!")
    embed.set_thumbnail(url = doomedUrl)
    embed.add_field(name = "Winner is "+str(winner), value = "Won " + str(bet) + goldEmoji)
    embed.add_field(name = "Loser is "+str(loser), value = "Lost " + str(bet) + goldEmoji)
    await channel.send(embed = embed)

    winnerData = await getUserData(winnerId)
    loserData = await getUserData(loserId)

    winnerCurrentBalance = winnerData[1]
    winnerName = winnerData[0]
    loserCurrentBalance = loserData[1]
    loserName = loserData[0]

    winnerNewBalance = str(int(winnerCurrentBalance) + int(bet))
    loserNewBalance = str(int(loserCurrentBalance) - int(bet))

    #winner transaction
    await addDrEntry(winnerId, str(bet), "DR win against " + loserName, "Bot", channel)

    await addDrEntry(loserId, "-" + str(bet), "DR lost against " + winnerName, "Bot", channel)

async def addDrEntry(id, addedBalance, note, creatorID, channel):
    userData = await getUserData(id)

    if not userData: #if id doesn't exist in sheet
        await channel.send("<@"+ str(id) +"> was not found in the sheet. Balance to this user has not been added.\n<@"+str(masterId)+"> fix")
        return

    nickname = userData[0]
    currentBalance = userData[1]

    creator = await getUserData(creatorID)
    if not creator: #If creator ID is not in sheet
        #report on error
        creatorNick = str(creatorID)
    else:
        creatorNick = creator[0]

    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    balanceEntry = [now, str(nickname), str(id), str(addedBalance), str(int(currentBalance)+int(addedBalance)), str(note), creatorNick]
    nextRow = len(list(filter(None, transSheet.col_values(1))))+1  #####NEXT ROW
    transSheet.insert_row(balanceEntry, nextRow)
    await updateBalanceAdded(id, addedBalance, 0)



async def cancelGame(channel,post):
    embed = discord.Embed(title = "Game cancelled!", description = post)
    await channel.send(embed = embed)

async def autoRoll(channel):
     drStatus["userTimedOut"].append(True)
     length = len(drStatus["userTimedOut"]) #check THAT timeout bool
     await asyncio.sleep(30)
     if drStatus["userTimedOut"][length-1]:
          await channel.send("roll")

drStatus = {
    "turnedOn": True, #an officer can turn off DR'ing
    "gameInit": False, #When someone starts a DR but before emote has been added
    "gameStarted": False, #Rolling is happening
    "userTimedOut": [], #For auto-rolling
    "playerA": "0", #id as str
    "playerB": "0",
    "nickA" : "a",
    "nickB" : "b",
    "bet": 0,
    "nextRoller": 0, #next person to roll, 0 for playerA, 1 for playerB
    "currentRoll": 0 #current max rng roll
}

def RepresentsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

async def requestBalance(message):
    await postBalance(message.channel, message.author)

async def RequestBalanceOfUser(message):
    await postBalance(message.channel, message.mentions[0])

async def postBalance(channel, user):
    data = await getUserData(user.id)
    if not data: #user is not in sheet
        await channel.send("You don't exist")
        return
    nickName = data[0]
    currentBalance = data[1]
    totalBalance = data[2]

    embedVar = discord.Embed(title=nickName+"'s Balance", color=0x00ff00)
    embedVar.add_field(name="Current Balance", value=currentBalance+goldEmoji, inline=False)
    embedVar.add_field(name="Total Balance", value=totalBalance+goldEmoji, inline=False)
    embedVar.set_thumbnail(url=user.avatar_url)
    #embedVar.setImage(message.author.avatarURL())
    await channel.send(embed=embedVar)

async def getUserData(id): #nick, current balance, total balance, ID - all as str
    try:
        findRow = nillBotSheet.find(str(id)).row
        row = nillBotSheet.row_values(findRow)
        return row
    except:
        return False

bot.run(TOKEN)
