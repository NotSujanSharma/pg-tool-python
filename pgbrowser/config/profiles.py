"""Connection profile persistence (load / save to disk)."""

import json
import os

PROFILES_FILE = os.path.expanduser("~/.config/pgbrowser/profiles.json")


def load_profiles() -> list:
    """Return saved connection profiles, or [] on error / missing file."""
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, "r") as fh:
                return json.load(fh)
        except Exception:
            return []
    return []


def save_profiles(profiles: list) -> None:
    """Atomically write profiles to disk with mode 0o600."""
    directory = os.path.dirname(PROFILES_FILE)
    os.makedirs(directory, exist_ok=True)
    tmp = PROFILES_FILE + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(profiles, fh, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, PROFILES_FILE)
