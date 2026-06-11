#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def quoted(path: Path) -> str:
    return f'"{path.resolve().as_posix()}"'


def build_temp_config(repo_root: Path, source_config: Path, site_dir: Path) -> Path:
    text = source_config.read_text(encoding="utf-8")

    if "docs_dir: ." not in text:
        raise RuntimeError("mkdocs.yml does not contain the expected `docs_dir: .` entry.")
    if "site_dir: site" not in text:
        raise RuntimeError("mkdocs.yml does not contain the expected `site_dir: site` entry.")

    text = text.replace("docs_dir: .", f"docs_dir: {quoted(repo_root)}", 1)
    text = text.replace("site_dir: site", f"site_dir: {quoted(site_dir)}", 1)

    temp_dir = Path(tempfile.mkdtemp(prefix="mkdocs-render-"))
    temp_config = temp_dir / "mkdocs.yml"
    temp_config.write_text(text, encoding="utf-8")
    return temp_config


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build MkDocs docs using a temporary wrapper config."
    )
    parser.add_argument(
        "--site-dir",
        type=Path,
        default=None,
        help="Output directory for the rendered site. Defaults to a sibling directory next to the repo.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Pass --strict to mkdocs build.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    source_config = repo_root / "mkdocs.yml"
    site_dir = args.site_dir or (repo_root.parent / f"{repo_root.name}_site")

    if site_dir.exists():
        try:
            shutil.rmtree(site_dir)
        except PermissionError as exc:
            raise RuntimeError(
                f"Cannot remove existing site directory: {site_dir}. "
                "It may be in use by a local preview server. "
                "Stop the server or pass --site-dir to use a different output directory."
            ) from exc
    site_dir.mkdir(parents=True, exist_ok=True)

    temp_config = build_temp_config(repo_root, source_config, site_dir)

    command = [sys.executable, "-m", "mkdocs", "build", "-f", str(temp_config)]
    if args.strict:
        command.append("--strict")

    try:
        completed = subprocess.run(command, check=False)
        return completed.returncode
    finally:
        shutil.rmtree(temp_config.parent, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
