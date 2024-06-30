import subprocess

def display_sleep():
    """Turn off the display."""
    global DISPLAY_ON
    # see https://forums.raspberrypi.com/viewtopic.php?t=363392 for more info
    os.system('ddcutil setvcp d6 4')
    DISPLAY_ON = False

def display_wake():
    """Turn on the display."""
    global DISPLAY_ON
    # see https://forums.raspberrypi.com/viewtopic.php?t=363392 for more info
    os.system('ddcutil setvcp d6 1')
    DISPLAY_ON = True

DISPLAY_ON = None
def display_on(check=False):
    """Return True if the display is on, otherwise False."""
    global DISPLAY_ON
    if check:
        # TODO: use pykms directly
        output = subprocess.check_output('ddcutil getvcp d6', shell=True).decode()
        if '0x01' in output:
            DISPLAY_ON = True
        elif '0x04' in output:
            DISPLAY_ON = False
        else:
            raise ValueError('Could not determine whether monitor was on or not')
    return DISPLAY_ON

# Initialize DISPLAY_ON
display_on(check=True)

def display_restore():
    pass
