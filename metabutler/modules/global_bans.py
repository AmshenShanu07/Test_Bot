import html
from io import BytesIO
from typing import Optional, List

from telegram import Message, Update, Bot, User, Chat, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.utils.helpers import mention_html, escape_markdown

import metabutler.modules.sql.global_bans_sql as sql
from metabutler import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, STRICT_GBAN, GBAN_LOGS
from metabutler.modules.helper_funcs.chat_status import user_admin, is_user_admin
from metabutler.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from metabutler.modules.helper_funcs.filters import CustomFilters
from metabutler.modules.helper_funcs.misc import send_to_list
from metabutler.modules.sql.users_sql import get_all_chats

from metabutler.modules.helper_funcs.alternate import send_message

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Peer_id_invalid",
    "Group chat was deactivated",
    "Need to be inviter of a user to kick it from a basic group",
    "Chat_admin_required",
    "Only the creator of a basic group can kick group administrators",
    "Channel_private",
    "Not in the chat"
}

UNGBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Method is available for supergroup and channel chats only",
    "Not in the chat",
    "Channel_private",
    "Chat_admin_required",
}


UPDATE_GBAN = """
<b>New Reason of Global Ban</b>\n
<b>Sudo Admin:</b> {}\n
<b>User:</b> {}\n
<b>ID:</b> <code>{}</code>\n
<b>Previous Reason:</b> {}\n
<b>New Reason:</b> {}"""


@run_async
def gban(update, context):
    banner = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    chat_name = update.effective_message.chat.title
    args = context.args

    user_id, reason = extract_user_and_text(message, args)
    if user_id == "error":
        send_message(update.effective_message, reason)
        return ""

    if not user_id:
        send_message(update.effective_message, "You don't seem to be referring to a user.")
        return

    if int(user_id) in SUDO_USERS:
        send_message(update.effective_message, "I spy, with my little eye... a sudo user war! Why are you guys turning on each other?")
        return

    if int(user_id) in SUPPORT_USERS:
        send_message(update.effective_message, "OOOH someone's trying to gban a support user! *grabs popcorn*")
        return

    if user_id == context.bot.id:
        send_message(update.effective_message, "So funny, lets gban myself why don't I? Nice try.")
        return

    try:
        user_chat = context.bot.get_chat(user_id)
    except BadRequest as excp:
        send_message(update.effective_message, excp.message)
        return

    if user_chat.type != 'private':
        send_message(update.effective_message, "That's not a user!")
        return

    if user_chat.first_name == '':
        send_message(update.effective_message, "That's a deleted account! Why even bother gbanning them?")
        return

    full_reason = f"{reason} // GBanned by {banner.first_name}"

    if sql.is_user_gbanned(user_id):
        if not reason:
            send_message(update.effective_message, "This user is already gbanned; I'd change the reason, but you haven't given me one...")
            return

        old_reason = sql.update_gban_reason(
                user_id, user_chat.username or user_chat.first_name, 
                full_reason) or "None"

        try:
            context.bot.send_message(
                    UPDATE_GBAN.format(
                    mention_html(banner.id, banner.first_name),
                    mention_html(user_chat.id, user_chat.first_name
                                 or "Deleted Account"), user_chat.id,
                    old_reason, full_reason),
                parse_mode=ParseMode.HTML)
        except Exception:
            pass

    # send_message(update.effective_message, "This user has already been gbanned. I have updated the reason.\nPrevious reason: <code>{}</code>\nNew reason: <code>{}</code>".format(
    #         html.escape(old_reason), html.escape(full_reason)),
    #                        parse_mode=ParseMode.HTML)
    # return

    starting = "Global Banning {} with the id <code>{}</code>...".format(
        mention_html(user_chat.id, user_chat.first_name or "Deleted Account"),
        user_chat.id)
    send_message(update.effective_message, starting, parse_mode=ParseMode.HTML)

    try:
        context.bot.send_message("{} is gbanning user {} with the following reason: <code>{}</code>.".format(
                             mention_html(banner.id, banner.first_name),
                             mention_html(user_chat.id, user_chat.first_name), 
                             full_reason
                             or "No reason given"),
                             html=True)
    except Exception:
        print("nut")

    

    sql.gban_user(user_id, user_chat.username or user_chat.first_name,
                  full_reason)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            context.bot.kick_chat_member(chat_id, user_id)
        except BadRequest as excp:
            if excp.message in GBAN_ERRORS:
                pass
            else:
                send_message(update.effective_message, "Could not gban due to: {}".format(excp.message))
                send_to_list(context.bot, SUDO_USERS + SUPPORT_USERS, "Could not un-gban due to: {}".format(excp.message))
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    log_message = (f"#GBANNED\n"
                  f"<b>Originated from:</b> {chat_name}\n"
                  f"<b>Admin:</b> {mention_html(banner.id, banner.first_name)}\n"
                  f"<b>Banned User:</b> {mention_html(user_chat.id, user_chat.first_name)}\n"
                  f"<b>Banned User ID:</b> {user_chat.id}\n"
                  f"<b>Reason:</b> {reason}" or "No reason given")

    if GBAN_LOGS:
        context.bot.send_message(GBAN_LOGS, log_message, parse_mode=ParseMode.HTML)
    send_to_list(context.bot, SUDO_USERS + SUPPORT_USERS, f"Admin {mention_html(banner.id, banner.first_name)} gbanned user {mention_html(user_chat.id, user_chat.first_name)}\nReason: {reason}" , html=True)
    send_message(update.effective_message, f"Admin {mention_html(banner.id, banner.first_name)} gbanned user {mention_html(user_chat.id, user_chat.first_name)}\nReason: {reason}" , parse_mode=ParseMode.HTML)


@run_async
def ungban(update, context):
    message = update.effective_message  # type: Optional[Message]
    chat_name = update.effective_message.chat.title
    args = context.args

    user_id = extract_user(message, args)
    if not user_id:
        send_message(update.effective_message, "You don't seem to be referring to a user.")
        return
    if user_id == "error":
        send_message(update.effective_message, "Error: Unknown user!")
        return ""

    user_chat = context.bot.get_chat(user_id)
    if user_chat.type != 'private':
        send_message(update.effective_message, "That's not a user!")
        return

    if not sql.is_user_gbanned(user_id):
        send_message(update.effective_message, "This user is not gbanned!")
        return

    banner = update.effective_user  # type: Optional[User]

    send_message(update.effective_message, "I'll give {} a second chance, globally.".format(user_chat.first_name))

    send_to_list(context.bot, SUDO_USERS + SUPPORT_USERS,
                 "{} has ungbanned user {}".format(mention_html(banner.id, banner.first_name),
                                                   mention_html(user_chat.id, user_chat.first_name)),
                 html=True)

    sql.ungban_user(user_id)

    

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = context.bot.get_chat_member(chat_id, user_id)
            if member.status == 'kicked':
                context.bot.unban_chat_member(chat_id, user_id)

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                send_message(update.effective_message, "Could not un-gban due to: {}".format(excp.message))
                context.bot.send_message(OWNER_ID, "Could not un-gban due to: {}".format(excp.message))
                return
        except TelegramError:
            pass

    log_message = (f"#UNGBANNED\n"
                  f"<b>Originated from:</b> {chat_name}\n"
                  f"<b>Admin:</b> {mention_html(banner.id, banner.first_name)}\n"
                  f"<b>Banned User:</b> {mention_html(user_chat.id, user_chat.first_name)}\n"
                  f"<b>Banned User ID:</b> {user_chat.id}")

    if GBAN_LOGS:
        context.bot.send_message(GBAN_LOGS, log_message, parse_mode=ParseMode.HTML)
    # send_to_list(context.bot, SUDO_USERS + SUPPORT_USERS, "un-gban complete!")

    # send_message(update.effective_message, "Person has been un-gbanned.")


@run_async
def gbanlist(update, context):
    banned_users = sql.get_gban_list()

    if not banned_users:
        send_message(update.effective_message, "There aren't any gbanned users! You're kinder than I expected...")
        return

    banfile = 'Screw these guys.\n'
    for user in banned_users:
        banfile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            banfile += "Reason: {}\n".format(user["reason"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(document=output, filename="gbanlist.txt",
                                                caption="Here is the list of currently gbanned users.")


def check_and_ban(update, user_id, should_message=True):
    if sql.is_user_gbanned(user_id):
        update.effective_chat.kick_member(user_id)
        if should_message:
            send_message(update.effective_message, "This is a bad person, they shouldn't be here!")


@run_async
def enforce_gban(update, context):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    if sql.does_chat_gban(update.effective_chat.id) and update.effective_chat.get_member(context.bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, user.id)

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user  # type: Optional[User]
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id, should_message=False)


@run_async
@user_admin
def gbanstat(update, context):
    args = context.args
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            send_message(update.effective_message, "I've enabled gbans in this group. This will help protect you from spammers, unsavoury characters, and the biggest trolls.")
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            send_message(update.effective_message, "I've disabled gbans in this group. GBans wont affect your users anymore. You'll be less protected from any trolls and spammers though!")
    else:
        send_message(update.effective_message, "Give me some arguments to choose a setting! on/off, yes/no!\n\n"
                                                "Your current setting is: {}\n"
                                                "When True, any gbans that happen will also happen in your group." 
                                                "When False, they won't, leaving you at the possible mercy of spammers.".format(sql.does_chat_gban(update.effective_chat.id)))


def __stats__():
    return "{} gbanned users.".format(sql.num_gbanned_users())


def __user_info__(user_id, chat_id):
    is_gbanned = sql.is_user_gbanned(user_id)

    text = "Globally banned: <b>{}</b>"
    if is_gbanned:
        text = text.format("Yes")
        user = sql.get_gbanned_user(user_id)
        if user.reason:
            text += "\nReason: {}".format(html.escape(user.reason))
    else:
        text = text.format("No")
    return text



def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "This chat is enforcing *gbans*: `{}`.".format(sql.does_chat_gban(chat_id))

"""
def __chat_settings_btn__(chat_id, user_id):
    getstatus = sql.does_chat_gban(chat_id)
    if getstatus:
        status = "✅ Aktif"
    else:
        status = "❎ Tidak Aktif"
    button = []
    button.append([InlineKeyboardButton(text=status, callback_data="set_gstats={}".format(chat_id))])
    return button

def GBAN_EDITBTN(bot: Bot, update: Update):
    query = update.callback_query
    user = update.effective_user
    print("User {} clicked button GBAN EDIT".format(user.id))
    chat_id = query.data.split("=")[1]
    isgban = sql.does_chat_gban(chat_id)
    if chat_id:
        button = []
        if isgban:
            sql.disable_gbans(chat_id)
            status = "❎ Tidak Aktif"
        else:
            sql.enable_gbans(chat_id)
            status = "✅ Aktif"
        chat = context.bot.get_chat(chat_id)
        text = "*{}* memiliki pengaturan berikut untuk modul *Welcomes/Goodbyes*:\n\n".format(escape_markdown(chat.title))
        text += "Obrolan ini memberlakukan *larangan global*: `{}`.".format(status)
        button.append([InlineKeyboardButton(text=status, callback_data="set_gstats={}".format(chat_id))])
        button.append([InlineKeyboardButton(text="Kembali", callback_data="stngs_back({})".format(chat_id))])
        query.message.edit_text(text=text,
                                  parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=InlineKeyboardMarkup(button))
        context.bot.answer_callback_query(query.id)
"""

__help__ = """
*Admin only:*
 - /gbanstat <on/off/yes/no>: Will disable the effect of global bans on your group, or return your current settings.

Gbans, also known as global bans, are used by the bot owners to ban spammers across all groups. This helps protect \
you and your groups by removing spam flooders as quickly as possible. They can be disabled for you group by calling \
/gbanstat
"""

__mod_name__ = "Global Bans"

GBAN_HANDLER = CommandHandler("gban", gban, pass_args=True,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
UNGBAN_HANDLER = CommandHandler("ungban", ungban, pass_args=True,
                                filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GBAN_LIST = CommandHandler("gbanlist", gbanlist,
                           filters=CustomFilters.sudo_filter | CustomFilters.support_filter)

GBAN_STATUS = CommandHandler("gbanstat", gbanstat, pass_args=True, filters=Filters.group)

GBAN_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gban)
# GBAN_BTNSET_HANDLER = CallbackQueryHandler(GBAN_EDITBTN, pattern=r"set_gstats")

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)
# dispatcher.add_handler(GBAN_BTNSET_HANDLER)

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
