import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, InlineKeyboardMarkup, ChatPermissions
from telegram import ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

from metabutler import dispatcher, updater, LOGGER
from metabutler.modules.disable import DisableAbleCommandHandler
from metabutler.modules.helper_funcs.chat_status import bot_admin, can_promote, user_admin, can_pin
from metabutler.modules.helper_funcs.extraction import extract_user
from metabutler.modules.helper_funcs.msg_types import get_message_type
from metabutler.modules.helper_funcs.misc import build_keyboard_alternate
from metabutler.modules.log_channel import loggable
from metabutler.modules.connection import connected
from metabutler.modules.sql import admin_sql as sql

from metabutler.modules.helper_funcs.alternate import send_message

ENUM_FUNC_MAP = {
	'Types.TEXT': dispatcher.bot.send_message,
	'Types.BUTTON_TEXT': dispatcher.bot.send_message,
	'Types.STICKER': dispatcher.bot.send_sticker,
	'Types.DOCUMENT': dispatcher.bot.send_document,
	'Types.PHOTO': dispatcher.bot.send_photo,
	'Types.AUDIO': dispatcher.bot.send_audio,
	'Types.VOICE': dispatcher.bot.send_voice,
	'Types.VIDEO': dispatcher.bot.send_video
}


@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def promote(update, context):
	chat_id = update.effective_chat.id
	message = update.effective_message  # type: Optional[Message]
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	args = context.args

	conn = connected(context.bot, update, chat, user.id, need_admin=True)
	if conn:
		chat = dispatcher.bot.getChat(conn)
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		if update.effective_message.chat.type == "private":
			send_message(update.effective_message, "You can do this command in groups, not PM")
			return ""
		chat = update.effective_chat
		chat_id = update.effective_chat.id
		chat_name = update.effective_message.chat.title

	user_id = extract_user(message, args)
	if not user_id:
		send_message(update.effective_message, "You don't seem to be referring to a user.")
		return ""
	if user_id == "error":
		send_message(update.effective_message, "Error: Unknown user!")
		return ""

	user_member = chat.get_member(user_id)
	if user_member.status == 'administrator' or user_member.status == 'creator':
		send_message(update.effective_message, "How am I meant to promote someone that's already an admin?")
		return ""

	if user_id == context.bot.id:
		send_message(update.effective_message, "I can't promote myself! Get an admin to do it for me.")
		return ""

	# set same perms as bot - bot can't assign higher perms than itself!
	bot_member = chat.get_member(context.bot.id)

	try:
		context.bot.promote_chat_member(chat_id, user_id,
							  # can_change_info=bot_member.can_change_info,
							  can_post_messages=bot_member.can_post_messages,
							  can_edit_messages=bot_member.can_edit_messages,
							  can_delete_messages=bot_member.can_delete_messages,
							  can_invite_users=bot_member.can_invite_users,
							  can_restrict_members=bot_member.can_restrict_members,
							  can_pin_messages=bot_member.can_pin_messages,
							  # can_promote_members=bot_member.can_promote_members
							)
	except BadRequest as error:
		if error.message == "Bot_groups_blocked":
			send_message(update.effective_message, "Failed to promote: Bot was locked")
		else:
			send_message(update.effective_message, "Cannot promote users, maybe I am not admin or do not have permission to promote users.")
		return

	send_message(update.effective_message, f"Admin {mention_html(user.id, user.first_name)} promoted {mention_html(user_member.user.id, user_member.user.first_name)}", parse_mode=ParseMode.HTML)
	
	return "<b>{}:</b>" \
		   "\n#PROMOTED" \
		   "\n<b>Admin:</b> {}" \
		   "\n<b>User:</b> {}".format(html.escape(chat.title),
					mention_html(user.id, user.first_name),
					mention_html(user_member.user.id, user_member.user.first_name))


@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def demote(update, context):
	chat = update.effective_chat  # type: Optional[Chat]
	message = update.effective_message  # type: Optional[Message]
	user = update.effective_user  # type: Optional[User]
	args = context.args

	conn = connected(context.bot, update, chat, user.id, need_admin=True)
	if conn:
		chat = dispatcher.bot.getChat(conn)
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		if update.effective_message.chat.type == "private":
			send_message(update.effective_message, "You can do this command in groups, not PM")
			return ""
		chat = update.effective_chat
		chat_id = update.effective_chat.id
		chat_name = update.effective_message.chat.title

	user_id = extract_user(message, args)
	if not user_id:
		send_message(update.effective_message, "You don't seem to be referring to a user.")
		return ""
	if user_id == "error":
		send_message(update.effective_message, "Error: Unknown user!")
		return ""

	user_member = chat.get_member(user_id)
	if user_member.status == 'creator':
		send_message(update.effective_message, "This person CREATED the chat, how would I demote them?")
		return ""

	if not user_member.status == 'administrator':
		send_message(update.effective_message, "Can't demote what wasn't promoted!")
		return ""

	if user_id == context.bot.id:
		send_message(update.effective_message, "I can't demote myself! Get an admin to do it for me.")
		return ""

	try:
		context.bot.promoteChatMember(int(chat.id), int(user_id),
							  can_change_info=False,
							  can_post_messages=False,
							  can_edit_messages=False,
							  can_delete_messages=False,
							  can_invite_users=False,
							  can_restrict_members=False,
							  can_pin_messages=False,
							  can_promote_members=False
							)
		send_message(update.effective_message, f"Admin {mention_html(user.id, user.first_name)} demoted {mention_html(user_member.user.id, user_member.user.first_name)}", parse_mode=ParseMode.HTML)
		return "<b>{}:</b>" \
			   "\n#DEMOTED" \
			   "\n<b>Admin:</b> {}" \
			   "\n<b>User:</b> {}".format(html.escape(chat.title),
										  mention_html(user.id, user.first_name),
										  mention_html(user_member.user.id, user_member.user.first_name))

	except BadRequest:
		send_message(update.effective_message, "Could not demote. I might not be admin, or the admin status was appointed by another user, so I can't act upon them!")
		return ""


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def pin(update, context):
	user = update.effective_user  # type: Optional[User]
	chat = update.effective_chat  # type: Optional[Chat]
	args = context.args
	pin_args = update.message.text.split()

	conn = connected(context.bot, update, chat, user.id, need_admin=True)
	if conn:
		chat = dispatcher.bot.getChat(conn)
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
		if len(args) <= 1:
			send_message(update.effective_message, "Use /pin <notify/loud/silent/violent> <message link>")
			return ""
		prev_message = args[1]
		if "/" in prev_message:
			prev_message = prev_message.split("/")[-1]
	else:
		if update.effective_message.chat.type == "private":
			send_message(update.effective_message, "You can do this command in groups, not PM")
			return ""
		chat = update.effective_chat
		chat_id = update.effective_chat.id
		chat_name = update.effective_message.chat.title
		if update.effective_message.reply_to_message:
			prev_message = update.effective_message.reply_to_message.message_id
		else:
			send_message(update.effective_message, "Reply to a message for pin that message in this group")
			return ""

	is_group = chat.type != "private" and chat.type != "channel"

	is_silent = False
	if len(pin_args) > 1:
		if pin_args[1].lower() == 'silent' or pin_args[1].lower() == 'off' or pin_args[1].lower() == 'mute':
			is_silent = True
	if len(pin_args) == 1:
		is_silent = True

	if prev_message and is_group:
		try:
			context.bot.pinChatMessage(chat.id, prev_message) if is_silent else context.bot.pinChatMessage(chat.id, prev_message, disable_notification=is_silent)
			if conn:
				send_message(update.effective_message, "I have pinned messages in the group {}".format(chat_name))
		except BadRequest as excp:
			if excp.message == "Chat_not_modified":
				pass
			else:
				raise
		return "<b>{}:</b>" \
			   "\n#PINNED" \
			   "\n<b>Admin:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name))

	return ""


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def unpin(update, context):
	chat = update.effective_chat
	user = update.effective_user  # type: Optional[User]
	args = context.args

	conn = connected(context.bot, update, chat, user.id, need_admin=True)
	if conn:
		chat = dispatcher.bot.getChat(conn)
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		if update.effective_message.chat.type == "private":
			send_message(update.effective_message, "You can do this command in groups, not PM")
			return ""
		chat = update.effective_chat
		chat_id = update.effective_chat.id
		chat_name = update.effective_message.chat.title

	try:
		context.bot.unpinChatMessage(chat.id)
		if conn:
			send_message(update.effective_message, "I have unpin the message in the group {}".format(chat_name))
	except BadRequest as excp:
		if excp.message == "Chat_not_modified":
			pass
		else:
			raise

	return "<b>{}:</b>" \
		   "\n#UNPINNED" \
		   "\n<b>Admin:</b> {}".format(html.escape(chat.title),
					mention_html(user.id, user.first_name))


# @run_async
# @bot_admin
# @user_admin
# def invite(update, context):
# 	chat = update.effective_chat  # type: Optional[Chat]
# 	user = update.effective_user  # type: Optional[User]
# 	args = context.args

# 	conn = connected(context.bot, update, chat, user.id, need_admin=True)
# 	if conn:
# 		chat = dispatcher.bot.getChat(conn)
# 		chat_id = conn
# 		chat_name = dispatcher.bot.getChat(conn).title
# 	else:
# 		if update.effective_message.chat.type == "private":
# 			send_message(update.effective_message, "You can do this command in groups, not PM")
# 			return ""
# 		chat = update.effective_chat
# 		chat_id = update.effective_chat.id
# 		chat_name = update.effective_message.chat.title

# 	if chat.username:
# 		send_message(update.effective_message, chat.username)
# 	elif chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
# 		bot_member = chat.get_member(context.bot.id)
# 		if bot_member.can_invite_users:
# 			invitelink = context.bot.exportChatInviteLink(chat.id)
# 			send_message(update.effective_message, invitelink)
# 		else:
# 			send_message(update.effective_message, "I don't have access to the invite link, try changing my permissions!")
# 	else:
# 		send_message(update.effective_message, "I can only give you invite links for supergroups and channels, sorry!")


@run_async
def adminlist(update, context):
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	args = context.args

	conn = connected(context.bot, update, chat, user.id, need_admin=False)
	if conn:
		chat = dispatcher.bot.getChat(conn)
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		if update.effective_message.chat.type == "private":
			send_message(update.effective_message, "You can do this command in groups, not PM")
			return ""
		chat = update.effective_chat
		chat_id = update.effective_chat.id
		chat_name = update.effective_message.chat.title

	administrators = context.bot.getChatAdministrators(chat_id)
	text = "Admin in *{}*:".format(update.effective_chat.title or "current chat")
	for admin in administrators:
		user = admin.user
		status = admin.status
		if user.first_name == '':
			name = "☠ Deleted Account"
		else:
			name = "{}".format(mention_markdown(user.id, user.first_name + " " + (user.last_name or "")))
		#if user.username:
		#    name = escape_markdown("@" + user.username)
		if status == "creator":
			text += "\n 👑 *Creator:*"
			text += "\n • {} (`{}`) \n\n 🔱 *Admins:*".format(name, user.id)
	for admin in administrators:
		user = admin.user
		status = admin.status
		if user.first_name == '':
			name = "☠ Deleted Account"
		else:
			name = "{}".format(mention_markdown(user.id, user.first_name + " " + (user.last_name or "")))
		#if user.username:
		#    name = escape_markdown("@" + user.username)
		if status == "administrator":
			text += "\n • {} (`{}`)".format(name, user.id)

	try:
		send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)
	except BadRequest:
		send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN, quote=False)


@run_async
@can_pin
@user_admin
def permapin(update, context):
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	message = update.effective_message  # type: Optional[Message]
	args = context.args

	conn = connected(context.bot, update, chat, user.id, need_admin=False)
	if conn:
		chat = dispatcher.bot.getChat(conn)
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		if update.effective_message.chat.type == "private":
			send_message(update.effective_message, "You can do this command in groups, not PM")
			return ""
		chat = update.effective_chat
		chat_id = update.effective_chat.id
		chat_name = update.effective_message.chat.title

	text, data_type, content, buttons = get_message_type(message)
	tombol = build_keyboard_alternate(buttons)
	try:
		message.delete()
	except BadRequest:
		pass
	if str(data_type) in ('Types.BUTTON_TEXT', 'Types.TEXT'):
		try:
			sendingmsg = context.bot.send_message(chat_id, text, parse_mode="markdown",
								 disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(tombol))
		except BadRequest:
			context.bot.send_message(chat_id, "Wrong markdown text!\nIf you don't know what markdown is, please type `/markdownhelp` in PM.", parse_mode="markdown")
			return
	else:
		sendingmsg = ENUM_FUNC_MAP[str(data_type)](chat_id, content, caption=text, parse_mode="markdown", disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(tombol))
	try:
		context.bot.pinChatMessage(chat_id, sendingmsg.message_id)
	except BadRequest:
		send_message(update.effective_message, "I don't have access to pin message!")


@run_async
@can_pin
@user_admin
def permanent_pin_set(update, context):
	user = update.effective_user  # type: Optional[User]
	chat = update.effective_chat  # type: Optional[Chat]
	args = context.args

	conn = connected(context.bot, update, chat, user.id, need_admin=True)
	if conn:
		chat = dispatcher.bot.getChat(conn)
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
		if not args:
			get_permapin = sql.get_permapin(chat_id)
			text_maker = "Current permanent pin: `{}`".format(bool(int(get_permapin)))
			if get_permapin:
				if chat.username:
					old_pin = "https://t.me/{}/{}".format(chat.username, get_permapin)
				else:
					old_pin = "https://t.me/c/{}/{}".format(str(chat.id)[4:], get_permapin)
				text_maker += "\nTo disable permanent pin: `/permanentpin off`"
				text_maker += "\n\n[Permanent pin message is here]({})".format(old_pin)
			send_message(update.effective_message, text_maker, parse_mode="markdown")
			return ""
		prev_message = args[0]
		if prev_message == "off":
			sql.set_permapin(chat_id, 0)
			send_message(update.effective_message, "Permanent pin has been disabled!")
			return
		if "/" in prev_message:
			prev_message = prev_message.split("/")[-1]
	else:
		if update.effective_message.chat.type == "private":
			send_message(update.effective_message, "You can do this command in groups, not PM")
			return ""
		chat = update.effective_chat
		chat_id = update.effective_chat.id
		chat_name = update.effective_message.chat.title
		if update.effective_message.reply_to_message:
			prev_message = update.effective_message.reply_to_message.message_id
		elif len(args) >= 1 and args[0] == "off":
			sql.set_permapin(chat.id, 0)
			send_message(update.effective_message, "Permanent pin has been disabled!")
			return
		else:
			get_permapin = sql.get_permapin(chat_id)
			text_maker = tl(update.effective_message, "Successfully set permanent pin: `{}`").format(bool(int(get_permapin)))
			if get_permapin:
				if chat.username:
					old_pin = "https://t.me/{}/{}".format(chat.username, get_permapin)
				else:
					old_pin = "https://t.me/c/{}/{}".format(str(chat.id)[4:], get_permapin)
				text_maker += "\nTo disable permanent pin: `/permanentpin off`"
				text_maker += "\n\n[Permanent pin message is here]({})".format(old_pin)
			send_message(update.effective_message, text_maker, parse_mode="markdown")
			return ""

	is_group = chat.type != "private" and chat.type != "channel"

	if prev_message and is_group:
		sql.set_permapin(chat.id, prev_message)
		send_message(update.effective_message, "Successfully set permanent pin!")
		return "<b>{}:</b>" \
			   "\n#PERMANENT_PIN" \
			   "\n<b>Admin:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name))

	return ""


@run_async
def permanent_pin(update, context):
	user = update.effective_user  # type: Optional[User]
	chat = update.effective_chat  # type: Optional[Chat]
	message = update.effective_message
	args = context.args

	get_permapin = sql.get_permapin(chat.id)
	if get_permapin and not user.id == context.bot.id:
		try:
			to_del = context.bot.pinChatMessage(chat.id, get_permapin, disable_notification=True)
		except BadRequest:
			sql.set_permapin(chat.id, 0)
			if chat.username:
				old_pin = "https://t.me/{}/{}".format(chat.username, get_permapin)
			else:
				old_pin = "https://t.me/c/{}/{}".format(str(chat.id)[4:], get_permapin)
			send_message(update.effective_message, "*Permanent pin error:*\nI can't pin messages here!\nMake sure I'm admin and can pin messages.\n\nPermanent pin disabled now, [here is your old pinned message]({})".format(old_pin), parse_mode="markdown")
			return

		if to_del:
			try:
				context.bot.deleteMessage(chat.id, message.message_id+1)
			except BadRequest:
				print("Permanent pin error: cannot delete pin msg")
	


def __chat_settings__(chat_id, user_id):
	administrators = dispatcher.bot.getChatAdministrators(chat_id)
	chat = dispatcher.bot.getChat(chat_id)
	text = "Admin in *{}*:".format(chat.title or "current chat")
	for admin in administrators:
		user = admin.user
		status = admin.status
		if user.first_name == '':
			name = user_id, "☠ Deleted Account"
		else:
			name = "{}".format(mention_markdown(user.id, user.first_name + " " + (user.last_name or "")))
		#if user.username:
		#    name = escape_markdown("@" + user.username)
		if status == "creator":
			text += "\n 👑 Creator:"
			text += "\n` • `{} \n\n 🔱 Admins:".format(name)
	for admin in administrators:
		user = admin.user
		status = admin.status
		if user.first_name == '':
			name = user_id, "☠ Deleted Account"
		else:
			name = "{}".format(mention_markdown(user.id, user.first_name + " " + (user.last_name or "")))
		#if user.username:
		#    name = escape_markdown("@" + user.username)
		if status == "administrator":
			text += "\n` • `{}".format(name)
	text += user_id, "\n\nYou are *{}*".format(dispatcher.bot.get_chat_member(chat_id, user_id).status)
	return text


__help__ = """
 - /adminlist | /admins: list of admins in the chat
*Admin only:*
 - /pin: silently pins the message replied to - add 'loud' or 'notify' to give notifs to users.
 - /unpin: unpins the currently pinned message
 - /permapin <text>: Pin a custom messages via bots. This message can contain markdown, and can be used in replies to the media include additional buttons and text.
 - /permanentpin: Set a permanent pin for supergroup chat, when an admin or telegram channel change pinned message, bot will change pinned message immediatelly
 - /promote: promotes the user replied to
 - /demote: demotes the user replied to
"""

__mod_name__ = "Admin"

PIN_HANDLER = CommandHandler("pin", pin, pass_args=True, filters=Filters.group)
UNPIN_HANDLER = CommandHandler("unpin", unpin, filters=Filters.group)
PERMAPIN_HANDLER = CommandHandler("permapin", permapin, filters=Filters.group)

# INVITE_HANDLER = CommandHandler("invitelink", invite, filters=Filters.group)

PROMOTE_HANDLER = CommandHandler("promote", promote, pass_args=True, filters=Filters.group)
DEMOTE_HANDLER = CommandHandler("demote", demote, pass_args=True, filters=Filters.group)

PERMANENT_PIN_SET_HANDLER = CommandHandler("permanentpin", permanent_pin_set, pass_args=True, filters=Filters.group)
PERMANENT_PIN_HANDLER = MessageHandler(Filters.status_update.pinned_message | Filters.user(777000), permanent_pin)

ADMINLIST_HANDLER = DisableAbleCommandHandler(["adminlist", "admins"], adminlist)

dispatcher.add_handler(PIN_HANDLER)
dispatcher.add_handler(UNPIN_HANDLER)
dispatcher.add_handler(PERMAPIN_HANDLER)
# dispatcher.add_handler(INVITE_HANDLER)
dispatcher.add_handler(PROMOTE_HANDLER)
dispatcher.add_handler(DEMOTE_HANDLER)
dispatcher.add_handler(PERMANENT_PIN_SET_HANDLER)
dispatcher.add_handler(PERMANENT_PIN_HANDLER)
dispatcher.add_handler(ADMINLIST_HANDLER)
