from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_import_app_main_is_side_effect_free() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    command = [
        sys.executable,
        "-u",
        "-c",
        "import app.main; print('ok', flush=True)",
    ]

    try:
        result = subprocess.run(
            command,
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError("import app.main hung for more than 5 seconds") from exc

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
