from telegram.ext import Application, ApplicationBuilder, ContextTypes, CommandHandler
from telegram.ext.filters import MessageFilter
from telegram import Update
import os
import datetime as dt
from functools import reduce

#%% This is the base container. Every bot should inherit from this, and this must be included at the end after all mixins.
# Important: Many, if not all mixins, will assume that the stuff in this class exist. For example, universal filters may be applied to every handler added.
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

#%%
class ControlInterface:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _addInterfaceHandlers(self):
        super()._addInterfaceHandlers()
        print("Adding ControlInterface:shutdown")
        self._app.add_handler(CommandHandler('shutdown', self.shutdown, filters=self.ufilts))

    async def shutdown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Shutting down.."
        )
        os._exit(0)

#%% Experimental admin privilege interface with roles assignment
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

class AdminInterface:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.adminIsSet = False
        self._roles = dict()

    def setAdmin(self, id: int):
        if self.adminIsSet:
            raise ValueError("Admin has already been specified!")
        else:
            self.adminIsSet = True
            self.ufilts.append(AdminFilter(id)) # Attach to the universal filters

    def _addInterfaceHandlers(self):
        super()._addInterfaceHandlers()
        print("Adding AdminInterface:roles")
        self._app.add_handler(CommandHandler('roles', self.roles, filters=self.ufilts))

    async def roles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Roles:\n %s" % (self._roles)
        )

#%%
if __name__ == "__main__":
    class GenericBot(AdminInterface, ControlInterface, StatusInterface, BotContainer):
        pass
    bot = GenericBot.fromEnvVar('TELEGRAM_TEST_TOKEN')
    print(GenericBot.__mro__)
    bot.run()




