# tksearchengine

[![PyPI version](https://img.shields.io/pypi/v/tksearchengine.svg)](https://pypi.org/project/tksearchengine/)
[![Python versions](https://img.shields.io/pypi/pyversions/tksearchengine.svg)](https://pypi.org/project/tksearchengine/)
[![License](https://img.shields.io/pypi/l/tksearchengine.svg)](https://pypi.org/project/tksearchengine/)
[![Tests](https://github.com/WhatIsMyRealName/tksearchengine/actions/workflows/tests.yml/badge.svg)](https://github.com/WhatIsMyRealName/tksearchengine/actions/workflows/tests.yml)

`tksearchengine` provides a reusable Tkinter search field with fuzzy,
multi-word suggestions. It combines an entry, a search button, and a listbox
in a single configurable widget.

## Features

- Placeholder text while the empty entry is not focused.
- Live suggestions while the entry is focused.
- Mouse selection and keyboard navigation with Up and Down.
- Tab accepts the highlighted suggestion, or the first suggestion by default.
- Return and the search button invoke the same callback.
- Case-insensitive, accent-insensitive, multi-word fuzzy matching.
- `-` and `'` are treated as word separators.
- Missing spaces and spaces accidentally replaced by `n` or `b` are handled.
- Exact words, exact prefixes, approximate prefixes, and approximate complete
  words are ranked in that order.
- No third-party runtime dependencies.

## Requirements

- Python 3.10 or newer.
- Tkinter, which is included with many Python installations but may require a
  separate operating-system package on Linux. For example, Debian and Ubuntu provide it in the `python3-tk` package.

## Installation

From PyPI:

```console
python -m pip install tksearchengine
```

From the project directory:

```console
python -m pip install .
```

For editable development:

```console
python -m pip install -e .
```

## Basic usage

```python
import tkinter as tk

from tksearchengine import SearchEngine


def run_search(text: str, selected_item: str | None) -> None:
    print("Search text:", text)
    print("Selected suggestion:", selected_item)


root = tk.Tk()

search = SearchEngine(
    root,
    items=["Paris", "Marseille", "Lyon", "Orléans"],
    command=run_search,
    placeholder="Search for a city",
    max_visible_results=6,
)
search.pack(fill="x", padx=20, pady=20)

root.mainloop()
```

## Configuration

The constructor accepts:

- `items`: searchable strings.
- `command`: callback receiving the current text and the selected suggestion. The second argument is `None` when the user submits free text without accepting a suggestion.
- `placeholder`: text displayed when the unfocused entry is empty.
- `button_text`: label or symbol displayed on the search button.
- `search_function`: optional replacement for the complete ranking function.
- `max_distance_function`: optional function returning the accepted edit
  distance for a given reference-word length.
- `max_visible_results`: maximum visible listbox rows.
- `placeholder_color` and `text_color`: entry text colors.
- `entry_options`, `button_options`, and `listbox_options`: mappings forwarded
  to the corresponding Tkinter widgets.
- Any remaining keyword arguments are forwarded to the containing `tk.Frame`.

Here is the `__init__` shape:
```python
    def __init__(
        self,
        master: tk.Misc | None = None,
        *,
        items: Sequence[str] = (),
        command: SearchCallback | None = None,
        placeholder: str = "Search…",
        button_text: str = "🔍",
        search_function: SearchFunction | None = None,
        max_distance_function: MaxDistanceFunction = _default_max_distance,
        max_visible_results: int = 8,
        placeholder_color: str = "grey",
        text_color: str = "black",
        entry_options: Mapping[str, Any] | None = None,
        button_options: Mapping[str, Any] | None = None,
        listbox_options: Mapping[str, Any] | None = None,
        **frame_options: Any,
    ) -> None:
```

Example with widget customization:

```python
search = SearchEngine(
    root,
    items=["Paris", "Marseille", "Lyon", "Orléans"],
    entry_options={
        "width": 32,
        "font": ("Segoe UI", 11),
        "relief": "solid",
    },
    button_options={
        "text": "Search",
        "font": ("Segoe UI", 10, "bold"),
        "padx": 12,
    },
    listbox_options={
        "font": ("Segoe UI", 10),
        "height": 6,
        "activestyle": "dotbox",
    },
)
```

These mappings are passed directly to `tk.Entry`, `tk.Button`, and `tk.Listbox`.
`SearchEngine` still owns the entry text variable, the button command, the
listbox selection behavior, and the visible result count.

A custom search function has this shape:

```python
from collections.abc import Sequence


def custom_search(items: Sequence[str], query: str) -> Sequence[str]:
    normalized_query = query.lower()
    return [item for item in items if normalized_query in item.lower()]
```

Pass it with `search_function=custom_search`. When a custom search function is
provided, it is responsible for filtering and ordering all results.

## Public methods

- `get()` returns the current search text without the placeholder.
- `set(text)` replaces the current search text.
- `set_items(items)` replaces the searchable collection.
- `invoke()` runs the configured callback.
- `selected_item` returns the highlighted or accepted suggestion, if any.

## Matching behavior

The default matcher normalizes text to lowercase, replaces common accented
letters with their unaccented forms, and treats `-` and `'` as spaces. Results are
ranked by:

1. number of unmatched query words;
2. match type, from exact word to approximate complete word;
3. normalized Levenshtein distance;
4. query-word order;
5. original item order.

The default maximum edit distance is `(word_length + 2) // 5`. Override
`max_distance_function(word_length)` when an application needs stricter or more permissive
matching.

## Running the example

The example contains 1,000 French commune names:

```console
python examples/communes.py
```
Filtering the 1,000 sample names should feel immediate on a typical desktop Python installation.

## Running the tests

After an editable installation:

```console
python -m unittest discover -s tests -v
```
