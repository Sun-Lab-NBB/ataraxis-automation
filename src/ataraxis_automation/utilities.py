"""This module contains service utility functions used by most packages and modules offered through this library.

The service functions are used to provide common low-level functionality, such as text message formatting, that should
be unified and widely available to all library components. The functions from this module are not intended to be called
directly by the end-users.
"""

import textwrap


def format_message(message: str) -> str:
    """Formats the input message string according ot the standards used across Ataraxis and related projects.

    Args:
        message: The text string to format according to Ataraxis standards.

    Returns:
        Formatted text message (augmented with newline and other service characters as necessary).
    """
    return textwrap.fill(message, width=120, break_long_words=False, break_on_hyphens=False)
