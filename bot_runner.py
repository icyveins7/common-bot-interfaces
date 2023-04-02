#%% Here we are going to create a class which will encapsulate a BotContainer and run it as a subprocess.
# The reason for this is to be able to completely terminate the script, perform actions on the script, and then
# re-run the script i.e. allow for updates.
#
# The best way to use this is to run this script as a module, providing the arguments
# (scriptname) (arg1) (arg2) etc as you would if you were running the script yourself.
# 
# Example where common_bot_interfaces is a submodule, and the main script is in a upper folder:
#   Normal calling structure:
#   python main_script.py arg1 arg2
#
#   Bot_runner calling structure:         
#   python -m common_bot_interfaces.bot_runner main_script.py arg1 arg2
# 
# Together with the GitInterface, this provides a way to continuously update the
# core bot code and update it remotely, as it resides completely in a separate file.


from common_bot_interfaces import *

import subprocess

class BotRunner:
    SHUTDOWN_CODE = 0
    
    def __init__(self, script: str):
        self._script = script

    def _run(self, *args):
        # Start a subprocess to run the script.
        command = " ".join(["python %s" % self._script, *args])
        print(command)
        returncode = subprocess.call(command, shell=True)
        return returncode

    def run(self, *args):
        while True:
            returncode = self._run(*args)
            if returncode == self.SHUTDOWN_CODE:
                print("Script shutting down permanently with return code %d" % returncode)
                break

            else:
                print("Script stopped running temporarily with return code %d" % returncode)




if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Run this as a module, e.g. python -m common_bot_interfaces.bot_runner main_script.py arg1 arg2")

    runner = BotRunner(sys.argv[1])

    runner.run(*sys.argv[2:])