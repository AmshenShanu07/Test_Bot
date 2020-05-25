import json
import html, time
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional, List
from hurry.filesize import size as sizee

from telegram import Message, Chat, Update, Bot, ParseMode
from telegram.error import BadRequest
from telegram.utils.helpers import escape_markdown, mention_html
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import run_async

from metabutler import dispatcher, LOGGER
from metabutler.modules.disable import DisableAbleCommandHandler
from metabutler.modules.helper_funcs.alternate import send_message

from requests import get

# Greeting all bot owners that is using this module,
# - RealAkito (used to be peaktogoo) [Module Maker]
# have spent so much time of their life into making this module better, stable, and well more supports.
# Please don't remove these comment, if you're still respecting me, the module maker.
#
# This module was inspired by Android Helper Bot by Vachounet.
# None of the code is taken from the bot itself, to avoid confusion.

#LOGGER.info("android: Original Android Modules by @RealAkito on Telegram")
DEVICES_DATA = 'https://raw.githubusercontent.com/androidtrackers/certified-android-devices/master/by_device.json'

@run_async
def shrp(update, context):
    chat_id = update.effective_chat.id
    msg_id = update.effective_message.message_id
    args = update.message.text.split()
    if len(args) == 1:
        context.bot.send_message(chat_id, text="You need to provide a device codename", reply_to_message_id=msg_id)
        return
    else:
        device = args[1]
        url = "https://sourceforge.net/projects/shrp/files/{0}/".format(device)
        request = get(url)
        if request.status_code == 404:
            context.bot.send_message(chat_id, "That device does not have a SHRP recovery released yet", reply_to_message_id=msg_id)
            return
        elif request.status_code == 200:
            soup = BeautifulSoup(request.text, 'html.parser')
            file_tag = soup.find('tr', class_='file')
            file_name = file_tag.get('title')
            dl_link = file_tag.find('th', headers='files_name_h').find('a').get('href')
            date = file_tag.find('td', headers='files_date_h').find('abbr').get('title')
            size = file_tag.find('td', headers='files_size_h').text
            keyboard = [[InlineKeyboardButton("Click Here to Download", dl_link)]]
            text = "<b>File Name - </b> {0}\n".format(file_name)
            text += "<b>File Size - </b> {0}\n".format(size)
            text += "<b>Date Uploaded - </b> {0}".format(date)
            context.bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML', reply_to_message_id=msg_id)
        else:
            context.bot.send_message(chat_id, "SourceForge is experiencing some error now, please try again later", reply_to_message_id=msg_id)

@run_async
def bliss(update, context):
    chat_id = update.effective_chat.id
    msg_id = update.effective_message.message_id
    args = update.message.text.split()
    if len(args) == 1:
        context.bot.send_message(chat_id, text="You need to provide a device codename", reply_to_message_id=msg_id)
        return
    else:
        device = args[1].lower()
        url = "https://raw.githubusercontent.com/BlissRoms-Devices/OTA/master/builds.json"
        response = get(url).json()
        response = {k.lower():v for k,v in response.items()}
        if device in response.keys():
            device_info = response[device][0]
            build_date = device_info['date']
            filename = device_info['filename']
            sha256 = device_info['sha256']
            size = (device_info['size']/1024)/1024
            size = ("%.2f"%size)
            version = device_info['version']
            dl_link = "https://sourceforge.net/projects/blissroms/files/Q" + device_info['filepath']
            keyboard = [[InlineKeyboardButton("Click Here to Download", dl_link)]]
            text = "<b>Build Date -</b> {0}\n".format(build_date)
            text += '<b>File Name -</b> <a href="{0}">{1}</a>\n'.format(dl_link, filename)
            text += "<b>SHA256 -</b> {0}\n".format(sha256)
            text += "<b>Size -</b> {0} MB\n".format(size)
            text += "<b>Version -</b> {0}\n".format(version)
            context.bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML', reply_to_message_id=msg_id)
        else:
            context.bot.send_message(chat_id, text="That device {0} does not have official BlissOS".format(device), reply_to_message_id=msg_id)

@run_async
def ofox(update, context):
    args = update.message.text.split()
    if len(args) == 0:
        reply = 'No codename provided, write a codename for fetching informations.'
        del_msg = send_message(update.effective_message, "{}".format(reply), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return
    device = str(args[1])
    url = get("https://api.orangefox.download/v2/device/{}".format(device))
    if url.status_code == 404:
        reply = "Couldn't find Orangefox downloads for {}!\n".format(device)
        send_message(update.effective_message, "{}".format(reply))
    else:
        reply = "<b>Latest Stable Orangefox for {0}</b>\n".format(device)
        url = get(f'https://api.orangefox.download/v2/device/{device}/releases/stable/last').json()
        try:
            bugs = url['bugs']
        except Exception:
            bugs = None
        try:
            notes = url['notes']
        except Exception:
            notes = None
        changelog = url['changelog']
        buildate = url['date']
        md5 = url['md5']
        size = url['size_human']
        link = url['url']
        version = url['version']
        if bugs is not None:
            reply += "<b>Bugs - </b> {0}\n".format(bugs)
        reply += "<b>Changelog - </b> {0}\n".format(changelog)
        reply += "<b>Build Date - </b> {0}\n".format(buildate)
        if notes is not None:
            reply += "<b>Notes - </b> {0}\n".format(notes)
        reply += "<b>MD5 - </b> {0}\n".format(md5)
        reply += "<b>Size - </b> {0}\n".format(size)
        reply += "<b>Version - </b> {0}\n".format(version)
        keyboard = [[InlineKeyboardButton("Click Here to Download", link)]]
        send_message(update.effective_message, "{}".format(reply), parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard), disable_web_page_preview=True)

@run_async
def twrp(update, context):
    args = context.args
    if len(args) == 0:
        reply = "No codename provided, write a codename for fetching informations."
        del_msg = send_message(update.effective_message, "{}".format(reply))
    device = " ".join(args)
    url = get(f'https://eu.dl.twrp.me/{device}/')
    if url.status_code == 404:
        reply = "Couldn't find twrp downloads for {}!\n".format(device)
        send_message(update.effective_message, "{}".format(reply))
    else:
        reply = f'*Latest Official TWRP for {device}*\n'            
        db = get(DEVICES_DATA).json()
        newdevice = device.strip('lte') if device.startswith('beyond') else device
        try:
            brand = db[newdevice][0]['brand']
            name = db[newdevice][0]['name']
            reply += f'*{brand} - {name}*\n'
        except KeyError as err:
            pass
        page = BeautifulSoup(url.content, 'lxml')
        date = page.find("em").text.strip()
        reply += f'*Updated:* {date}\n'
        trs = page.find('table').find_all('tr')
        row = 2 if trs[0].find('a').text.endswith('tar') else 1
        for i in range(row):
            download = trs[i].find('a')
            dl_link = f"https://eu.dl.twrp.me{download['href']}"
            dl_file = download.text
            size = trs[i].find("span", {"class": "filesize"}).text
        keyboard = [[InlineKeyboardButton("Click Here to Download", dl_link)]]
        send_message(update.effective_message, "{}".format(reply), parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard), disable_web_page_preview=True)


@run_async
def magisk(update, context):
    url = 'https://raw.githubusercontent.com/topjohnwu/magisk_files/'
    releases = ""
    for type, branch in {"Stable":["master/stable","master"], "Beta":["master/beta","master"], "Canary (release)":["canary/release","canary"], "Canary (debug)":["canary/debug","canary"]}.items():
        data = get(url + branch[0] + '.json').json()
        releases += f'*{type}*: \n' \
                    f'• [Changelog](https://github.com/topjohnwu/magisk_files/blob/{branch[1]}/notes.md)\n' \
                    f'• Zip - [{data["magisk"]["version"]}-{data["magisk"]["versionCode"]}]({data["magisk"]["link"]}) \n' \
                    f'• App - [{data["app"]["version"]}-{data["app"]["versionCode"]}]({data["app"]["link"]}) \n' \
                    f'• Uninstaller - [{data["magisk"]["version"]}-{data["magisk"]["versionCode"]}]({data["uninstaller"]["link"]})\n\n'
                        

    del_msg = send_message(update.effective_message, "*Latest Magisk Releases:*\n{}".format(releases),
                               parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    time.sleep(300)
    try:
        del_msg.delete()
        update.effective_message.delete()
    except BadRequest as err:
        if (err.message == "Message to delete not found" ) or (err.message == "Message can't be deleted" ):
            return


@run_async
def havoc(update, context):
    cmd_name = "havoc"
    message = update.effective_message
    chat = update.effective_chat  # type: Optional[Chat]
    device = message.text[len(f'/{cmd_name} '):]

    fetch = get(
        f'https://raw.githubusercontent.com/Havoc-Devices/android_vendor_OTA/pie/{device}.json'
    )

    if device == '':
        reply_text = "Please type your device **codename**!\nFor example, `/{} tissot".format(cmd_name)
        send_message(update.effective_message, reply_text,
                           parse_mode=ParseMode.MARKDOWN,
                           disable_web_page_preview=True)
        return

    if fetch.status_code == 200:
        usr = fetch.json()
        response = usr['response'][0]
        filename = response['filename']
        url = response['url']
        buildsize_a = response['size']
        buildsize_b = sizee(int(buildsize_a))
        version = response['version']

        reply_text = "*Download:* [{}]({})\n".format(filename, url)
        reply_text += "*Build Size:* `{}`\n".format(buildsize_b)
        reply_text += "*Version:* `{}`\n".format(version)

        keyboard = [[
            InlineKeyboardButton(text="Click here to Download", url=f"{url}")
        ]]
        send_message(update.effective_message, reply_text,
                           reply_markup=InlineKeyboardMarkup(keyboard),
                           parse_mode=ParseMode.MARKDOWN,
                           disable_web_page_preview=True)
        return

    elif fetch.status_code == 404:
        reply_text = "Couldn't find any results matching your query."

    send_message(update.effective_message, reply_text,
                       parse_mode=ParseMode.MARKDOWN,
                       disable_web_page_preview=True)


@run_async
def pixys(update, context):
    message = update.effective_message
    device = message.text[len('/pixys '):]

    if device == '':
        reply_text = "Please type your device **codename** into it!\nFor example, `/pixys tissot`"
        send_message(update.effective_message, reply_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    fetch = get(f'https://raw.githubusercontent.com/PixysOS-Devices/official_devices/master/{device}/build.json')
    if fetch.status_code == 200:
        usr = fetch.json()
        response = usr['response'][0]
        filename = response['filename']
        url = response['url']
        buildsize_a = response['size']
        buildsize_b = sizee(int(buildsize_a))
        romtype = response['romtype']
        version = response['version']

        reply_text = (f"*Download:* [{filename}]({url})\n"
                      f"*Build size:* `{buildsize_b}`\n"
                      f"*Version:* `{version}`\n"
                      f"*Rom Type:* `{romtype}`")

        keyboard = [[InlineKeyboardButton(text="Click to Download", url=f"{url}")]]
        send_message(update.effective_message, reply_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    elif fetch.status_code == 404:
        reply_text = "Device not found."
    send_message(update.effective_message, reply_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


@run_async
def dotos(update, context):
    message = update.effective_message
    device = message.text[len('/dotos '):]

    if device == '':
        reply_text = "Please type your device **codename** into it!\nFor example, `/dotos tissot`"
        send_message(update.effective_message, reply_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    fetch = get(f'https://raw.githubusercontent.com/DotOS/ota_config/dot-p/{device}.json')
    if fetch.status_code == 200:
        usr = fetch.json()
        response = usr['response'][0]
        filename = response['filename']
        url = response['url']
        buildsize_a = response['size']
        buildsize_b = sizee(int(buildsize_a))
        version = response['version']
        changelog = response['changelog_device']

        reply_text = (f"*Download:* [{filename}]({url})\n"
                      f"*Build size:* `{buildsize_b}`\n"
                      f"*Version:* `{version}`\n"
                      f"*Device Changelog:* `{changelog}`")

        keyboard = [[InlineKeyboardButton(text="Click to Download", url=f"{url}")]]
        send_message(update.effective_message, reply_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    elif fetch.status_code == 404:
        reply_text="Device not found"
    send_message(update.effective_message, reply_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


@run_async
def viper(update, context):
    message = update.effective_message
    device = message.text[len('/viper '):]

    if device == '':
        reply_text = "Please type your device **codename** into it!\nFor example, `/viper tissot`"
        send_message(update.effective_message, reply_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    fetch = get(f'https://raw.githubusercontent.com/Viper-Devices/official_devices/master/{device}/build.json')
    if fetch.status_code == 200:
        usr = fetch.json()
        response = usr['response'][0]
        filename = response['filename']
        url = response['url']
        buildsize_a = response['size']
        buildsize_b = sizee(int(buildsize_a))
        version = response['version']

        reply_text = (f"*Download:* [{filename}]({url})\n"
                      f"*Build size:* `{buildsize_b}`\n"
                      f"*Version:* `{version}`")

        keyboard = [[InlineKeyboardButton(text="Click to Download", url=f"{url}")]]
        send_message(update.effective_message, reply_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    elif fetch.status_code == 404:
        reply_text="Device not found"
    send_message(update.effective_message, reply_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


def enesrelease(update, context):
    args = context.args
    message = update.effective_message
    usr = get(f'https://api.github.com/repos/EnesSastim/Downloads/releases/latest').json()
    reply_text = "*Enes Sastim's lastest upload(s)*\n"
    for i in range(len(usr)):
        try:
            name = usr['assets'][i]['name']
            url = usr['assets'][i]['browser_download_url']
            reply_text += f"[{name}]({url})\n"
        except IndexError:
            continue
    send_message(update.effective_message, reply_text, parse_mode=ParseMode.MARKDOWN)


def descendant(update, context):
    args = context.args
    message = update.effective_message
    usr = get(f'https://api.github.com/repos/Descendant/InOps/releases/latest').json()
    reply_text = "*Descendant GSI Download(s)*\n"
    for i in range(len(usr)):
        try:
            name = usr['assets'][i]['name']
            url = usr['assets'][i]['browser_download_url']
            download_count = usr['assets'][i]['download_count']
            reply_text += f"[{name}]({url}) - Downloaded `{download_count}` Times\n\n"
        except IndexError:
            continue
    send_message(update.effective_message, reply_text, parse_mode=ParseMode.MARKDOWN)

@run_async
def los(update, context):
    cmd_name = "los"
    message = update.effective_message
    chat = update.effective_chat  # type: Optional[Chat]
    device = message.text[len(f'/{cmd_name} '):]

    if device == '':
        reply_text = "Please type your device **codename**!\nFor example, `/{} tissot`".format(cmd_name)
        send_message(update.effective_message, reply_text,
                           parse_mode=ParseMode.MARKDOWN,
                           disable_web_page_preview=True)
        return

    fetch = get(f'https://download.lineageos.org/api/v1/{device}/nightly/*')
    if fetch.status_code == 200 and len(fetch.json()['response']) != 0:
        usr = fetch.json()
        response = usr['response'][0]
        filename = response['filename']
        url = response['url']
        buildsize_a = response['size']
        buildsize_b = sizee(int(buildsize_a))
        version = response['version']

        reply_text = "*Download:* [{}]({})\n".format(filename, url)
        reply_text += "*Build Size:* `{}`\n".format(buildsize_b)
        reply_text += "*Version:* `{}`\n".format(version)

        keyboard = [[
            InlineKeyboardButton(text="Click here to Download", url=f"{url}")
        ]]
        send_message(update.effective_message, reply_text,
                           reply_markup=InlineKeyboardMarkup(keyboard),
                           parse_mode=ParseMode.MARKDOWN,
                           disable_web_page_preview=True)
        return

    else:
        reply_text = "Couldn't find any results matching your query."
    send_message(update.effective_message, reply_text,
                       parse_mode=ParseMode.MARKDOWN,
                       disable_web_page_preview=True)


@run_async
def evo(update, context):
    cmd_name = "evo"
    message = update.effective_message
    chat = update.effective_chat  # type: Optional[Chat]
    device = message.text[len(f'/{cmd_name} '):]

    if device == "example":
        reply_text = "Why are you trying to get the example device?"
        send_message(update.effective_message, reply_text,
                           parse_mode=ParseMode.MARKDOWN,
                           disable_web_page_preview=True)
        return

    if device == "x00t":
        device = "X00T"

    if device == "x01bd":
        device = "X01BD"

    fetch = get(
        f'https://raw.githubusercontent.com/Evolution-X-Devices/official_devices/master/builds/{device}.json'
    )

    if device == '':
        reply_text = "Please type your device **codename**!\nFor example, `/{} tissot`".format(cmd_name)
        send_message(update.effective_message, reply_text,
                           parse_mode=ParseMode.MARKDOWN,
                           disable_web_page_preview=True)
        return

    if device == 'gsi':
        reply_text = "Please check Evolution X Updates channel(@EvolutionXUpdates) or click the button down below to download the GSIs!"

        keyboard = [[
            InlineKeyboardButton(
                text="Click here to Download",
                url="https://sourceforge.net/projects/evolution-x/files/GSI/")
        ]]
        send_message(update.effective_message, reply_text,
                           reply_markup=InlineKeyboardMarkup(keyboard),
                           parse_mode=ParseMode.MARKDOWN,
                           disable_web_page_preview=True)
        return

    if fetch.status_code == 200:
        try:
            usr = fetch.json()
            filename = usr['filename']
            url = usr['url']
            version = usr['version']
            maintainer = usr['maintainer']
            maintainer_url = usr['telegram_username']
            size_a = usr['size']
            size_b = sizee(int(size_a))

            reply_text = "*Download:* [{}]({})\n".format(filename, url)
            reply_text += "*Build Size:* `{}`\n".format(size_b)
            reply_text += "*Android Version:* `{}`\n".format(version)
            reply_text += "*Maintainer:* {}\n".format(
                f"[{maintainer}](https://t.me/{maintainer_url})")

            keyboard = [[
                InlineKeyboardButton(text="Click here to Download", url=f"{url}")
            ]]
            send_message(update.effective_message, reply_text,
                               reply_markup=InlineKeyboardMarkup(keyboard),
                               parse_mode=ParseMode.MARKDOWN,
                               disable_web_page_preview=True)
            return

        except ValueError:
            reply_text = "Tell the rom maintainer to fix their OTA json. I'm sure this won't work with OTA and it won't work with this bot too :P"
            send_message(update.effective_message, reply_text,
                               parse_mode=ParseMode.MARKDOWN,
                               disable_web_page_preview=True)
            return

    elif fetch.status_code == 404:
        reply_text = "Couldn't find any results matching your query."
        send_message(update.effective_message, reply_text,
                           parse_mode=ParseMode.MARKDOWN,
                           disable_web_page_preview=True)
        return


def phh(update, context):
    args = context.args
    romname = "Phh's"
    message = update.effective_message
    chat = update.effective_chat  # type: Optional[Chat]

    usr = get(
        f'https://api.github.com/repos/phhusson/treble_experimentations/releases/latest'
    ).json()
    reply_text = "*{} latest release(s)*\n".format(romname)
    for i in range(len(usr)):
        try:
            name = usr['assets'][i]['name']
            url = usr['assets'][i]['browser_download_url']
            reply_text += f"[{name}]({url})\n"
        except IndexError:
            continue
    send_message(update.effective_message, reply_text, parse_mode=ParseMode.MARKDOWN)


@run_async
def bootleggers(update, context):
    cmd_name = "bootleggers"
    message = update.effective_message
    chat = update.effective_chat  # type: Optional[Chat]
    codename = message.text[len(f'/{cmd_name} '):]

    if codename == '':
        reply_text ="Please type your device **codename**!\nFor example, `/{} tissot`".format(cmd_name)
        send_message(update.effective_message, reply_text,
                           parse_mode=ParseMode.MARKDOWN,
                           disable_web_page_preview=True)
        return

    fetch = get('https://bootleggersrom-devices.github.io/api/devices.json')
    if fetch.status_code == 200:
        nestedjson = fetch.json()

        if codename.lower() == 'x00t':
            devicetoget = 'X00T'
        else:
            devicetoget = codename.lower()

        reply_text = ""
        devices = {}

        for device, values in nestedjson.items():
            devices.update({device: values})

        if devicetoget in devices:
            for oh, baby in devices[devicetoget].items():
                dontneedlist = ['id', 'filename', 'download', 'xdathread']
                peaksmod = {
                    'fullname': 'Device name',
                    'buildate': 'Build date',
                    'buildsize': 'Build size',
                    'downloadfolder': 'SourceForge folder',
                    'mirrorlink': 'Mirror link',
                    'xdathread': 'XDA thread'
                }
                if baby and oh not in dontneedlist:
                    if oh in peaksmod:
                        oh = peaksmod[oh]
                    else:
                        oh = oh.title()

                    if oh == 'SourceForge folder':
                        reply_text += f"\n*{oh}:* [Here]({baby})"
                    elif oh == 'Mirror link':
                        reply_text += f"\n*{oh}:* [Here]({baby})"
                    else:
                        reply_text += f"\n*{oh}:* `{baby}`"

            reply_text += "*XDA Thread:* [Here]({})\n".format(
                devices[devicetoget]['xdathread'])
            reply_text += "*Download:* [{}]({})\n".format(
                devices[devicetoget]['filename'],
                devices[devicetoget]['download'])
        else:
            reply_text = "Couldn't find any results matching your query."

    elif fetch.status_code == 404:
        reply_text = "Couldn't reach the API"
    send_message(update.effective_message, reply_text,
                       parse_mode=ParseMode.MARKDOWN,
                       disable_web_page_preview=True)


__help__ = """
*This module is made with love by* @peaktogoo *and code beauty by* @kandnub
*Orangefox code added with love by* @AgileArchon
 *Device Specific Rom*
 - /magisk - gets the latest magisk release for Stable/Beta/Canary
 - /twrp <codename> -  gets latest twrp for the android device using the codename
 - /ofox <codename> - Get the latest stable Orangefox Recovery download link using the codename
 - /havoc <device>: Get the Havoc Rom
 - /viper <device>: Get the Viper Rom
 - /evo <device>: Get the Evolution X Rom
 - /dotos <device>: Get the DotOS Rom
 - /pixys <device>: Get the Pixy Rom
 - /los <device>: Get the LineageOS Rom
 - /bootleggers <device>: Get the Bootleggers Rom
 *GSI*
 - /phh: Get the lastest Phh AOSP Oreo GSI!
 - /descendant: Get the lastest Descendant GSI!
 - /enesrelease: Get the lastest Enes upload
"""

__mod_name__ = "Android"


EVO_HANDLER = DisableAbleCommandHandler("evo", evo, admin_ok=True)
MAGISK_HANDLER = DisableAbleCommandHandler("magisk", magisk)
BLISS_HANDLER = DisableAbleCommandHandler("bliss", bliss, pass_args=True)
TWRP_HANDLER = DisableAbleCommandHandler("twrp", twrp, pass_args=True)
OFOX_HANDLER = DisableAbleCommandHandler("ofox", ofox, pass_args=True)
SHRP_HANDLER = DisableAbleCommandHandler("shrp", shrp, pass_args=True)
DOTOS_HANDLER = DisableAbleCommandHandler("dotos", dotos, admin_ok=True)
PIXYS_HANDLER = DisableAbleCommandHandler("pixys", pixys, admin_ok=True)
DESCENDANT_HANDLER = DisableAbleCommandHandler("descendant", descendant, pass_args=True, admin_ok=True)
ENES_HANDLER = DisableAbleCommandHandler("enesrelease", enesrelease, pass_args=True, admin_ok=True)
VIPER_HANDLER = DisableAbleCommandHandler("viper", viper, admin_ok=True)
HAVOC_HANDLER = DisableAbleCommandHandler("havoc", havoc, admin_ok=True)
PHH_HANDLER = DisableAbleCommandHandler("phh",
                                        phh,
                                        pass_args=True,
                                        admin_ok=True)
LOS_HANDLER = DisableAbleCommandHandler("los", los, admin_ok=True)
BOOTLEGGERS_HANDLER = DisableAbleCommandHandler("bootleggers",
                                                bootleggers,
                                                admin_ok=True)

dispatcher.add_handler(EVO_HANDLER)
dispatcher.add_handler(MAGISK_HANDLER)
dispatcher.add_handler(TWRP_HANDLER)
dispatcher.add_handler(OFOX_HANDLER)
dispatcher.add_handler(SHRP_HANDLER)
dispatcher.add_handler(BLISS_HANDLER)
dispatcher.add_handler(HAVOC_HANDLER)
dispatcher.add_handler(VIPER_HANDLER)
dispatcher.add_handler(DOTOS_HANDLER)
dispatcher.add_handler(PIXYS_HANDLER)
dispatcher.add_handler(DESCENDANT_HANDLER)
dispatcher.add_handler(ENES_HANDLER)
dispatcher.add_handler(PHH_HANDLER)
dispatcher.add_handler(LOS_HANDLER)
dispatcher.add_handler(BOOTLEGGERS_HANDLER)
