import json


def strip(line: str) -> str:
    in_string = False
    index = 0
    while index < len(line):
        char = line[index]
        if char == '\\':
            # Skip past the escaped character.
            index += 2
            continue

        if char == '"':
            in_string = not in_string

        if (char == '#' or line[index:index+2] == '//') and not in_string:
            return line[:index]

        index += 1
    return line


def loads(string: str):
    """Like json.loads, but allows // comments."""
    return json.loads('\n'.join(
        strip(line) for line in string.splitlines()
    ))
