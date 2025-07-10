# input_xss
Brute-force solution to getting XScreenSavers under Wayland

This watches /dev/input/event*, issues "xscreensaver-command -activate" after the configured timeout period (in seconds) when it doesn't see keyboard/mouse input, and issues "xscreensaver-command -deactivate" when it sees some input (even though that shouldn't be necessary!). 
It also watches DBus for Inhibit events, but because of some bullshit I can't comprehend there's apparently no Uninhibit sent to the portal...? Or I'm too retarded to figure it out. Anyway, I'm catching KDE Inhibit events, instead, which seems to work: your YouTube video should stop the screensaver from starting, and the idle countdown should start running as soon as you pause.

Alright so Wayland fucking sucks but they're going to ram it down our throats anyway, right? Because apparently X11 is a fascist protocol or something. Sure, buddy...

Problem: Wayland doesn't support screensavers because apparently a feature available on every major operating system "isn't needed anymore" according to the fucking morons at DeadRat who have placed themselves in charge of deciding what I get to have on my computer (which doesn't even run their F-tier shitstribution). 

Solution: xscreensaver's daemon still works, still accepts commands via xscreensaver-command, still displays the screensavers full-screen, and still exits cleanly on mouse movement. This is enough for me: I'm not using screensavers for security, but because they look neat.

Caveat: this requires you to either give your unpriv user access to read /dev/input/event* devices, or change the permissions on those devices so anybody can access them. Up to you.

