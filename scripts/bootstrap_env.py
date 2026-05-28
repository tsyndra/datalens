#!/usr/bin/env python3
"""
Merge sibling .env snippets into datalens/.env (gitignored).

Usage:
  ./scripts/bootstrap_env.py           # write REPO_ROOT/.env
  ./scripts/bootstrap_env.py --dry-run
  IIKO_ENV_SOURCE=/abs/a.env:/abs/b.env ./scripts/bootstrap_env.py

See docs in README.md and .env.example.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKDIR_PARENT = REPO_ROOT.parent

FORCED_RESTO_BASE = "https://hatimaki-co.iiko.it:443/resto"
FORCED_OLAP_HOST = "https://hatimaki-co.iiko.it:443"
DEFAULT_CLOUD_API_BASE = "https://api-ru.iiko.services"

SKIP_KEYS_ALWAYS = frozenset({"IIKO_BASE_URLS"})
_CLOUD_HINTS = ("api-ru.iiko.services", "api-iiko")


def postgres_related_key(key: str) -> bool:
    if key == "DATABASE_URL":
        return True
    if key.startswith("POSTGRES_"):
        return True
    if key.startswith(("PGDATABASE", "PGUSER", "PGPASSWORD", "PGHOST", "PGPORT")):
        return True
    if key.startswith("DATALENS_"):
        return True
    return False


def _explicit_sources_resolved() -> Set[Path]:
    out: Set[Path] = set()
    raw = os.environ.get("IIKO_ENV_SOURCE", "").strip()
    if not raw:
        return out
    for part in re.split(r"[\n:;]+", raw):
        p = Path(part.strip()).expanduser()
        try:
            if p.is_file():
                out.add(p.resolve())
        except OSError:
            continue
    return out


def credentials_only_source(path: Path) -> bool:
    """Repo DB/Datalens settings — не подтягиваются из чужих приложений под workdir."""
    try:
        rp = path.resolve()
    except OSError:
        return False

    if rp == (REPO_ROOT / ".credentials.env").resolve():
        return True
    if rp == (REPO_ROOT / ".env").resolve():
        return True
    return rp in _explicit_sources_resolved()


def env_key_allowed(key: str, source: Path) -> bool:
    if postgres_related_key(key):
        return credentials_only_source(source)
    if key.startswith("IIKO_"):
        return key not in SKIP_KEYS_ALWAYS
    return False


def strip_val(raw_val: str) -> str:
    v = raw_val.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1].strip()
    return v


_ENV_LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def parse_dotenv_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        m = _ENV_LINE_RE.match(line)
        if not m:
            continue
        key, rhs = m.group(1), m.group(2)
        if key in SKIP_KEYS_ALWAYS or not env_key_allowed(key, path):
            continue
        out[key] = strip_val(rhs)
    return out


def split_sources_env() -> List[Path]:
    paths: List[Path] = []
    env_src = os.environ.get("IIKO_ENV_SOURCE", "").strip()
    if not env_src:
        return paths
    for part in re.split(r"[\n:;]+", env_src):
        p = Path(part.strip()).expanduser()
        if p.is_file():
            paths.append(p)
    return paths


def dedupe(paths: Iterable[Path]) -> List[Path]:
    seen: Set[str] = set()
    out: List[Path] = []
    for p in paths:
        rp = str(p.resolve())
        if rp not in seen:
            seen.add(rp)
            out.append(p)
    return out


def _alias_key(key: str) -> str:
    if key == "IIKO_USER":
        return "IIKO_LOGIN"
    if key == "IIKO_API_KEY":
        return "IIKO_API_LOGIN"
    return key


def merge_ordered(file_paths: Sequence[Path]) -> Tuple[Dict[str, str], List[str]]:
    merged: Dict[str, str] = {}
    warns: List[str] = []

    oldest_first = sorted(file_paths, key=lambda p: (p.stat().st_mtime, str(p)))

    for path in oldest_first:
        try:
            data = parse_dotenv_file(path)
        except OSError as e:
            warns.append(f"SKIP {path}: {e}")
            continue
        for key, raw in data.items():
            key = _alias_key(key)
            val = raw.strip()
            if not val:
                continue
            prev = merged.get(key)
            if prev is not None and prev != val:
                warns.append(f"conflicting {key}: value from newer file wins -> {path}")
            merged[key] = val

    return merged, warns


def _looks_cloud(url: str) -> bool:
    u = url.lower()
    return any(h in u for h in _CLOUD_HINTS)


def canon_cloud_base(merged: Dict[str, str]) -> Optional[str]:
    for k in ("IIKO_CLOUD_API_BASE_URL", "IIKO_API_BASE_URL"):
        v = merged.get(k, "").strip()
        if v and _looks_cloud(v):
            return v.rstrip("/")
    legacy = merged.get("IIKO_BASE_URL", "").strip()
    if legacy and _looks_cloud(legacy):
        return legacy.rstrip("/")
    if merged.get("IIKO_API_LOGIN"):
        return DEFAULT_CLOUD_API_BASE.rstrip("/")
    return None


def finalize(merged: Dict[str, str]) -> Dict[str, str]:
    out = dict(merged)

    login_slot = out.get("IIKO_API_LOGIN", "").strip()
    if login_slot:
        out["IIKO_API_LOGIN"] = login_slot
        out["IIKO_API_KEY"] = login_slot

    cloud_base = canon_cloud_base(out)
    if cloud_base:
        out["IIKO_CLOUD_API_BASE_URL"] = cloud_base
        out["IIKO_API_BASE_URL"] = cloud_base

    out.pop("IIKO_CLOUD_BASE", None)

    out["IIKO_RESTO_BASE_URL"] = FORCED_RESTO_BASE.rstrip("/")
    out["IIKO_OLAP_SERVER_URL"] = FORCED_OLAP_HOST.rstrip("/")

    assert SKIP_KEYS_ALWAYS.isdisjoint(out.keys())

    return out

def _needs_env_quotes(val: str) -> bool:
    if not val:
        return True

    safe = r"^[A-Za-z0-9_.:@%+/-]+$"

    return not re.fullmatch(safe, val)


def render_env(data: Dict[str, str]) -> str:
    lines = [
        "# Generated by scripts/bootstrap_env.py — do not commit",
        "",
    ]

    def sort_key(k: str) -> Tuple[int, str]:
        priority = {
            "IIKO_CLOUD_API_BASE_URL": 0,
            "IIKO_API_BASE_URL": 1,
            "IIKO_API_LOGIN": 2,
            "IIKO_API_KEY": 3,
            "IIKO_RESTO_BASE_URL": 4,
            "IIKO_OLAP_SERVER_URL": 5,
            "DATABASE_URL": 6,
        }
        return priority.get(k, 20), k

    for k in sorted(data.keys(), key=sort_key):
        v = data[k]
        if _needs_env_quotes(v):
            esc = v.replace('"', '\\"')
            lines.append(f'{k}="{esc}"')
        else:
            lines.append(f"{k}={v}")
    lines.append("")
    return "\n".join(lines)


def discover_sources_fixup() -> List[Path]:
    local = REPO_ROOT / ".env"
    cand: List[Path] = []

    cand.extend(split_sources_env())
    cc = REPO_ROOT / ".credentials.env"
    if cc.is_file():
        cand.append(cc)
    if WORKDIR_PARENT.is_dir():
        cand.extend(sorted(p for p in WORKDIR_PARENT.glob("*/.env") if p.is_file()))
        cand.extend(sorted(p for p in WORKDIR_PARENT.glob("*/*/.env") if p.is_file()))

    cand = dedupe(cand)

    lr = local.resolve()

    cand = [p for p in cand if p.resolve() != lr]
    cand.sort(key=lambda p: (p.stat().st_mtime, str(p)))

    if local.is_file():
        cand.append(local)
    return cand


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Print to stdout, do not write .env")
    ap.add_argument(
        "--verbose",
        action="store_true",
        help="Log source files / warnings about overwrites",
    )
    ns = ap.parse_args()

    try:
        srcs = discover_sources_fixup()
        merged_raw, warns = merge_ordered(srcs)
        finalized = finalize(merged_raw)

        if ns.verbose:
            print("Sources (oldest first for merge):")
            for i, path in enumerate(sorted(srcs, key=lambda p: (p.stat().st_mtime, str(p))), 1):
                print(f"  [{i}] {path}")
            print("Warnings:")
            for w in warns:
                print(f"  {w}")

        text = render_env(finalized)

        if ns.dry_run:
            sys.stdout.write(text)
            return 0

        out_path = REPO_ROOT / ".env"
        tmp = out_path.with_suffix(".env.tmp")

        tmp.write_text(text, encoding="utf-8")
        tmp.replace(out_path)

        print(f"Wrote {out_path} from {len(srcs)} inputs.", file=sys.stderr)
        return 0
    except Exception as exc:
        print(f"bootstrap_env FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
