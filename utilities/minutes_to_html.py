#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Iterable


CHAT_LINE_RE = re.compile(r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) From (?P<speaker>.+?) to Everyone:$")
CC_LINE_RE = re.compile(r"^\[(?P<speaker>.+?)\] (?P<timestamp>\d{2}:\d{2}:\d{2})$")
DATE_IN_FILENAME_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
FILLER_RE = re.compile(r"(?:\b(?:um|uh)\b(?!-)(?:[,.]+)?|\.\.\.|\u2026)", re.IGNORECASE)


@dataclass(frozen=True)
class Message:
    timestamp: datetime
    speaker: str
    text: str
    sort_key: tuple[datetime, int]
    source_order: int
    source: str = "transcript"  # "chat" or "transcript"


@dataclass
class PendingMessage:
    timestamp: datetime
    speaker: str
    lines: list[str]
    source_order: int


def normalize_speaker(name: str) -> str:
    name = re.sub(r'^Replying to\s+".*":\s*$', "", name).strip()
    name = re.sub(r"\s+", " ", name)
    return name.casefold()


def parse_chat_file(path: Path) -> list[Message]:
    lines = path.read_text(encoding="utf-8").splitlines()
    messages: list[Message] = []
    current: PendingMessage | None = None
    source_order = 0

    for line in lines:
        match = CHAT_LINE_RE.match(line)
        if match:
            if current is not None:
                messages.append(
                    Message(
                        timestamp=current.timestamp,
                        speaker=current.speaker,
                        text="\n".join(current.lines).strip(),
                        sort_key=(current.timestamp, current.source_order),
                        source_order=current.source_order,
                        source="chat",
                    )
                )
            timestamp = datetime.strptime(match.group("timestamp"), "%Y-%m-%d %H:%M:%S")
            current = PendingMessage(
                timestamp=timestamp,
                speaker=match.group("speaker").strip(),
                lines=[],
                source_order=source_order,
            )
            source_order += 1
            continue

        if current is None:
            continue

        stripped = line.strip()
        if not stripped:
            if current.lines and current.lines[-1] != "":
                current.lines.append("")
            continue

        current.lines.append(stripped)

    if current is not None:
        messages.append(
            Message(
                timestamp=current.timestamp,
                speaker=current.speaker,
                text="\n".join(current.lines).strip(),
                sort_key=(current.timestamp, current.source_order),
                source_order=current.source_order,
                source="chat",
            )
        )

    return messages


def parse_closed_caption_file(path: Path, meeting_date: date) -> list[Message]:
    lines = path.read_text(encoding="utf-8").splitlines()
    messages: list[Message] = []
    current_speaker: str | None = None
    current_timestamp: datetime | None = None
    current_lines: list[str] = []
    source_order = 0

    def flush() -> None:
        nonlocal current_speaker, current_timestamp, current_lines, source_order
        if current_speaker is None or current_timestamp is None or not current_lines:
            return
        messages.append(
            Message(
                timestamp=current_timestamp,
                speaker=current_speaker,
                text=" ".join(line.strip() for line in current_lines if line.strip()).strip(),
                sort_key=(current_timestamp, source_order),
                source_order=source_order,
            )
        )
        source_order += 1
        current_speaker = None
        current_timestamp = None
        current_lines = []

    for line in lines:
        if not line.strip():
            flush()
            continue

        match = CC_LINE_RE.match(line)
        if match:
            flush()
            current_speaker = match.group("speaker").strip()
            time_only = datetime.strptime(match.group("timestamp"), "%H:%M:%S").time()
            current_timestamp = datetime.combine(meeting_date, time_only)
            continue

        if current_speaker is not None:
            current_lines.append(line.strip())

    flush()
    return messages


def identify_source(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if CHAT_LINE_RE.match(line):
            return "chat"
        if CC_LINE_RE.match(line):
            return "transcript"
        break
    filename = path.name.casefold()
    if "chat" in filename:
        return "chat"
    if "caption" in filename or "transcript" in filename:
        return "transcript"
    raise ValueError(f"Could not identify {path} as a chat or closed caption export.")


def date_from_filename(path: Path) -> date | None:
    match = DATE_IN_FILENAME_RE.search(path.name)
    return date.fromisoformat(match.group()) if match else None


def merge_messages(messages: Iterable[Message]) -> list[Message]:
    ordered = sorted(messages, key=lambda message: message.sort_key)
    merged: list[Message] = []

    for message in ordered:
        if merged and normalize_speaker(merged[-1].speaker) == normalize_speaker(message.speaker) and merged[-1].source == message.source:
            previous = merged[-1]
            combined_text = previous.text + ("\n" if previous.text and message.text else "") + message.text
            merged[-1] = Message(
                timestamp=previous.timestamp,
                speaker=previous.speaker,
                text=combined_text,
                sort_key=previous.sort_key,
                source_order=previous.source_order,
                source=previous.source,
            )
            continue

        merged.append(message)

    return merged


def clean_text(text: str) -> str:
    cleaned = FILLER_RE.sub("", text)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    return cleaned.strip()


def render_html(messages: Iterable[Message]) -> str:
    blocks = []
    for message in messages:
        speaker = html.escape(message.speaker)
        text = html.escape(clean_text(message.text)).replace("\n", "<br>")
        css_class = "chat" if message.source == "chat" else "message"
        blocks.append(
            f'<p class="{css_class}"><cite class="speaker">{speaker}: </cite>'
            f'<span class="text">{text}</span></p>'
        )
    return "\n".join(blocks)


def build_html_fragment(input_paths: Iterable[Path], meeting_date: date | None = None) -> str:
    chat_path: Path | None = None
    transcript_path: Path | None = None
    for path in input_paths:
        source = identify_source(path)
        if source == "chat":
            if chat_path is not None:
                raise ValueError("Only one chat export can be processed at a time.")
            chat_path = path
        else:
            if transcript_path is not None:
                raise ValueError("Only one closed caption export can be processed at a time.")
            transcript_path = path

    chat_messages = parse_chat_file(chat_path) if chat_path else []
    meeting_date = meeting_date or (
        chat_messages[0].timestamp.date()
        if chat_messages
        else date_from_filename(transcript_path) if transcript_path else None
    )
    if transcript_path and meeting_date is None:
        raise ValueError("A transcript without chat data needs --meeting-date or a YYYY-MM-DD date in its filename.")

    transcript_messages = (
        parse_closed_caption_file(transcript_path, meeting_date)
        if transcript_path and meeting_date is not None
        else []
    )
    merged = merge_messages(chat_messages + transcript_messages)
    return render_html(merged)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge a transcript and chat export into HTML.")
    parser.add_argument(
        "input_files",
        type=Path,
        nargs="+",
        help="One chat export, one closed caption export, or both in either order",
    )
    parser.add_argument(
        "--meeting-date",
        type=date.fromisoformat,
        help="Meeting date (YYYY-MM-DD), required for transcript-only files without a date in the filename",
    )
    parser.add_argument("-o", "--output", type=Path, required=True, help="Path to write the HTML fragment")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    html_fragment = build_html_fragment(args.input_files, args.meeting_date)
    args.output.write_text(html_fragment + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()