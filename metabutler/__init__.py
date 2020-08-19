import logging
import os
import sys
import time
from datetime import datetime
from functools import wraps

import telegram.ext as tg

# enable logging
logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO)

LOGGER = logging.getLogger(__name__)

# if version < 3.6, stop bot.
if sys.version_info[0] < 3 or sys.version_info[1] < 6:
        LOGGER.error("You MUST have a python version of at least 3.6! Multiple features depend on this. Bot quitting.")
        quit(1)

# Check if system is reboot or not
try:
        os.remove("reboot")
except:
        pass

ENV = bool(os.environ.get('ENV', False))

if ENV:
        TOKEN = os.environ.get('TOKEN', None)
        try:
                OWNER_ID = int(os.environ.get('OWNER_ID', None))
        except ValueError:
                raise Exception("Your OWNER_ID env variable is not a valid integer.")

        MESSAGE_DUMP = os.environ.get('MESSAGE_DUMP', None)
        OWNER_USERNAME = os.environ.get("OWNER_USERNAME", None)
        IS_DEBUG = os.environ.get("IS_DEBUG", False)

        try:
                SUDO_USERS = set(int(x) for x in os.environ.get("SUDO_USERS", "").split())
        except ValueError:
                raise Exception("Your sudo users list does not contain valid integers.")

        try:
                SUPPORT_USERS = set(int(x) for x in os.environ.get("SUPPORT_USERS", "").split())
        except ValueError:
                raise Exception("Your support users list does not contain valid integers.")

        try:
                SPAMMERS = set(int(x) for x in os.environ.get("SPAMMERS", "").split())
        except ValueError:
                raise Exception("Your spammers users list does not contain valid integers.")

        try:
                GROUP_BLACKLIST = set(int(x) for x in os.environ.get("GROUP_BLACKLIST", "").split())
        except ValueError:
                raise Exception("Your GROUP_BLACKLIST users list does not contain valid integers.")

        try:
                WHITELIST_USERS = set(int(x) for x in os.environ.get("WHITELIST_USERS", "").split())
        except ValueError:
                raise Exception("Your whitelisted users list does not contain valid integers.")

        WEBHOOK = bool(os.environ.get('WEBHOOK', False))
        URL = os.environ.get('URL', "")  # Does not contain token
        FED_LOGS = os.environ.get('FED_LOGS', None)
        PORT = int(os.environ.get('PORT', 5000))
        GBAN_LOGS = os.environ.get('GBAN_LOGS', None)

        CERT_PATH = os.environ.get("CERT_PATH")

        DB_URI = os.environ.get('DATABASE_URL')
        LOAD = os.environ.get("LOAD", "").split()
        NO_LOAD = os.environ.get("NO_LOAD", "").split()
        DEL_CMDS = bool(os.environ.get('DEL_CMDS', False))
        STRICT_GBAN = bool(os.environ.get('STRICT_GBAN', False))
        WORKERS = int(os.environ.get('WORKERS', 8))
        BAN_STICKER = os.environ.get('BAN_STICKER', 'CAADBAAD4kYAAuOnXQW5LUN400QOBQI')
        # ALLOW_EXCL = os.environ.get('ALLOW_EXCL', False)
        CUSTOM_CMD = os.environ.get('CUSTOM_CMD', False)
        TEMPORARY_DATA = os.environ.get('TEMPORARY_DATA', None)
        SPAMWATCH_TOKEN = os.environ.get('SPAMWATCH_TOKEN', None)

else:
        from metabutler.config import Development as Config
        TOKEN = Config.API_KEY
        try:
                OWNER_ID = int(Config.OWNER_ID)
        except ValueError:
                raise Exception("Your OWNER_ID variable is not a valid integer.")

        MESSAGE_DUMP = Config.MESSAGE_DUMP
        OWNER_USERNAME = Config.OWNER_USERNAME
        try:
                IS_DEBUG = Config.IS_DEBUG
        except AttributeError:
                IS_DEBUG = False

        try:
                SUDO_USERS = set(int(x) for x in Config.SUDO_USERS or [])
        except ValueError:
                raise Exception("Your sudo users list does not contain valid integers.")

        try:
                SUPPORT_USERS = set(int(x) for x in Config.SUPPORT_USERS or [])
        except ValueError:
                raise Exception("Your support users list does not contain valid integers.")

        try:
                SPAMMERS = set(int(x) for x in Config.SPAMMERS or [])
        except ValueError:
                raise Exception("Your spammers users list does not contain valid integers.")

        try:
                GROUP_BLACKLIST = set(int(x) for x in Config.GROUP_BLACKLIST or [])
        except ValueError:
                raise Exception("Your GROUP_BLACKLIST users list does not contain valid integers.")

        try:
                WHITELIST_USERS = set(int(x) for x in Config.WHITELIST_USERS or [])
        except ValueError:
                raise Exception("Your whitelisted users list does not contain valid integers.")

        GBAN_LOGS = Config.GBAN_LOGS
        FED_LOGS = Config.FED_LOGS
        WEBHOOK = Config.WEBHOOK
        URL = Config.URL

        PORT = Config.PORT
        CERT_PATH = Config.CERT_PATH

        DB_URI = Config.SQLALCHEMY_DATABASE_URI
        LOAD = Config.LOAD
        NO_LOAD = Config.NO_LOAD
        DEL_CMDS = Config.DEL_CMDS
        STRICT_GBAN = Config.STRICT_GBAN
        WORKERS = Config.WORKERS
        BAN_STICKER = Config.BAN_STICKER
        # ALLOW_EXCL = Config.ALLOW_EXCL
        CUSTOM_CMD = Config.CUSTOM_CMD
        TEMPORARY_DATA = Config.TEMPORARY_DATA
        try:
                SPAMWATCH_TOKEN = Config.SPAMWATCH_TOKEN
        except:
                pass


SUDO_USERS.add(OWNER_ID)

updater = tg.Updater(TOKEN, workers=WORKERS, use_context=True)

dispatcher = updater.dispatcher

SUDO_USERS = list(SUDO_USERS)
WHITELIST_USERS = list(WHITELIST_USERS)
SUPPORT_USERS = list(SUPPORT_USERS)
SPAMMERS = list(SPAMMERS)
GROUP_BLACKLIST = list(GROUP_BLACKLIST)

# Load at end to ensure all prev variables have been set
from metabutler.modules.helper_funcs.handlers import CustomCommandHandler

if CUSTOM_CMD and len(CUSTOM_CMD) >= 1:
        tg.CommandHandler = CustomCommandHandler
