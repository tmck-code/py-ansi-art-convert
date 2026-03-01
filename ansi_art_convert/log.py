import sys
from typing import Any

DEBUG = False


def dprint(*args: Any, **kwargs: Any) -> None:
    if DEBUG:
        print(*args, **kwargs, file=sys.stderr)
