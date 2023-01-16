# Picture screensaver

This screensaver tries to show an interesting assortment of pictures. It features:

- A picture selection algorithm that attempts to show interesting and novel pictures (see below for details about the algorithm)
- Mouse and keyboard interaction to easily go back and forward through the pictures previously displayed and display new pictures (missed a picture? you can easily see what everyone else is talking about!).
- Customizable information displayed about the picture as well as the current time
- A night mode that automatically suspends the monitor at night and turns it back on in the morning. You can also manually suspend the monitor.
- A relatively long default picture cycle time (40 minutes) so that the picture display does not continually suck attention from the room


## Pi setup


- install pygame
- Make sure your monitor is set to 1080p resolution
- Run the program by opening a terminal and typing `python picture.py` or [setting up a desktop link](https://www.raspberrypi.org/forums/viewtopic.php?t=248380).

### Pictures

Each picture should be stored in the `/home/pi/Export1080p/` directory, with the first 8 characters of the filename indicating the date of the picture in the format `YYYYMMDD`, i.e., filenames are like `20181231-any-other-text.jpg`. (You can have other filenames, but the picture selection algorithm won't be able to use the picture's date and we won't be able to display the date.)

We use the filename to derive the date of the picture because we assume that the filesystem is relatively slow. We don't want to open up each picture to read its metadata. Instead, we'd rather get the dates of the pictures by just scanning the filenames in the directory.

### Suspending the monitor

In order to get the night mode to work (which suspends the monitor to power-saving mode at night), edit `/boot/config.txt` and add `hdmi_blanking=1`. 



## How to use the program

- At any time, to pick and display a new random picture, press `space` or the middle mouse button.
- To show the picture that was displayed before the current picture, press the left arrow key or the left mouse button. If the first picture is currently displayed, these do nothing.
- To show the picture that was displayed after the current picture, press the right arrow key or right mouse button. If the last picture is currently displayed, these do nothing.
- To cycle the information displayed, press the enter key. Information display cycles between:
  1. No information displayed
  2. The date displayed (derived from the filename)
  3. The filename displayed (without the extension)
- To blank the screen, press the `b` key. You can do this at night to put the monitor to sleep
- To wake the monitor, press any key or move the mouse (you can put it back to sleep with `b` again)
- To quit the program, press `Shift Escape` or hold any mouse button for 30 seconds (these are designed so that young children do not inadvertently quit the program)

## Fun games

We like to play a "Guess the date" game. 

1. Change the display so no information is displayed by pressing the enter key.
2. Display a new picture by pressing the `space` key or the middle mouse button.
3. Have people guess the date of the picture and the story around the picture.
4. Press the enter key to reveal the date of the picture.
5. Go to step 1 and repeat.

Because the program is designed to cycle pictures using just a mouse, we also like to give a bluetooth mouse to anyone in the room and use it as a "clicker" to advance pictures or review past pictures.

## Internal notes

### Picture selection

We show pictures by randomly picking a day weighted by how far the day is from the current day and the log of how many pictures in that day that we haven't shown to you yet. This attempts to pick a picture that:

1. **You haven't seen yet** (we keep track of which pictures we've shown you, and avoid picking them again until there are relatively few pictures left to show you), and
2. **is more likely to be close to this time of year** (we weight days we pick from based on how far from the current day it is, following a normal distribution), and 
3. **likely is different from other pictures you've been seeing** (we assume that the number of pictures in a day follows a power law, and that if there are a *lot* of pictures in a single day, they are likely to be similar, so we weight the day by the log of the number of pictures rather than the actual number of pictures)

But given all that, we occasionally surprise you with a new picture from a completely random day just for fun.

All history about what pictures were displayed is lost when the program is restarted.

### Suspending the monitor

We use `xset dpms force off` to blank the screen and turn off the monitor until another key is pressed. See https://www.raspberrypi.org/documentation/configuration/config-txt/video.md and https://github.com/raspberrypi/linux/issues/487.

See also
- https://wiki.libsdl.org/FAQUsingSDL
- https://stackoverflow.com/questions/39914670/sdl-pollevent-causes-screen-to-wake-up-after-xset-dpms-force-off
- https://ubuntuforums.org/showthread.php?t=1317747&page=3&p=9433671#post9433671


### Other setup tips

To automatically log in and run a program: http://www.raspberry-projects.com/pi/pi-operating-systems/raspbian/auto-running-programs-gui

To control the LEDs: https://www.jeffgeerling.com/blogs/jeff-geerling/controlling-pwr-act-leds-raspberry-pi - set the trigger for each led (if 'none' doesn't work to turn them off, try 'gpio')

