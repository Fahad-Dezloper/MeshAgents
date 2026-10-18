# Teleprompter for the demo video

Read the script on your laptop while the demo video plays on your recording screen and OBS records
your camera, your voice and that screen. The script follows the video's real playback position, so the two
can never drift apart.

## One-time setup (2 minutes)
1. Put `MeshAgents-demo.mp4` in this folder (a copy is here already; re-copy it if the video changes).
2. Open `teleprompter.html` in Chrome on your **laptop screen** (the one next to your camera).

## Every take
1. **OBS:** scene with three sources: Display Capture of your **recording screen** (screen 2), your camera
   (Video Capture Device, small, bottom-right), and your microphone. 1920x1080, 30 fps. Do NOT add desktop
   audio (the video is silent). Check the mic meter moves when you speak.
2. In the teleprompter click **1. Open video window**. Drag the new window to your recording screen and
   double-click it for full screen. It shows the first frame (the empty board) and waits.
3. Click **Practice** first: press Space in the teleprompter *without* opening the video window to rehearse
   the lines with the timer (Space starts, Space pauses, R restarts).
4. For the real take: in OBS press **Start Recording**. Wait 2 seconds. Click the teleprompter window
   (so it has focus) and press **Space**. A 3-2-1 countdown runs, then the video starts and the teleprompter
   starts with it. Read the highlighted green word onward. Look at the camera between lines.
5. When the screen says "Done", stop the OBS recording. The file is your submission video
   (screen + your face + your voice, already in sync).

## Keys
Space start / pause, R restart, M mirror (for a glass prompter), + / - text size, F full screen.

## Edit the words
The script is at the top of `teleprompter.html` (`SCRIPT`). Each line has a start second that matches the video
(see `../voiceover-demo.md` for what is on screen when). About 2 words per second is a comfortable pace.

## If something goes wrong
- Pop-up blocked: allow pop-ups for the page and click "Open video window" again.
- Video window shows a file chooser: pick `MeshAgents-demo.mp4`.
- Teleprompter says "practice mode": the video window is not connected; click Open video window again.
- Out of step after a pause: press R and start the take again.
