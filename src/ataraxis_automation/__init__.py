"""This library exposes functions used by tox tasks to automate project development and provides a cli-interface for
calling these functions.

The library is not designed to be used directly. Instead, it is meant to be used with 'tox' and other helper packages
like 'mypy', 'ruff', 'stubgen'. The functions exposed through this library augment the functionality of these
helpers by either setting-up, tearing-down or otherwise supporting their runtime.

All functions in this library assume the project they work with is formatted according to Sun Lab standards. Therefore,
significant refactoring may be required to use this library for projects that do not follow those standards.
"""
