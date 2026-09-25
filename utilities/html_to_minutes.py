#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import re
from datetime import date
from pathlib import Path

SPEAKER_RE = re.compile(r'<cite class="speaker">(?P<speaker>.*?):\s*</cite>')
DATE_IN_FILENAME_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
PRONOUN_RE = re.compile(r"\s*\((?:[^()]*/[^()]*)\)\s*$")

DEFAULT_TEMPLATE = Path(__file__).with_name("minutes_MonthDay_Year_Template.html")
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "minutes"
FRAGMENT_INDENT = "\t\t\t\t"


def normalize_speaker(name: str) -> str:
    name = html.unescape(name)
    name = PRONOUN_RE.sub("", name)
    return re.sub(r"\s+", " ", name).strip()


def extract_speakers(fragment: str) -> list[str]:
    speakers: list[str] = []
    seen: set[str] = set()
    for match in SPEAKER_RE.finditer(fragment):
        speaker = normalize_speaker(match.group("speaker"))
        key = speaker.casefold()
        if speaker and key not in seen:
            seen.add(key)
            speakers.append(speaker)
    return speakers


def indent_fragment(fragment: str) -> str:
    lines = [line.rstrip() for line in fragment.strip().splitlines()]
    return "\n".join(FRAGMENT_INDENT + line if line else "" for line in lines)


def date_from_filename(path: Path) -> date | None:
    match = DATE_IN_FILENAME_RE.search(path.name)
    return date.fromisoformat(match.group()) if match else None


def long_date(meeting_date: date) -> str:
    return f"{meeting_date.day} {meeting_date:%B %Y}"


def output_filename(meeting_date: date) -> str:
    return f"minutes_{meeting_date:%b}{meeting_date:%d}_{meeting_date:%Y}.html"


def build_minutes(
    fragment: str,
    template: str,
    meeting_date: date,
    chair: str,
    attendees: list[str] | None = None,
) -> str:
    speakers = attendees if attendees is not None else extract_speakers(fragment)
    present = [speaker for speaker in speakers if speaker.casefold() != chair.casefold()]

    document = template.replace("{DATE}", html.escape(long_date(meeting_date)))
    document = document.replace(
        "{Names}", html.escape(", ".join(present)) if present else "None recorded"
    )
    document = document.replace("{Chair}", html.escape(chair))
    return document.replace(
        '<h2>Meeting Minutes</h2>\n',
        '<h2>Meeting Minutes</h2>\n\n' + indent_fragment(fragment) + "\n",
        1,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wrap a minutes HTML fragment in the meeting minutes template."
    )
    parser.add_argument("fragment", type=Path, help="HTML fragment produced by minutes_to_html.py")
    parser.add_argument(
        "--meeting-date",
        type=date.fromisoformat,
        help="Meeting date (YYYY-MM-DD); inferred from the fragment filename when it contains one",
    )
    parser.add_argument("--chair", default="Chair", help="Name of the meeting chair")
    parser.add_argument(
        "--attendees",
        help="Comma-separated attendee list; defaults to the speakers found in the fragment",
    )
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="Template file")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write minutes_MMMdd_YYYY.html into",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Full path of the file to write; overrides --output-dir and the generated filename",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    meeting_date = args.meeting_date or date_from_filename(args.fragment)
    if meeting_date is None:
        raise SystemExit("A meeting date is required: pass --meeting-date YYYY-MM-DD.")

    attendees = (
        [name.strip() for name in args.attendees.split(",") if name.strip()]
        if args.attendees
        else None
    )
    document = build_minutes(
        fragment=args.fragment.read_text(encoding="utf-8"),
        template=args.template.read_text(encoding="utf-8"),
        meeting_date=meeting_date,
        chair=args.chair,
        attendees=attendees,
    )

    output_path = args.output or (args.output_dir / output_filename(meeting_date))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
