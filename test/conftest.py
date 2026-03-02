import difflib


def pytest_assertrepr_compare(op: str, left: str, right: str) -> list[str] | None:
    if not (isinstance(left, str) and isinstance(right, str) and op == "=="):
        return None

    diff = list(difflib.unified_diff(left.splitlines(), right.splitlines()))
    debugDiff = list(difflib.unified_diff(f'{left!r}', f'{right!r}'))

    return [
        "Comparing strings:",
        "   diff:",
        *diff,
        *debugDiff,
        *[f'{left!r}', f'{right!r}'],
    ]
