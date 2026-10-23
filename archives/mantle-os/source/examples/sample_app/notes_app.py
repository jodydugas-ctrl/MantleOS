#!/usr/bin/env python3
"""A deliberately ordinary notes app -- the Mantle OS Path-B teaching host.

This file is intentionally NOT Mantle code. It is plain host software that a coding
agent can dissect read-only, then map into Mantle's organism vocabulary without changing
host behavior. That makes it the smallest useful assimilation specimen:

    host app -> read-only inventory -> organ map -> optional anchor/graft

Expected organ surfaces:
    Heart:            on_timer_tick, main_loop
    Senses:           handle_create_note
    Memory:           set_note, update_note, save_notes
    Immune:           validate_note, sanitize_note_text, check_auth_token
    Limbs:            send_notification, render_note_list
    Brain affordance: suggest_tags_with_llm
    External host:    summarize_notes

Run the read-only dissection against it:
    python -m mantle assimilate examples/sample_app --dry-run
"""
import json
import os
import time

NOTES = {}
CONFIG = {"api_key": "sk-EXAMPLEEXAMPLEEXAMPLE", "store": "notes.json"}


# --- immune-ish tissue -------------------------------------------------------
def sanitize_note_text(text):
    """Normalize untrusted inbound text before it becomes host state."""
    return " ".join(str(text).strip().split())


def validate_note(text):
    """Reject empty or oversized notes."""
    return bool(text) and len(text) < 10_000


def check_auth_token(token):
    """Compare a presented token against the configured secret."""
    return token == CONFIG["api_key"]


# --- memory tissue -----------------------------------------------------------
def set_note(note_id, text):
    """Mutate in-memory state."""
    NOTES[note_id] = {"text": sanitize_note_text(text), "ts": time.time()}


def update_note(note_id, text):
    """Mutate existing note state if the note exists."""
    if note_id not in NOTES:
        return {"ok": False, "reason": "missing"}
    NOTES[note_id]["text"] = sanitize_note_text(text)
    NOTES[note_id]["ts"] = time.time()
    return {"ok": True}


def save_notes():
    """Persist state to disk."""
    with open(CONFIG["store"], "w") as f:
        json.dump(NOTES, f)


# --- senses tissue -----------------------------------------------------------
def handle_create_note(request):
    """An inbound request arrives."""
    text = sanitize_note_text(request.get("text", ""))
    if not validate_note(text):
        return {"ok": False}
    set_note(request["id"], text)
    return {"ok": True}


def on_timer_tick(now):
    """A scheduled trigger."""
    return {"tick": now}


# --- limbs tissue --------------------------------------------------------------
def send_notification(user, message):
    """Call an external service (an effect on the world)."""
    # import requests; requests.post("https://notify.example/api", ...)
    return {"sent_to": user, "message": message}


def render_note_list():
    """Human-visible output."""
    for nid, n in NOTES.items():
        print("note %s: %s" % (nid, n["text"][:40]))


def summarize_notes():
    """Ordinary host helper: useful, but not an organ boundary by itself."""
    return {"count": len(NOTES), "ids": sorted(NOTES)}


# --- a dormant brain affordance ---------------------------------------------------
def suggest_tags_with_llm(text):
    """A judgment point: would call a model. Dormant until Phase 2."""
    return ["todo"]  # placeholder; an LLM call would live here


# --- the heart -----------------------------------------------------------------
def main_loop():
    """The pulse of the app."""
    for i in range(3):
        on_timer_tick(time.time())
        time.sleep(0.01)


if __name__ == "__main__":
    handle_create_note({"id": "n1", "text": "water the plants"})
    update_note("n1", "water the plants twice")
    render_note_list()
    main_loop()
    save_notes()
    os.remove(CONFIG["store"])
