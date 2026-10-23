// A JavaScript twin of notes_app.py -- used to verify the language-agnostic NECROMANCY
// claim: scanner_ts (tree-sitter) must produce the same organ map as the Python scanner
// for an equivalent host, reusing the same classify_symbol unchanged.
//
// This file is a dissection FIXTURE only; it is not executed by the test suite.
//
// Expected organ surfaces:
//   Heart:            onTimerTick, mainLoop
//   Senses:           handleCreateNote
//   Memory:           setNote, updateNote, saveNotes
//   Immune:           validateNote, sanitizeNoteText, checkAuthToken
//   Limbs:            sendNotification, renderNoteList
//   Brain affordance: suggestTagsWithLlm
//   External host:    summarizeNotes

const NOTES = {};
const CONFIG = { apiKey: "sk-EXAMPLEEXAMPLEEXAMPLE", store: "notes.json" };

// --- immune-ish tissue -------------------------------------------------------
function sanitizeNoteText(text) {
  return String(text).trim().split(/\s+/).filter(Boolean).join(" ");
}

function validateNote(text) {
  return Boolean(text) && text.length < 10000;
}

function checkAuthToken(token) {
  return token === CONFIG.apiKey;
}

// --- memory tissue -----------------------------------------------------------
function setNote(noteId, text) {
  NOTES[noteId] = { text: sanitizeNoteText(text), ts: Date.now() };
}

function updateNote(noteId, text) {
  if (!Object.prototype.hasOwnProperty.call(NOTES, noteId)) {
    return { ok: false, reason: "missing" };
  }
  NOTES[noteId].text = sanitizeNoteText(text);
  NOTES[noteId].ts = Date.now();
  return { ok: true };
}

function saveNotes() {
  require("fs").writeFileSync(CONFIG.store, JSON.stringify(NOTES));
}

// --- senses tissue -----------------------------------------------------------
function handleCreateNote(request) {
  const text = sanitizeNoteText(request.text || "");
  if (!validateNote(text)) {
    return { ok: false };
  }
  setNote(request.id, text);
  return { ok: true };
}

function onTimerTick(now) {
  return { tick: now };
}

// --- limbs tissue --------------------------------------------------------------
function sendNotification(user, message) {
  return { sentTo: user, message };
}

function renderNoteList() {
  for (const [nid, n] of Object.entries(NOTES)) {
    console.log("note " + nid + ": " + n.text.slice(0, 40));
  }
}

function summarizeNotes() {
  return { count: Object.keys(NOTES).length, ids: Object.keys(NOTES).sort() };
}

// --- a dormant brain affordance ---------------------------------------------------
function suggestTagsWithLlm(text) {
  return ["todo"]; // placeholder; an LLM call would live here
}

// --- the heart -----------------------------------------------------------------
function mainLoop() {
  for (let i = 0; i < 3; i++) {
    onTimerTick(Date.now());
  }
}

module.exports = {
  sanitizeNoteText, validateNote, checkAuthToken, setNote, updateNote, saveNotes,
  handleCreateNote, onTimerTick, sendNotification, renderNoteList, summarizeNotes,
  suggestTagsWithLlm, mainLoop,
};
