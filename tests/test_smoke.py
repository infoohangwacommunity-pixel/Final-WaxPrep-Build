"""Smoke tests: package is importable through the normal test runner."""

from __future__ import annotations

import unittest


class PackageSmokeTests(unittest.TestCase):
    def test_waxprep_package_imports(self) -> None:
        import waxprep

        self.assertIsNotNone(waxprep)
        self.assertTrue(hasattr(waxprep, "__name__"))
        self.assertEqual(waxprep.__name__, "waxprep")


if __name__ == "__main__":
    unittest.main()
