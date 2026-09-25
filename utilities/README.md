# Meeting Minutes HTML Converter

Three scripts make up the minutes workflow:

1. `minutes_to_html.py` converts Zoom chat exports and closed-caption transcripts into an HTML fragment. When both files are supplied, entries are ordered by timestamp and adjacent messages from the same speaker and source are combined.
2. `html_to_minutes.py` wraps that fragment in `minutes_MonthDay_Year_Template.html` and writes a complete `minutes_MMMdd_YYYY.html` page.
3. `make_minutes.py` runs both steps in one go, prompting for the input files, meeting date, chair, attendees, template, and output location.

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

## Guided run: `make_minutes.py`

```sh
python3 make_minutes.py
```

The script asks for each value in turn and shows a default in square brackets; press Enter to accept it.

1. **Transcript or chat export** — path to the first input file.
2. **Second export** — path to the other input file, or Enter to use only one.
3. **Meeting date** — `YYYY-MM-DD`, pre-filled when an input filename contains a date.
4. **Save the intermediate HTML fragment?** — optionally keep the fragment and choose where to write it.
5. **Template file** — defaults to `minutes_MonthDay_Year_Template.html` in this directory.
6. **Chair** — name placed in the `Chair` field.
7. **Attendees** — the detected speakers are listed; accept them or type a comma-separated replacement.
8. **Output directory** and **output filename** — default to the repository `minutes/` directory and `minutes_MMMdd_YYYY.html`. An existing file is only replaced after confirmation.

Relative paths are resolved against the current directory, or against `input_dir` when it is configured. Absolute paths and `~` are also accepted.

### Defaults for another project

Create `minutes_config.json` beside the scripts, or pass `--config path/to/file.json`, to change the suggested defaults:

```json
{
  "input_dir": "~/meetings/exports",
  "fragment_dir": "~/meetings/fragments",
  "template": "~/meetings/templates/minutes-template.html",
  "output_dir": "~/site/minutes",
  "chair": "Chair Name"
}
```

Every key is optional, and each one only changes a prompt default, so any value can still be overridden during the run.

## Commands: `minutes_to_html.py`

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

### Fragment output

The output is an HTML fragment, with one paragraph per merged message:

```html
<p class="message"><cite class="speaker">Speaker: </cite><span class="text">Transcript text</span></p>
<p class="chat"><cite class="speaker">Speaker: </cite><span class="text">Chat text</span></p>
```

Before rendering, standalone `um` and `uh` filler words, three-dot ellipses (`...`), and Unicode ellipses are removed. Surrounding whitespace and punctuation are normalized after cleanup. Other filler words are not removed, so a manual check is still required. 

Use the `message` and `chat` CSS classes to style transcript and chat messages differently when embedding the fragment in a larger minutes page.

## Commands: `html_to_minutes.py`

### Build a minutes page

```sh
python3 html_to_minutes.py OUTPUT --meeting-date 2026-09-25 --chair "{Chair Name}"
```

This reads the fragment, fills in the template, and writes `../minutes/minutes_Sep25_2026.html`. The path of the file written is printed on completion.

When the fragment filename contains a `YYYY-MM-DD` date, `--meeting-date` can be omitted:

```sh
python3 html_to_minutes.py minutes-2026-09-25.html --chair "{Chair Name}"
```

### Options

- `--meeting-date` — meeting date in `YYYY-MM-DD` form. Required unless the fragment filename contains a date.
- `--chair` — name placed in the `Chair` field. Defaults to `Chair`.
- `--attendees` — comma-separated attendee list that replaces the speakers detected in the fragment.
- `--template` — template file to use. Defaults to `minutes_MonthDay_Year_Template.html` in this directory.
- `-o`, `--output-dir` — directory to write into. Defaults to the `minutes/` directory of the repository, and is created if it does not exist.
- `--output` — full path of the file to write. Overrides `--output-dir` and the generated filename.

### What gets filled in

- `{DATE}` in the page title and heading becomes the long form date, for example `25 September 2026`.
- `{Names}` becomes the distinct speakers found in the fragment, in the order they first speak. Trailing pronouns such as `(she/her)` are removed, and the chair is excluded. If no other speakers are found, `None recorded` is used.
- `{Chair}` becomes the `--chair` value.
- The fragment is inserted into `<section id="minutes">` after the `Meeting Minutes` heading.

Speaker names come from transcript labels, so the attendee list should still be reviewed. Use `--attendees` to correct it.

### Output filename

The filename is derived from the meeting date as `minutes_MMMdd_YYYY.html`, for example `minutes_Sep25_2026.html`. An existing file with the same name is overwritten. Use `--output` to write to a specific path instead.

## Errors

- Only one chat export and one closed-caption transcript can be processed per command.
- A transcript supplied without chat data needs `--meeting-date` or a `YYYY-MM-DD` date in its filename.
- An input whose format cannot be identified must have a filename containing `chat`, `caption`, or `transcript`.
- `html_to_minutes.py` needs `--meeting-date` or a `YYYY-MM-DD` date in the fragment filename.
- `make_minutes.py` re-asks for any file path that does not exist, any date that is not `YYYY-MM-DD`, and any pair of inputs that turn out to be the same type.
