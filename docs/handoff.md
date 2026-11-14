# Handoff: stan projektu neurhon UI (dla kolejnego Claude'a)

Ten plik opisuje, co zostało zrobione, dlaczego, i jak pracować z użytkownikiem.
Przeczytaj go w całości, zanim cokolwiek zmienisz lub zaczniesz tłumaczyć kod.

## 1. Kontekst projektu
- Zespół (hackathon HOTB2k27) buduje system: opaska EEG (BrainAccess MINI) -> odczyt "moodu" -> dynamiczna playlista Spotify.
- **Użytkownik robi tylko aplikację/UI.** Koledzy robią część EEG (`neurhon/data_aquisition/`, `neurhon/entry.py`, komenda `neurhon-run`) i integrację Spotify. **Nie zmieniaj `entry.py` ani `livestream.py`.**
- Użytkownik jest początkujący w tym stosie i chce **rozumieć każdą linijkę**. Dlatego kod powstawał krok po kroku.
- Użytkownik pracuje na własnym repo, żeby nie przeszkadzać kolegom: `https://github.com/Aleksander-Pol/UI-HOTB` (remote `origin`). Stare repo kolegów (`shejduk/hotb2k27`) zostało odłączone.

## 2. Jak użytkownik chce pracować (ważne)
- **Język rozmowy: polski.** Kod, komentarze i teksty w UI: angielski.
- **Tłumacz dokładnie**, prostymi słowami, co robi każda funkcja/linia i dlaczego tak. Dobrze działają: krótkie przykłady, tabelki porównawcze, diagramy. Lubi skille `learn` (tłumaczenie z jednym pytaniem kontrolnym) i `artifact-diagramming` (diagramy).
- **Nie zadawaj pytań, dopóki użytkownik o nie nie poprosi** (powiedział to wprost). Wyjątek: realna blokada.
- Wcześniej wymagał trybu "jeden krok na raz, czekaj na `dalej`". Później kazał zrobić całą pierwszą wersję naraz. Trzymaj się tego, o co prosi w danej chwili.
- **Commity: bez śladu Claude'a.** Użytkownik nie chce `Co-Authored-By: Claude`, linii `Claude-Session` ani wzmianek o Claude w commitach. Commity są pod jego nazwiskiem. Nie commituj i nie pushuj bez prośby. **Pusha robi użytkownik sam.**
- Plan prac: `docs/plan.md`. Kontrakt dla kolegów: `docs/api.md`.
- Użytkownik chciał też osobny `CLAUDE.local.md` (tylko dla jego sesji, w `.gitignore`), ale **nie podał jeszcze treści**. Nie wymyślaj jej.

## 3. Stan gitu (w chwili pisania)
- Gałęzie: `main` i `ui`. Cała praca była na `ui`, potem `ui` zmergowano lokalnie do `main` (commit `b1cd43f`). `main` było wtedy 4 commity przed `origin/main`, czyli **push do `main` należał do użytkownika**. Sprawdź `git status -sb`.
- Na GitHubie użytkownik początkowo nie widział folderu `ui`, bo oglądał `main`, a pliki były na gałęzi `ui`.
- Znany drobiazg: `neurhon/__pycache__/__init__.cpython-314.pyc` jest śledzony przez git mimo wpisu w `.gitignore`. Można go zdjąć z repo przez `git rm --cached` (zaproponowano, użytkownik jeszcze nie zdecydował).
- Ten plik (`docs/handoff.md`) nie jest zacommitowany.

## 4. Decyzje projektowe (ustalone przez "grillowanie" użytkownika)
- **Lokalna aplikacja WWW**: backend Python (FastAPI) na `127.0.0.1`, UI w przeglądarce. Dostęp tylko z tego komputera. Układ responsywny na zapas. Tray i okno desktopowe: później.
- **Frontend**: czysty HTML + JS (moduły ES), Tailwind przez CDN, **bez Node i bez kroku budowania**. Później ewentualnie Alpine/Preact przez CDN. Logika (`api.js`, `state.js`) jest oddzielona od widoków, żeby zmiana frameworka dotyczyła tylko widoków.
- **Spotify**: sterowanie istniejącym klientem przez Web API (Premium). Klucze w `.env` (gitignored). UI pokazuje tylko status i nieaktywny przycisk Connect (logowanie robią koledzy).
- **Historia**: JSON Lines za interfejsem `HistoryStore` (podmienialne na SQLite). Bez surowego EEG.
- **Mood**: etykieta + słownik metryk 0..1 (`valence`, `energy`, `focus`; wcześniej było `arousal`, zastąpione przez `energy`). Elastyczne: nowa metryka = nowy klucz.
- **Sterowanie**: tryb auto on/off, pauza, następny utwór.
- **Wygląd**: ciemny motyw, kolor akcentu zależny od aktualnego moodu, UI po angielsku. Opcja w Settings "pauza odświeżania w tle" (Page Visibility API; nagrywanie i historia działają dalej).
- **Rozszerzenia**: rejestr zakładek w `neurhon/ui/js/modules.js` (jedna linia + jeden plik widoku). Szczegóły mechanizmu użytkownik zostawił na później.
- **Walidacja 0..1 w `Mood`**: pytanie o to, czy ma ją robić typ, czy warstwa serwera, **pozostało bez odpowiedzi**. Na razie brak walidacji.

## 5. Mapa kodu

### `neurhon/server/` (backend)
| Plik | Rola |
|---|---|
| `interfaces.py` | Kontrakty. Typy danych: `Mood`, `Track`, `HistoryEntry`. Klasy abstrakcyjne (`ABC`): `MoodProvider.get_mood()`, `MusicController` (`play`, `pause`, `next_track`, `now_playing`, `is_playing`), `HistoryStore` (`append`, `get_entries`). To jedyne, co muszą znać koledzy. |
| `mocks.py` | Atrapy: `MockMoodProvider` (losowy mood, zmiana etykiety co 8 s, dryf wartości), `MockMusicController` (4 wymyślone utwory, stan w pamięci). |
| `history_jsonl.py` | `JsonlHistoryStore`: dopisuje linię JSON na wpis, czyta od najnowszego, pomija uszkodzone linie, `Lock` na zapisie. |
| `config.py` | `METRICS`, `MOOD_LABELS` (id, tytuł, kolor, pozycja na mapie energy/valence, stałe trybu przerwy), `DATA_DIR`/`HISTORY_PATH`, `load_env`/`get_setting` (własny prosty parser `.env`). |
| `app.py` | `create_app(mood, music, history)` buduje FastAPI. Endpointy REST, WebSocket `/ws/mood`, serwowanie `neurhon/ui/`. `step()` + `mood_loop()` w `lifespan` czytają mood co 1 s i rozsyłają go. |
| `main.py` | Komenda `neurhon-ui` / `python -m neurhon.server.main`. **Jedyne miejsce wybierające implementacje** (dziś mocki). Opcje `--port`, `--no-browser`. |

Idee, które warto tłumaczyć użytkownikowi na przykładach z tego kodu:
- `@dataclass` i `field(default_factory=dict)` (dlaczego nie `= {}`): `Mood.scores`.
- Klasy abstrakcyjne i `@abstractmethod`, kontrakt vs implementacja: `interfaces.py` vs `mocks.py`. Podmiana mocka w `main.py` to zmiana jednej linii.
- Czemu `next_track`, a nie `next`, i `get_entries`, a nie `list` (nie przesłaniamy wbudowanych nazw).
- `interfaces.py` (kształt danych, rzadko się zmienia) vs `config.py` (wartości, zmieniane swobodnie).
- GET vs POST, `asdict`, FastAPI i adnotacje typów, `lifespan` i zadanie w tle (`asyncio.create_task`), WebSocket (serwer sam wysyła dane), `Lock`.
- Wzorzec fabryki (`create_app` przyjmuje obiekty z interfejsów).

### `neurhon/ui/` (frontend)
| Plik | Rola |
|---|---|
| `index.html` | Szkielet, Tailwind CDN, czcionki Bricolage Grotesque i Figtree. |
| `css/app.css` | Tokeny kolorów, `--mood` (zarejestrowane `@property`, animowane), karty, mapa, widok mobilny (dolny pasek poniżej 860 px). |
| `js/dom.js` | Pomocniki: `h()` (tworzenie DOM), `s()` (SVG), `icon()`, `toast()`. |
| `js/api.js` | **Jedyny plik rozmawiający z serwerem**: `fetch` + `openMoodSocket` (automatyczny reconnect). |
| `js/state.js` | Wspólny stan, `subscribe`, ustawienia w `localStorage`, logika pauzy w tle (`isPaused`), ustawianie koloru akcentu. |
| `js/modules.js` | Rejestr zakładek. Menu i router budują się z tej listy. |
| `js/app.js` | Start, menu, router po `#hash`, pasek statusu. |
| `js/views/*.js` | `dashboard` (mapa energy/valence z kropką i śladem, Now playing, przełącznik trybu przerwy, paski sygnałów; przełącznik Auto mode jest w Settings), `history` (filtry, grupy po dniach), `settings`, `extensions`. Każdy eksportuje `render(container)` i może zwrócić funkcję sprzątającą. |

Diagram przepływu danych (prywatny artefakt, link może wymagać uprawnień): `https://claude.ai/artifact/4W2udUs5dFtnnWN4dEAQpF`.

## 6. Jak uruchomić i sprawdzić
```
python -m neurhon.server.main --no-browser --port 8000   # z katalogu głównego repo
```
- Zależności: `fastapi`, `uvicorn[standard]` (**`[standard]` jest potrzebne do WebSocketów**). Jest to już w `pyproject.toml`. Komenda `neurhon-ui` wymaga `pip install -e .`.
- Interaktywna dokumentacja API: `http://127.0.0.1:8000/docs`.
- Weryfikacja robiona dotąd: `node --input-type=module --check < plik.js` dla każdego pliku JS, wywołania `curl`, klient WebSocket w Pythonie (`websockets`), zrzuty ekranu przez headless Edge:
  `msedge --headless=new --window-size=1280,860 --virtual-time-budget=9000 --screenshot=plik.png http://127.0.0.1:8000/#dashboard`.
- Dane testowe trafiają do `data/` (gitignored). Po testach usuwaj `data/history.jsonl`, żeby nie zostawić fałszywej historii.

## 7. Znane ograniczenia i otwarte sprawy
- **Tryb auto to placeholder**: przy zmianie etykiety moodu `step()` wywołuje `music.next_track()` i zapisuje wpis `auto: mood became X`. Prawdziwy wybór muzyki z moodu mają napisać koledzy.
- Spotify: `connected` jest na sztywno `False`, przycisk Connect nieaktywny.
- `MockMoodProvider` ma własną tabelę środków etykiet, zdublowaną z `config.MOOD_LABELS` (świadomie, bo to mock).
- Nie testowano ręcznego klikania przycisków w prawdziwej przeglądarce ani opcji pauzy w tle przy ukrytym oknie. Widok mobilny sprawdzony przy 500 px.
- `step()` w pętli asynchronicznej wywołuje synchroniczne `get_mood()`: prawdziwy provider musi zwracać ostatni odczyt natychmiast (nie czekać na EEG).
- Tailwind i czcionki wymagają internetu.
- Brak testów automatycznych.
- Niezrobione z planu: `CLAUDE.local.md` (czeka na treść od użytkownika), tray/okno desktopowe, autostart.

## 8. Tryb przerwy (wersja 2: muzyka pobudzająca, push, jasnoniebieskie uśpienie)
Uzgodniony z użytkownikiem w rozmowie typu grill-me. Przebieg:
1. Break mode włączony (przełącznik w Settings, domyślnie wyłączony), `focus` poniżej progu (Settings, domyślnie 0.30) przez 20 s z rzędu: **faza budzenia**.
2. Budzenie: `capture_state()` (zapamiętanie, co grało i głośność), potem `play_track(losowy z config.WAKE_TRACKS, volume=WAKE_VOLUME, repeat=True)` (Rick Astley, AC/DC, Metallica; głośność 80). Tryb auto nie zmienia utworu. Wpis w historii `break: low focus (x)`. **Powiadomienie systemowe Windows** i baner w aplikacji z przyciskami "Stop music" i "Not now" (kliknięcie w jednym zamyka drugie).
3. **"Not now":** `restore_state(..., resume=True)` (dawna muzyka i głośność wracają), przez **10 minut focus nie jest mierzony** (`BREAK_COOLDOWN_MINUTES`).
4. **"Stop music"** = początek przerwy: `restore_state(..., resume=False)` (głośność wraca, cisza), jasnoniebieska nakładka `#BFDFFF` z ciemnym tekstem, odliczanie 10 min, "End break now". W przerwie nie czytamy nastroju, nie ruszamy muzyki, nie piszemy historii.
5. Koniec przerwy (czas albo przycisk): `restore_state(..., resume=True)` (dawna muzyka wraca), po upływie czasu powiadomienie "Break over". Focus jest mierzony **od razu** (`BREAK_GRACE_MINUTES = 0`), z warunkiem 20 s; przy nadal niskim focusie muzyka pobudzająca wraca.
6. Gdy muzyka nie może wystartować (brak urządzenia, Premium, atrapa), powiadomienie i baner i tak się pokazują. Settings ma przycisk **"Test break mode"** (uruchamia sekwencję i włącza Break mode).

Gdzie jest kod:
- `neurhon/server/break_mode.py`: `BreakMonitor`, czysta maszyna stanów (off, watching, offer, active) z podmienialnym zegarem.
- `neurhon/server/break_flow.py`: `BreakFlow`, łączy monitor z muzyką i powiadomieniami, trzyma zapamiętany stan odtwarzania, wszystko pod `RLock` (wołane z pętli serwera, wątków FastAPI i wątku powiadomień).
- `neurhon/server/notify.py`: `DesktopNotifier` (biblioteka `windows-toasts`, przyciski wywołują funkcje w naszym procesie) i `NullNotifier` (gdy biblioteki brak, działa sam baner). Zależność w `pyproject.toml` tylko dla Windowsa.
- `neurhon/server/notify_setup.py`: jednorazowa rejestracja nazwy "neurhon" i ikony ρ w `HKCU\Software\Classes\AppUserModelId\neurhon.ui` (`python -m neurhon.server.notify_setup`, usunięcie przez `--remove`). Bez niej powiadomienia działają, ale bez własnej nazwy i ikony, a przycisk po przeniesieniu do Centrum akcji może nie zadziałać.
- UI: `neurhon/ui/js/break.js` (baner i nakładka na każdej zakładce); przełącznik Break mode, próg i przycisk testowy są w Settings (z Dashboardu usunięte, tak jak Auto mode).
- Testy: `python -m unittest` (`tests/test_break_mode.py`, `tests/test_break_flow.py`, `tests/test_notify.py`). Testy powiadomień wymagają `windows-toasts` (w `.venv` jest, w globalnym Pythonie są pomijane).
- **Zmiana kontraktu `MusicController`:** `play_track(track, volume=None, repeat=False)`, `capture_state() -> PlaybackState`, `restore_state(state, resume)`. Koledzy od EEG muszą zwracać klucze `energy` i `focus` (zamiast `arousal`).
- Niezweryfikowane bez użytkownika: czy powiadomienie faktycznie wyskakuje i czy jego przyciski działają na jego komputerze (także przy "Nie przeszkadzać"), oraz jak brzmi muzyka na prawdziwym Spotify.

## 9. Wygląd: motyw ρ (dodany później)
- Tożsamość wizualna pochodzi z `docs/rho.png` (grecka litera ρ). Przetworzona wersja z kanałem alfa: `neurhon/ui/img/rho.png` (używana jako maska CSS, więc ma kolor `currentColor`) i `neurhon/ui/img/favicon.png`.
- **Monochromat:** grafit i biel, bez kolorów. Użytkownik wprost zrezygnował z dodatkowych kolorów "na razie". Kolory nastrojów z `config.py` są wyłączone stałą `USE_MOOD_COLORS = false` w `neurhon/ui/js/state.js` (włączenie jednej stałej je przywraca). Nastrój rozpoznaje się po nazwie (duży napis i podpis przy kropce na mapie).
- Czcionki: `Instrument Serif` (napisy wyświetlne, wordmark "neurhon" w kursywie) i `Figtree` (treść).
- **Mapa nastroju:** bez śladu (trace) i bez kotwic z nazwami nastrojów. Zostaje tylko kropka z podpisem aktualnego nastroju, która jedzie razem z nią, i fala przy zmianie nastroju. Użytkownik wprost zrezygnował z trace'u i kotwic. Pola `energy`/`valence` w `MOOD_LABELS` zostają w `config.py`, ale UI ich już nie rysuje.
- Animacje: wartości z skilla `better-ui` (wejście 300 ms z blurem 4 px i przesunięciem 12 px, schodkowo co 100 ms; wyjścia 150 ms; wciśnięcie 0.96). Cały ruch jest za `prefers-reduced-motion: no-preference`, bez niego zostaje cross-fade opacity. Duży ρ w tle "oddycha" (8 s).
- Powierzchnie mają cień zamiast obramowania (z `border: 1px solid transparent` na tryb forced-colors).

## 10. Poradnik dla zespołów EEG i Spotify
- `docs/poradnik_dla_zespolu.pdf` (9 stron, po polsku): gdzie wstawić `EegMoodProvider` i `SpotifyMusicController`, jak je podpiąć w `main.py`, zasady (szybkie `get_mood()`, cache stanu Spotify, odświeżenie po poleceniu), tryb auto i przerwy, lista kontrolna i najczęstsze problemy.
- Szablony kodu z poradnika przetestowano na atrapach (bez opaski i Spotify). Nazw metod biblioteki `spotipy` nie sprawdzano na prawdziwym koncie.
- PDF zbudowano skryptem `reportlab` poza repo; po zmianach kontraktu trzeba go odświeżyć.
