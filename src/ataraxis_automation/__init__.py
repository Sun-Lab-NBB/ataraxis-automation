"""Supports tox-based development automation pipelines and provides agentic skills for Claude Code used by other
Sun (NeuroAI) lab projects.

See the `documentation <https://ataraxis-automation-api-docs.netlify.app/>`_ for the description of available
assets. See the `source code repository <https://github.com/Sun-Lab-NBB/ataraxis-automation>`_ for more details.

Authors: Ivan Kondratyev (Inkaros)
"""

from .automation import (
    ProjectEnvironment,
    move_stubs,
    delete_stubs,
    verify_pypirc,
    format_message,
    colorize_message,
    resolve_library_root,
    generate_typed_marker,
    resolve_project_directory,
)

__all__ = [
    "ProjectEnvironment",
    "colorize_message",
    "delete_stubs",
    "format_message",
    "generate_typed_marker",
    "move_stubs",
    "resolve_library_root",
    "resolve_project_directory",
    "verify_pypirc",
]
