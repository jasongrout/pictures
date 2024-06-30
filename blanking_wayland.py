import subprocess
import re
import os
################################################################
## BEGIN X-based screen blanking
###############################################################

# Getting screen blanking to work well is a bit tricky.
# 1. Edit /boot/config.txt and add 'hdmi_blanking=1' so that we can trigger the dpms off mode (see https://www.raspberrypi.org/documentation/configuration/config-txt/video.md and https://github.com/raspberrypi/linux/issues/487.)
# 2. When this program is started, turn off the screen saver and dpms timeouts. Turn these back on when exiting. Note that if xscreensaver is installed, it already disables the default screensaver timeouts and sets the dpms timeouts and disables the dpms. However, when we force dpms off mode below, we activate dpms, which means that the existing timeouts then apply.

SCREENSAVER_SETTINGS = {}
def screensaver_off():
    global SCREENSAVER_SETTINGS
    xset = subprocess.check_output(['xset', '-q']).decode('utf-8')
    m=re.search(r'^\s*timeout:\s*(\d+)\s*cycle:\s*(\d+)', xset, re.MULTILINE)
    if m:
        SCREENSAVER_SETTINGS['timeout'] = int(m.groups()[0])
        SCREENSAVER_SETTINGS['cycle'] = int(m.groups()[1])

    m=re.search(r'^\s*Standby:\s*(\d+)\s*Suspend:\s*(\d+)\s*Off:\s*(\d+)', xset, re.MULTILINE)
    if m:
        SCREENSAVER_SETTINGS['standby'] = int(m.groups()[0])
        SCREENSAVER_SETTINGS['suspend'] = int(m.groups()[1])
        SCREENSAVER_SETTINGS['off'] = int(m.groups()[2])
    m = re.search(r'DPMS is (Enabled|Disabled)', xset)
    if m:
        setting = m.groups()[0]
        if setting == 'Enabled':
            SCREENSAVER_SETTINGS['enabled'] = True
        elif setting == 'Disabled':
            SCREENSAVER_SETTINGS['enabled'] = False

    subprocess.run('xset s 0 0 '.split())
    subprocess.run('xset dpms 0 0 0'.split())

def screensaver_restore():
    global SCREENSAVER_SETTINGS
    if 'timeout' in SCREENSAVER_SETTINGS:
        subprocess.run('xset s {timeout} {cycle}'.format(**SCREENSAVER_SETTINGS).split())
    if 'standby' in SCREENSAVER_SETTINGS:
        subprocess.run('xset dpms {standby} {suspend} {off}'.format(**SCREENSAVER_SETTINGS).split())
    if 'enabled' in SCREENSAVER_SETTINGS:
        subprocess.run('xset {}dpms'.format('+' if SCREENSAVER_SETTINGS['enabled'] else '-').split())

# os.environ['SDL_VIDEO_ALLOW_SCREENSAVER']='1'
# screensaver_off()

def run(cmd):
    print(f"running: {cmd}")
    print(subprocess.check_output(cmd, shell=True))

def display_sleep():
    """Turn off the display."""
    run('wlr-randr --output HDMI-A-1 --off')
    run('wlr-randr')

def display_wake():
    """Turn on the display."""
    run('wlr-randr --output HDMI-A-1 --on')

def display_on(check=False):
    """Return True if the display is on, otherwise False."""
    return False
    output = subprocess.check_output('xset q'.split(), text=True)
    if 'Monitor is On' in output:
        return True
    elif 'Monitor is Off' in output:
        return False
    else:
        raise ValueError('Could not determine whether monitor was on or not')

def display_restore():
    return
    screensaver_restore()
