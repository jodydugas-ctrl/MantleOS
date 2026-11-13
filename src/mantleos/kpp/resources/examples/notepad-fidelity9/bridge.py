"""Persistent virtual-only JSONL bridge for authorized language hosts."""
import json
import sys
from logical_engine import LogicalMachine

MAX_LINE = 262144


def unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError('Duplicate key')
        result[k] = v
    return result


def main():
    machine = LogicalMachine()
    while True:
        line = sys.stdin.buffer.readline(MAX_LINE + 1)
        if not line:
            return 0
        if len(line) > MAX_LINE:
            print(json.dumps({'error': 'Oversized command; session closed'}), flush=True)
            return 2
        try:
            value = json.loads(line, object_pairs_hook=unique,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
            if type(value) is not dict or set(value) != {'action', 'payload'}:
                raise ValueError('Expected action and payload')
            result = machine.send(value['action'], value['payload'])
        except (ValueError, UnicodeError) as error:
            result = {'error': str(error)}
        # Escaped JSON preserves Unicode through legacy Windows stdout encodings.
        print(json.dumps(result, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
