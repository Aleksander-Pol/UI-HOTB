// Dashboard: where you are on the mood map, what is playing, and the player controls.

import { api } from "../api.js";
import { capitalize, h, icon, s, toast } from "../dom.js";
import { moodMeta, setAuto, setPlayer, state, subscribe } from "../state.js";

// Drawing area of the mood map (SVG units).
const W = 460;
const H = 430;
const PX = 44;
const PY = 16;
const PW = 400;
const PH = 380;
const xOf = (valence) => PX + valence * PW;
const yOf = (arousal) => PY + (1 - arousal) * PH;

const PLAY = "M8 5v14l11-7z";
const PAUSE = "M7 5h3.5v14H7zM13.5 5H17v14h-3.5z";
const NEXT = "M6 5l9 7-9 7zM18 5v14";

function sideLabel(text, x, y, anchor, rotate) {
  return s(
    "text",
    {
      class: "plane-text",
      x,
      y,
      "text-anchor": anchor,
      transform: rotate ? `rotate(-90 ${x} ${y})` : null,
    },
    text
  );
}

function buildPlane(moods) {
  const midX = xOf(0.5);
  const midY = yOf(0.5);

  const trail = s("polyline", { class: "plane-trail", points: "" });
  const dot = s(
    "g",
    { class: "plane-dot" },
    s("circle", { class: "halo", r: 22 }),
    s("circle", { class: "core", r: 9 })
  );
  dot.style.transform = `translate(${midX}px, ${midY}px)`;

  const anchors = moods.map((mood) =>
    s(
      "g",
      null,
      s("circle", { cx: xOf(mood.valence), cy: yOf(mood.arousal), r: 5, fill: mood.color, opacity: 0.85 }),
      s(
        "text",
        { class: "plane-anchor-label", x: xOf(mood.valence) + 10, y: yOf(mood.arousal) + 4, fill: mood.color },
        mood.title
      )
    )
  );

  const svg = s(
    "svg",
    { class: "plane", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Mood map: arousal against valence" },
    s("rect", { class: "plane-bg", x: PX, y: PY, width: PW, height: PH, rx: 14 }),
    s("line", { class: "plane-axis", x1: midX, y1: PY, x2: midX, y2: PY + PH }),
    s("line", { class: "plane-axis", x1: PX, y1: midY, x2: PX + PW, y2: midY }),
    sideLabel("Unpleasant", PX, PY + PH + 22, "start"),
    sideLabel("Valence", midX, PY + PH + 22, "middle"),
    sideLabel("Pleasant", PX + PW, PY + PH + 22, "end"),
    sideLabel("Low energy", 16, PY + PH, "start", true),
    sideLabel("Arousal", 16, midY, "middle", true),
    sideLabel("High energy", 16, PY, "end", true),
    ...anchors,
    trail,
    dot
  );

  return {
    svg,
    move(arousal, valence, history) {
      dot.style.transform = `translate(${xOf(valence)}px, ${yOf(arousal)}px)`;
      trail.setAttribute(
        "points",
        history.map((p) => `${xOf(p.valence).toFixed(1)},${yOf(p.arousal).toFixed(1)}`).join(" ")
      );
    },
  };
}

async function togglePlay() {
  try {
    setPlayer(await (state.player?.playing ? api.pause() : api.play()));
  } catch {
    toast("Could not reach the server.");
  }
}

async function skip() {
  try {
    setPlayer(await api.next());
  } catch {
    toast("Could not reach the server.");
  }
}

async function toggleAuto() {
  try {
    const result = await api.setAuto(!state.auto);
    setAuto(result.auto);
  } catch {
    toast("Could not change auto mode.");
  }
}

export function render(root) {
  const plane = buildPlane(state.config.moods);

  const notice = h(
    "div",
    { class: "notice", hidden: true },
    "Showing demo data. No headband or Spotify is connected yet."
  );
  const moodTitle = h("h1", { class: "mood-title" }, "Waiting for data");
  const moodSub = h("p", { class: "mood-sub" }, "Connecting to the server.");

  const playlist = h("p", { class: "now-playlist" });
  const trackTitle = h("p", { class: "now-title" }, "Nothing loaded");
  const artist = h("p", { class: "now-artist" });
  const playButton = h("button", { class: "btn btn-primary btn-round", type: "button", onclick: togglePlay });
  const nextButton = h(
    "button",
    { class: "btn btn-round", type: "button", "aria-label": "Next track", onclick: skip },
    icon(NEXT, true)
  );

  const autoSwitch = h(
    "button",
    { class: "switch", type: "button", role: "switch", "aria-checked": "false", "aria-labelledby": "auto-label", onclick: toggleAuto },
    h("span", { class: "knob" })
  );

  const metricsBox = h("div");
  const meterRows = new Map();

  function meterFor(key, title, description) {
    if (!meterRows.has(key)) {
      const value = h("span", { class: "meter-value" });
      const bar = h("span");
      const row = h(
        "div",
        { class: "meter-row", title: description || null },
        h("div", { class: "meter-head" }, h("span", null, title), value),
        h("div", { class: "meter" }, bar)
      );
      metricsBox.append(row);
      meterRows.set(key, { value, bar });
    }
    return meterRows.get(key);
  }

  function update(st) {
    const mood = st.mood;
    notice.hidden = !st.status?.mood_source?.startsWith("Mock");

    if (mood) {
      const meta = moodMeta(mood.label);
      moodTitle.textContent = meta?.title ?? capitalize(mood.label);
      moodSub.textContent = `Reading from ${new Date(mood.timestamp * 1000).toLocaleTimeString()}`;

      const scores = mood.scores || {};
      plane.move(scores.arousal ?? 0.5, scores.valence ?? 0.5, st.trail);

      const known = st.config.metrics.map((m) => m.id);
      const extra = Object.keys(scores).filter((key) => !known.includes(key));
      const list = [...st.config.metrics, ...extra.map((id) => ({ id, title: capitalize(id) }))];
      for (const metric of list) {
        if (scores[metric.id] == null) continue;
        const row = meterFor(metric.id, metric.title, metric.description);
        row.value.textContent = scores[metric.id].toFixed(2);
        row.bar.style.width = `${Math.round(scores[metric.id] * 100)}%`;
      }
    }

    const player = st.player;
    playlist.textContent = player?.track?.playlist || "No playlist";
    trackTitle.textContent = player?.track?.title ?? "Nothing loaded";
    artist.textContent = player?.track?.artist ?? "";
    playButton.replaceChildren(icon(player?.playing ? PAUSE : PLAY, true));
    playButton.setAttribute("aria-label", player?.playing ? "Pause" : "Play");
    autoSwitch.setAttribute("aria-checked", String(st.auto));
  }

  root.append(
    notice,
    h(
      "div",
      { class: "dash" },
      h("section", { class: "card" }, moodTitle, moodSub, plane.svg),
      h(
        "div",
        { class: "dash-side" },
        h(
          "section",
          { class: "card" },
          h("h2", { class: "card-title" }, "Now playing"),
          playlist,
          trackTitle,
          artist,
          h("div", { class: "controls" }, playButton, nextButton)
        ),
        h(
          "section",
          { class: "card" },
          h(
            "div",
            { class: "row-between" },
            h(
              "div",
              null,
              h("strong", { id: "auto-label" }, "Auto mode"),
              h("p", { class: "hint" }, "Skips to a new song when your mood changes. Works while music is playing.")
            ),
            autoSwitch
          )
        ),
        h("section", { class: "card" }, h("h2", { class: "card-title" }, "Signals"), metricsBox)
      )
    )
  );

  return subscribe(update);
}
