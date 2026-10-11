#!/usr/bin/env python3
"""Search a binary for hex bytes; each ?? matches exactly one arbitrary byte."""

import argparse
import re
from pathlib import Path


def compile_pattern(pattern):
    tokens = pattern.split()
    if not tokens:
        raise ValueError('The pattern must contain at least one byte.')
    parts = []
    for token in tokens:
        if token == '??':
            parts.append(b'.')
        elif re.fullmatch(r'[0-9a-fA-F]{2}', token):
            parts.append(re.escape(bytes.fromhex(token)))
        else:
            raise ValueError('Use two-digit hex bytes or ?? separated by spaces.')
    return re.compile(b''.join(parts), re.DOTALL)


def find_offsets(data, pattern):
    regex = compile_pattern(pattern)
    return [match.start() for match in re.finditer(b'(?=' + regex.pattern + b')', data, re.DOTALL)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('pattern', help='For example: "55 48 ?? 00"')
    args = parser.parse_args()
    try:
        offsets = find_offsets(args.file.read_bytes(), args.pattern)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    for offset in offsets:
        print(hex(offset))
    print('Matches:', len(offsets))


if __name__ == '__main__':
    main()
