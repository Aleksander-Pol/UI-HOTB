# neurhon UI: contract for the EEG and Spotify side

The UI never talks to the headband or to Spotify. It talks to the server in
`neurhon/server/`, and the server talks to three interfaces defined in
`neurhon/server/interfaces.py`. Implement those, and the UI works.

## What to implement

| Interface | Method | Returns |
|---|---|---|
| `MoodProvider` | `get_mood()` | `Mood`: the latest reading. Must return fast (read the newest value, do not wait for new EEG data). |
| `MusicController` | `play()`, `pause()`, `next_track()` | nothing |
| | `now_playing()` | `Track` or `None` |
| | `is_playing()` | `bool` |
| `HistoryStore` | `append(entry)`, `get_entries(limit, since)` | already done by `JsonlHistoryStore` |

`Mood` = `label` (an `id` from `MOOD_LABELS` in `config.py`) + `scores` (dict of
metric name to a number from 0 to 1) + `timestamp` (unix seconds).
The UI draws the mood map from `arousal` and `valence`. Any other key in
`scores` shows up automatically as an extra bar. Add it to `METRICS` in
`config.py` to give it a nice title.

To add a mood label, add a `MoodLabel` to `config.py` (id, title, color, and
its position on the arousal/valence map).

## How to plug your code in

Open `neurhon/server/main.py` and replace the two mocks:

```python
mood = MockMoodProvider()        # -> YourEegMoodProvider(...)
music = MockMusicController()    # -> YourSpotifyController(...)
```

Run with `neurhon-ui` (after `pip install -e .`) or `python -m neurhon.server.main`.

## Auto mode

`step()` in `app.py` reads the mood once per second. When auto mode is on, the
mood label changed and music is playing, it calls `music.next_track()` and
writes a history entry. This is a placeholder: choosing songs from the mood is
your job, so replace that call with your own selection logic.
Per-mood genre or playlist hints typed in Settings are stored in
`data/mappings.json` (also readable at `GET /api/mappings`).

## HTTP and WebSocket (for reference)

| Endpoint | Purpose |
|---|---|
| `GET /api/mood` | latest `Mood` |
| `GET /api/player` | `{track, playing}` |
| `POST /api/player/play`, `/pause`, `/next` | control, returns `{track, playing}` |
| `GET /api/history?limit=&since=` | history, newest first |
| `GET /api/config` | metrics and mood labels |
| `GET /api/status` | data source names, auto mode, Spotify state |
| `POST /api/auto` `{"enabled": true}` | switch auto mode |
| `GET /api/mappings`, `PUT /api/mappings` `{"mappings": {...}}` | mood to genre hints |
| `WS /ws/mood` | pushes `{mood, player, auto}` every second |

Interactive docs while the server runs: `http://127.0.0.1:8000/docs`.
