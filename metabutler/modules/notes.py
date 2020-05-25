import re, ast
from io import BytesIO
from typing import Optional, List

from telegram import MAX_MESSAGE_LENGTH, ParseMode, InlineKeyboardMarkup
from telegram import Message, Update, Bot
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown, mention_markdown

import metabutler.modules.sql.notes_sql as sql
from metabutler import dispatcher, MESSAGE_DUMP, LOGGER, OWNER_ID
from metabutler.modules.disable import DisableAbleCommandHandler
from metabutler.modules.helper_funcs.chat_status import user_admin
from metabutler.modules.helper_funcs.misc import build_keyboard_parser, revert_buttons
from metabutler.modules.helper_funcs.msg_types import get_note_type
from metabutler.modules.helper_funcs.string_handling import escape_invalid_curly_brackets

from metabutler.modules.connection import connected
from metabutler.modules.helper_funcs.alternate import send_message

FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")
STICKER_MATCHER = re.compile(r"^###sticker(!photo)?###:")
BUTTON_MATCHER = re.compile(r"^###button(!photo)?###:(.*?)(?:\s|$)")
MYFILE_MATCHER = re.compile(r"^###file(!photo)?###:")
MYPHOTO_MATCHER = re.compile(r"^###photo(!photo)?###:")
MYAUDIO_MATCHER = re.compile(r"^###audio(!photo)?###:")
MYVOICE_MATCHER = re.compile(r"^###voice(!photo)?###:")
MYVIDEO_MATCHER = re.compile(r"^###video(!photo)?###:")
MYVIDEONOTE_MATCHER = re.compile(r"^###video_note(!photo)?###:")

ENUM_FUNC_MAP = {
	sql.Types.TEXT.value: dispatcher.bot.send_message,
	sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
	sql.Types.STICKER.value: dispatcher.bot.send_sticker,
	sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
	sql.Types.PHOTO.value: dispatcher.bot.send_photo,
	sql.Types.AUDIO.value: dispatcher.bot.send_audio,
	sql.Types.VOICE.value: dispatcher.bot.send_voice,
	sql.Types.VIDEO.value: dispatcher.bot.send_video,
	sql.Types.VIDEO_NOTE.value: dispatcher.bot.send_video_note
}


# Do not async
def get(bot, update, notename, show_none=True, no_format=False):
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	conn = connected(bot, update, chat, user.id, need_admin=False)
	if conn:
		chat_id = conn
		send_id = user.id
	else:
		chat_id = update.effective_chat.id
		send_id = chat_id

	note = sql.get_note(chat_id, notename)
	message = update.effective_message  # type: Optional[Message]

	if note:
		# If we're replying to a message, reply to that message (unless it's an error)
		if message.reply_to_message:
			reply_id = message.reply_to_message.message_id
		else:
			reply_id = message.message_id

		if note.is_reply:
			if MESSAGE_DUMP:
				try:
					bot.forward_message(chat_id=chat_id, from_chat_id=MESSAGE_DUMP, message_id=note.value)
				except BadRequest as excp:
					if excp.message == "Message to forward not found":
						send_message(update.effective_message, "This message seems to have been lost - I'll remove it from your notes list.")
						sql.rm_note(chat_id, notename)
					else:
						raise
			else:
				try:
					bot.forward_message(chat_id=chat_id, from_chat_id=chat_id, message_id=note.value)
				except BadRequest as excp:
					if excp.message == "Message to forward not found":
						send_message(update.effective_message, "Looks like the original sender of this note has deleted their message - sorry! Get your bot admin to start using a message dump to avoid this. I'll remove this note from your saved notes.")
						sql.rm_note(chat_id, notename)
					else:
						raise
		else:

			VALID_WELCOME_FORMATTERS = ['first', 'last', 'fullname', 'username', 'id', 'chatname', 'mention', 'rules']
			valid_format = escape_invalid_curly_brackets(note.value, VALID_WELCOME_FORMATTERS)
			if valid_format:
				text = valid_format.format(first=escape_markdown(message.from_user.first_name),
											  last=escape_markdown(message.from_user.last_name or message.from_user.first_name),
											  fullname=escape_markdown(" ".join([message.from_user.first_name, message.from_user.last_name] if message.from_user.last_name else [message.from_user.first_name])), username="@" + message.from_user.username if message.from_user.username else mention_markdown(message.from_user.id, message.from_user.first_name), mention=mention_markdown(message.from_user.id, message.from_user.first_name), chatname=escape_markdown(message.chat.title if message.chat.type != "private" else message.from_user.first_name), id=message.from_user.id, rules="http://t.me/{}?start={}".format(bot.username, chat_id))
			else:
				text = ""

			keyb = []
			parseMode = ParseMode.MARKDOWN
			buttons = sql.get_buttons(chat_id, notename)
			if no_format:
				parseMode = None
				text += revert_buttons(buttons)
			else:
				keyb = build_keyboard_parser(bot, chat_id, buttons)

			keyboard = InlineKeyboardMarkup(keyb)

			try:
				is_private, is_delete = sql.get_private_note(chat.id)
				if note.msgtype in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
					try:
						if is_delete:
							update.effective_message.delete()
						if is_private:
							bot.send_message(user.id, text,
										 parse_mode=parseMode, disable_web_page_preview=True,
										 reply_markup=keyboard)
						else:
							bot.send_message(send_id, text, reply_to_message_id=reply_id,
										 parse_mode=parseMode, disable_web_page_preview=True,
										 reply_markup=keyboard)
					except BadRequest as excp:
						if excp.message == "Wrong http url":
							failtext = "Error: URL on the button is invalid! Please update this note."
							failtext += "\n\n```\n{}```".format(note.value + revert_buttons(buttons))
							send_message(update.effective_message, failtext, parse_mode="markdown")
						elif excp.message == "Button_url_invalid":
							failtext = "Error: URL on the button is invalid! Please update this note."
							failtext += "\n\n```\n{}```".format(note.value + revert_buttons(buttons))
							send_message(update.effective_message, failtext, parse_mode="markdown")
						elif excp.message == "Message can't be deleted":
							pass
						elif excp.message == "Have no rights to send a message":
							pass
					except Unauthorized as excp:
						send_message(update.effective_message, "Contact me in PM first to get this note.", parse_mode="markdown")
						pass
				else:
					try:
						if is_delete:
							update.effective_message.delete()
						if is_private:
							ENUM_FUNC_MAP[note.msgtype](user.id, note.file, caption=text, parse_mode=parseMode, disable_web_page_preview=True, reply_markup=keyboard)
						else:
							ENUM_FUNC_MAP[note.msgtype](send_id, note.file, caption=text, reply_to_message_id=reply_id, parse_mode=parseMode, disable_web_page_preview=True, reply_markup=keyboard)
					except BadRequest as excp:
						if excp.message == "Message can't be deleted":
							pass
						elif excp.message == "Have no rights to send a message":
							pass
					except Unauthorized as excp:
						send_message(update.effective_message, "Contact me in PM first to get this note.", parse_mode="markdown")
						pass
					
			except BadRequest as excp:
				if excp.message == "Entity_mention_user_invalid":
					send_message(update.effective_message, "Looks like you tried to mention someone I've never seen before. If you really want to mention them, forward one of their messages to me, and I'll be able to tag them!")
				elif FILE_MATCHER.match(note.value):
					send_message(update.effective_message, "This note was an incorrectly imported file from another bot - I can't use it. If you really need it, you'll have to save it again. In the meantime, I'll remove it from your notes list.")
					sql.rm_note(chat_id, notename)
				else:
					send_message(update.effective_message, "This note could not be sent, as it is incorrectly formatted.")
					LOGGER.exception("Unable to parse message #%s in chat %s", notename, str(chat_id))
					LOGGER.warning("Message it: %s", str(note.value))
		return
	elif show_none:
		send_message(update.effective_message, "This note doesn't exist")


@run_async
def cmd_get(update, context):
	args = context.args
	if len(args) >= 2 and args[1].lower() == "noformat":
		get(context.bot, update, args[0], show_none=True, no_format=True)
	elif len(args) >= 1:
		get(context.bot, update, args[0], show_none=True)
	else:
		send_message(update.effective_message, "Get what?")


@run_async
def hash_get(update, context):
	message = update.effective_message.text
	fst_word = message.split()[0]
	no_hash = fst_word[1:]
	get(context.bot, update, no_hash, show_none=False)


# TODO: FIX THIS
@run_async
@user_admin
def save(update, context):
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	conn = connected(context.bot, update, chat, user.id)
	if conn:
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		chat_id = update.effective_chat.id
		if chat.type == "private":
			chat_name = "local note"
		else:
			chat_name = chat.title

	msg = update.effective_message  # type: Optional[Message]

	checktext = msg.text.split()
	if msg.reply_to_message:
		if len(checktext) <= 1:
			send_message(update.effective_message, "You must give a name for this note!")
			return
	else:
		if len(checktext) <= 2:
			send_message(update.effective_message, "You must give a name for this note!")
			return

	note_name, text, data_type, content, buttons = get_note_type(msg)

	if data_type is None:
		send_message(update.effective_message, "Dude, there's no note")
		return

	if len(text.strip()) == 0:
		text = "`" + note_name + "`"
		
	sql.add_note_to_db(chat_id, note_name, text, data_type, buttons=buttons, file=content)
	if conn:
		savedtext = "Ok, saved note `{note_name}` in *{chat_name}*.".format(note_name=note_name, chat_name=chat_name)
	else:
		savedtext = "Ok, saved note `{note_name}`.".format(note_name=note_name)
	try:
		send_message(update.effective_message, savedtext, parse_mode=ParseMode.MARKDOWN)
	except BadRequest:
		if conn:
			savedtext = "Ok, saved note <code>{note_name}</code> in <b>{chat_name}</b>.".format(note_name=note_name, chat_name=chat_name)
		else:
			savedtext = "Ok, saved note <code>{note_name}</code>.".format(note_name=note_name)
		send_message(update.effective_message, savedtext, parse_mode=ParseMode.HTML)

	#if msg.reply_to_message and msg.reply_to_message.from_user.is_bot:
	#    if text:
	#        send_message(update.effective_message, "Sepertinya Anda mencoba menyimpan pesan dari bot. Sayangnya, "
	#                       "bot tidak dapat meneruskan pesan bot, jadi saya tidak dapat menyimpan pesan yang tepat. "
	#                       "\nSaya akan menyimpan semua teks yang saya bisa, tetapi jika Anda menginginkan lebih banyak, "
	#                       "Anda harus melakukannya meneruskan pesan sendiri, lalu simpan.")
	#    else:
	#        send_message(update.effective_message, "Bot agak cacat oleh telegram, sehingga sulit untuk berinteraksi dengan "
	#                       "bot lain, jadi saya tidak dapat menyimpan pesan ini. "
	#                       "Apakah Anda keberatan meneruskannya dan "
	#                       "lalu menyimpan pesan baru itu? Terima kasih! ☺️")
	#    return


@run_async
@user_admin
def clear(update, context):
	args = context.args
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	conn = connected(context.bot, update, chat, user.id)
	if conn:
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		chat_id = update.effective_chat.id
		if chat.type == "private":
			chat_name = "local notes"
		else:
			chat_name = chat.title

	if len(args) >= 1:
		catatan = []
		catatangagal = []
		for x in range(len(args)):
			notename = args[x]
			if sql.rm_note(chat_id, notename):
				catatan.append(notename)
			else:
				catatangagal.append(notename)
		if len(catatan) >= 1 and len(catatangagal) == 0:
			if conn:
				rtext = "Note in *{chat_name}* for `{note_name}` deleted".format(chat_name=chat_name, note_name=", ".join(catatan))
			else:
				rtext = "Note `{note_name}` deleted".format(note_name=", ".join(catatan))
			try:
				send_message(update.effective_message, rtext, parse_mode=ParseMode.MARKDOWN)
			except BadRequest:
				if conn:
					rtext = "Note in <b>{chat_name}</b> for <code>{note_name}</code> deleted".format(chat_name=chat_name, note_name=", ".join(catatan))
				else:
					rtext = "Note <code>{note_name}</code> deleted".format(note_name=", ".join(catatan))
				send_message(update.effective_message, rtext, parse_mode=ParseMode.HTML)
		elif len(catatangagal) >= 0 and len(catatan) == 0:
			if conn:
				rtext = "Failed to delete note in *{chat_name}* for `{fnote_name}`!".format(chat_name=chat_name, fnote_name=", ".join(catatangagal))
			else:
				rtext = "Failed to delete note `{fnote_name}`!".format(fnote_name=", ".join(catatangagal))
			try:
				send_message(update.effective_message, rtext, parse_mode=ParseMode.MARKDOWN)
			except BadRequest:
				if conn:
					rtext = "Failed to delete note in <b>{chat_name}</b> for <code>{fnote_name}</code>!".format(chat_name=chat_name, fnote_name=", ".join(catatangagal))
				else:
					rtext = "Failed to delete note <code>{fnote_name}</code>!".format(fnote_name=", ".join(catatangagal))
				send_message(update.effective_message, rtext, parse_mode=ParseMode.HTML)
		else:
			if conn:
				rtext = "Note `{note_name}` deleted in *{chat_name}*\nFailed to delete note `{fnote_name}`!".format(chat_name=chat_name, note_name=", ".join(catatan), fnote_name=", ".join(catatangagal))
			else:
				rtext = "Note `{note_name}` deleted\nFailed to delete note `{fnote_name}`!".format(note_name=", ".join(catatan), fnote_name=", ".join(catatangagal))
			try:
				send_message(update.effective_message, rtext, parse_mode=ParseMode.MARKDOWN)
			except BadRequest:
				if conn:
					rtext = "Note <code>{note_name}</code> deleted in <b>{chat_name}</b>\nFailed to delete note <code>{fnote_name}</code>!".format(chat_name=chat_name, note_name=", ".join(catatan), fnote_name=", ".join(catatangagal))
				else:
					rtext = "Note <code>{note_name}</code> deleted\nFailed to delete note <code>{fnote_name}</code>!".format(note_name=", ".join(catatan), fnote_name=", ".join(catatangagal))
				send_message(update.effective_message, rtext, parse_mode=ParseMode.HTML)

	else:
		send_message(update.effective_message, "What you want to delete?")

@run_async
@user_admin
def private_note(update, context):
	args = context.args
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	conn = connected(context.bot, update, chat, user.id)
	if conn:
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
	else:
		chat_id = update.effective_chat.id
		if chat.type == "private":
			chat_name = chat.title
		else:
			chat_name = chat.title

	if len(args) >= 1:
		if args[0] in ("yes", "on"):
			if len(args) >= 2:
				if args[1] == "del":
					sql.private_note(str(chat_id), True, True)
					send_message(update.effective_message, "Private Note was *enabled*, when users get notes, the message will be sent to the PM and the hashtag message will be deleted.", parse_mode="markdown")
				else:
					sql.private_note(str(chat_id), True, False)
					send_message(update.effective_message, "Private Note was *enabled*, when users get notes, the message will be sent to the PM.", parse_mode="markdown")
			else:
				sql.private_note(str(chat_id), True, False)
				send_message(update.effective_message, "Private Note was *enabled*, when users get notes, the message will be sent to the PM.", parse_mode="markdown")
		elif args[0] in ("no", "off"):
			sql.private_note(str(chat_id), False, False)
			send_message(update.effective_message, "Private Note was *disabled*, notes will be sent to group.", parse_mode="markdown")
		else:
			send_message(update.effective_message, "Unknown argument - please use 'yes', or 'no'.")
	else:
		is_private, is_delete = sql.get_private_note(chat_id)
		print(is_private, is_delete)
		send_message(update.effective_message, "Current Private Note settings at {}: *{}*{}".format(chat_name, "Enabled" if is_private else "Disabled", " - *Hash will be deleted*" if is_delete else ""), parse_mode="markdown")


@run_async
def list_notes(update, context):
	chat = update.effective_chat  # type: Optional[Chat]
	user = update.effective_user  # type: Optional[User]
	conn = connected(context.bot, update, chat, user.id, need_admin=False)
	if conn:
		chat_id = conn
		chat_name = dispatcher.bot.getChat(conn).title
		msg = "*Notes in {}:*\n".format(chat_name)
	else:
		chat_id = update.effective_chat.id
		if chat.type == "private":
			chat_name = ""
			msg = "*Local notes:*\n"
		else:
			chat_name = chat.title
			msg = "*Notes in {}:*\n".format(chat_name)

	note_list = sql.get_all_chat_notes(chat_id)

	for note in note_list:
		note_name = " ➺  `#{}`\n".format(note.name)
		if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
			send_message(update.effective_message, msg, parse_mode=ParseMode.MARKDOWN)
			msg = ""
		msg += note_name

	if msg == "*Notes in {}:*\n".format(chat_name) or msg == "*Local notes:*\n":
		if conn:
			send_message(update.effective_message, "No notes in *{}*!".format(chat_name), parse_mode="markdown")
		else:
			send_message(update.effective_message, "No notes in this chat!")

	elif len(msg) != 0:
		msg += "\nYou can retrieve these notes by using `/get notename`, or `#notename`"
		try:
			send_message(update.effective_message, msg, parse_mode=ParseMode.MARKDOWN)
		except BadRequest:
			if chat.type == "private":
				chat_name = ""
				msg = "<b>Local notes:</b>\n"
			else:
				chat_name = chat.title
				msg = "<b>Notes in {}:</b>\n".format(chat_name)
			for note in note_list:
				note_name = " - <code>{}</code>\n".format(note.name)
				if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
					send_message(update.effective_message, msg, parse_mode=ParseMode.MARKDOWN)
					msg = ""
				msg += note_name
			msg += "\nYou can retrieve these notes by using <code>/get notename</code>, or <code>#notename</code>"
			send_message(update.effective_message, msg, parse_mode=ParseMode.HTML)


def __import_data__(chat_id, data):
	failures = []
	for notename, notedata in data.get('extra', {}).items():
		match = FILE_MATCHER.match(notedata)
		matchsticker = STICKER_MATCHER.match(notedata)
		matchbtn = BUTTON_MATCHER.match(notedata)
		matchfile = MYFILE_MATCHER.match(notedata)
		matchphoto = MYPHOTO_MATCHER.match(notedata)
		matchaudio = MYAUDIO_MATCHER.match(notedata)
		matchvoice = MYVOICE_MATCHER.match(notedata)
		matchvideo = MYVIDEO_MATCHER.match(notedata)
		matchvn = MYVIDEONOTE_MATCHER.match(notedata)

		if match:
			failures.append(notename)
			notedata = notedata[match.end():].strip()
			if notedata:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)
		elif matchsticker:
			content = notedata[matchsticker.end():].strip()
			if content:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.STICKER, file=content)
		elif matchbtn:
			parse = notedata[matchbtn.end():].strip()
			notedata = parse.split("<###button###>")[0]
			buttons = parse.split("<###button###>")[1]
			buttons = ast.literal_eval(buttons)
			if buttons:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.BUTTON_TEXT, buttons=buttons)
		elif matchfile:
			file = notedata[matchfile.end():].strip()
			file = file.split("<###TYPESPLIT###>")
			notedata = file[1]
			content = file[0]
			if content:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.DOCUMENT, file=content)
		elif matchphoto:
			photo = notedata[matchphoto.end():].strip()
			photo = photo.split("<###TYPESPLIT###>")
			notedata = photo[1]
			content = photo[0]
			if content:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.PHOTO, file=content)
		elif matchaudio:
			audio = notedata[matchaudio.end():].strip()
			audio = audio.split("<###TYPESPLIT###>")
			notedata = audio[1]
			content = audio[0]
			if content:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.AUDIO, file=content)
		elif matchvoice:
			voice = notedata[matchvoice.end():].strip()
			voice = voice.split("<###TYPESPLIT###>")
			notedata = voice[1]
			content = voice[0]
			if content:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.VOICE, file=content)
		elif matchvideo:
			video = notedata[matchvideo.end():].strip()
			video = video.split("<###TYPESPLIT###>")
			notedata = video[1]
			content = video[0]
			if content:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.VIDEO, file=content)
		elif matchvn:
			video_note = notedata[matchvn.end():].strip()
			video_note = video_note.split("<###TYPESPLIT###>")
			notedata = video_note[1]
			content = video_note[0]
			if content:
				sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.VIDEO_NOTE, file=content)
		else:
			sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)

	if failures:
		with BytesIO(str.encode("\n".join(failures))) as output:
			output.name = "failed_imports.txt"
			dispatcher.bot.send_document(chat_id, document=output, filename="failed_imports.txt",
										 caption="These files/photos failed to import due to originating from another bot. This is a telegram API restriction, and can't be avoided. Sorry for the inconvenience!")


def __stats__():
	return "{} notes, accross {} chats.".format(sql.num_notes(), sql.num_chats())


def __migrate__(old_chat_id, new_chat_id):
	sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
	notes = sql.get_all_chat_notes(chat_id)
	return "There are `{}` notes in this chat.".format(len(notes))


__help__ = """
 - /get <notename>: get the note with this notename
 - #<notename>: same as /get
 - /notes or /saved: list all saved notes in this chat

If you would like to retrieve the contents of a note without any formatting, use `/get <notename> noformat`. This can \
be useful when updating a current note.

*Admin only:*
 - /save <notename> <notedata>: saves notedata as a note with name notename
A button can be added to a note by using standard markdown link syntax - the link should just be prepended with a \
`buttonurl:` section, as such: `[somelink](buttonurl:example.com)`. Check /markdownhelp for more info.
 - /save <notename>: save the replied message as a note with name notename
 - /clear <notename>: clear note with this name
  - /privatenote <on/yes/off/no> <? del>: whether or not to send the note in PM. Write `del` besides on/off to delete hashtag message on group.
"""

__mod_name__ = "Notes"

GET_HANDLER = CommandHandler("get", cmd_get, pass_args=True)
HASH_GET_HANDLER = MessageHandler(Filters.regex(r"^#[^\s]+"), hash_get)

SAVE_HANDLER = CommandHandler("save", save)
DELETE_HANDLER = CommandHandler("clear", clear, pass_args=True)

PMNOTE_HANDLER = CommandHandler("privatenote", private_note, pass_args=True)

LIST_HANDLER = DisableAbleCommandHandler(["notes", "saved"], list_notes, admin_ok=True)

dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(PMNOTE_HANDLER)
dispatcher.add_handler(HASH_GET_HANDLER)
