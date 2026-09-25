import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import retained_payment_secret


def test_payment_secret_keeps_stored_value_for_empty_or_masked_submission():
    existing = "live_secret_value"

    assert retained_payment_secret("", existing) == existing
    assert retained_payment_secret("   ", existing) == existing
    assert retained_payment_secret("***", existing) == existing
    assert retained_payment_secret("••••••••", existing) == existing


def test_payment_secret_accepts_only_a_real_replacement_value():
    assert retained_payment_secret("  replacement_secret  ", "old_secret") == "replacement_secret"