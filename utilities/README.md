# Meeting Minutes HTML Converter

`minutes_to_html.py` converts Zoom chat exports and closed-caption transcripts into an HTML fragment. When both files are supplied, entries are ordered by timestamp and adjacent messages from the same speaker and source are combined.

## Requirements

- Python 3.10 or later
- No third-party packages

Run all commands from this directory:

```sh
cd "utilities/"
```

## Input files

The command accepts one or two input files in either order:

- A Zoom chat export: records begin with a date and time followed by `From ... to Everyone:`.
- A closed-caption transcript: speaker records begin with `[Speaker name] HH:MM:SS`.

The script detects the input type from its contents. For an empty input, it falls back to the filename: names containing `chat` are treated as chat exports; names containing `caption` or `transcript` are treated as closed-caption exports.

## Commands

### Merge chat and transcript

```sh
python3 minutes_to_html.py -o OUTPUT 
  input/meeting_saved_new_chat_sept11.txt 
  input/ATAGCGtranscript_2026-09-11_09.59.10.txt
```

The input order does not matter:

```sh
python3 minutes_to_html.py -o OUTPUT \
  input/ATAGCGtranscript_2026-09-11_09.59.10.txt \
  input/meeting_saved_new_chat_sept11.txt
```

### Convert a chat export only

```sh
python3 minutes_to_html.py -o chat.html input/meeting_saved_new_chat_sept11.txt
```

### Convert a dated transcript only

When the filename contains a date in `YYYY-MM-DD` form, the script uses that date automatically:

```sh
python3 minutes_to_html.py -o transcript.html 
  input/ATAGCGtranscript_2026-09-11_09.59.10.txt
```

### Convert an undated transcript only

Closed-caption records contain only times, so provide the meeting date when the filename has no `YYYY-MM-DD` date:

```sh
python3 minutes_to_html.py --meeting-date 2026-06-01 -o transcript.html 
  input/meeting_saved_closed_caption_jun.txt
```

## Output

The output is an HTML fragment, with one paragraph per merged message:

```html
<p class="message"><cite class="speaker">Speaker: </cite><span class="text">Transcript text</span></p>
<p class="chat"><cite class="speaker">Speaker: </cite><span class="text">Chat text</span></p>
```

Before rendering, standalone `um` and `uh` filler words, three-dot ellipses (`...`), and Unicode ellipses are removed. Surrounding whitespace and punctuation are normalized after cleanup. Other filler words are not removed, so a manual check is still required. 

Use the `message` and `chat` CSS classes to style transcript and chat messages differently when embedding the fragment in a larger minutes page.

## Errors

- Only one chat export and one closed-caption transcript can be processed per command.
- A transcript supplied without chat data needs `--meeting-date` or a `YYYY-MM-DD` date in its filename.
- An input whose format cannot be identified must have a filename containing `chat`, `caption`, or `transcript`.
