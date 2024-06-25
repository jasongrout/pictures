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

from random import SystemRandom
import pygame
import os
import pygame.freetype
import subprocess
import datetime
from bisect import bisect, bisect_left, bisect_right
from pathlib import Path
from collections import defaultdict
from math import log
import itertools
from normdist import NormalDist

# Set the variables so we can easily change the program
FULLSCREEN = True
SMALL_SCREEN_SIZE=(600,400)
DISPLAY_TIME_MS = 40 * 60 * 1000 # miliseconds a picture is displayed by default
FONTSIZE = 120

# The default text format:
# - 0: no text
# - 1: date
# - 2: filename
FORMAT = 1

# The directory of pictures
PIC_DIRECTORY = Path('/home/pi/Export1080p/')

# Time (hour, minute) of sleep and wake each day
WAKE = (6, 30)
SLEEP = (21,30)



# import stuff we need

################################################################
## BEGIN X-based screen blanking
###############################################################

# Getting screen blanking to work well is a bit tricky.
# 1. Edit /boot/config.txt and add 'hdmi_blanking=1' so that we can trigger the dpms off mode (see https://www.raspberrypi.org/documentation/configuration/config-txt/video.md and https://github.com/raspberrypi/linux/issues/487.)
# 2. When this program is started, turn off the screen saver and dpms timeouts. Turn these back on when exiting. Note that if xscreensaver is installed, it already disables the default screensaver timeouts and sets the dpms timeouts and disables the dpms. However, when we force dpms off mode below, we activate dpms, which means that the existing timeouts then apply.

# SCREENSAVER_SETTINGS = {}
# def screensaver_off():
#     global SCREENSAVER_SETTINGS
#     xset = subprocess.check_output(['xset', '-q']).decode('utf-8')
#     m=re.search(r'^\s*timeout:\s*(\d+)\s*cycle:\s*(\d+)', xset, re.MULTILINE)
#     if m:
#         SCREENSAVER_SETTINGS['timeout'] = int(m.groups()[0])
#         SCREENSAVER_SETTINGS['cycle'] = int(m.groups()[1])

#     m=re.search(r'^\s*Standby:\s*(\d+)\s*Suspend:\s*(\d+)\s*Off:\s*(\d+)', xset, re.MULTILINE)
#     if m:
#         SCREENSAVER_SETTINGS['standby'] = int(m.groups()[0])
#         SCREENSAVER_SETTINGS['suspend'] = int(m.groups()[1])
#         SCREENSAVER_SETTINGS['off'] = int(m.groups()[2])
#     m = re.search(r'DPMS is (Enabled|Disabled)', xset)
#     if m:
#         setting = m.groups()[0]
#         if setting == 'Enabled':
#             SCREENSAVER_SETTINGS['enabled'] = True
#         elif setting == 'Disabled':
#             SCREENSAVER_SETTINGS['enabled'] = False

#     subprocess.run('xset s 0 0 '.split())
#     subprocess.run('xset dpms 0 0 0'.split())

# def screensaver_restore():
#     global SCREENSAVER_SETTINGS
#     if 'timeout' in SCREENSAVER_SETTINGS:
#         subprocess.run('xset s {timeout} {cycle}'.format(**SCREENSAVER_SETTINGS).split())
#     if 'standby' in SCREENSAVER_SETTINGS:
#         subprocess.run('xset dpms {standby} {suspend} {off}'.format(**SCREENSAVER_SETTINGS).split())
#     if 'enabled' in SCREENSAVER_SETTINGS:
#         subprocess.run('xset {}dpms'.format('+' if SCREENSAVER_SETTINGS['enabled'] else '-').split())

# os.environ['SDL_VIDEO_ALLOW_SCREENSAVER']='1'
# screensaver_off()
# def display_sleep_x():
#     """Turn off the display."""
#     subprocess.run('xset dpms force off'.split())

# def display_wake_x():
#     """Turn on the display."""
#     subprocess.run('xset dpms force on'.split())

# def display_on_x():
#     """Return True if the display is on, otherwise False."""
#     output = subprocess.check_output('xset q'.split(), text=True)
#     if 'Monitor is On' in output:
#         return True
#     elif 'Monitor is Off' in output:
#         return False
#     else:
#         raise ValueError('Could not determine whether monitor was on or not')

################################################################
## END X-based screen blanking
###############################################################


def display_sleep():
    """Turn off the display."""
    # see https://forums.raspberrypi.com/viewtopic.php?t=363392 for more info
    os.system('ddcutil setvcp d6 4')

def display_wake():
    """Turn on the display."""
    # see https://forums.raspberrypi.com/viewtopic.php?t=363392 for more info
    os.system('ddcutil setvcp d6 1')

def display_on():
    """Return True if the display is on, otherwise False."""
    # TODO: use pykms directly
    output = subprocess.check_output('ddcutil getvcp d6', shell=True).decode()
    if '0x01' in output:
        return True
    elif '0x04' in output:
        return False
    else:
        raise ValueError('Could not determine whether monitor was on or not')

def format_filename(filename):
    """Format the filename string to display the date, depending on the global FORMAT."""
    if FORMAT == 0:
        return ''
    elif FORMAT == 1:
        if filename[0] == '2':
            return datetime.strptime(filename[:8], "%Y%m%d").strftime("%d %b %Y")
        else:
            return ''
    elif FORMAT == 2:
        os.path.splitext(filename)[0]

def group_by_day(data):
    """Group picture filenames like 20200528.jpg into days."""
    groups = defaultdict(list)
    for name in data:
        groups[name[:8]].append(name)
    return groups

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
    """Show a picture. If filename is not specified, refresh the current picture."""
    global CURRENT_PICTURE
    global CURRENT_IMAGE
    if filename is None:
        filename = CURRENT_PICTURE
        cimage = CURRENT_IMAGE
    else:
        cimage = pygame.image.load(PIC_DIRECTORY / filename).convert()
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
    words = font.render( format_filename(filename),  fgcolor=(255,255,255), bgcolor=(0,0,0,100))
    screen.blit(words[0], (10, screen_height - words[0].get_height() - 5))

    # Time is 5 pixels from bottom, 10 pixels from right edge
    datetext = font.render( datetime.datetime.now().strftime("%H:%M"), fgcolor=(255,255,255), bgcolor=(0,0,0,100))
    screen.blit(datetext[0], (screen_width - datetext[0].get_width() - 10, screen_height - datetext[0].get_height() - 5))

    pygame.display.flip()

# Total history of filenames that have been viewed since the program start, even across `seen` resets
PIC_HISTORY = []

# The position of the current picture in the history array
PIC_HISTORY_INDEX = -1

# Tracking data for the list of possible pictures, weights, etc.
PIC_FILES = []
PIC_DIRECTORY_MTIME = None
PIC_GROUPS = []
PIC_DAYS = []
DAY_WEIGHTS = []
CUM_DAY_WEIGHTS = []

# The pics we have already seen in the current cycle of pictures. This can be reset
# if we don't have many pictures left to show.
PICS_SEEN = set()

# weight the days logarithmically
# See https://docs.python.org/3.5/library/random.html#examples-and-recipes

def reset_weights():
    """Reset the weights on the remaining pics in groups and days"""
    global PIC_DIRECTORY_MTIME, PIC_FILES, DAY_WEIGHTS, CUM_DAY_WEIGHTS, PIC_GROUPS, PIC_DAYS

    # If we have hardly any pics left (by weight), reset everything so the scan picks up everything
    # The threshold value relies on the log weighting scale and the kernel being normalized
    if max(DAY_WEIGHTS or [0])<=1e-5:
        seen = set()
        PIC_DIRECTORY_MTIME = None

    # If the pic directory has changed (or mtime been reset), rescan all the files
    if  PIC_DIRECTORY_MTIME != PIC_DIRECTORY.stat().st_mtime:
        PIC_FILES = sorted(set(os.listdir(PIC_DIRECTORY)) - seen)
        PIC_DIRECTORY_MTIME = PIC_DIRECTORY.stat().st_mtime
        PIC_GROUPS = group_by_day(PIC_FILES)
        PIC_DAYS = list(PIC_GROUPS.keys())

    # Calculate the weights applied to each day based on how far their week
    # is from the current week
    current_week = datetime.datetime.now().isocalendar()[1]

    kernel = NormalDist(0, 1.5).pdf

    # Power law fall-off
    # kernel = lambda x: (x+1)**-1.5

    # Linear fall-off
    # kernel = lambda x: max(1-.2*x, 0)

    normalization = kernel(0)
    def day_weight(day):
        try:
            d = datetime.datetime(int(day[:4]), int(day[4:6]), int(day[6:8]))
        except:
            # pictures without a date are automatically preferred as if they were 4 weeks away
            return kernel(3)/normalization
        week = d.isocalendar()[1]
        tmp = abs(current_week - week)
        # Absolute distance of the day's week from the current week
        distance = min(tmp, 53-tmp)
        # Weight the day by kernel
        return kernel(distance)/normalization

    # use log base N for weights, so one picture weights the day at 1.0,
    # N pictures makes a weight of 2, N^2 pictures makes a weight of 3,
    # N^3 pictures makes a weight of 4, and so on
    DAY_WEIGHTS = [(log(len(PIC_GROUPS[day]), 2)+1)*day_weight(day) for day in PIC_DAYS]
    CUM_DAY_WEIGHTS = list(itertools.accumulate(DAY_WEIGHTS))

    #for (d,w) in sorted(zip(days, weights), key=lambda x: x[1]):
    #    print(d,"%f"%day_weight(d), "%f"%w)

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
            if random.random() < 0.1:
                # Every tenth time or so, pick a picture from a random day, just to
                # change things up a bit
                day = random.choice(PIC_DAYS)
            else:
                # pick a day, weighted according to cumdist, then pick a random pic from that day
                # See https://docs.python.org/3.5/library/random.html#examples-and-recipes
                day = PIC_DAYS[bisect(CUM_DAY_WEIGHTS, random.random() * CUM_DAY_WEIGHTS[-1])]
            x = random.choice(PIC_GROUPS[day])
            PIC_HISTORY.append(x)
            PICS_SEEN.add(x)
            PIC_HISTORY_INDEX = -1

            show(PIC_HISTORY[PIC_HISTORY_INDEX])

            # Update the pics to remove the one we just showed so we don't show it again
            PIC_GROUPS[day].remove(x)
            if len(PIC_GROUPS[day])==0:
                PIC_DAYS.remove(day)
                del PIC_GROUPS[day]
            reset_weights()

        pygame.time.set_timer(PICTURE_CHANGE,DISPLAY_TIME_MS)


    # Change the date format
    if (f.type == pygame.KEYDOWN and f.key == pygame.K_RETURN):
        FORMAT = (FORMAT+1) % 3
        show()

    # Show the previous picture in history
    if ((f.type == pygame.KEYDOWN and f.key == pygame.K_LEFT)
        or (f.type == pygame.MOUSEBUTTONDOWN and f.button == 1)):
        if len(PIC_HISTORY) > -PIC_HISTORY_INDEX:
            PIC_HISTORY_INDEX -= 1
            show(PIC_HISTORY[PIC_HISTORY_INDEX])
            pygame.time.set_timer(PICTURE_CHANGE,DISPLAY_TIME_MS)

    # Show the next picture in history
    if ((f.type == pygame.KEYDOWN and f.key == pygame.K_RIGHT)
        or (f.type == pygame.MOUSEBUTTONDOWN and f.button == 3)):
        if PIC_HISTORY_INDEX < -1:
            PIC_HISTORY_INDEX += 1
            show(PIC_HISTORY[PIC_HISTORY_INDEX])
            pygame.time.set_timer(PICTURE_CHANGE,DISPLAY_TIME_MS)

    # Show the next picture in sorted order that we haven't seen yet (i.e., chronologically)
    # Do not put this pic in our history
    if f.type == pygame.KEYDOWN and f.key == pygame.K_DOWN:
        # Find the place just after where the current pic would have been
        index = bisect_right(PIC_FILES, CURRENT_PICTURE)
        if index < len(PIC_FILES):
            show(PIC_FILES[index])
            pygame.time.set_timer(PICTURE_CHANGE,DISPLAY_TIME_MS)

    # Show the previous picture in sorted order that we haven't seen yet (i.e., chronologically)
    # Do not put this pic in our history
    if f.type == pygame.KEYDOWN and f.key == pygame.K_UP:
        # Find the place in the current pics array where we would have to insert the current pic
        # The pic we want is just before this.
        index = bisect_left(PIC_FILES, CURRENT_PICTURE) - 1
        if index > 0:
            show(PIC_FILES[index])
            pygame.time.set_timer(PICTURE_CHANGE,DISPLAY_TIME_MS)

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

    # Blank the screen on pressing 'b'
    if (f.type == pygame.KEYDOWN
        and f.key == pygame.K_b):
        display_sleep()
    # Any other key or mouse down makes sure we are awake if we are not
    elif (f.type == pygame.KEYDOWN or f.type == pygame.MOUSEBUTTONDOWN) and not display_on():
        display_wake()

    # Wake the screen at the same time every day
    if f.type == SCREEN_WAKE:
        display_wake()
        # Set a sleep timer for 24 hours from now for the next wake
        pygame.time.set_timer(SCREEN_WAKE, 1000*60*60*24)

    # Sleep the screen at the same time every day
    if f.type == SCREEN_SLEEP:
        display_sleep()
        # Set a sleep timer for 24 hours from now for the next sleep
        pygame.time.set_timer(SCREEN_SLEEP, 1000*60*60*24)

    # Update the time every minute
    if f.type == UPDATE_TIME:
        # Refresh the current picture, which will update the time
        if display_on():
            show()
        # Set the next update at the start of the next minute
        pygame.time.set_timer(UPDATE_TIME, next_time())

# Just before exiting, restore the screensaver settings
# screensaver_restore()
