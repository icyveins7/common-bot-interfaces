from telegram.ext import Application, ApplicationBuilder, ContextTypes, CommandHandler
from telegram.ext.filters import MessageFilter
from telegram import Update, constants
import os
import datetime as dt
from functools import reduce
import subprocess

#%% This is the base container. Every bot should inherit from this, and this must be included at the end after all mixins.
# Important: Many, if not all mixins, will assume that the stuff in this class exist. For example, universal filters may be applied to every handler added.
# All functionality is placed in separate interfaces, which are inherited (mixed-in) in the eventual application-specific class.
# This means that all mixin interfaces must abide by a few rules:
# The first is the _addInterfaceHandlers() method. All mixins must implement this method, and should always call super()._addInterfaceHandlers(),
# so that all other mixins will be able to add their own handlers.
# The second is that the universal filters is appended to after super().__init__() in the individual init methods. Mixin individual
# handlers can choose whether to use the universal set of filters in their handler methods.
class BotContainer:
    def __init__(self, app: Application):
        '''Basic container with the app as a member variable.'''
        self._app = app
        print(self._app)
        # Create the universal filters
        self._ufilts = []
        # Add all handlers
        print("Bot has initialised.")

    @property
    def link(self):
        if self.botname is not None:
            return "https://t.me/" + self._app.botname
        else:
            return "No botname was set."
        
    def setBotname(self, botname: str):
        self.botname = botname

    @property
    def ufilts(self):
        return reduce(lambda x, y: x & y, self._ufilts)

    def _addInterfaceHandlers(self):
        print("BotContainer passthrough.")
        pass

    def run(self):
        # We add the interface handlers before running as this allows us to fill in filters without worrying about order
        print("Adding handlers..")
        self._addInterfaceHandlers()

        print("Running..")
        self._app.run_polling()

    @classmethod
    def fromEnvVar(cls, envVar: str):
        '''Initialisation from an environment variable containing the bot token.'''
        token = os.environ[envVar]
        container = cls(ApplicationBuilder().token(token).build())
        return container
    
    @classmethod
    def fromTokenString(cls, token: str):
        '''Initialisation from a string containing the bot token.'''
        container = cls(ApplicationBuilder().token(token).build())
        return container

#%%
class AliveFilter(MessageFilter):
    '''Prevents messages/commands sent before the bot started from being processed.'''
    def __init__(self, t0: float, *args, **kwargs):
        self._t0 = t0
        super().__init__(*args, **kwargs)

    @property
    def t0(self):
        return self._t0

    def filter(self, message):
        print("Msg: %f\nBot start: %f" % (message.date.timestamp(), self._t0))
        return message.date.timestamp() > self._t0


#%% 
class StatusInterface:
    def __init__(self, *args, **kwargs):
        self._t0 = dt.datetime.now(tz=dt.timezone.utc).timestamp()
        super().__init__(*args, **kwargs)
        
        # Adds the filter to the universal list
        self._ufilts.append(AliveFilter(self._t0))
        
        print("Bot started at %f" % (self._t0))

    def _addInterfaceHandlers(self):
        super()._addInterfaceHandlers()
        print("Adding StatusInterface:status")
        self._app.add_handler(CommandHandler('status', self.status, filters=self.ufilts))


    @property
    def elapsedSeconds(self):
        return dt.datetime.now(tz=dt.timezone.utc).timestamp() - self._t0

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="This bot began at %f and has been alive for %fs" % (self._t0, self.elapsedSeconds)
        )


#%% Experimental admin privilege filter
class AdminFilter(MessageFilter):
    '''Prevents messages/commands sent by non-admins from being processed.'''
    def __init__(self, id: int, *args, **kwargs):
        self._id = id
        super().__init__(*args, **kwargs)

    @property
    def id(self):
        return self._id

    def filter(self, message):
        print("Msg from: %d\nAdmin: %d" % (message.from_user.id, self._id))
        return message.from_user.id == self._id

#%% Admin
class AdminInterface:
    """
    This is the basic admin interface, which provides a way to set the admin and then access the filter via self._adminfilter.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._adminfilter = None

    def setAdmin(self, id: int):
        self._adminfilter = AdminFilter(id)
    
    def _addInterfaceHandlers(self):
        super()._addInterfaceHandlers()

        if self._adminfilter is None:
            raise ValueError("Specify an admin ID before continuing.")
        
        print("Adding AdminInterface:admin")
        self._app.add_handler(CommandHandler('admin', self.admin, filters=self.ufilts & self._adminfilter))

    async def admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You have admin rights."
        )


class SystemInterface(AdminInterface):
    """
    This inherits AdminInterface, and adds the ability to invoke system commands.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _addInterfaceHandlers(self):
        super()._addInterfaceHandlers()

        print("Adding SystemInterface:execute")
        self._app.add_handler(CommandHandler('execute', self.execute, filters=self.ufilts & self._adminfilter))

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        returncode = os.system(" ".join(context.args))

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Return code: %d" % returncode
        )

#%%
class ControlInterface(AdminInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _addInterfaceHandlers(self):
        super()._addInterfaceHandlers()
        print("Adding ControlInterface:shutdown")
        self._app.add_handler(CommandHandler('shutdown', self.shutdown, filters=self.ufilts & self._adminfilter))
        print("Adding ControlInterface:restart")
        self._app.add_handler(CommandHandler('restart', self.restart, filters=self.ufilts & self._adminfilter))

    async def shutdown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Shutting down.."
        )
        os._exit(0) # This is the shut down code for the bot runner.

    async def restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Restarting.."
        )
        os._exit(1) # Any number other than 0 will restart the bot in the bot runner.

class GitInterface(AdminInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _addInterfaceHandlers(self):
        super()._addInterfaceHandlers()
        print("Adding GitInterface:gitpull")
        self._app.add_handler(CommandHandler('gitpull', self.gitPull, filters=self.ufilts & self._adminfilter))
        print("Adding GitInterface:gitLog")
        self._app.add_handler(CommandHandler('gitlog', self.gitLog, filters=self.ufilts & self._adminfilter))

    async def gitPull(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        os.system("git pull")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Git pull complete."
        )

    async def gitLog(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        gitlogstr = subprocess.check_output(['git', 'log', '-1', '--oneline']).strip().decode('utf-8')
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=gitlogstr
        )


#%% Context filtering
class PrivateOnlyChatFilter(MessageFilter):
    """
    Filter that only allows messages sent to a private chat.
    """

    def filter(self, message):
        chat = message.chat
        return chat.type == constants.ChatType.PRIVATE
    
class GroupOnlyChatFilter(MessageFilter):
    """
    Filter that only allows messages sent to a group chat.
    """

    def filter(self, message):
        chat = message.chat
        return chat.type == constants.ChatType.GROUP


#%%
if __name__ == "__main__":
    import sys
    class GenericBot(GitInterface, SystemInterface, ControlInterface, StatusInterface, BotContainer):
        def _addInterfaceHandlers(self):
            super()._addInterfaceHandlers()

            self._app.add_handler(CommandHandler('private', self.testPrivateOnly, filters=self.ufilts & PrivateOnlyChatFilter()))
            self._app.add_handler(CommandHandler('group', self.testGroupOnly, filters=self.ufilts & GroupOnlyChatFilter()))

        async def testPrivateOnly(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="This is a private message."
            )

        async def testGroupOnly(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="This is a group message."
            )

    bot = GenericBot.fromEnvVar('TELEGRAM_TEST_TOKEN')
    bot.setAdmin(int(sys.argv[1]))
    print(GenericBot.__mro__)
    bot.run()




