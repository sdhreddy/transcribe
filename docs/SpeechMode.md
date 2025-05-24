# Speech Mode #

Default option in Transcribe is to provide responses as text in the response window.

Use the **Read Responses Continuously** switch to automatically hear every AI response as it is generated. When this is disabled, you can still hear a single response using the **Suggest Response and Read** button shown in the image below. Toggle state is saved so the app remembers your preference.

Continuous Read Aloud helps users with accessibility needs or for hands‑free use.

While audio is being spoken, speaker input capture is temporarily muted to avoid echo. If you speak while a response is playing, playback stops immediately so your words are transcribed.
To fully eliminate echo, capture resumes only after a brief delay and any input matching the last spoken response within one second is ignored.

If audio playback fails, ensure your speakers are enabled and `ffplay` from FFmpeg is installed and on your PATH.

![Screenshot](../assets/ReadResponses.png)
