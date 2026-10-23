"""Bounded, duplicate-safe JSON contracts and identifiers; no interpreter."""
import hashlib
import json
import re

LIMIT = 1_000_000


class Error(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise Error(message)


def canonical(value, limit=LIMIT):
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        require(len(encoded.encode("utf-8")) <= limit, "JSON size limit exceeded")
        return encoded
    except (TypeError, RecursionError, UnicodeError) as exc:
        raise Error("invalid JSON value") from exc


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def loads(text):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    try:
        result = json.loads(text, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(Error("nonfinite JSON")))
        canonical(result)
        return result
    except (ValueError, RecursionError) as exc:
        raise Error(str(exc)) from exc


def shape(value, keys):
    require(type(value) is dict and set(value) == set(keys), "unexpected fields: expected " + ", ".join(sorted(keys)))


def identifier(value):
    require(type(value) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,95}", value), "invalid identifier")
    return value


def text(value, maximum=4096, blank=False):
    require(type(value) is str and (blank or bool(value.strip())) and len(value.encode("utf-8")) <= maximum, "invalid or oversized text")
    return value


