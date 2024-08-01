
import subprocess
import os
from display import Display

class Console(Display):
    _display_on = True
    
    def __init__(self):
        self._display_on = self.on(check=True)

    def sleep(self):
        """Turn off the display."""
        # see https://forums.raspberrypi.com/viewtopic.php?t=363392 for more info
        os.system('ddcutil setvcp d6 4')
        self.DISPLAY_ON = False

    def wake(self):
        """Turn on the display."""
        # see https://forums.raspberrypi.com/viewtopic.php?t=363392 for more info
        os.system('ddcutil setvcp d6 1')
        self.DISPLAY_ON = True

    def on(self, check=False):
        """Return True if the display is on, otherwise False."""
        if check:
            # TODO: use pykms directly
            try:
                output = subprocess.check_output('ddcutil getvcp d6', shell=True).decode()
                if '0x01' in output:
                    self.DISPLAY_ON = True
                elif '0x04' in output:
                    self.DISPLAY_ON = False
                else:
                    raise ValueError('Could not determine whether monitor was on or not')
            except subprocess.CalledProcessError:
                # TODO: check exit code to make sure monitor was not reachable
                self.DISPLAY_ON = False
        return self.DISPLAY_ON

    def restore(self):
        return
    
    @staticmethod
    def active():
        return True


