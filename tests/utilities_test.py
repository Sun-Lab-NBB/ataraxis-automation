"""Tests service functions available through the utilities module."""

from ataraxis_automation.utilities import format_message


def test_format_message():
    """Verifies correct functioning of the format-message function"""

    # Verifies that a long message is formatted appropriately.
    long_message = (
        "This is a very long message that needs to be formatted properly. It should be wrapped at 120 characters "
        "without breaking long words or splitting on hyphens. The formatting should be applied correctly to ensure "
        "readability and consistency across the library."
    )
    # DO NOT REFORMAT. This will break the test.
    # noinspection LongLine
    expected_long_message = (
        "This is a very long message that needs to be formatted properly. It should be wrapped at 120 characters without breaking\n"
        "long words or splitting on hyphens. The formatting should be applied correctly to ensure readability and consistency\n"
        "across the library."
    )
    assert format_message(long_message) == expected_long_message

    # Verifies that a short message remains unaffected.
    short_message = "This is a short message."
    assert format_message(short_message) == short_message
