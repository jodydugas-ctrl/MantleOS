"""Pantry example adapter. Render the host's existing ordered rows as text."""


def render(rows):
    return "".join(f"{note_id}: {text}\n" for note_id, text in rows)
