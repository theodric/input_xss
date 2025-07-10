# input_xss
Brute-force solution to getting XScreenSavers under Wayland

This watches /dev/input/event*, issues "xscreensaver-command -activate" after the configured timeout period (in seconds) when it doesn't see keyboard/mouse input, and issues "xscreensaver-command -deactivate" when it sees some input (even though that shouldn't be necessary!). 

Alright so Wayland fucking sucks but they're going to ram it down our throats anyway, right? Because apparently X11 is a fascist protocol or something. Sure, buddy...

Problem: Wayland doesn't support screensavers because apparently a feature available on every major operating system "isn't needed anymore" according to the fucking morons at DeadRat who have placed themselves in charge of deciding what I get to have on my computer that doesn't even run their F-tier distribution. 

Solution: xscreensaver's daemon still works, still accepts commands via xscreensaver-command, still displays the screensavers full-screen, and still exits cleanly on mouse movement. This is enough for me: I'm not using screensavers for security, but because they look neat.

Caveat: this requires you to either give your unpriv user access to read /dev/input/event* devices, or change the permissions on those devices so anybody can access them. Up to you.

