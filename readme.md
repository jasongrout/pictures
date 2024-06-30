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

The picture selection algorithm revolves around picking a day of the year, then showing a random picture that was taken on that day of the year that we haven't displayed yet. The interesting part is how to pick a day of the year that we'd like to show a picture from. We weight the days of the year in two different ways simultaneously to try to pick a day:

1. **close to the current week of the year** - we center a normal distribution at the current week of the year and weight all weeks in the year by this normal distribution. We work at the week level instead of the day level so that weights do not dramatically shift day-to-day. We picked the parameters of the normal distribution so that you usually get pictures from the current month, occasionally get pictures from the month before or the month after, and very rarely get pictures from outside of that range.
2. **that has a lot of unseen pictures** - we assume that days typically have either just a couple of pictures or have dozens/hundreds of pictures from a really cool activity. If we weighted the days by how many total pictures were in that day, you'd almost never see a picture from the day with just a couple of pictures. We want to be smarter than that, so we assume the day with hundreds of pictures is probably centered around a single story, and we don't want to always just be swamped by pictures just from that single story. Therefore we weight days based on the *logarithm* of the number of unseen pictures in that day. Currently the weight for a day is calculated as one plus the log base 2 of the number of unseen pictures in the day, which means that a day with 128 unseen pictures is only 8 times more likely to be picked than a day in the same week with one unseen picture. The effect is that we bias towards picking pictures from the cool activities with lots of pictures, but we still are pretty likely to see pictures from normal days as well.

We multiply these two weights together to get a weight for every day, then randomly pick a day of the year according to these weights. Every time we show a picture, we recalculate the weights ignoring it and other pictures we've displayed. If the sum of the weights is very small (i.e., we don't have very many pictures left that we'd like to show), then we forget what pictures we've shown you and start with a fresh weight calculation including all pictures.

Given all that, we occasionally ignore all of the above and surprise you with a new picture from a completely random day, just for fun. This happens about 10% of the time, i.e., about once or twice a day.

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

### Items to do

- [X] Turn off screen at night (see note below about `xset dpms force off`. Also see https://wiki.libsdl.org/FAQUsingSDL#Why_does_SDL_disable_my_screensaver_by_default.3F about allowing the screen to blank while running the program - we'll need to set an environment variable in this program using os.environ).
- [x] Move from using X to just using the display buffer from the command line and ddcutil to actually turn a monitor off
- [ ] Save the pic history to a file to easily pick it back up again after restart
- [x] bias against showing pics we've already shown. Perhaps if we generate a pic already in the history list, try at least once to pick a new random picture, or after we show a picture, take it out of the list.
- [ ] Be able to rate a picture from 1-5, show the rating next, maybe make it more likely to be picked. Be able to say "don't show this pic again".
- [ ] Make it easy to turn on or off LED lights. Ask about good default.
- [x] Picture selection logic - higher preference to pictures in similar season, pics with higher ratings, etc.
- [ ] Print info about the pic on the pic display (date, filename, keywords, caption, etc.)
- [x] up/down keys go through the pictures chronologically?
- [ ] Handle pics with different sizes/orientations. Rotate? Put upright and blur the background? Center smaller pics

- [ ] Read in the next random pic + the next and previous chronological pics pre-emptively. We spend a lot of time in io buffers, so we should be able to eagerly do that read. Perhaps we store NEXT_PICTURE and NEXT_PICTURE_DIRECTION. Anytime we get a new picture direction, we go ahead and calculate the next picture in that direction and store it as well. That way going going in a specific direction gets much faster.
- [ ] Pressing 'f' toggles to/from the filename format. Otherwise Enter just moves us to/from date or empty. Since we hardly ever use the filename format, we are always skipping past it
- [ ] 'h' and '?' shows the keystrokes and mousebuttons registered on a blank screen
- [x] display_on is called a lot - perhaps we cache its output and only call every once in a while?

- [ ] Hook up hardware buttons and switch: buttons to go prev/next, switch to hold a pic, buttons to rate a pic up or down.
