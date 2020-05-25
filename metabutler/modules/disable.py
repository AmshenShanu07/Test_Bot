from typing import Union, List, Optional

from future.utils import string_types
from telegram import ParseMode, Update, Bot, Chat, User, MessageEntity
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram.utils.helpers import escape_markdown

from metabutler import dispatcher, OWNER_ID
from metabutler.modules.helper_funcs.handlers import CMD_STARTERS
from metabutler.modules.helper_funcs.misc import is_module_loaded
from metabutler.modules.connection import connected

from metabutler.modules.helper_funcs.alternate import send_message

FILENAME = __name__.rsplit(".", 1)[-1]

# If module is due to be loaded, then setup all the magical handlers
if is_module_loaded(FILENAME):
    from metabutler.modules.helper_funcs.chat_status import user_admin, is_user_admin
    from telegram.ext.dispatcher import run_async

    from metabutler.modules.sql import disable_sql as sql

    DISABLE_CMDS = []
    DISABLE_OTHER = []
    ADMIN_CMDS = []

    class DisableAbleCommandHandler(CommandHandler):
        def __init__(self, command, callback, admin_ok=False, **kwargs):
            super().__init__(command, callback, **kwargs)
            self.admin_ok = admin_ok
            if isinstance(command, string_types):
                DISABLE_CMDS.append(command)
                if admin_ok:
                    ADMIN_CMDS.append(command)
            else:
                DISABLE_CMDS.extend(command)
                if admin_ok:
                    ADMIN_CMDS.extend(command)
            sql.disableable_cache(command)

        def check_update(self, update):
            if isinstance(update, Update) and update.effective_message:
                message = update.effective_message

                if (message.entities and message.entities[0].type == MessageEntity.BOT_COMMAND
                        and message.entities[0].offset == 0):
                    command = message.text[1:message.entities[0].length]
                    args = message.text.split()[1:]
                    command = command.split('@')
                    command.append(message.bot.username)

                    if not (command[0].lower() in self.command
                            and command[1].lower() == message.bot.username.lower()):
                        return None

                    filter_result = self.filters(update)
                    if filter_result:
                        chat = update.effective_chat
                        user = update.effective_user
                        # disabled, admincmd, user admin
                        if sql.is_command_disabled(chat.id, command[0].lower()):
                            # check if command was disabled
                            is_disabled = command[0] in ADMIN_CMDS and is_user_admin(chat, user.id)
                            if not is_disabled and sql.is_disable_del(chat.id):
                                # disabled and should delete
                                update.effective_message.delete()
                            if not is_disabled:
                                return None
                            else:
                                return args, filter_result

                        return args, filter_result
                    else:
                        return False


    class DisableAbleMessageHandler(MessageHandler):
        def __init__(self, pattern, callback, friendly="", **kwargs):
            super().__init__(pattern, callback, **kwargs)
            DISABLE_OTHER.append(friendly or pattern)
            sql.disableable_cache(friendly or pattern)
            self.friendly = friendly or pattern

        def check_update(self, update):
            if isinstance(update, Update) and update.effective_message:
                chat = update.effective_chat
                return self.filters(update) and not sql.is_command_disabled(chat.id, self.friendly)


    @run_async
    @user_admin
    def disable(update, context):
        chat = update.effective_chat  # type: Optional[Chat]
        user = update.effective_user
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

        if len(args) >= 1:
            disable_cmd = args[0]
            if disable_cmd.startswith(CMD_STARTERS):
                disable_cmd = disable_cmd[1:]

            if disable_cmd in set(DISABLE_CMDS + DISABLE_OTHER):
                sql.disable_command(chat.id, disable_cmd)
                if conn:
                    text = "Disabled the use of `{}` in *{}*".format(disable_cmd, chat_name)
                else:
                    text = "Disabled the use of `{}`".format(disable_cmd)
                send_message(update.effective_message, text,
                                                    parse_mode=ParseMode.MARKDOWN)
            else:
                send_message(update.effective_message, "That command can't be disabled")

        else:
            send_message(update.effective_message, "What should I disable?")


    @run_async
    @user_admin
    def enable(update, context):
        chat = update.effective_chat  # type: Optional[Chat]
        user = update.effective_user
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

        if len(args) >= 1:
            enable_cmd = args[0]
            if enable_cmd.startswith(CMD_STARTERS):
                enable_cmd = enable_cmd[1:]

            if sql.enable_command(chat.id, enable_cmd):
                if conn:
                    text = "Enabled the use of `{}` in *{}*".format(enable_cmd, chat_name)
                else:
                    text = "Enabled the use of `{}`".format(enable_cmd)
                send_message(update.effective_message, text,
                                                    parse_mode=ParseMode.MARKDOWN)
            else:
                send_message(update.effective_message, "Is that even disabled?")

        else:
            send_message(update.effective_message, "What should I enable?")


    @run_async
    @user_admin
    def list_cmds(update, context):
        if DISABLE_CMDS + DISABLE_OTHER:
            result = ""
            for cmd in set(DISABLE_CMDS + DISABLE_OTHER):
                result += " - `{}`\n".format(escape_markdown(cmd))
            send_message(update.effective_message, "The following commands are toggleable:\n{}".format(result),
                                                parse_mode=ParseMode.MARKDOWN)
        else:
            send_message(update.effective_message, "No commands can be disabled.")

    @run_async
    @user_admin
    def disable_del(update, context):
        msg = update.effective_message
        chat = update.effective_chat

        if len(msg.text.split()) >= 2:
            args = msg.text.split(None, 1)[1]
            if args == "yes" or args == "on":
                sql.disabledel_set(chat.id, True)
                send_message(update.effective_message, "When command was disabled, I *will delete* that message.", parse_mode="markdown")
                return
            elif args == "no" or args == "off":
                sql.disabledel_set(chat.id, False)
                send_message(update.effective_message, "When command was disabled, I *will not delete* that message.", parse_mode="markdown")
                return
            else:
                send_message(update.effective_message, "Unknown argument - please use 'yes', or 'no'.")
        else:
            send_message(update.effective_message, "Current disable del settings: *{}*".format("Enabled" if sql.is_disable_del(chat.id) else "Disabled"), parse_mode="markdown")


    # do not async
    def build_curr_disabled(chat_id: Union[str, int]) -> str:
        disabled = sql.get_all_disabled(chat_id)
        if not disabled:
            return "No commands are disabled!"

        result = ""
        for cmd in disabled:
            result += " - `{}`\n".format(escape_markdown(cmd))
        return "The following commands are currently restricted:\n{}".format(result)


    @run_async
    def commands(update, context):
        chat = update.effective_chat
        user = update.effective_user
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

        text = build_curr_disabled(chat.id)
        send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)


    def __stats__():
        return "{} disabled items, across {} chats.".format(sql.num_disabled(), sql.num_chats())


    def __import_data__(chat_id, data):
        disabled = data.get('disabled', {})
        for disable_cmd in disabled:
            sql.disable_command(chat_id, disable_cmd)


    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)


    def __chat_settings__(chat_id, user_id):
        return build_curr_disabled(chat_id)


    __mod_name__ = "Command disabling"

    __help__ = """
 - /cmds: check the current status of disabled commands

*Admin only:*
 - /enable <cmd name>: enable that command
 - /disable <cmd name>: disable that command
 - /listcmds: list all possible toggleable commands
 - /disabledel: delete message when command is disabled
    """

    DISABLE_HANDLER = CommandHandler("disable", disable, pass_args=True)#, filters=Filters.group)
    ENABLE_HANDLER = CommandHandler("enable", enable, pass_args=True)#, filters=Filters.group)
    COMMANDS_HANDLER = CommandHandler(["cmds", "disabled"], commands)#, filters=Filters.group)
    TOGGLE_HANDLER = CommandHandler("listcmds", list_cmds)#, filters=Filters.group)
    DISABLEDEL_HANDLER = CommandHandler("disabledel", disable_del)

    dispatcher.add_handler(DISABLE_HANDLER)
    dispatcher.add_handler(ENABLE_HANDLER)
    dispatcher.add_handler(COMMANDS_HANDLER)
    dispatcher.add_handler(TOGGLE_HANDLER)
    dispatcher.add_handler(DISABLEDEL_HANDLER)

else:
    DisableAbleCommandHandler = CommandHandler
    DisableAbleMessageHandler = MessageHandler
