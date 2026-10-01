import unittest

from waxprep.config import (
    ConfigurationError,
    Settings,
    load_settings,
)


class LoadSettingsTests(unittest.TestCase):
    def test_missing_environment_fails_clearly(self) -> None:
        with self.assertRaisesRegex(
            ConfigurationError,
            r"Required configuration 'WAXPREP_ENV' is missing\.",
        ):
            load_settings({})

    def test_present_environment_loads(self) -> None:
        settings = load_settings(
            {
                "WAXPREP_ENV": "production",
            }
        )

        self.assertEqual(
            settings,
            Settings(environment="production"),
        )

    def test_environment_is_normalized(self) -> None:
        settings = load_settings(
            {
                "WAXPREP_ENV": " Development ",
            }
        )

        self.assertEqual(
            settings.environment,
            "development",
        )

    def test_malformed_environment_fails_without_echoing_value(
        self,
    ) -> None:
        secret_like_value = (
            "definitely-not-a-valid-environment-secret-123"
        )

        with self.assertRaises(ConfigurationError) as raised:
            load_settings(
                {
                    "WAXPREP_ENV": secret_like_value,
                }
            )

        error_message = str(raised.exception)

        self.assertNotIn(
            secret_like_value,
            error_message,
        )

        self.assertIn(
            "WAXPREP_ENV",
            error_message,
        )

        self.assertIn(
            "development",
            error_message,
        )

        self.assertIn(
            "production",
            error_message,
        )

        self.assertIn(
            "test",
            error_message,
        )


if __name__ == "__main__":
    unittest.main()
