// Shared app state. Views subscribe and redraw when it changes.

import { api, openMoodSocket } from "./api.js";

const SETTINGS_KEY = "neurhon.ui.settings";
const TRAIL_LENGTH = 30;
const DEFAULT_COLOR = "#4f8cff";

// ---- settings kept in this browser only ----

const defaults = { pauseInBackground: true };

function loadSettings() {
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}") };
  } catch {
    return { ...defaults };
  }
}

export const settings = loadSettings();

export function saveSettings(patch) {
  Object.assign(settings, patch);
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch {
    // storage can be blocked; the setting then lasts until the page closes
  }
}

// ---- live state ----

export const state = {
  config: { metrics: [], moods: [] },
  status: null,
  mood: null,
  player: null,
  auto: false,
  live: false,
  trail: [],
};

const listeners = new Set();
let pending = false;

/** True while the window is hidden and the user asked us not to redraw. */
export function isPaused() {
  return settings.pauseInBackground && document.hidden;
}

export function moodMeta(label) {
  return state.config.moods.find((m) => m.id === label) || null;
}

function applyAccent() {
  const color = moodMeta(state.mood?.label)?.color || DEFAULT_COLOR;
  document.documentElement.style.setProperty("--mood", color);
}

function notify() {
  if (isPaused()) {
    pending = true;
    return;
  }
  pending = false;
  applyAccent();
  listeners.forEach((fn) => fn(state));
}

/** Calls fn now and again on every change. Returns an unsubscribe function. */
export function subscribe(fn) {
  listeners.add(fn);
  fn(state);
  return () => listeners.delete(fn);
}

function applySnapshot(message) {
  state.mood = message.mood;
  state.player = message.player;
  state.auto = message.auto;

  const { arousal, valence } = message.mood?.scores || {};
  if (arousal != null && valence != null) {
    state.trail.push({ arousal, valence });
    if (state.trail.length > TRAIL_LENGTH) state.trail.shift();
  }
  notify();
}

export function setPlayer(player) {
  state.player = player;
  notify();
}

export function setAuto(auto) {
  state.auto = auto;
  notify();
}

export function redraw() {
  notify();
}

export async function initState() {
  try {
    const [config, status] = await Promise.all([api.config(), api.status()]);
    state.config = config;
    state.status = status;
    state.auto = status.auto;
  } catch (error) {
    console.error("Could not load config and status", error);
  }

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && pending) notify();
  });

  openMoodSocket({
    onMessage: applySnapshot,
    onOpen: () => {
      state.live = true;
      notify();
    },
    onClose: () => {
      state.live = false;
      notify();
    },
  });
}
