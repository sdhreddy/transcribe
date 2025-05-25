# Speech Mode #

Default option in Transcribe is to provide responses as text in the response window.

Use the **Read Responses Continuously** switch to automatically hear every AI response as it is generated. When this is disabled, you can still hear a single response using the **Suggest Response and Read** button shown in the image below. Toggle state is saved so the app remembers your preference.

Continuous Read Aloud helps users with accessibility needs or for hands‑free use.

While audio is being spoken, speaker input capture is temporarily muted to avoid echo. If you speak while a response is playing, playback stops immediately so your words are transcribed.

To fully eliminate echo, capture resumes only after a brief delay and any input similar to the last spoken response within two seconds is ignored. After playback ends, the last response is retained so it won't be read again until a new answer is produced.


To fully eliminate echo, capture resumes only after a brief delay and any input similar to the last spoken response within two seconds is ignored. Playback state resets after each answer so only the latest response is spoken.

To fully eliminate echo, capture resumes only after a brief delay and any input similar to the last spoken response within two seconds is ignored. After playback ends, the last response is retained so it won't be read again until a new answer is produced.



If audio playback fails, ensure your speakers are enabled and `ffplay` from FFmpeg is installed and on your PATH.

![Screenshot](../assets/ReadResponses.png)

### Adjust Speech Rate

Add `tts_speech_rate` under the `General` section of `parameters.yaml` to control how quickly responses are spoken. A value of `1.0` is normal speed, while higher values play audio faster. Example:

```yaml
General:
  tts_speech_rate: 1.3
```

The default is `1.3`, which provides a more natural pace.
