#!/usr/bin/env python3
"""Interactive front end for minutes_to_html.py and html_to_minutes.py."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from html_to_minutes import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TEMPLATE,
    build_minutes,
    date_from_filename,
    extract_speakers,
    output_filename,
)
from minutes_to_html import build_html_fragment, identify_source  # noqa: E402

DEFAULT_CONFIG_PATH = SCRIPT_DIR / "minutes_config.json"
CONFIG_KEYS = ("input_dir", "template", "output_dir", "fragment_dir", "chair")


def load_config(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {key: str(data[key]) for key in CONFIG_KEYS if key in data}


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        answer = input(f"{prompt}{suffix}: ").strip()
        if answer:
            return answer
        if default is not None:
            return default
        print("A value is required.")


def ask_yes_no(prompt: str, default: bool) -> bool:
    answer = ask(f"{prompt} (y/n)", "y" if default else "n").casefold()
    return answer.startswith("y")


def resolve_path(value: str, base: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (base / path)


def ask_existing_file(prompt: str, base: Path, allow_skip: bool) -> Path | None:
    while True:
        answer = ask(prompt, "" if allow_skip else None)
        if not answer:
            return None
        path = resolve_path(answer, base)
        if path.is_file():
            return path
        print(f"No file found at {path}")


def ask_input_files(base: Path) -> list[Path]:
    while True:
        first = ask_existing_file("Transcript or chat export", base, allow_skip=False)
        second = ask_existing_file(
            "Second export (press Enter to skip)", base, allow_skip=True
        )
        paths = [path for path in (first, second) if path is not None]
        try:
            sources = [identify_source(path) for path in paths]
        except ValueError as error:
            print(error)
            continue
        if len(sources) == len(set(sources)):
            return paths
        print("The two files are the same type. Provide one chat export and one transcript.")


def ask_meeting_date(paths: list[Path]) -> date:
    inferred = next((found for path in paths if (found := date_from_filename(path))), None)
    while True:
        answer = ask("Meeting date (YYYY-MM-DD)", inferred.isoformat() if inferred else None)
        try:
            return date.fromisoformat(answer)
        except ValueError:
            print("Enter the date as YYYY-MM-DD.")


def ask_attendees(fragment: str, chair: str) -> list[str]:
    detected = [name for name in extract_speakers(fragment) if name.casefold() != chair.casefold()]
    print(f"Speakers found: {', '.join(detected) if detected else 'none'}")
    if detected and ask_yes_no("Use this attendee list?", True):
        return detected
    answer = ask("Attendees (comma separated)", ", ".join(detected))
    return [name.strip() for name in answer.split(",") if name.strip()]


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"JSON file with default paths ({', '.join(CONFIG_KEYS)})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    cwd = Path.cwd()

    input_base = resolve_path(config.get("input_dir", "."), cwd)
    print(f"Paths may be absolute or relative to {input_base}")

    input_paths = ask_input_files(input_base)
    meeting_date = ask_meeting_date(input_paths)
    fragment = build_html_fragment(input_paths, meeting_date)

    if ask_yes_no("Save the intermediate HTML fragment?", False):
        fragment_base = resolve_path(config.get("fragment_dir", "."), cwd)
        fragment_path = resolve_path(
            ask("Fragment file", f"fragment_{meeting_date.isoformat()}.html"), fragment_base
        )
        write_file(fragment_path, fragment + "\n")
        print(f"Wrote {fragment_path}")

    template_path = resolve_path(config.get("template", str(DEFAULT_TEMPLATE)), cwd)
    template_path = resolve_path(ask("Template file", str(template_path)), cwd)

    chair = ask("Chair", config.get("chair", "Chair"))
    attendees = ask_attendees(fragment, chair)

    output_dir = resolve_path(config.get("output_dir", str(DEFAULT_OUTPUT_DIR)), cwd)
    output_dir = resolve_path(ask("Output directory", str(output_dir)), cwd)
    output_path = output_dir / ask("Output filename", output_filename(meeting_date))

    if output_path.exists() and not ask_yes_no(f"{output_path} exists. Overwrite?", False):
        print("Nothing written.")
        return

    document = build_minutes(
        fragment=fragment,
        template=template_path.read_text(encoding="utf-8"),
        meeting_date=meeting_date,
        chair=chair,
        attendees=attendees,
    )
    write_file(output_path, document)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        sys.exit(1)
