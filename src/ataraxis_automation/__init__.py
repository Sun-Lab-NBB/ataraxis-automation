"""Supports tox-based development automation pipelines used by other Ataraxis framework projects.

See the `documentation <https://ataraxis-automation-api-docs.netlify.app/>`_ for the description of available
assets. See the `source code repository <https://github.com/Sun-Lab-NBB/ataraxis-automation>`_ for more details.

Authors: Ivan Kondratyev (Inkaros)
"""

from .automation import (
    ProjectEnvironment,
    NetlifyMigrationResult,
    move_stubs,
    delete_stubs,
    robust_rmtree,
    verify_pypirc,
    format_message,
    colorize_message,
    verify_netlifyrc,
    read_netlify_site,
    write_netlify_site,
    derive_netlify_site,
    resolve_pypirc_path,
    deploy_documentation,
    resolve_library_root,
    generate_typed_marker,
    migrate_legacy_pypirc,
    resolve_netlifyrc_path,
    migrate_legacy_netlifyrc,
    resolve_project_directory,
    resolve_application_directory,
    resolve_documented_project_directory,
)

__all__ = [
    "NetlifyMigrationResult",
    "ProjectEnvironment",
    "colorize_message",
    "delete_stubs",
    "deploy_documentation",
    "derive_netlify_site",
    "format_message",
    "generate_typed_marker",
    "migrate_legacy_netlifyrc",
    "migrate_legacy_pypirc",
    "move_stubs",
    "read_netlify_site",
    "resolve_application_directory",
    "resolve_documented_project_directory",
    "resolve_library_root",
    "resolve_netlifyrc_path",
    "resolve_project_directory",
    "resolve_pypirc_path",
    "robust_rmtree",
    "verify_netlifyrc",
    "verify_pypirc",
    "write_netlify_site",
]
