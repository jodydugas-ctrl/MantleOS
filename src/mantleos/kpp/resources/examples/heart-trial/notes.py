"""Standalone synthetic host. Its storage and commands work before implantation."""
import argparse
import json
from pathlib import Path
import sqlite3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("operation", choices=["create", "list", "read", "update", "export"])
    parser.add_argument("values", nargs="*")
    args = parser.parse_args()
    lengths = {"create": 1, "list": 0, "read": 1, "update": 2, "export": 0}
    if len(args.values) != lengths[args.operation]:
        parser.error("wrong number of operation arguments")
    with sqlite3.connect(args.db) as db:
        db.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, text TEXT NOT NULL)")
        if args.operation == "create":
            result = db.execute("INSERT INTO notes(text) VALUES (?)", args.values).lastrowid
        elif args.operation == "update":
            cursor = db.execute("UPDATE notes SET text=? WHERE id=?", args.values[::-1])
            if not cursor.rowcount:
                parser.error("note not found")
            result = True
        elif args.operation == "read":
            row = db.execute("SELECT text FROM notes WHERE id=?", args.values).fetchone()
            if row is None:
                parser.error("note not found")
            result = row[0]
        else:
            rows = db.execute("SELECT id,text FROM notes ORDER BY id").fetchall()
            if args.operation == "export":
                try:
                    from notes_export import render
                except ModuleNotFoundError as error:
                    if error.name != "notes_export":
                        raise
                    parser.error("text export has not been admitted")
                print(render(rows), end="")
                return
            result = rows
        print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
