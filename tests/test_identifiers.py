"""Tests for the WaxPrep identifier scheme."""

from __future__ import annotations

import unittest
from unittest.mock import patch
from uuid import RFC_4122, UUID

from waxprep.identifiers import (
    InvalidWaxId,
    ParsedWaxId,
    WaxIdKind,
    generate_wax_id,
    is_valid_wax_id,
    parse_wax_id,
)


class WaxIdGenerationTests(unittest.TestCase):
    def test_generates_unique_ids_for_many_objects(self) -> None:
        identifiers = {generate_wax_id(WaxIdKind.EVENT) for _ in range(2_000)}

        self.assertEqual(len(identifiers), 2_000)

    def test_id_has_human_readable_wax_kind_prefix(self) -> None:
        identifier = generate_wax_id(WaxIdKind.SESSION)

        self.assertTrue(identifier.startswith("wax_session_"))

    def test_generated_id_parses_as_uuidv7(self) -> None:
        identifier = generate_wax_id(WaxIdKind.ACTION)

        parsed = parse_wax_id(identifier)

        self.assertIsInstance(parsed, ParsedWaxId)
        self.assertEqual(parsed.kind, WaxIdKind.ACTION)
        self.assertEqual(parsed.uuid.version, 7)
        self.assertEqual(parsed.uuid.variant, RFC_4122)

    def test_all_supported_kinds_can_be_generated_and_parsed(self) -> None:
        for kind in WaxIdKind:
            with self.subTest(kind=kind):
                identifier = generate_wax_id(kind)
                parsed = parse_wax_id(identifier)
                self.assertEqual(parsed.kind, kind)


class WaxIdOrderingTests(unittest.TestCase):
    def test_ids_sort_by_timestamp_when_created_in_different_milliseconds(
        self,
    ) -> None:
        timestamps = iter([1_800_000_000_000, 1_800_000_000_001])

        with patch(
            "waxprep.identifiers._timestamp_milliseconds",
            side_effect=timestamps,
        ):
            first = generate_wax_id(WaxIdKind.EVENT)
            second = generate_wax_id(WaxIdKind.EVENT)

        self.assertLess(first, second)

    def test_timestamp_is_stored_in_the_uuid_prefix(self) -> None:
        timestamp_ms = 1_800_000_000_123

        with patch(
            "waxprep.identifiers._timestamp_milliseconds",
            return_value=timestamp_ms,
        ):
            identifier = generate_wax_id(WaxIdKind.EVENT)

        uuid_value = parse_wax_id(identifier).uuid.int
        stored_timestamp = uuid_value >> 80

        self.assertEqual(stored_timestamp, timestamp_ms)


class WaxIdValidationTests(unittest.TestCase):
    def test_valid_id_returns_true(self) -> None:
        identifier = generate_wax_id(WaxIdKind.TURN)

        self.assertTrue(is_valid_wax_id(identifier))

    def test_malformed_id_is_rejected(self) -> None:
        self.assertFalse(is_valid_wax_id("wax_event_not-an-id"))

        with self.assertRaises(InvalidWaxId):
            parse_wax_id("wax_event_not-an-id")

    def test_unknown_kind_is_rejected(self) -> None:
        uuid_text = str(UUID("0199d2f4-7a4c-7a31-9f2e-4f7a9b7f5d10"))
        value = f"wax_student_{uuid_text}"

        self.assertFalse(is_valid_wax_id(value))

        with self.assertRaises(InvalidWaxId):
            parse_wax_id(value)

    def test_non_string_is_rejected(self) -> None:
        self.assertFalse(is_valid_wax_id(None))

        with self.assertRaises(InvalidWaxId):
            parse_wax_id(123)  # type: ignore[arg-type]

    def test_uuidv4_is_rejected_even_if_shape_is_correct(self) -> None:
        value = "wax_event_550e8400-e29b-41d4-a716-446655440000"

        self.assertFalse(is_valid_wax_id(value))

        with self.assertRaises(InvalidWaxId):
            parse_wax_id(value)

    def test_kind_input_is_normalized(self) -> None:
        identifier = generate_wax_id(" EVENT ")

        parsed = parse_wax_id(identifier)

        self.assertEqual(parsed.kind, WaxIdKind.EVENT)

    def test_unknown_generation_kind_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            generate_wax_id("student")


if __name__ == "__main__":
    unittest.main()
