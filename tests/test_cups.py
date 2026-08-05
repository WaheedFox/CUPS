"""Phase 0 smoke tests — verify CUPS package is importable."""

import cups


def test_cups_importable() -> None:
    """cups package can be imported."""
    assert cups is not None
