from __future__ import annotations

import sys
import types
import unittest
from collections.abc import Sequence

try:
    import tkinter  # noqa: F401
except ModuleNotFoundError:
    tkinter_stub = types.ModuleType("tkinter")
    tkinter_stub.Frame = object
    tkinter_stub.END = "end"
    sys.modules["tkinter"] = tkinter_stub

import tksearchengine
from tksearchengine import SearchEngine, search_engine


class LevenshteinTests(unittest.TestCase):
    def test_common_distances_and_symmetry(self) -> None:
        cases = {
            ("", ""): 0,
            ("", "abc"): 3,
            ("chat", "chat"): 0,
            ("chat", "chats"): 1,
            ("kitten", "sitting"): 3,
        }
        for (first, second), expected in cases.items():
            with self.subTest(first=first, second=second):
                self.assertEqual(
                    search_engine._levenshtein_distance(first, second), expected
                )
                self.assertEqual(
                    search_engine._levenshtein_distance(second, first), expected
                )

    def test_default_threshold_boundaries(self) -> None:
        expected = {2: 0, 3: 1, 7: 1, 8: 2, 10: 2, 12: 2, 13: 3}
        self.assertEqual(
            {length: search_engine._default_max_distance(length) for length in expected},
            expected,
        )


class FuzzySearchTests(unittest.TestCase):
    def search(self, items: list[str], query: str) -> list[str]:
        return search_engine._fuzzy_search(
            items, query, search_engine._default_max_distance
        )

    def test_empty_query_preserves_every_item(self) -> None:
        items = ["Premier", "", "Troisième"]
        self.assertEqual(self.search(items, "   "), items)

    def test_case_and_accents_are_ignored(self) -> None:
        self.assertEqual(self.search(["École élémentaire"], "ecole ELEMENTAIRE"), [
            "École élémentaire"
        ])

    def test_hyphens_are_treated_as_spaces(self) -> None:
        self.assertEqual(
            self.search(["Saint-Étienne"], "saint etienne"),
            ["Saint-Étienne"],
        )

    def test_incomplete_word_matches_an_exact_prefix(self) -> None:
        self.assertEqual(self.search(["Orléans", "Paris"], "orl"), ["Orléans"])

    def test_one_letter_matches_only_exact_prefixes(self) -> None:
        self.assertEqual(
            self.search(["Orléans", "Orange", "Paris"], "o"),
            ["Orléans", "Orange"],
        )

    def test_approximate_prefix_is_supported(self) -> None:
        self.assertEqual(self.search(["Orléans"], "orx"), ["Orléans"])

    def test_exact_word_precedes_exact_prefix(self) -> None:
        self.assertEqual(
            self.search(["Orléans", "Or"], "or"),
            ["Or", "Orléans"],
        )

    def test_more_matched_keywords_have_priority(self) -> None:
        items = ["alpha", "alphi beto"]
        self.assertEqual(self.search(items, "alpha beta"), ["alphi beto", "alpha"])

    def test_distance_then_word_order_then_original_order_break_ties(self) -> None:
        items = ["beta alpha", "alpha beta", "alpha beta"]
        self.assertEqual(
            self.search(items, "alpha beta"),
            ["alpha beta", "alpha beta", "beta alpha"],
        )

    def test_one_candidate_word_cannot_match_two_keywords(self) -> None:
        items = ["chat", "chat shat"]
        self.assertEqual(self.search(items, "chat chat"), ["chat shat", "chat"])

    def test_missing_or_replaced_space_is_recognized(self) -> None:
        items = ["Jean Dupont"]
        for query in ("Jean Dupont", "JeanDupont", "JeannDupont", "JeanbDupont"):
            with self.subTest(query=query):
                self.assertEqual(self.search(items, query), items)

    def test_only_one_boundary_is_repaired(self) -> None:
        self.assertEqual(
            self.search(["un deux trois"], "unbdeuxbtrois"),
            [],
        )

    def test_items_without_a_match_are_excluded(self) -> None:
        self.assertEqual(self.search(["Paris", "Londres"], "zzzz"), [])

    def test_custom_threshold_is_used(self) -> None:
        strict = lambda _length: 0
        self.assertEqual(search_engine._fuzzy_search(["chat"], "chut", strict), [])


class _ListboxStub:
    def delete(self, _first: object, _last: object) -> None:
        pass

    def insert(self, _index: object, _item: str) -> None:
        pass

    def configure(self, **_options: object) -> None:
        pass

    def grid(self, **_options: object) -> None:
        pass

    def grid_remove(self) -> None:
        pass


class WidgetFilteringTests(unittest.TestCase):
    def test_each_search_receives_the_complete_item_list(self) -> None:
        queries = iter(("a", "ab"))
        received_items: list[list[str]] = []

        def search(items: Sequence[str], query: str) -> list[str]:
            received_items.append(list(items))
            return [item for item in items if query in item]

        widget = types.SimpleNamespace(
            get=lambda: next(queries),
            _items=["a", "ab", "b"],
            _search_function=search,
            _max_distance_function=search_engine._default_max_distance,
            _filtered_items=[],
            _max_visible_results=8,
            listbox=_ListboxStub(),
            _hide_results=lambda: None,
        )

        SearchEngine._refresh_results(widget)
        SearchEngine._refresh_results(widget)

        self.assertEqual(received_items, [["a", "ab", "b"], ["a", "ab", "b"]])

    def test_only_search_engine_is_exported(self) -> None:
        self.assertIs(tksearchengine.SearchEngine, SearchEngine)
        self.assertEqual(tksearchengine.__all__, ["SearchEngine"])
        self.assertEqual(search_engine.__all__, ["SearchEngine"])


if __name__ == "__main__":
    unittest.main()
