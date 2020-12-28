import re

NEVER_CHECK_TIMEOUT = 100_000_000


def camel_to_snake(string: str) -> str:
    string = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", string)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", string).lower()


def snake_to_camel(string: str) -> str:
    return "".join(word.title() for word in string.split("_"))
