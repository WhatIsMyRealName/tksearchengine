"""Reusable Tkinter search widget with autocomplete suggestions."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Mapping, Sequence
from fractions import Fraction
from functools import lru_cache
from typing import Any, TypeAlias

SearchCallback: TypeAlias = Callable[[str, str | None], None]
SearchFunction: TypeAlias = Callable[[Sequence[str], str], Sequence[str]]
MaxDistanceFunction: TypeAlias = Callable[[int], int]

__version__ = "1.0.0"
__author__ = "WhatIsMyRealName"
__created_with__ = "Codex"
__created_on__ = "2026-07-17"

__all__ = ["SearchEngine"]

_NORMALIZATION_TABLE = str.maketrans(
    {
        "à": "a",
        "á": "a",
        "â": "a",
        "ä": "a",
        "ã": "a",
        "å": "a",
        "æ": "ae",
        "ç": "c",
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "ì": "i",
        "í": "i",
        "î": "i",
        "ï": "i",
        "ñ": "n",
        "ò": "o",
        "ó": "o",
        "ô": "o",
        "ö": "o",
        "õ": "o",
        "œ": "oe",
        "ù": "u",
        "ú": "u",
        "û": "u",
        "ü": "u",
        "ý": "y",
        "ÿ": "y",
        "-": " ",
        "'": " ",
    }
)


@lru_cache(maxsize=8192)
def _normalize(text: str) -> str:
    return text.lower().translate(_NORMALIZATION_TABLE) # ajouter la suppression de plusieurs espaces consécutifs, en début et fin de chaîne comme au début ? *(  )+* => * *


def _default_max_distance(length: int) -> int:
    return (length + 2) // 5


@lru_cache(maxsize=8192)
def _levenshtein_distance(first: str, second: str) -> int:
    """Return the Levenshtein edit distance between two strings.

    The distance is the minimum number of insertions, deletions and
    substitutions required to transform one string into the other.
    """
    if len(first) < len(second):
        first, second = second, first

    previous_row = list(range(len(second) + 1))
    for first_index, first_character in enumerate(first, start=1):
        current_row = [first_index]
        for second_index, second_character in enumerate(second, start=1):
            insertion = current_row[second_index - 1] + 1
            deletion = previous_row[second_index] + 1
            substitution = previous_row[second_index - 1] + (
                first_character != second_character
            )
            current_row.append(min(insertion, deletion, substitution))
        previous_row = current_row

    return previous_row[-1]


def _candidate_variants(words: Sequence[str]) -> list[list[str]]:
    variants = [list(words)]
    for boundary in range(len(words) - 1):
        before = list(words[:boundary])
        after = list(words[boundary + 2 :])
        for replacement in ("", "n", "b"):
            merged = words[boundary] + replacement + words[boundary + 1]
            variants.append([*before, merged, *after])
    return variants


def _word_match_score(
    query_word: str,
    candidate_word: str,
    max_distance_function: MaxDistanceFunction,
) -> tuple[int, Fraction] | None:
    if query_word == candidate_word:
        return 0, Fraction(0)

    if len(query_word) < len(candidate_word):
        candidate_prefix = candidate_word[: len(query_word)]
        prefix_distance = _levenshtein_distance(query_word, candidate_prefix)
        if prefix_distance == 0:
            return 1, Fraction(0)
        if prefix_distance <= max_distance_function(len(query_word)):
            return 2, Fraction(prefix_distance, len(query_word) or 1)

    reference_length = len(candidate_word)
    maximum_distance = max_distance_function(reference_length)
    if abs(len(query_word) - reference_length) > maximum_distance:
        return None

    distance = _levenshtein_distance(query_word, candidate_word)
    if distance > maximum_distance:
        return None

    normalization_length = max(len(query_word), reference_length)
    return 3, Fraction(distance, normalization_length or 1)


def _score_variant(
    query_words: Sequence[str],
    candidate_words: Sequence[str],
    max_distance_function: MaxDistanceFunction,
) -> tuple[int, int, Fraction, int]:
    match_scores: list[list[tuple[int, Fraction] | None]] = []
    for query_word in query_words:
        row: list[tuple[int, Fraction] | None] = []
        for candidate_word in candidate_words:
            row.append(
                _word_match_score(
                    query_word, candidate_word, max_distance_function
                )
            )
        match_scores.append(row)

    @lru_cache(maxsize=None)
    def find_best(
        query_index: int, used_candidates: int
    ) -> tuple[int, int, Fraction, int]:
        if query_index == len(query_words):
            return 0, 0, Fraction(0), 0

        unmatched, match_priority, distance_sum, inversions = find_best(
            query_index + 1, used_candidates
        )
        best = unmatched + 1, match_priority, distance_sum, inversions

        for candidate_index, match_score in enumerate(match_scores[query_index]):
            candidate_bit = 1 << candidate_index
            if match_score is None or used_candidates & candidate_bit:
                continue
            priority, normalized_distance = match_score
            child = find_best(query_index + 1, used_candidates | candidate_bit)
            preceding_inversions = sum(
                1
                for previous_index in range(candidate_index + 1, len(candidate_words))
                if used_candidates & (1 << previous_index)
            )
            score = (
                child[0],
                child[1] + priority,
                child[2] + normalized_distance,
                child[3] + preceding_inversions,
            )
            if score < best:
                best = score

        return best

    return find_best(0, 0)


def _fuzzy_search(
    items: Sequence[str],
    query: str,
    max_distance_function: MaxDistanceFunction,
) -> list[str]:
    query_words = _normalize(query).split()
    if not query_words:
        return list(items)

    ranked_items: list[tuple[tuple[int, int, Fraction, int, int], str]] = []
    for original_index, item in enumerate(items):
        candidate_words = _normalize(item).split()
        if not candidate_words:
            continue
        best_score = min(
            _score_variant(query_words, variant, max_distance_function)
            for variant in _candidate_variants(candidate_words)
        )
        unmatched_words, match_priority, distance_sum, inversions = best_score
        if unmatched_words == len(query_words):
            continue
        ranked_items.append(
            (
                (
                    unmatched_words,
                    match_priority,
                    distance_sum,
                    inversions,
                    original_index,
                ),
                item,
            )
        )

    ranked_items.sort(key=lambda ranked_item: ranked_item[0])
    return [item for _score, item in ranked_items]


class SearchEngine(tk.Frame):
    """A search field with a button and a filtered suggestion list.

    ``command`` is called with the current text and the selected suggestion
    (or ``None``). It is invoked both by Return and by the search button.

    Widget-specific Tk options can be passed through ``entry_options``,
    ``button_options`` and ``listbox_options``. Remaining keyword arguments
    are applied to the containing :class:`tk.Frame`.
    """

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
        super().__init__(master, **frame_options)

        if max_visible_results < 1:
            raise ValueError("max_visible_results must be greater than or equal to 1")
        if search_function is not None and not callable(search_function):
            raise TypeError("search_function must be callable or None")
        if not callable(max_distance_function):
            raise TypeError("max_distance_function must be callable")
        if command is not None and not callable(command):
            raise TypeError("command must be callable or None")

        self._items = list(items)
        self._command = command
        self._placeholder = placeholder
        self._search_function = search_function
        self._max_distance_function = max_distance_function
        self._max_visible_results = max_visible_results
        self._placeholder_color = placeholder_color
        self._text_color = text_color
        self._showing_placeholder = False
        self._filtered_items: list[str] = []
        self._accepted_item: str | None = None

        self.variable = tk.StringVar(self)

        entry_config = dict(entry_options or {})
        entry_config["textvariable"] = self.variable
        self.entry = tk.Entry(self, **entry_config)

        button_config = dict(button_options or {})
        button_config.setdefault("text", button_text)
        button_config["command"] = self.invoke
        self.button = tk.Button(self, **button_config)

        listbox_config = dict(listbox_options or {})
        listbox_config.setdefault("exportselection", False)
        listbox_config.setdefault("height", 1)
        self.listbox = tk.Listbox(self, **listbox_config)

        self.entry.grid(row=0, column=0, sticky="ew")
        self.button.grid(row=0, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)

        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<Return>", self._on_submit)
        self.entry.bind("<KP_Enter>", self._on_submit)
        self.entry.bind("<Tab>", self._on_tab)
        self.entry.bind("<Down>", self._on_down)
        self.entry.bind("<Up>", self._on_up)
        self.listbox.bind("<ButtonRelease-1>", self._on_listbox_click)
        self.listbox.bind("<Return>", self._on_listbox_accept)

        self._display_placeholder()

    def get(self) -> str:
        """Return the search text, excluding the visual placeholder."""
        return "" if self._showing_placeholder else self.variable.get()

    def set(self, text: str) -> None:
        """Replace the search text and refresh suggestions when focused."""
        self._accepted_item = None
        self._showing_placeholder = False
        self.entry.configure(fg=self._text_color)
        self.variable.set(text)
        if self.entry.focus_get() == self.entry:
            self._refresh_results()
        elif not text:
            self._display_placeholder()

    def set_items(self, items: Sequence[str]) -> None:
        """Replace the searchable values."""
        self._items = list(items)
        if self.entry.focus_get() == self.entry:
            self._refresh_results()

    def invoke(self) -> None:
        """Run the configured search callback."""
        if self._command is not None:
            self._command(self.get(), self.selected_item)

    @property
    def selected_item(self) -> str | None:
        """Return the highlighted suggestion, if any."""
        selection = self.listbox.curselection()
        if not selection:
            return self._accepted_item
        index = selection[0]
        if index >= len(self._filtered_items):
            return None
        return self._filtered_items[index]

    def _display_placeholder(self) -> None:
        if self.variable.get() or self.entry.focus_get() == self.entry:
            return
        self._showing_placeholder = True
        self.entry.configure(fg=self._placeholder_color)
        self.variable.set(self._placeholder)

    def _hide_results(self) -> None:
        self.listbox.grid_remove()

    def _refresh_results(self) -> None:
        query = self.get()
        if self._search_function is None:
            results = _fuzzy_search(
                self._items, query, self._max_distance_function
            )
        else:
            results = self._search_function(self._items, query)
        self._filtered_items = list(results)

        self.listbox.delete(0, tk.END)
        for item in self._filtered_items:
            self.listbox.insert(tk.END, item)

        if not self._filtered_items:
            self._hide_results()
            return

        self.listbox.configure(
            height=min(len(self._filtered_items), self._max_visible_results)
        )
        self.listbox.grid(row=1, column=0, columnspan=2, sticky="ew")

    def _on_focus_in(self, _event: tk.Event[tk.Misc]) -> None:
        if self._showing_placeholder:
            self.variable.set("")
            self._showing_placeholder = False
            self.entry.configure(fg=self._text_color)
        self._refresh_results()

    def _on_focus_out(self, _event: tk.Event[tk.Misc]) -> None:
        self.after_idle(self._finish_focus_out)

    def _finish_focus_out(self) -> None:
        focused = self.focus_get()
        if focused == self.listbox:
            return
        self._hide_results()
        self._display_placeholder()

    def _on_key_release(self, event: tk.Event[tk.Misc]) -> None:
        if event.keysym not in {"Up", "Down", "Tab", "Return", "KP_Enter"}:
            self._accepted_item = None
            self._refresh_results()

    def _on_submit(self, _event: tk.Event[tk.Misc]) -> str:
        self.invoke()
        return "break"

    def _on_tab(self, _event: tk.Event[tk.Misc]) -> str | None:
        if not self._filtered_items:
            return None
        selection = self.listbox.curselection()
        self._accept_index(selection[0] if selection else 0)
        return "break"

    def _move_selection(self, step: int) -> str:
        if not self._filtered_items:
            return "break"
        selection = self.listbox.curselection()
        current = selection[0] if selection else (-1 if step > 0 else 0)
        target = (current + step) % len(self._filtered_items)
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(target)
        self.listbox.activate(target)
        self.listbox.see(target)
        return "break"

    def _on_down(self, _event: tk.Event[tk.Misc]) -> str:
        return self._move_selection(1)

    def _on_up(self, _event: tk.Event[tk.Misc]) -> str:
        return self._move_selection(-1)

    def _accept_index(self, index: int) -> None:
        accepted_item = self._filtered_items[index]
        self.set(accepted_item)
        self._accepted_item = accepted_item
        self.entry.icursor(tk.END)
        self.entry.focus_set()
        self._hide_results()

    def _on_listbox_click(self, _event: tk.Event[tk.Misc]) -> None:
        selection = self.listbox.curselection()
        if selection:
            self._accept_index(selection[0])

    def _on_listbox_accept(self, _event: tk.Event[tk.Misc]) -> str:
        selection = self.listbox.curselection()
        if selection:
            self._accept_index(selection[0])
        return "break"
