# Plan: neurhon UI (local web app) + server skeleton

## Context
Zespół buduje system, który czyta mood z EEG (opaska BrainAccess MINI) i dynamicznie dostosowuje playlistę Spotify. Moja część: UI + szkielet serwera z interfejsami i mockami, żeby koledzy mogli podpiąć prawdziwy kod (EEG, Spotify) bez dotykania UI. Repo dziś: tylko `neurhon/entry.py` (`neurhon-run`) i `neurhon/data_aquisition/livestream.py` (strumień EEG). UI nie istnieje.

## Ustalone decyzje
- Lokalna aplikacja WWW: backend Python (FastAPI) serwuje UI + API na `127.0.0.1`. Okno desktopowe/tray później.
- Frontend: czysty HTML + JS (moduły ES) + Tailwind przez CDN, bez Node i buildu. Logika (`api.js`, stan) oddzielona od widoków, żeby później dało się dodać Alpine/Preact.
- Układ responsywny, ale dostęp tylko z tego komputera w v1.
- Spotify: sterowanie istniejącym klientem przez Web API (Premium). Klucze w `.env` (gitignored); UI pokazuje tylko status + przycisk "Connect to Spotify".
- Historia: JSON Lines za interfejsem `HistoryStore` (wpis: timestamp, utwór/playlista, mood, powód zmiany). Bez surowego EEG.
- Mood: etykieta + arousal + valence (0–1), lista etykiet z konfiguracji.
- Sterowanie: tryb auto on/off, pauza, następny utwór.
- Ciemny motyw, akcent zależny od moodu. UI i kod po angielsku.
- Ustawienie "pause UI updates when window is in background" (Page Visibility API); nagrywanie i historia działają dalej.
- Rozszerzenia: rejestr zakładek w jednym pliku (`modules.js`), szczegóły później; kod ma być elastyczny.
- Git: gałąź `ui`, commity tylko na prośbę użytkownika.
- Poza zakresem: logika Spotify i EEG (koledzy).

## Wyjaśnienia
- **entry.py:** NIE jest zmieniany. `neurhon-run` nadal robi to samo (strumień EEG). UI dostaje własną, osobną komendę `neurhon-ui` (`neurhon/server/main.py`). Koledzy później podłączą swój kod EEG/Spotify do interfejsów serwera, nie edytując entry.py.
- **Mock:** atrapa prawdziwego modułu. `MockMoodProvider` zwraca losowy mood co kilka sekund, a `MockMusicController` udaje odtwarzanie (zmienia "teraz gra" w pamięci). Dzięki temu UI da się rozwijać i testować bez opaski i bez Spotify. Gdy koledzy napiszą prawdziwe klasy z tym samym interfejsem, podmieniają mock jedną linią.

## Struktura plików
```
neurhon/
  entry.py, data_aquisition/   # bez zmian (neurhon-run)
  server/
    app.py            # FastAPI: REST + WebSocket, serwuje neurhon/ui
    interfaces.py     # MoodProvider, MusicController, HistoryStore (ABC/Protocol)
    mocks.py          # MockMoodProvider (losowy mood), MockMusicController, w pamięci
    history_jsonl.py  # prawdziwy HistoryStore (JSONL)
    config.py         # etykiety moodu, ścieżki, odczyt .env
    main.py           # entry dla neurhon-ui (domyślnie mocki)
  ui/
    index.html
    js/ api.js, state.js, modules.js (rejestr zakładek), views/{dashboard,history,settings,extensions}.js
    css/ app.css      # drobne style poza Tailwindem, zmienne koloru moodu
docs/api.md           # kontrakt REST/WebSocket dla kolegów
pyproject.toml        # + fastapi, uvicorn; skrypt neurhon-ui
.gitignore            # + .env, CLAUDE.local.md
```

## Kroki
1. Gałąź `ui` z `main`.
2. `interfaces.py` + `mocks.py` + `history_jsonl.py` + `config.py`.
3. `app.py`: endpointy (status, mood now, now playing, controls: auto/pause/next, history list + filtry, settings, Spotify connect status) oraz WebSocket `/ws/mood`.
4. `docs/api.md` z kontraktem.
5. UI: szkielet (nawigacja z `modules.js`, ciemny motyw, akcent z moodu), potem Dashboard, History, Settings, Extensions (pusty slot).
6. `pyproject.toml`: zależności i skrypt `neurhon-ui`; `.gitignore`.
7. Przed UI: `find-skills` w poszukiwaniu skilla do designu UI (na prośbę użytkownika); instalacja po potwierdzeniu.

## Osobisty CLAUDE.md
Preferencje użytkownika mają działać tylko w jego sesji, nie u kolegów. Rozwiązanie: `CLAUDE.local.md` w katalogu głównym repo (osobisty, dodany do `.gitignore`, nie trafia do gita) lub globalny `~/.claude/CLAUDE.md`. Wybieram `CLAUDE.local.md`. Zawartość poda użytkownik; wspólny `CLAUDE.md` (zasady projektu) tworzymy tylko, jeśli zespół tego chce.

## Weryfikacja
- `pip install -e .` i `neurhon-ui` startują bez opaski (mocki); UI otwiera się na `http://127.0.0.1:<port>`.
- Dashboard: mood zmienia się live przez WebSocket; akcent kolorystyczny zmienia się z moodem; opcja background-pause zatrzymuje odświeżanie po przełączeniu karty.
- Controls (auto/pause/next) wywołują mock i widać efekt w UI.
- History: wpisy trafiają do pliku JSONL, filtry działają, po restarcie historia jest zachowana.
- Dodanie dummy zakładki jedną linią w `modules.js` pojawia się w menu.
- Podgląd w wąskim oknie (~375 px) sprawdza responsywność.
- `neurhon-run` nadal działa bez zmian.
