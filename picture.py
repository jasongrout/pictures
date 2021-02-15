#!/usr/bin/env python3

# Things we can still do:

# [X] Turn off screen at night (see note below about `xset dpms force off`. Also see https://wiki.libsdl.org/FAQUsingSDL#Why_does_SDL_disable_my_screensaver_by_default.3F about allowing the screen to blank while running the program - we'll need to set an environment variable in this program using os.environ).
# [ ] Save the pic history to a file to easily pick it back up again
# [ ] bias against showing pics we've already shown. Perhaps if we generate a pic already in the history list, try at least once to pick a new random picture, or after we show a picture, take it out of the list.
# [ ] Be able to rate a picture from 1-5, show the rating next, maybe make it more likely to be picked. Be able to say "don't show this pic again".

# Later
# [ ] Make it easy to turn on or off LED lights. Ask about good default.
# [ ] Picture selection logic - higher preference to pictures in similar season, pics with higher ratings, etc.
# [ ] Print info about the pic on the pic display (date, filename, keywords, caption, etc.)
# [ ] up/down keys go through the pictures chronologically?
# [ ] Handle pics with different sizes/orientations. Rotate? Put upright and blur the background? Center smaller pics
# [ ] Hook up hardware buttons and switch: buttons to go prev/next, switch to hold a pic, buttons to rate a pic up or down.

# autorun: http://www.raspberry-projects.com/pi/pi-operating-systems/raspbian/auto-running-programs-gui
# control LEDs: https://www.jeffgeerling.com/blogs/jeff-geerling/controlling-pwr-act-leds-raspberry-pi - set the trigger for each led (if 'none' doesn't work to turn them off, try 'gpio')


# In order to get the screen blanking to work, edit /boot/config.txt and add `hdmi_blanking=1`. Then you can use `xset dpms force off` to blank the screen and turn off the monitor until another key is pressed. See https://www.raspberrypi.org/documentation/configuration/config-txt/video.md and https://github.com/raspberrypi/linux/issues/487.


###########


#turns off the screen, works in python.
# https://wiki.libsdl.org/FAQUsingSDL
# https://stackoverflow.com/questions/39914670/sdl-pollevent-causes-screen-to-wake-up-after-xset-dpms-force-off
# https://ubuntuforums.org/showthread.php?t=1317747&page=3&p=9433671#post9433671

# Set the variables so we can easily change the program
FULLSCREEN = False
SMALL_SCREEN_SIZE=(600,400)
TIMER = 40 # minutes between picture changes
FONTSIZE = 120
FORMAT = 1
PIC_DIRECTORY = '/home/pi/Export1080p/'
# Time of sleep and wake each day
WAKE = (6, 30)
SLEEP = (21,30)



# import stuff we need
from random import SystemRandom
import pygame
import os
import pygame.freetype
import subprocess
import re
import datetime


from time import process_time

class timer:
    def __enter__(self):
        self.t = process_time()
        return self

    def __exit__(self, type, value, traceback):
        self.e = process_time()
        self.elapsed = 1000*(self.e - self.t)
        print(self)

    def __float__(self):
        return float(self.elapsed)

    def __coerce__(self, other):
        return (float(self), other)

    def __str__(self):
        return str(float(self))

    def __repr__(self):
        return str(float(self))


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

os.environ['SDL_VIDEO_ALLOW_SCREENSAVER']='1'
screensaver_off()


def display_sleep():
    """Turn off the display."""
    subprocess.run('xset dpms force off'.split())
    DISPLAY=False

def display_wake():
    """Turn on the display."""
    subprocess.run('xset dpms force on'.split())
    DISPLAY=True

def display_on():
    """Return True if the display is on, otherwise False."""
    output = subprocess.check_output('xset q'.split(), text=True)
    if 'Monitor is On' in output:
        return True
    elif 'Monitor is Off' in output:
        return False
    else:
        raise ValueError('Could not determine whether monitor was on or not')

def date (filename):
    """Format the filename string to display the date, depending on the global FORMAT."""
    global FORMAT
    if FORMAT == 0:
        return ''
    elif FORMAT == 1:
        if filename[0] == '2':
            return convert(filename)
        else:
            return ''
    elif FORMAT == 2:
        return filename[:-4]

def convert(date):
    """Format a date string like 20200521 into a date for display like 21 May 2020."""
    months = {
        '01': 'Jan',
        '02': 'Feb',
        '03': 'Mar',
        '04': 'Apr',
        '05': 'May',
        '06': 'June',
        '07': 'July',
        '08': 'Aug',
        '09': 'Sep',
        '10': 'Oct',
        '11': 'Nov',
        '12': 'Dec'
    }
    year = date[:4]
    month = date[4:6]
    day = date[6:8]
    month = months[month]
    return day+' '+month+' '+year

def group(data):
    """Group picture filenames like 20200528.jpg into days.

    For now, we also only include filenames that match the current month.
    """
    dic = {}
    for name in data:
        start = name[:8]
        if start not in dic:
            dic[start] = [name]
        else:
            dic[start].append(name)
    return dic

# Start pygame up, setting allowed events
pygame.freetype.init()
pygame.display.init()
pygame.event.set_allowed(None)
pygame.event.set_allowed([pygame.USEREVENT,pygame.KEYDOWN,pygame.QUIT, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP])
if FULLSCREEN:
    pygame.mouse.set_visible(False)
    screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN) # fullscreen
else:
    screen = pygame.display.set_mode(SMALL_SCREEN_SIZE) # development


# Define custom pygame events we will use.
PICTURE_CHANGE = pygame.USEREVENT
SCREEN_SLEEP = pygame.USEREVENT + 1
SCREEN_WAKE = pygame.USEREVENT + 2
UPDATE_TIME = pygame.USEREVENT + 3

random = SystemRandom()
font = pygame.freetype.SysFont('freesans', FONTSIZE)

CURRENT_PICTURE = None
CURRENT_IMAGE = None
def show(filename = None):
    global CURRENT_PICTURE
    global CURRENT_IMAGE
    if filename is None:
        filename = CURRENT_PICTURE
        cimage = CURRENT_IMAGE
    else:
        cimage = pygame.image.load(PIC_DIRECTORY + filename).convert()
        CURRENT_PICTURE = filename
        CURRENT_IMAGE = cimage

    screen_width = screen.get_width()
    screen_height = screen.get_height()

    screen.fill([0,0,0])
    if FULLSCREEN:
        x = screen_width
        n = cimage.get_width()
        offset = round((x-n)/2)
        screen.blit(cimage, (offset,0))
    else:
        pygame.transform.smoothscale(cimage, SMALL_SCREEN_SIZE, screen) # development


    # Put the filename 5 pixels from the bottom of the screen, 10 pixels from left edge
    words = font.render( date(filename),  fgcolor=(255,255,255), bgcolor=(0,0,0,100))
    screen.blit(words[0], (10, screen_height - words[0].get_height() - 5))

    # Time is 5 pixels from bottom, 10 pixels from right edge
    datetext = font.render( datetime.datetime.now().strftime("%H:%M"), fgcolor=(255,255,255), bgcolor=(0,0,0,100))
    screen.blit(datetext[0], (screen_width - datetext[0].get_width() - 10, screen_height - datetext[0].get_height() - 5))

    pygame.display.flip()



# Set up the picture history
position = -1
history = [] # list of filenames that you have viewed
# Get all of the filenames in the picture directory
pic_files = os.listdir(path=PIC_DIRECTORY)
groups = []
days = []
weights = []
cumdist = []

# weight the days logarithmically
# See https://docs.python.org/3.5/library/random.html#examples-and-recipes
from math import log
import itertools
from bisect import bisect
from normdist import NormalDist

def reset_weights():
    global weights, cumdist, groups, days

    # If we have hardly any pics left (by weight)
    # This relies on the log weighting scale, and the kernel being normalized
    if max(weights or [0])<=1e-5:
        groups = group(pic_files)
        days = list(groups.keys())

    # Calculate the weights applied to each day based on how far their week
    # is from the current week
    current_week = datetime.datetime.now().isocalendar()[1]

    kernel = NormalDist(0, 2).pdf

    # Power law fall-off
    # kernel = lambda x: (x+1)**-1.5

    # Linear fall-off
    # kernel = lambda x: max(1-.2*i, 0)

    normalization = kernel(0)
    def day_weight(day):
        try:
            d = datetime.datetime(int(day[:4]), int(day[4:6]), int(day[6:8]))
        except:
            # pictures without a date are automatically preferred as if they were 4 weeks away
            return kernel(4)/normalization
        week = d.isocalendar()[1]
        tmp = abs(current_week - week)
        # Absolute distance of the day's week from the current week
        distance = min(tmp, 53-tmp)
        # Weight the day by kernel
        return kernel(distance)/normalization

    # use log base N for weights, so one picture weights the day at 1.0,
    # N pictures makes a weight of 2, N^2 pictures makes a weight of 3,
    # N^3 pictures makes a weight of 4, and so on
    weights = [(log(len(groups[day]), 2)+1)*day_weight(day) for day in days]
    cumdist = list(itertools.accumulate(weights))

    # for (d,w) in sorted(zip(days, weights), key=lambda x: x[1]):
    #     print(d,"%f"%day_weight(d), "%f"%w)

reset_weights()

# Show the first picture after a second
pygame.time.set_timer(PICTURE_CHANGE, 1000)


def next_time(time = None):
    """Return the milliseconds until the time given ( (hour, minute))
    If time is None, the time returned is the milliseconds until the next minute
    """
    now = datetime.datetime.now()
    if time is None:
        want = now.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
    else:
        want = now.replace(hour=time[0], minute=time[1], second=0, microsecond=0)
    if now >= want:
        want += datetime.timedelta(days=1)
    return int((want - now).total_seconds()*1000)


# Initialize the display sleep and wake timers
pygame.time.set_timer(SCREEN_WAKE, next_time(WAKE))
pygame.time.set_timer(SCREEN_SLEEP, next_time(SLEEP))
pygame.time.set_timer(UPDATE_TIME, next_time())

# Handle events
while True:
    f=pygame.event.wait()

    # Show a new random picture
    if (f.type == PICTURE_CHANGE
        or (f.type == pygame.KEYDOWN and (f.key == pygame.K_SPACE))
        or (f.type == pygame.MOUSEBUTTONDOWN and f.button == 2)):

        if display_on():
            # pick a day, weighted according to cumdist, then pick a random pic from that day
            # See https://docs.python.org/3.5/library/random.html#examples-and-recipes
            dayindex = bisect(cumdist, random.random() * cumdist[-1])
            day = days[dayindex]
            x = random.choice(groups[day])
            history.append(x)

            position = -1
            show(history[position])

            # Update the pics to remove the one we just showed so we don't show it again
            groups[day].remove(x)
            if len(groups[day])==0:
                days.remove(day)
                del groups[day]
            reset_weights()

        pygame.time.set_timer(PICTURE_CHANGE,TIMER*60*1000)


    # Change the date format
    if (f.type == pygame.KEYDOWN and f.key == pygame.K_RETURN):
        FORMAT = FORMAT+1
        if FORMAT == 3:
            FORMAT = 0
        show()

    # Show the previous picture
    if (f.type == pygame.KEYDOWN and f.key == pygame.K_LEFT) or (f.type == pygame.MOUSEBUTTONDOWN and f.button == 1):
        if len(history) > -position:
            position = position-1
            show(history[position])
            pygame.time.set_timer(PICTURE_CHANGE,TIMER*60*1000)

    # Show the next picture
    if (f.type == pygame.KEYDOWN and f.key == pygame.K_RIGHT) or (f.type == pygame.MOUSEBUTTONDOWN and f.button == 3):
        if position < -1:
            position = position+1
            show(history[position])
            pygame.time.set_timer(PICTURE_CHANGE,TIMER*60*1000)

    # Quit the program
    if f.type == pygame.QUIT:
        break

    # Quit if shift-escape
    if (f.type == pygame.KEYDOWN
        and f.key == pygame.K_ESCAPE
        and (f.mod & pygame.KMOD_SHIFT != 0)):
        break

    # Quit if you  hold down a mouse button for 30 seconds
    if (f.type == pygame.MOUSEBUTTONDOWN and f.button in [1,2,3]):
        pygame.time.set_timer(pygame.QUIT,1000*30)
    if (f.type == pygame.MOUSEBUTTONUP and f.button in [1,2,3]):
        # Cancel the quit event since we let up on the mouse button
        pygame.time.set_timer(pygame.QUIT,0)

    if (f.type == pygame.KEYDOWN
        and f.key == pygame.K_b):
        display_sleep()

    if f.type == SCREEN_WAKE:
        display_wake()
        # Set a sleep timer for 24 hours from now for the next wake
        pygame.time.set_timer(SCREEN_WAKE, 1000*60*60*24)

    if f.type == SCREEN_SLEEP:
        display_sleep()
        # Set a sleep timer for 24 hours from now for the next sleep
        pygame.time.set_timer(SCREEN_SLEEP, 1000*60*60*24)

    if f.type == UPDATE_TIME:
        # Show the current picture, which will update the time as well
        show()
        # Set the next update at the start of the next minute
        pygame.time.set_timer(UPDATE_TIME, next_time())

# Just before exiting, restore the screensaver settings
screensaver_restore()