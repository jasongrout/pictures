#!/usr/bin/env python3

""" 
Display pictures in a screensaver
"""

from random import SystemRandom
import datetime
import pygame
import os
import pygame.freetype
import datetime
from bisect import bisect, bisect_left, bisect_right
from collections import defaultdict
from math import log
import itertools
from normdist import NormalDist
from blanking_console import Console
from blanking_wayland import Wayland

def logmsg(msg):
    timemsg =f"{datetime.datetime.now()} {msg}" 
    print(timemsg)
    with open('pictures.log', 'a') as f:
        f.write(timemsg+'\n')


# Create the right display object
for c in (Wayland, Console):
    if c.active():
        logmsg(f"display {c}")
        DISPLAY = c()
        logmsg(f"display on: {DISPLAY.on(check=True)}")
        break

# Set the variables so we can easily change the program
FULLSCREEN = True
SMALL_SCREEN_SIZE=(600,400)
DISPLAY_TIME_MS = 40 * 60 * 1000 # milliseconds a picture is displayed by default
FONTSIZE = 120

# The default text format:
# - 0: no text
# - 1: date
# - 2: filename
FORMAT = 1

# The directory of pictures
PIC_DIRECTORY = '/home/pi/Export1080p/'

# Time (hour, minute) of sleep and wake each day
WAKE = (6, 30)
SLEEP = (21,30)


def format_filename(filename):
    """Format the filename string to display the date, depending on the global FORMAT."""
    if FORMAT == 0:
        return ''
    elif FORMAT == 1:
        if filename[0] == '2':
            return datetime.datetime.strptime(filename[:8], "%Y%m%d").strftime("%d %b %Y")
        else:
            return ''
    elif FORMAT == 2:
        return os.path.splitext(filename)[0]

def group_by_day(data):
    """Group picture filenames like 20200528.jpg into days."""
    groups = defaultdict(list)
    for name in data:
        groups[name[:8]].append(name)
    return groups

# Define custom pygame events we will use.
PICTURE_CHANGE = pygame.USEREVENT
SCREEN_SLEEP = pygame.USEREVENT + 1
SCREEN_WAKE = pygame.USEREVENT + 2
UPDATE_TIME = pygame.USEREVENT + 3

random = SystemRandom()

CURRENT_FILENAME = None
CURRENT_IMAGE = None

NEXT_RANDOM_FILENAME = None
NEXT_RANDOM_IMAGE = None

NEXT_FILENAME = None
NEXT_IMAGE = None

def load(filename):
    try:
        path = os.path.join(PIC_DIRECTORY, filename)
        image = pygame.image.load(path).convert()
    except:
        print(f"Error loading file ${path}")
        raise
    # Sometimes we are halting because cimage seems to be None below. We'll try
    # to trap that error early.
    if image is None:
        raise ValueError(f"Could not load image ${filename}")
    return image

def show(file = None):
    """Show a picture. file is a (filename, pygame image) pair. If file not specified, refresh the current picture."""
    global CURRENT_FILENAME
    global CURRENT_IMAGE

    if file is not None:
        CURRENT_FILENAME, CURRENT_IMAGE = file

    screen_width = screen.get_width()
    screen_height = screen.get_height()

    # blank the screen
    screen.fill([0,0,0])

    # Show the image
    if FULLSCREEN:
        offset = round((screen_width - CURRENT_IMAGE.get_width()) / 2)
        screen.blit(CURRENT_IMAGE, (offset, 0))
    else:
        pygame.transform.smoothscale(CURRENT_IMAGE, SMALL_SCREEN_SIZE, screen) # development

    # Put the filename 5 pixels from the bottom of the screen, 10 pixels from left edge
    words = font.render( format_filename(CURRENT_FILENAME),  fgcolor=(255,255,255), bgcolor=(0,0,0,100))
    screen.blit(words[0], (10, screen_height - words[0].get_height() - 5))

    # Time is 5 pixels from bottom, 10 pixels from right edge
    datetext = font.render( datetime.datetime.now().strftime("%H:%M"), fgcolor=(255,255,255), bgcolor=(0,0,0,100))
    screen.blit(datetext[0], (screen_width - datetext[0].get_width() - 10, screen_height - datetext[0].get_height() - 5))

    pygame.display.flip()

# Total history of filenames that have been viewed since the program start, even across `seen` resets
PIC_HISTORY = []

# The position of the current picture in the history array
PIC_HISTORY_INDEX = len(PIC_HISTORY) - 1

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
    global PIC_DIRECTORY_MTIME, PIC_FILES, PICS_SEEN, DAY_WEIGHTS, CUM_DAY_WEIGHTS, PIC_GROUPS, PIC_DAYS

    # If we have hardly any pics left (by weight), reset everything so the scan picks up everything
    # The threshold value relies on the log weighting scale and the kernel being normalized
    if max(DAY_WEIGHTS or [0])<=1e-5:
        PICS_SEEN = set()
        PIC_DIRECTORY_MTIME = None

    # If the pic directory has changed (or mtime been reset), rescan all the files
    if  PIC_DIRECTORY_MTIME != os.path.getmtime(PIC_DIRECTORY):
        PIC_FILES = sorted(set(os.listdir(PIC_DIRECTORY)) - PICS_SEEN)
        PIC_DIRECTORY_MTIME = os.path.getmtime(PIC_DIRECTORY)
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

logmsg("Loading pictures...")
reset_weights()
logmsg("Loaded!")

def choose_random_pic():
    """Return a random pic according to the distribution"""
    if random.random() < 0.1:
        # Every tenth time or so, pick a picture from a random day, just to
        # change things up a bit
        day = random.choice(PIC_DAYS)
    else:
        # pick a day, weighted according to cumdist, then pick a random pic from that day
        # See https://docs.python.org/3.5/library/random.html#examples-and-recipes
        day = PIC_DAYS[bisect(CUM_DAY_WEIGHTS, random.random() * CUM_DAY_WEIGHTS[-1])]
    
    filename = random.choice(PIC_GROUPS[day])

    # Update the global pic data to remove the one we just showed picked so we
    # don't pick it again
    PIC_GROUPS[day].remove(filename)
    if len(PIC_GROUPS[day])==0:
        PIC_DAYS.remove(day)
        del PIC_GROUPS[day]
    reset_weights()
    return filename

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
font = pygame.freetype.SysFont('freesans', FONTSIZE)

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
        or (f.type == pygame.KEYDOWN and f.key in (pygame.K_SPACE, pygame.K_KP_0))
        or (f.type == pygame.MOUSEBUTTONDOWN and f.button == 2)):

        if DISPLAY.on():
            if NEXT_RANDOM_FILENAME is None:
                NEXT_RANDOM_FILENAME = choose_random_pic()
                NEXT_RANDOM_IMAGE = load(NEXT_RANDOM_FILENAME)
            PIC_HISTORY.append(NEXT_RANDOM_FILENAME)
            PIC_HISTORY_INDEX = len(PIC_HISTORY) - 1
            PICS_SEEN.add(NEXT_RANDOM_FILENAME)

            show((NEXT_RANDOM_FILENAME, NEXT_RANDOM_IMAGE))

            # Update NEXT_FILENAME
            NEXT_RANDOM_FILENAME = choose_random_pic()
            NEXT_RANDOM_IMAGE = load(NEXT_RANDOM_FILENAME)

        pygame.time.set_timer(PICTURE_CHANGE,DISPLAY_TIME_MS)


    # Change the date format
    if (f.type == pygame.KEYDOWN and f.key in (pygame.K_RETURN, pygame.K_KP_ENTER)):
        FORMAT = (FORMAT+1) % 3
        show()

    # Show the previous picture in history
    if ((f.type == pygame.KEYDOWN and f.key in (pygame.K_LEFT, pygame.K_KP_4))
        or (f.type == pygame.MOUSEBUTTONDOWN and f.button == 1)):
        if PIC_HISTORY_INDEX > 0:
            PIC_HISTORY_INDEX -= 1
            file = PIC_HISTORY[PIC_HISTORY_INDEX]
            image = NEXT_IMAGE if NEXT_FILENAME == file else load(file)
            show((file, image))

            if PIC_HISTORY_INDEX - 1 > 0:
                NEXT_FILENAME = PIC_HISTORY[PIC_HISTORY_INDEX - 1]
                NEXT_IMAGE = load(NEXT_FILENAME)
            pygame.time.set_timer(PICTURE_CHANGE,DISPLAY_TIME_MS)

    # Show the next picture in history
    if ((f.type == pygame.KEYDOWN and f.key in (pygame.K_RIGHT, pygame.K_KP_6))
        or (f.type == pygame.MOUSEBUTTONDOWN and f.button == 3)):
        if PIC_HISTORY_INDEX < len(PIC_HISTORY) - 1:
            PIC_HISTORY_INDEX += 1
            file = PIC_HISTORY[PIC_HISTORY_INDEX]
            image = NEXT_IMAGE if NEXT_FILENAME == file else load(file)
                
            show((file, image))

            if PIC_HISTORY_INDEX + 1 < len(PIC_HISTORY) - 1:
                NEXT_FILENAME = PIC_HISTORY[PIC_HISTORY_INDEX + 1]
                NEXT_IMAGE = load(NEXT_FILENAME)

            pygame.time.set_timer(PICTURE_CHANGE,DISPLAY_TIME_MS)

    # Show the next picture in sorted order that we haven't seen yet (i.e., chronologically)
    # Do not put this pic in our history
    if f.type == pygame.KEYDOWN and f.key in (pygame.K_DOWN, pygame.K_KP_2):
        # Find the place just after where the current pic would have been
        index = bisect_right(PIC_FILES, CURRENT_FILENAME)
        if index < len(PIC_FILES):
            file = PIC_FILES[index]
            image = NEXT_IMAGE if NEXT_FILENAME == file else load(file)
            show((file, image))
            if index + 1 < len(PIC_FILES):
                NEXT_FILENAME = PIC_FILES[index + 1]
                NEXT_IMAGE = load(NEXT_FILENAME)
            pygame.time.set_timer(PICTURE_CHANGE,DISPLAY_TIME_MS)

    # Show the previous picture in sorted order that we haven't seen yet (i.e., chronologically)
    # Do not put this pic in our history
    if f.type == pygame.KEYDOWN and f.key in (pygame.K_UP, pygame.K_KP_8):
        # Find the place in the current pics array where we would have to insert the current pic
        # The pic we want is just before this.
        index = bisect_left(PIC_FILES, CURRENT_FILENAME) - 1
        if index > 0:
            file = PIC_FILES[index]
            show((file, load(file)))

            if index - 1 > 0:
                NEXT_FILENAME = PIC_FILES[index - 1]
                NEXT_IMAGE = load(NEXT_FILENAME)

            pygame.time.set_timer(PICTURE_CHANGE,DISPLAY_TIME_MS)

    # Quit the program
    if f.type == pygame.QUIT:
        break

    # Quit if shift-escape
    if (f.type == pygame.KEYDOWN
        and f.key == pygame.K_ESCAPE
        and (f.mod & pygame.KMOD_SHIFT != 0)):
        break

    # Quit if you hold down a mouse button for 30 seconds
    if (f.type == pygame.MOUSEBUTTONDOWN and f.button in [1,2,3]):
        pygame.time.set_timer(pygame.QUIT,1000*30)
    if (f.type == pygame.MOUSEBUTTONUP and f.button in [1,2,3]):
        # Cancel the quit event since we let up on the mouse button
        pygame.time.set_timer(pygame.QUIT,0)

    # Blank the screen on pressing 'b'
    if (f.type == pygame.KEYDOWN and f.key in (pygame.K_b, pygame.K_KP_MINUS)):
        DISPLAY.sleep()
    # Any other key or mouse down makes sure we are awake if we are not
    elif (f.type == pygame.KEYDOWN or f.type == pygame.MOUSEBUTTONDOWN) and not DISPLAY.on():
        DISPLAY.wake()
        show()
        logmsg(f"Woke, display is now {DISPLAY.on(check=True)}")

    # Wake the screen at the same time every day
    if f.type == SCREEN_WAKE:
        DISPLAY.wake()
        show()
        # Set a sleep timer for 24 hours from now for the next wake
        pygame.time.set_timer(SCREEN_WAKE, 1000*60*60*24)
        logmsg(f"Woke, display is now {DISPLAY.on(check=True)}")

    # Sleep the screen at the same time every day
    if f.type == SCREEN_SLEEP:
        DISPLAY.sleep()
        # Set a sleep timer for 24 hours from now for the next sleep
        pygame.time.set_timer(SCREEN_SLEEP, 1000*60*60*24)

    # Update the time every minute
    if f.type == UPDATE_TIME:
        # every so often when it is not time-sensitive, do a hard refresh of DISPLAY.on
        # Refresh the current picture, which will update the time
        if DISPLAY.on(check=True):
            show()
            logmsg("Refreshed time")
        else:
            logmsg("skipped time refresh, DISPLAY.on is {DISPLAY.on(check=True)}")
        # Set the next update at the start of the next minute
        nexttime = next_time()
        pygame.time.set_timer(UPDATE_TIME, nexttime)
        logmsg(f"Set time refresh to {nexttime}")

# Just before exiting, restore the screensaver settings
DISPLAY.restore()
