// Settings: connections, display options and the mood-to-music mapping.

import { api } from "../api.js";
import { h, toast } from "../dom.js";
import { saveSettings, setBreak, settings, state } from "../state.js";

function spotifySection(spotify) {
  const configured = spotify?.configured;
  return h(
    "section",
    { class: "card" },
    h("h2", { class: "card-title" }, "Spotify"),
    h(
      "dl",
      { class: "kv" },
      h("dt", null, "Keys"),
      h("dd", null, configured ? "Found in .env" : "Not set"),
      h("dt", null, "Account"),
      h("dd", null, spotify?.connected ? "Connected" : "Not connected")
    ),
    !configured
      ? h(
          "p",
          { class: "hint" },
          "Add ",
          h("code", null, "SPOTIFY_CLIENT_ID"),
          " and ",
          h("code", null, "SPOTIFY_CLIENT_SECRET"),
          " to a ",
          h("code", null, ".env"),
          " file in the project folder."
        )
      : null,
    h(
      "div",
      { style: "margin-top:14px" },
      h("button", { class: "btn", type: "button", disabled: true, "aria-disabled": "true" }, "Connect to Spotify")
    ),
    h("p", { class: "hint" }, "The login is still being built by the team.")
  );
}

function deviceSection(status) {
  return h(
    "section",
    { class: "card" },
    h("h2", { class: "card-title" }, "Data sources"),
    h(
      "dl",
      { class: "kv" },
      h("dt", null, "Mood"),
      h("dd", null, status?.mood_source ?? "Unknown"),
      h("dt", null, "Music"),
      h("dd", null, status?.music_source ?? "Unknown")
    ),
    h("p", { class: "hint" }, "Names starting with Mock are demo data. The team swaps them for the real headband and Spotify in main.py.")
  );
}

function displaySection() {
  const toggle = h(
    "button",
    { class: "switch", type: "button", role: "switch", "aria-checked": String(settings.pauseInBackground), "aria-labelledby": "pause-label" },
    h("span", { class: "knob" })
  );
  toggle.addEventListener("click", () => {
    saveSettings({ pauseInBackground: !settings.pauseInBackground });
    toggle.setAttribute("aria-checked", String(settings.pauseInBackground));
  });

  return h(
    "section",
    { class: "card" },
    h("h2", { class: "card-title" }, "Display"),
    h(
      "div",
      { class: "row-between" },
      h(
        "div",
        null,
        h("strong", { id: "pause-label" }, "Pause live updates in the background"),
        h("p", { class: "hint" }, "When this window is hidden, the screen stops redrawing. Recording and history keep running.")
      ),
      toggle
    )
  );
}

function mappingSection() {
  const inputs = new Map();
  const grid = h("div", { class: "map-grid" });

  for (const mood of state.config.moods) {
    const input = h("input", { class: "field", type: "text", id: `map-${mood.id}`, placeholder: "e.g. ambient, lo-fi" });
    inputs.set(mood.id, input);
    grid.append(h("label", { for: `map-${mood.id}` }, mood.title), input);
  }

  api
    .mappings()
    .then((saved) => {
      for (const [id, input] of inputs) input.value = saved[id] || "";
    })
    .catch(() => {});

  async function save() {
    const mappings = {};
    for (const [id, input] of inputs) {
      if (input.value.trim()) mappings[id] = input.value.trim();
    }
    try {
      await api.saveMappings(mappings);
      toast("Mappings saved");
    } catch {
      toast("Could not save mappings.");
    }
  }

  return h(
    "section",
    { class: "card" },
    h("h2", { class: "card-title" }, "Mood to music"),
    h("p", { class: "hint", style: "margin-bottom:14px" }, "A genre or playlist for each mood. The music side reads these when it picks songs. Empty means no preference."),
    grid,
    h("div", { style: "margin-top:16px" }, h("button", { class: "btn btn-primary", type: "button", onclick: save }, "Save mappings"))
  );
}

function breakSection() {
  const input = h("input", {
    class: "field",
    type: "number",
    id: "break-threshold",
    min: "0.05",
    max: "0.95",
    step: "0.05",
    value: state.break.threshold.toFixed(2),
    "aria-label": "Focus threshold",
  });

  async function save() {
    const value = Number(input.value);
    if (!(value >= 0.05 && value <= 0.95)) {
      toast("Enter a number between 0.05 and 0.95.");
      return;
    }
    try {
      setBreak(await api.setBreakThreshold(value));
      toast("Threshold saved");
    } catch {
      toast("Could not save the threshold.");
    }
  }

  return h(
    "section",
    { class: "card" },
    h("h2", { class: "card-title" }, "Break mode"),
    h("p", { class: "hint", style: "margin-bottom:14px" }, "When Focus stays below this value, a calm song plays and you are offered a break. Turn the mode on from the Dashboard."),
    h(
      "div",
      { class: "filters", style: "margin:0" },
      h("label", { for: "break-threshold", style: "align-self:center" }, "Focus threshold"),
      input,
      h("button", { class: "btn btn-primary", type: "button", onclick: save }, "Save threshold")
    ),
    h(
      "dl",
      { class: "kv", style: "margin-top:14px" },
      h("dt", null, "Low for"),
      h("dd", null, "20 seconds in a row"),
      h("dt", null, "Break length"),
      h("dd", null, "10 minutes, the app is paused")
    )
  );
}

export function render(root) {
  root.append(
    h("h1", { class: "page-title" }, "Settings"),
    h("p", { class: "page-sub" }, "Connections, display options and how moods map to music."),
    h("div", { class: "stack" }, spotifySection(state.status?.spotify), deviceSection(state.status), breakSection(), displaySection(), mappingSection())
  );
}
