"""Record what produced an experiment's outputs. Call `record_run` before writing results."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.rstrip()


def record_run(out_dir: Path, **params) -> None:
    """Write out_dir/run.json with commit, dirty files, command line and parameters."""
    out_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": _git("rev-parse", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": _git("status", "--porcelain").splitlines(),
        "command": " ".join(sys.argv),
        "params": params,
    }
    (out_dir / "run.json").write_text(json.dumps(record, indent=2, default=str))
