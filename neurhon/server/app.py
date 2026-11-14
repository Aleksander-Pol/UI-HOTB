"""The web server: connects the UI to the mood, music and history modules."""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from neurhon.server.config import DATA_DIR, METRICS, MOOD_LABELS, get_setting
from neurhon.server.interfaces import (
    HistoryEntry,
    HistoryStore,
    MoodProvider,
    MusicController,
)

UI_DIR = Path(__file__).resolve().parent.parent / "ui"
TICK_SECONDS = 1.0  # how often the mood is read and pushed to the UI


class AutoBody(BaseModel):
    enabled: bool


class MappingsBody(BaseModel):
    mappings: dict[str, str]


def create_app(
    mood: MoodProvider,
    music: MusicController,
    history: HistoryStore,
    data_dir: Path = DATA_DIR,
) -> FastAPI:
    """Build the app. It only knows the interfaces, never the real implementations."""

    state = {"auto": False, "mood": None}
    clients: set[WebSocket] = set()
    mappings_path = data_dir / "mappings.json"

    def latest_mood():
        return state["mood"] or mood.get_mood()

    def player_state() -> dict:
        track = music.now_playing()
        return {
            "track": asdict(track) if track else None,
            "playing": music.is_playing(),
        }

    def snapshot() -> dict:
        return {
            "mood": asdict(latest_mood()),
            "player": player_state(),
            "auto": state["auto"],
        }

    def log_change(reason: str) -> None:
        track = music.now_playing()
        if track:
            history.append(HistoryEntry(time.time(), track, latest_mood(), reason))

    def step() -> None:
        """Read the mood once. In auto mode, skip to a new song when the label changes.

        PLACEHOLDER: choosing the music from the mood is the Spotify side's job.
        Here the next song of the mock playlist stands in for that choice.
        """
        previous = state["mood"]
        current = mood.get_mood()
        state["mood"] = current
        if (
            state["auto"]
            and previous is not None
            and previous.label != current.label
            and music.is_playing()
        ):
            music.next_track()
            log_change(f"auto: mood became {current.label}")

    async def broadcast() -> None:
        message = snapshot()
        for client in list(clients):
            try:
                await client.send_json(message)
            except Exception:
                clients.discard(client)

    async def mood_loop() -> None:
        while True:
            try:
                step()
                await broadcast()
            except Exception as error:  # keep the loop alive whatever a provider does
                print(f"mood loop error: {error!r}")
            await asyncio.sleep(TICK_SECONDS)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        task = asyncio.create_task(mood_loop())
        yield
        task.cancel()

    app = FastAPI(title="neurhon", lifespan=lifespan)

    def load_mappings() -> dict[str, str]:
        try:
            return json.loads(mappings_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    @app.get("/api/mood")
    def get_mood():
        return asdict(latest_mood())

    @app.get("/api/player")
    def get_player():
        return player_state()

    @app.post("/api/player/play")
    def play():
        music.play()
        return player_state()

    @app.post("/api/player/pause")
    def pause():
        music.pause()
        return player_state()

    @app.post("/api/player/next")
    def next_track():
        music.next_track()
        log_change("manual skip")
        return player_state()

    @app.get("/api/history")
    def get_history(limit: int = 100, since: float | None = None):
        return [asdict(entry) for entry in history.get_entries(limit, since)]

    @app.get("/api/config")
    def get_config():
        return {
            "metrics": [asdict(metric) for metric in METRICS],
            "moods": [asdict(label) for label in MOOD_LABELS],
        }

    @app.get("/api/status")
    def get_status():
        return {
            "mood_source": type(mood).__name__,
            "music_source": type(music).__name__,
            "auto": state["auto"],
            # "connected" stays False until the Spotify side implements the login.
            "spotify": {
                "configured": bool(get_setting("SPOTIFY_CLIENT_ID")),
                "connected": False,
            },
        }

    @app.post("/api/auto")
    def set_auto(body: AutoBody):
        state["auto"] = body.enabled
        return {"auto": state["auto"]}

    @app.get("/api/mappings")
    def get_mappings():
        return load_mappings()

    @app.put("/api/mappings")
    def put_mappings(body: MappingsBody):
        mappings_path.parent.mkdir(parents=True, exist_ok=True)
        mappings_path.write_text(
            json.dumps(body.mappings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return body.mappings

    @app.websocket("/ws/mood")
    async def mood_socket(websocket: WebSocket):
        await websocket.accept()
        clients.add(websocket)
        try:
            await websocket.send_json(snapshot())
            while True:
                await websocket.receive_text()  # we only wait for the client to leave
        except WebSocketDisconnect:
            pass
        finally:
            clients.discard(websocket)

    # Mounted last, so the /api and /ws routes above take priority.
    if UI_DIR.exists():
        app.mount("/", StaticFiles(directory=UI_DIR, html=True), name="ui")

    return app
