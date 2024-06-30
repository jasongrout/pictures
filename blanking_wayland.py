import subprocess
import time
from display import Display
import os
class Wayland(Display):
    def sleep(self):
        """Turn off the display."""
        subprocess.run('wlr-randr --output HDMI-A-1 --off', shell=True)

    def wake(self):
        """Turn on the display."""
        subprocess.run('wlr-randr --output HDMI-A-1 --on', shell=True)
        # Let the display wake up before trying to show anything
        time.sleep(2)

    def on(self, check=False):
        """Return True if the display is on, otherwise False."""
        output = subprocess.check_output('wlr-randr ', shell=True, text=True)
        if 'Enabled: yes' in output:
            return True
        elif 'Enabled: no' in output:
            return False
        else:
            raise ValueError('Could not determine whether monitor was on or not')

    def restore(self):
        return
    
    @staticmethod
    def active():
        return os.environ.get('XDG_SESSION_TYPE', '') == 'wayland'

