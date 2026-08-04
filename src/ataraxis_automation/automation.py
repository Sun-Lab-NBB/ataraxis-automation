"""Provides the assets that support various project development automation Command Line Interface (CLI) commands
exposed by the 'cli' module. Implements the logic of all automation tasks.
"""

import io
import os
import re
import sys
import stat
import time
import shlex
from types import TracebackType
import shutil
from typing import Any
from pathlib import Path
import tomllib
import zipfile
import textwrap
import subprocess
from dataclasses import dataclass
from configparser import ConfigParser
from collections.abc import Callable

import click
import requests
import platformdirs

_SUPPORTED_PLATFORMS: dict[str, str] = {
    "win32": "_win",
    "linux": "_lin",
    "darwin": "_osx",
}
"""Stores supported platform (OS) names together with their suffixes. This library is designed to work only with the
listed operating systems."""

_BASE_NAME_PATTERN: re.Pattern[str] = re.compile(r"^([a-zA-Z0-9_.-]+)")
"""Stores the module-level compiled regex pattern for extracting package base names."""

_FILE_RETRY_COUNT: int = 5
"""Stores the maximum number of attempts made for file operations that may fail due to transient Windows file
locks."""

_FILE_RETRY_INITIAL_DELAY: float = 0.5
"""Stores the initial delay in seconds between file operation retry attempts. Each subsequent retry doubles the
delay."""

_NETLIFY_API_URL: str = "https://api.netlify.com/api/v1"
"""Stores the base URL of the Netlify REST API used to deploy the project's API documentation."""

_NETLIFY_DEPLOY_TIMEOUT: int = 300
"""Stores the maximum time, in seconds, to wait for the Netlify deployment request to complete."""

_APPLICATION_NAME: str = "ataraxis_automation"
"""Stores the application name used to resolve the directory that keeps the credentials shared by all projects
managed on the host-machine."""

_APPLICATION_AUTHOR: str = "ataraxis"
"""Stores the application author used to resolve the shared credentials directory on Windows platforms."""

_PYPIRC_FILE_NAME: str = ".pypirc"
"""Stores the name of the file that keeps the PyPI API token."""

_NETLIFYRC_FILE_NAME: str = ".netlifyrc"
"""Stores the name of the file that keeps the Netlify API token."""

_NETLIFY_SITE_FILE_NAME: str = ".netlify-site"
"""Stores the name of the project-local file that keeps the Netlify site identifier. The identifier differs for each
project, so it is versioned with the project instead of being shared through the application directory."""

_NETLIFY_SITE_SUFFIX: str = "-api-docs.netlify.app"
"""Stores the suffix appended to the project's directory name to derive the default Netlify site identifier."""

_PYTHON_PROJECT_ITEMS: tuple[str, ...] = ("src", "envs", "pyproject.toml", "tox.ini")
"""Stores the names of the root directory items that identify a valid Ataraxis framework Python project."""

_DOCUMENTED_PROJECT_ITEMS: tuple[str, ...] = ("src", "docs", "tox.ini")
"""Stores the names of the root directory items shared by every Ataraxis framework project archetype that builds API
documentation, including the C++ PlatformIO projects that have no Python package layout."""

_CERTIFICATE_VARIABLES: dict[str, str | None] = {
    "SSL_CERT_FILE": "__CONDA_OPENSSL_CERT_FILE_SET",
    "SSL_CERT_DIR": "__CONDA_OPENSSL_CERT_DIR_SET",
    "REQUESTS_CA_BUNDLE": None,
    "CURL_CA_BUNDLE": None,
}
"""Stores the environment variables that override the certificate bundle used by the package managers this library
calls, mapped to the conda guard variable that marks the override as conda-generated. Variables that conda does not
manage are mapped to None."""


@dataclass(frozen=True, slots=True)
class ProjectEnvironment:
    """Encapsulates the data used to interface with the project's mamba environment.

    Notes:
        This class should not be instantiated directly. Instead, use the ``resolve_project_environment()`` class method
        to get an instance of this class.
    """

    activate_command: str
    """Stores the command used to activate the project's mamba environment."""
    deactivate_command: str
    """Stores the command used to deactivate any current environment and switch to the base environment."""
    create_command: str
    """Stores the command used to generate a minimally-configured mamba environment."""
    create_dry_run_command: str
    """Stores the command used to verify that the project's mamba environment resolves without creating it."""
    create_from_yaml_command: str | None
    """Stores the command used to create a new mamba environment from an existing .yml file."""
    remove_command: str
    """Stores the command used to remove (delete) the project's mamba environment."""
    install_dependencies_command: str
    """Stores the command used to install all project dependencies into the project's mamba environment using uv."""
    update_command: str | None
    """Stores the command used to update an already existing mamba environment using an existing .yml file."""
    install_project_command: str
    """Stores the command used to build and install the project as a library into the project's mamba environment."""
    uninstall_project_command: str
    """Stores the command used to uninstall the project library from the project's mamba environment."""
    environment_name: str
    """Stores the name of the project's mamba environment with the appended os-suffix."""
    environment_directory: Path
    """Stores the path to the project's mamba environment directory."""
    environment_yaml_path: Path
    """Stores the path to the os-specific .yml file that keeps the project's exported environment specification."""

    @classmethod
    def resolve_project_environment(
        cls,
        project_root: Path,
        environment_name: str,
        python_version: str = "3.13",
        environment_directory: Path | None = None,
        *,
        prerelease: bool = False,
    ) -> "ProjectEnvironment":
        """Generates the mamba and uv commands used to manipulate the project- and os-specific mamba
        environment and packages them into a ProjectEnvironment instance.

        Args:
            project_root: The absolute path to the root directory of the processed project.
            environment_name: The base-name of the project's mamba environment.
            python_version: The Python version installed into the mamba environment when the environment is created.
            environment_directory: Optional. The absolute path to the directory used by the mamba / conda manager to
                store Python environments. This argument only needs to be provided if the automatic (default)
                environment resolution fails.
            prerelease: Determines whether uv is allowed to install prerelease versions of dependencies.

        Returns:
            The resolved ProjectEnvironment instance.

        Raises:
            RuntimeError: If the host OS is unsupported, mamba or uv is not accessible, or the mamba environments
                directory cannot be resolved and no manual override is provided.
            ValueError: If the project name cannot be extracted from pyproject.toml, duplicate dependencies are
                found, or the pyproject.toml file declares no dependencies at all.
        """
        # Gets the environment name with the appropriate os-extension and the path to the .yml file.
        extended_environment_name, yaml_path = _resolve_environment_files(
            project_root=project_root, environment_base_name=environment_name
        )

        # Gets the name of the project from the pyproject.toml file.
        project_name = _resolve_project_name(project_root=project_root)

        # Verifies that mamba and uv are accessible to the caller.
        _check_package_engines()

        # Resolves the physical path to the project's mamba environment directory.
        try:
            target_environment_directory = _resolve_mamba_environments_directory().joinpath(extended_environment_name)
        # Only uses the manual override if the automated resolution fails.
        except RuntimeError:
            if environment_directory is not None:
                target_environment_directory = environment_directory.joinpath(extended_environment_name)
            else:
                # If no manual override is available, re-raises the original error.
                raise

        # Resolves the command used to initialize conda before an environment is activated or deactivated. The host OS
        # is read from sys.platform, which is the same source _resolve_environment_files() uses to select the
        # os-suffix, so the initialization command and the environment name always agree.
        if sys.platform == "win32":
            # Uses 'conda' for activation, as it is more streamlined and performs equally well. Redirects stdout and
            # stderr to null.
            conda_initialization_command = "call conda.bat >NUL 2>&1"
        else:
            conda_initialization_command = '. "$(conda info --base)/etc/profile.d/conda.sh"'

        # Resolves activation and deactivation commands using the resolved conda initialization command. Every
        # interpolated path is quoted, as these commands are executed through the host's command shell, which would
        # otherwise split a path containing spaces into separate arguments.
        quoted_environment_directory = _quote_path(path=target_environment_directory)
        activate_command = f"{conda_initialization_command} && conda activate {quoted_environment_directory}"
        deactivate_command = f"{conda_initialization_command} && conda deactivate"

        # Resolves the dependencies to install into the environment. An empty list produces a uv command with no
        # package operands, so it is rejected here, where the cause can still be named.
        dependencies = _resolve_dependencies(project_root=project_root)
        if not dependencies:
            message: str = (
                f"Unable to resolve the mamba environment for the project stored under {project_root}. The project's "
                f"pyproject.toml file declares no runtime or development dependencies, so there is nothing to install "
                f"into the environment."
            )
            raise ValueError(format_message(message=message))

        # Generates dependency installation commands using uv:
        prerelease_flag = " --prerelease=allow" if prerelease else ""
        install_dependencies_command = (
            f"uv pip install {' '.join(dependencies)} --resolution highest "
            f"--refresh --compile-bytecode --python={quoted_environment_directory} --strict --exact{prerelease_flag}"
        )
        uninstall_project_command = f"uv pip uninstall {project_name} --python={quoted_environment_directory}"
        install_project_command = (
            f"uv pip install . --resolution highest --refresh --reinstall-package {project_name} --compile-bytecode "
            f"--python={quoted_environment_directory} --strict{prerelease_flag}"
        )

        # Generates mamba environment manipulation commands.
        # Creation (base) generates a minimal mamba environment. Project dependencies are added afterwards by the uv
        # command generated above. Note, installs the latest versions of tox, uv, and tox-uv with the expectation that
        # the dependency installation command uses --exact to pin these packages to the requested versions.
        create_command = (
            f"mamba create -n {extended_environment_name} python={python_version} uv tox tox-uv --yes "
            f"--retry-clean-cache --pyc --use-uv"
        )
        create_dry_run_command = f"{create_command} --dry-run"
        remove_command = f"mamba remove -n {extended_environment_name} --all --yes"

        # Resolves .yml based commands. These commands are set to valid string-commands only if the .yml file for the
        # project's environment exists and to None otherwise. Both commands pin the target environment name, so the
        # 'name' key stored inside the .yml file cannot redirect them to a different environment.
        yaml_create_command: str | None = None
        update_command: str | None = None
        if yaml_path.exists():
            quoted_yaml_path = _quote_path(path=yaml_path)
            yaml_create_command = (
                f"mamba env create -n {extended_environment_name} -f {quoted_yaml_path} --yes --retry-clean-cache "
                f"--pyc --use-uv"
            )
            update_command = (
                f"mamba env update -n {extended_environment_name} -f {quoted_yaml_path} --yes --prune --use-uv"
            )

        return cls(
            activate_command=activate_command,
            deactivate_command=deactivate_command,
            create_command=create_command,
            create_dry_run_command=create_dry_run_command,
            create_from_yaml_command=yaml_create_command,
            remove_command=remove_command,
            install_dependencies_command=install_dependencies_command,
            update_command=update_command,
            environment_name=extended_environment_name,
            install_project_command=install_project_command,
            uninstall_project_command=uninstall_project_command,
            environment_directory=target_environment_directory,
            environment_yaml_path=yaml_path,
        )

    def verify_removable(self) -> None:
        """Verifies that the environment is not the one hosting the interpreter of the running process.

        Notes:
            Windows holds an open handle on every loaded module, so the files of the environment that provides the
            running interpreter stay locked for as long as the process lives. Mamba unlinks the packages, renames the
            files it is unable to delete to '.mamba_trash', and leaves a directory that no longer resolves as an
            environment. The check runs before the removal starts, which keeps the environment intact.

        Raises:
            RuntimeError: If the environment provides the interpreter or the conda prefix of the running process.
        """
        # POSIX platforms unlink the files of a running process on request, so the removal completes there.
        if sys.platform != "win32":
            return

        # The base prefix names the environment whose interpreter created the virtual environment this command runs
        # in, and the conda prefix names the environment the calling shell activated.
        hosting_directories: list[Path] = [Path(sys.base_prefix), Path(sys.prefix)]
        conda_prefix: str | None = os.environ.get("CONDA_PREFIX")
        if conda_prefix:
            hosting_directories.append(Path(conda_prefix))

        environment_directory = self.environment_directory.resolve()
        if all(environment_directory != directory.resolve() for directory in hosting_directories):
            return

        message: str = (
            f"Unable to remove the '{self.environment_name}' mamba environment stored under "
            f"{self.environment_directory}. This environment provides the interpreter that runs the current command, "
            f"and Windows keeps the files of a running interpreter locked, so mamba is unable to delete them. Run "
            f"this command from the 'base' environment instead."
        )
        raise RuntimeError(format_message(message=message))

    def environment_exists(self) -> bool:
        """Determines whether the environment can be activated (exists).

        Returns:
            True if the project's mamba environment exists and can be activated, and False if it does not exist.

        Raises:
            RuntimeError: If the environment directory carries conda-meta package records, which identify it as a
                registered environment that the conda activation machinery is nonetheless unable to activate.
        """
        # Verifies that the project- and os-specific mamba environment can be activated.
        try:
            subprocess.run(
                self.activate_command,
                shell=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            # A conda-meta directory holding package records is a registered environment, so a failure to activate it
            # points at the conda installation rather than at a missing environment. Reporting the two conditions as
            # one would let the callers that remove environments delete a working one. An empty conda-meta directory
            # is the remnant of an interrupted removal, which the callers clear as a missing environment instead.
            if any(self.environment_directory.joinpath("conda-meta").glob("*.json")):
                message: str = (
                    f"Unable to activate the '{self.environment_name}' mamba environment stored under "
                    f"{self.environment_directory}, although the directory contains a valid environment. This "
                    f"typically indicates that conda is not installed or initialized on this machine. Make sure "
                    f"miniforge3 is installed and initialized before using the ataraxis-automation cli."
                )
                raise RuntimeError(format_message(message=message)) from None
            return False
        else:
            return True

    def export_environment(self) -> None:
        """Exports the project's mamba environment to the os-specific .yml file stored in the project's 'envs'
        directory.

        Notes:
            The specification is written to a temporary file inside the target directory and renamed over the
            destination only after mamba reports a successful export that declares at least one dependency. A failed
            export therefore leaves the previously exported file intact.

        Raises:
            RuntimeError: If mamba fails to export the environment or exports a specification that declares no
                dependencies.
        """
        try:
            completed_process = subprocess.run(  # noqa: S603 - Every command element is generated by this library.
                ["mamba", "env", "export", "--name", self.environment_name, "--use-uv"],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as error:
            message: str = (
                f"Unable to export the '{self.environment_name}' mamba environment to a .yml file. Mamba exited with "
                f"the code {error.returncode} and the following error: {error.stderr.strip()}."
            )
            raise RuntimeError(format_message(message=message)) from None

        # Mamba appends the absolute path to the environment as the last line of the specification. The path is
        # host-specific, so it is removed to keep the exported file portable across machines.
        specification_lines: list[str] = completed_process.stdout.splitlines()
        if specification_lines and specification_lines[-1].startswith("prefix:"):
            specification_lines = specification_lines[:-1]

        # Mamba exports a contentless skeleton with a zero exit code when it is asked for an environment it does not
        # track. Writing that skeleton over the project's file would discard the stored dependency pins.
        if not _declares_dependencies(specification_lines=specification_lines):
            message = (
                f"Unable to export the '{self.environment_name}' mamba environment to a .yml file. Mamba exported a "
                f"specification that declares no dependencies, which indicates that it does not track an environment "
                f"under that name. The previously exported file has been left unchanged."
            )
            raise RuntimeError(format_message(message=message))

        # Writes the specification through a temporary file in the destination directory, so that an interrupted write
        # cannot leave the exported file partially overwritten.
        temporary_path = self.environment_yaml_path.with_name(f"{self.environment_yaml_path.name}.tmp")
        temporary_path.write_text("\n".join(specification_lines) + "\n", encoding="utf-8")
        temporary_path.replace(self.environment_yaml_path)


@dataclass(frozen=True, slots=True)
class NetlifyMigrationResult:
    """Stores the outcome of migrating the legacy Netlify credentials of a project.

    Notes:
        The token and the site identifier are migrated independently, so a migration frequently moves one of them and
        leaves the other in place.
    """

    token_migrated: bool
    """Determines whether the API token was copied to the shared .netlifyrc file."""
    site_migrated: bool
    """Determines whether the site identifier was written to the project's .netlify-site file."""

    def __bool__(self) -> bool:
        """Returns True if at least one credential was migrated."""
        return self.token_migrated or self.site_migrated


def format_message(message: str) -> str:
    """Formats input message strings to follow the general Ataraxis framework style.

    Args:
        message: The input message string to format.

    Returns:
        The formatted message string.
    """
    return textwrap.fill(
        text=message,
        width=120,
        break_long_words=False,
        break_on_hyphens=False,
    )


def colorize_message(message: str, color: str, *, wrap: bool = True) -> str:
    """Modifies the input string to include an ANSI color code and, if necessary, formats the message by wrapping it
    at 120 characters.

    Args:
        message: The input message string to format and colorize.
        color: The ANSI color code to use for coloring the message.
        wrap: Determines whether to format the message by wrapping it at 120 characters.

    Returns:
        The colorized and wrapped (if requested) message string.
    """
    if wrap:
        message = format_message(message=message)

    return click.style(text=message, fg=color)


def resolve_project_directory() -> Path:
    """Resolves the current working directory and verifies that it points to a valid Ataraxis framework project.

    Returns:
        The absolute path to the current working directory, if it points to a valid Ataraxis framework project.

    Raises:
        RuntimeError: If the current working directory does not point to a valid Ataraxis framework project.
    """
    return _resolve_project_directory(
        required_items=_PYTHON_PROJECT_ITEMS,
        project_description="Python",
        items_description="'/src', '/envs', 'pyproject.toml' and 'tox.ini'",
    )


def resolve_documented_project_directory() -> Path:
    """Resolves the current working directory and verifies that it points to an Ataraxis framework project that builds
    API documentation.

    Notes:
        This verification accepts every project archetype that builds API documentation, including the C++ PlatformIO
        projects that have no Python package layout.

    Returns:
        The absolute path to the current working directory, if it points to a project that builds API documentation.

    Raises:
        RuntimeError: If the current working directory does not point to a project that builds API documentation.
    """
    return _resolve_project_directory(
        required_items=_DOCUMENTED_PROJECT_ITEMS,
        project_description="documented",
        items_description="'/src', '/docs' and 'tox.ini'",
    )


def resolve_library_root(project_root: Path) -> Path:
    """Resolves the absolute path to the project's root library directory.

    Notes:
        This function relies on the following resolution heuristic: library root is a directory at most one
        level below /src with an __init__.py file.

    Args:
        project_root: The absolute path to the root directory of the processed project.

    Returns:
        The absolute path to the root library directory.

    Raises:
        RuntimeError: If the valid root directory candidate cannot be found based on the determination heuristics.
    """
    src_path: Path = project_root.joinpath("src")

    # If the __init__.py is found inside the /src directory, this indicates /src is the library root. This is typically
    # true for C-extension projects, but not for pure Python projects.
    if src_path.joinpath("__init__.py").exists():
        return src_path

    # If __init__.py is not found at the level of the src, this implies that the processed project is a pure python
    # project and, in this case, it is expected that there is a single library-directory under /src that is the
    # root.

    # Discovers all candidates for the library root directory. Candidates are expected to be directories directly under
    # /src that also contain an __init__.py file.
    candidates: set[Path] = {
        candidate_path
        for candidate_path in src_path.iterdir()
        if candidate_path.is_dir() and (candidate_path.joinpath("__init__.py")).exists()
    }

    # The expectation is that there is exactly one candidate that fits the requirements. If this is not true, the
    # project structure is not well-configured and should not be processed.
    if len(candidates) != 1:
        message: str = (
            f"Unable to resolve the path to the library root directory from the project root path {project_root}. "
            f"Specifically, did not find an __init__.py inside the /src directory and found {len(candidates)} "
            f"sub-directories with __init__.py inside the /src directory. Make sure there is an __init__.py "
            f"inside /src or ONE of the sub-directories under /src."
        )
        raise RuntimeError(format_message(message=message))

    return candidates.pop()


def generate_typed_marker(library_root: Path) -> None:
    """Crawls the library directory tree and ensures that the py.typed marker exists only at the root level of the
    directory.

    Args:
        library_root: The path to the root level of the library directory.
    """
    # Adds py.typed to the root directory if it doesn't exist.
    root_py_typed = library_root.joinpath("py.typed")
    if not root_py_typed.exists():
        root_py_typed.touch()
        message: str = f"Added py.typed marker to library root ({library_root})."
        click.echo(colorize_message(message=message, color="white"), color=True)

    # Removes py.typed from all subdirectories.
    for path in library_root.rglob("py.typed"):
        if path != root_py_typed:
            _unlink_with_retry(path=path)
            message = f"Removed no longer needed py.typed marker file {path}."
            click.echo(colorize_message(message=message, color="white"), color=True)


def move_stubs(stubs_directory: Path, library_root: Path) -> None:
    """Moves typing stub (.pyi) files from the 'stubs' directory to the appropriate level(s) of the library directory
    tree.

    Notes:
        The 'stubs' directory is expected to hold the output of stubgen, which is exactly one subdirectory with an
        __init__.pyi file. That subdirectory is considered to be the library root in the 'stubs' directory structure.

    Args:
        stubs_directory: The absolute path to the project's "stubs" directory.
        library_root: The absolute path to the root library directory.

    Raises:
        RuntimeError: If the 'stubs' directory does not contain exactly one subdirectory with an __init__.pyi file.
    """
    # Compiles regex patterns once to optimize the cycles below.
    copy_pattern = re.compile(r" (\d+)\.pyi$")
    base_name_pattern = re.compile(r" \d+\.pyi$")

    # Verifies the 'stubs' directory structure and finds the library name. To do so, first generates a set of all
    # subdirectories under /stubs that also have an __init__.pyi file.
    valid_subdirectories = [
        subdirectory
        for subdirectory in stubs_directory.iterdir()
        if subdirectory.is_dir() and subdirectory.joinpath("__init__.pyi").exists()
    ]

    # Expects that the process above yields a single output directory. Otherwise, raises a RuntimeError.
    if len(valid_subdirectories) != 1:
        message: str = (
            f"Unable to move the generated stub files to appropriate levels of the library source code directory. "
            f"Expected exactly one subdirectory with __init__.pyi in '{stubs_directory}', but found "
            f"{len(valid_subdirectories)}."
        )
        raise RuntimeError(format_message(message=message))

    # Extracts the single valid directory and uses it as the source for .pyi files.
    source_directory = valid_subdirectories[0]

    # Moves .pyi files from source to destination and tracks moved files for duplicate handling.
    # Assumes that the structure of the source_directory exactly matches the structure of the library_root.
    moved_files: dict[Path, list[Path]] = {}

    for stub_path in source_directory.rglob("*.pyi"):
        relative_path = stub_path.relative_to(source_directory)
        destination_path = library_root.joinpath(relative_path)

        # Ensures the destination directory exists.
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        # Removes the old .pyi file if it already exists.
        _unlink_with_retry(path=destination_path, missing_ok=True)

        # Moves the stub file to its destination directory using rename (this is more efficient than shutil.move).
        _rename_with_retry(source=stub_path, destination=destination_path)

        message = f"Moved stub file from /stubs to /src: {destination_path.name}."
        click.echo(colorize_message(message=message, color="white"), color=True)

        # Tracks moved files by directory for duplicate handling.
        moved_files.setdefault(destination_path.parent, []).append(destination_path)

    # Handles an OSX-unique issue, where this function produces multiple copies that have space+copy_number appended
    # to each file name, rather than a single copy of the .pyi file.

    # Processes each directory that received stub files.
    for directory_path, files in moved_files.items():
        # Groups files by their base name (without space and number).
        file_groups: dict[str, list[Path]] = {}
        for file_path in files:
            # Extracts base name without copy number.
            base_name = base_name_pattern.sub(".pyi", file_path.name)
            file_groups.setdefault(base_name, []).append(file_path)

        # Handles duplicates within each group.
        for base_name, group in file_groups.items():
            # If the group only has a single file, renames it if it has a copy number.
            if len(group) == 1:
                file_path = group[0]
                if file_path.name != base_name:
                    new_path = file_path.with_name(base_name)
                    _rename_with_retry(source=file_path, destination=new_path)
                    message = f"Renamed stub file in {directory_path}: {file_path.name} -> {base_name}."
                    click.echo(colorize_message(message=message, color="white"), color=True)
            # If the group has multiple files, keeps the one with the highest copy number.
            else:
                # Sorts by copy number in the descending order and keeps the first item.
                group.sort(key=lambda path: _get_copy_number(path=path, copy_pattern=copy_pattern), reverse=True)
                kept_file = group[0]

                # Removes all duplicates.
                for file_to_remove in group[1:]:
                    _unlink_with_retry(path=file_to_remove)
                    message = f"Removed duplicate .pyi file in {directory_path}: {file_to_remove.name}."
                    click.echo(colorize_message(message=message, color="white"), color=True)

                # Renames the kept file to remove copy number if needed.
                if kept_file.name != base_name:
                    new_path = kept_file.with_name(base_name)
                    _rename_with_retry(source=kept_file, destination=new_path)
                    message = f"Renamed stub file in {directory_path}: {kept_file.name} -> {base_name}."
                    click.echo(colorize_message(message=message, color="white"), color=True)


def delete_stubs(library_root: Path) -> None:
    """Removes all .pyi stub files from the root library directory and its subdirectories.

    Args:
        library_root: The absolute path to the root library directory.
    """
    # Iterates over all .pyi files in the directory tree and removes them.
    pyi_file: Path
    for pyi_file in library_root.rglob("*.pyi"):
        _unlink_with_retry(path=pyi_file)
        click.echo(colorize_message(message=f"Removed stub file: {pyi_file.name}.", color="white"), color=True)


def resolve_application_directory() -> Path:
    """Resolves the path to the directory that stores the API tokens shared by all projects managed on the
    host-machine.

    Notes:
        The directory is created if it does not already exist.

    Returns:
        The absolute path to the application directory.
    """
    application_directory = Path(platformdirs.user_data_dir(appname=_APPLICATION_NAME, appauthor=_APPLICATION_AUTHOR))
    application_directory.mkdir(parents=True, exist_ok=True)
    return application_directory


def resolve_pypirc_path() -> Path:
    """Resolves the path to the .pypirc file that stores the PyPI API token shared by all projects managed on the
    host-machine.

    Returns:
        The absolute path to the .pypirc file.
    """
    return resolve_application_directory().joinpath(_PYPIRC_FILE_NAME)


def resolve_netlifyrc_path() -> Path:
    """Resolves the path to the .netlifyrc file that stores the Netlify API token shared by all projects managed on the
    host-machine.

    Returns:
        The absolute path to the .netlifyrc file.
    """
    return resolve_application_directory().joinpath(_NETLIFYRC_FILE_NAME)


def verify_pypirc(file_path: Path) -> bool:
    """Verifies that the target .pypirc file contains valid PyPI authentication credentials (API token).

    Notes:
        This function is not able to verify whether the token is currently active.

    Args:
        file_path: The absolute path to the .pypirc file to verify.

    Returns:
        True if the .pypirc file appears to contain a well-configured API token and False otherwise.

    Raises:
        configparser.Error: If the .pypirc file exists but contains malformed INI syntax.
    """
    config_validator: ConfigParser = ConfigParser()
    config_validator.read(file_path)
    return (
        config_validator.has_section("pypi")
        and config_validator.has_option(section="pypi", option="username")
        and config_validator.has_option(section="pypi", option="password")
        and config_validator.get(section="pypi", option="username") == "__token__"
        and config_validator.get(section="pypi", option="password").startswith("pypi-")
    )


def verify_netlifyrc(file_path: Path) -> bool:
    """Verifies that the target .netlifyrc file contains the Netlify authentication credentials (API token).

    Notes:
        This function is not able to verify whether the token is currently active.

    Args:
        file_path: The absolute path to the .netlifyrc file to verify.

    Returns:
        True if the .netlifyrc file appears to contain a well-configured API token and False otherwise.

    Raises:
        configparser.Error: If the .netlifyrc file exists but contains malformed INI syntax.
    """
    config_validator: ConfigParser = ConfigParser()
    config_validator.read(file_path)
    return (
        config_validator.has_section("netlify")
        and config_validator.has_option(section="netlify", option="token")
        and bool(config_validator.get(section="netlify", option="token").strip())
    )


def derive_netlify_site(project_root: Path) -> str:
    """Derives the Netlify site identifier of the target project from the name of its root directory.

    Notes:
        The derived identifier follows the site naming convention shared by nearly all Ataraxis framework and Sollertia
        platform projects, and projects that use a different identifier override it with the value stored in their
        .netlify-site file.

    Args:
        project_root: The absolute path to the root directory of the processed project.

    Returns:
        The derived Netlify site identifier.
    """
    return f"{project_root.name}{_NETLIFY_SITE_SUFFIX}"


def read_netlify_site(project_root: Path) -> str | None:
    """Reads the Netlify site identifier stored in the target project's .netlify-site file.

    Args:
        project_root: The absolute path to the root directory of the processed project.

    Returns:
        The stored Netlify site identifier, or None if the file does not exist or stores no identifier.
    """
    site_path = project_root.joinpath(_NETLIFY_SITE_FILE_NAME)
    if not site_path.is_file():
        return None

    return site_path.read_text(encoding="utf-8").strip() or None


def write_netlify_site(project_root: Path, site: str) -> None:
    """Writes the Netlify site identifier to the target project's .netlify-site file.

    Notes:
        Unlike the API token, the site identifier is not a secret and differs for each project, so the file it is
        written to is tracked by the project's version control system.

    Args:
        project_root: The absolute path to the root directory of the processed project.
        site: The Netlify site identifier to store in the file.
    """
    project_root.joinpath(_NETLIFY_SITE_FILE_NAME).write_text(f"{site}\n", encoding="utf-8")


def migrate_legacy_pypirc(project_root: Path) -> bool:
    """Copies the PyPI API token stored in the target project's root directory to the shared application directory.

    Notes:
        Earlier library versions stored the token inside the root directory of each project. This function preserves
        the token of a project that still uses that layout, so the user does not have to enter it again.

    Args:
        project_root: The absolute path to the root directory of the processed project.

    Returns:
        True if the token was migrated and False if the shared token is already configured or there is no legacy token
        to migrate.

    Raises:
        configparser.Error: If either .pypirc file exists but contains malformed INI syntax.
    """
    if verify_pypirc(file_path=resolve_pypirc_path()):
        return False

    legacy_path = project_root.joinpath(_PYPIRC_FILE_NAME)
    if not verify_pypirc(file_path=legacy_path):
        return False

    shutil.copyfile(src=legacy_path, dst=resolve_pypirc_path())
    return True


def migrate_legacy_netlifyrc(project_root: Path) -> NetlifyMigrationResult:
    """Splits the Netlify credentials stored in the target project's root directory between the shared application
    directory and the project's .netlify-site file.

    Notes:
        Earlier library versions stored both the site identifier and the API token inside a single .netlifyrc file in
        the root directory of each project. This function preserves both values of a project that still uses that
        layout, so the user does not have to enter them again.

    Args:
        project_root: The absolute path to the root directory of the processed project.

    Returns:
        The result of the migration, which reports the token and the site identifier separately, as each is migrated
        only when its destination is not already configured.

    Raises:
        configparser.Error: If either .netlifyrc file exists but contains malformed INI syntax.
    """
    legacy_credentials: ConfigParser = ConfigParser()
    legacy_credentials.read(project_root.joinpath(_NETLIFYRC_FILE_NAME))
    if not legacy_credentials.has_section("netlify"):
        return NetlifyMigrationResult(token_migrated=False, site_migrated=False)

    token_migrated: bool = False
    site_migrated: bool = False

    token = legacy_credentials.get(section="netlify", option="token", fallback="").strip()
    if token and not verify_netlifyrc(file_path=resolve_netlifyrc_path()):
        credentials: ConfigParser = ConfigParser()
        credentials["netlify"] = {"token": token}
        with resolve_netlifyrc_path().open(mode="w") as config_file:
            credentials.write(config_file)
        token_migrated = True

    site = legacy_credentials.get(section="netlify", option="site", fallback="").strip()
    if site and read_netlify_site(project_root=project_root) is None:
        write_netlify_site(project_root=project_root, site=site)
        site_migrated = True

    return NetlifyMigrationResult(token_migrated=token_migrated, site_migrated=site_migrated)


def deploy_documentation(documentation_directory: Path, site: str, token: str) -> str:
    """Deploys the pre-built API documentation to the target Netlify site.

    Packages the documentation directory into a ZIP archive and uploads it to Netlify as a production deployment.

    Notes:
        Netlify deployments are atomic. The uploaded archive has to contain every file served by the site, as each
        deployment fully replaces the content of the previous one.

    Args:
        documentation_directory: The absolute path to the directory that stores the built documentation .html files.
        site: The Netlify site identifier. Both the site's API (UUID) identifier and its domain name are accepted.
        token: The Netlify API token used to authenticate the deployment request.

    Returns:
        The URL of the website that serves the deployed documentation.

    Raises:
        RuntimeError: If the documentation directory does not contain the 'index.html' file. If the deployment
            request does not reach Netlify or if Netlify rejects the deployment.
    """
    if not documentation_directory.joinpath("index.html").is_file():
        message: str = (
            f"Unable to deploy the API documentation stored in {documentation_directory}. The directory does not "
            f"contain the 'index.html' file, which indicates that the documentation has not been built. Build the "
            f"documentation with the 'docs' ('tox -e docs') task before deploying it."
        )
        raise RuntimeError(format_message(message=message))

    archive: io.BytesIO = io.BytesIO()
    with zipfile.ZipFile(file=archive, mode="w", compression=zipfile.ZIP_DEFLATED) as archive_file:
        for file_path in sorted(documentation_directory.rglob("*")):
            if file_path.is_file():
                archive_file.write(filename=file_path, arcname=file_path.relative_to(documentation_directory))

    try:
        response: requests.Response = requests.post(
            url=f"{_NETLIFY_API_URL}/sites/{site}/deploys",
            headers={"Content-Type": "application/zip", "Authorization": f"Bearer {token}"},
            data=archive.getvalue(),
            timeout=_NETLIFY_DEPLOY_TIMEOUT,
        )
    except requests.RequestException as error:
        message = (
            f"Unable to deploy the API documentation to the '{site}' Netlify site. The deployment request failed with "
            f"the following error: {error}."
        )
        raise RuntimeError(format_message(message=message)) from None

    if not response.ok:
        message = (
            f"Unable to deploy the API documentation to the '{site}' Netlify site. Netlify rejected the deployment "
            f"request with the status code {response.status_code} and the following response: {response.text}."
        )
        raise RuntimeError(format_message(message=message))

    # Netlify reports the address of the deployed website under one of two keys, depending on whether the site is
    # configured to serve traffic over HTTPS. A success status carrying an empty or non-JSON body still describes an
    # accepted deployment, so the site domain is used as the address in that case.
    try:
        deployment_data: Any = response.json()
    except ValueError:
        deployment_data = {}
    if not isinstance(deployment_data, dict):
        deployment_data = {}

    website_url: str = deployment_data.get("ssl_url") or deployment_data.get("url") or f"https://{site}"
    return website_url


def robust_rmtree(path: Path) -> None:
    """Removes a directory tree with retry logic to handle transient Windows file locks.

    On Windows, antivirus scanners, the Search Indexer, and recently-exited processes can hold file handles briefly
    after the calling process has finished with them. This function wraps ``shutil.rmtree()`` with an ``onerror``
    handler that clears read-only attributes and an outer retry loop with exponential backoff to tolerate these
    transient locks. On non-Windows platforms, calls ``shutil.rmtree()`` directly with no retry overhead.

    Args:
        path: The absolute path to the directory tree to remove.

    Raises:
        OSError: If the directory cannot be removed. On Windows, transient PermissionErrors are retried with
            exponential backoff before the error is re-raised. On non-Windows platforms and for other error types,
            the error propagates immediately.
    """
    # On non-Windows platforms, file locks are advisory, so no retry logic is needed.
    if sys.platform != "win32":
        shutil.rmtree(path)
        return

    # On Windows, retries with exponential backoff to tolerate transient file locks.
    delay = _FILE_RETRY_INITIAL_DELAY
    for attempt in range(_FILE_RETRY_COUNT):
        try:
            shutil.rmtree(path, onerror=_rmtree_onerror)
        except PermissionError:
            if attempt < _FILE_RETRY_COUNT - 1:
                time.sleep(delay)
                delay *= 2
            else:
                raise
        else:
            return


def repair_stale_certificate_variables() -> tuple[str, ...]:
    """Clears the certificate-bundle environment variables that point to paths which no longer exist.

    Notes:
        The conda-forge openssl package ships activation scripts only for Windows, where they point SSL_CERT_FILE and
        SSL_CERT_DIR into the active environment. Those scripts assign a variable only when it is unset, so a value
        left behind by a removed environment survives every later activation. The package managers this library calls
        then read a bundle that is absent and refuse to trust any certificate, which fails every download.

        Each variable is cleared rather than repointed at the active conda prefix, because the environment named by a
        stale value is usually the one the caller is rebuilding. Clearing it restores the bundled certificate roots of
        uv and requests. The conda guard variable is cleared alongside the variable it tracks, as the activation
        scripts skip a variable whose guard remains set.

    Returns:
        The names of the cleared environment variables, in the order they were evaluated.
    """
    cleared_variables: list[str] = []
    for variable_name, guard_name in _CERTIFICATE_VARIABLES.items():
        variable_value: str | None = os.environ.get(variable_name)

        # A value that still resolves to an existing path is left alone, as it may have been assigned deliberately to
        # redirect the package managers at a specific certificate bundle.
        if not variable_value or Path(variable_value).exists():
            continue

        del os.environ[variable_name]
        cleared_variables.append(variable_name)

        # Clears the guard so that the next conda activation assigns the variable instead of skipping it.
        if guard_name is not None:
            os.environ.pop(guard_name, None)

    return tuple(cleared_variables)


def _quote_path(path: Path) -> str:
    """Wraps the input path in the quoting syntax understood by the host platform's command shell.

    Notes:
        POSIX shells and cmd.exe use different quoting syntax, so the form is selected from sys.platform. Quoting is
        required for every path spliced into a command executed through a shell, as an unquoted path containing
        whitespace is split into separate arguments.

    Args:
        path: The path to quote.

    Returns:
        The quoted path, suitable for interpolation into a shell command string.
    """
    if sys.platform == "win32":
        return f'"{path}"'

    return shlex.quote(str(path))


def _declares_dependencies(specification_lines: list[str]) -> bool:
    """Determines whether an exported mamba environment specification lists at least one dependency.

    Args:
        specification_lines: The lines of the environment specification exported by mamba.

    Returns:
        True if the specification contains a 'dependencies' section holding at least one entry.
    """
    try:
        dependencies_index = next(
            index for index, line in enumerate(specification_lines) if line.startswith("dependencies:")
        )
    except StopIteration:
        return False

    return any(line.lstrip().startswith("- ") for line in specification_lines[dependencies_index + 1 :])


def _resolve_project_directory(
    required_items: tuple[str, ...], project_description: str, items_description: str
) -> Path:
    """Verifies that the current working directory contains all required root directory items and resolves the path to
    it.

    Args:
        required_items: The names of the root directory items that have to be present in the project directory.
        project_description: The description of the expected project type, used to build the error message.
        items_description: The human-readable listing of the required items, used to build the error message.

    Returns:
        The absolute path to the current working directory, if it contains all required root directory items.

    Raises:
        RuntimeError: If the current working directory does not contain at least one of the required items.
    """
    project_directory = Path.cwd()

    if not all(project_directory.joinpath(item).exists() for item in required_items):
        message: str = (
            f"Unable to confirm that ataraxis automation CLI has been called from the root directory of a valid "
            f"{project_description} project. This CLI expects that the current working directory is set to the root "
            f"directory of the project, judged by the presence of {items_description}. Current working "
            f"directory is set to {project_directory}, which does not contain at least one of the required files."
        )
        raise RuntimeError(format_message(message=message))

    return project_directory


def _rmtree_onerror(
    failing_function: Callable[[str], None],
    path: str,
    exception_information: tuple[type[BaseException], BaseException, TracebackType],
) -> None:
    """Handles errors during ``shutil.rmtree()`` by clearing the Windows read-only attribute and retrying.

    Args:
        failing_function: The function that raised the exception (e.g., ``os.remove`` or ``os.rmdir``).
        path: The path to the file or directory that could not be removed.
        exception_information: The exception information tuple returned by ``sys.exc_info()``.

    Raises:
        BaseException: Re-raises the original exception unchanged when it is not a PermissionError.
    """
    exception = exception_information[1]
    if isinstance(exception, PermissionError):
        Path(path).chmod(stat.S_IWRITE)
        failing_function(path)
    else:
        raise exception


def _unlink_with_retry(path: Path, *, missing_ok: bool = False) -> None:
    """Removes a file with retry logic to handle transient Windows file locks.

    On Windows, makes up to ``_FILE_RETRY_COUNT`` attempts with exponential backoff when a ``PermissionError`` is
    encountered. On non-Windows platforms, calls ``Path.unlink()`` directly with no retry overhead.

    Args:
        path: The absolute path to the file to remove.
        missing_ok: Determines whether to suppress ``FileNotFoundError`` if the file does not exist.

    Raises:
        FileNotFoundError: If the file does not exist and 'missing_ok' is False.
        PermissionError: If the file cannot be removed after exhausting all retry attempts on Windows, or immediately
            on non-Windows platforms.
    """
    if sys.platform != "win32":
        path.unlink(missing_ok=missing_ok)
        return

    delay = _FILE_RETRY_INITIAL_DELAY
    for attempt in range(_FILE_RETRY_COUNT):
        try:
            path.unlink(missing_ok=missing_ok)
        except PermissionError:
            if attempt < _FILE_RETRY_COUNT - 1:
                time.sleep(delay)
                delay *= 2
            else:
                raise
        else:
            return


def _rename_with_retry(source: Path, destination: Path) -> None:
    """Renames a file with retry logic to handle transient Windows file locks.

    On Windows, makes up to ``_FILE_RETRY_COUNT`` attempts with exponential backoff when a ``PermissionError`` is
    encountered. On non-Windows platforms, calls ``Path.rename()`` directly with no retry overhead.

    Args:
        source: The absolute path to the file to rename.
        destination: The absolute path to the target file name.

    Raises:
        PermissionError: If the file cannot be renamed after exhausting all retry attempts on Windows, or immediately
            on non-Windows platforms.
    """
    if sys.platform != "win32":
        source.rename(destination)
        return

    delay = _FILE_RETRY_INITIAL_DELAY
    for attempt in range(_FILE_RETRY_COUNT):
        try:
            source.rename(destination)
        except PermissionError:
            if attempt < _FILE_RETRY_COUNT - 1:
                time.sleep(delay)
                delay *= 2
            else:
                raise
        else:
            return


def _get_copy_number(path: Path, copy_pattern: re.Pattern[str]) -> int:
    """Extracts the copy number from a stub file path name for duplicate sorting.

    Args:
        path: The path to the stub file to extract the copy number from.
        copy_pattern: The compiled regex pattern used to match copy number suffixes.

    Returns:
        The extracted copy number, or 0 if no copy number is present.
    """
    match = copy_pattern.search(path.name)
    return int(match.group(1)) if match else 0


def _get_base_name(dependency: str) -> str:
    """Extracts the base name of a dependency, removing versions, extras, and platform markers.

    Args:
        dependency: The dependency name to process.

    Returns:
        The processed dependency name, stripped of version, platform, and any other modifiers.
    """
    # Strips quotes if present.
    dependency = dependency.strip("\"'")

    # Strips platform markers first (anything after semicolon).
    dependency = dependency.split(";")[0].strip()

    # Uses regex to extract the base package name, removing extras and version specifiers in one operation.
    match = _BASE_NAME_PATTERN.match(dependency)
    return match.group(1) if match else dependency.strip()


def _add_dependency(dependency: str, dependencies: list[str], processed_dependencies: set[str]) -> None:
    """Verifies that the dependency base-name has not already been processed and, if not, adds it to the input list.

    This function ensures that each dependency only appears in a single pyproject.toml dependency list, preventing
    listing dependencies as both required and development.

    Notes:
        As part of its runtime, it modifies the input 'dependencies' list and 'processed_dependencies' set to include
        resolved dependency names.

    Args:
        dependency: The name of the evaluated dependency.
        dependencies: The list to which the processed dependency is added if it passes verification.
        processed_dependencies: The set used to store already processed dependencies.

    Raises:
        ValueError: If the extracted dependency is found in multiple pyproject.toml dependency lists.
    """
    # Strips the version, extras, and platform markers from dependencies to verify they are not duplicates.
    stripped_dependency: str = _get_base_name(dependency=dependency)
    if stripped_dependency in processed_dependencies:
        message: str = (
            f"Unable to resolve project dependencies. Found a duplicate dependency for '{dependency}', listed in the "
            f"pyproject.toml file. A dependency should only be found once across the 'dependencies' and "
            f"'dependency-groups' lists."
        )
        raise ValueError(format_message(message=message))

    # Wraps dependency in quotes to properly handle version specifiers and platform markers when dependencies are
    # installed via uv. This is needed for 'special' version specifications that use < or > and similar notations,
    # as well as for platform markers containing spaces.
    dependencies.append(f'"{dependency}"')
    processed_dependencies.add(stripped_dependency)


def _resolve_dependencies(project_root: Path) -> tuple[str, ...]:
    """Extracts project dependencies from pyproject.toml as a tuple of all dependencies (runtime and development).

    Notes:
        Reads runtime dependencies from ``[project].dependencies`` and development dependencies from
        ``[dependency-groups].dev`` (PEP 735). Falls back to ``[project.optional-dependencies].dev`` for backward
        compatibility with projects that have not yet migrated. As part of its runtime, this function also ensures
        that each dependency appears in only one list, preventing duplicates.

    Args:
        project_root: The absolute path to the root directory of the processed project.

    Returns:
        A tuple that stores the extracted and verified dependencies. Each dependency is wrapped in double quotes, so
        that version specifiers and platform markers survive being joined into a shell command.

    Raises:
        ValueError: If duplicate dependencies (based on versionless dependency names) are found in different pyproject
            dependency lists.
    """
    # Resolves the paths to the .toml file. The function that generates the project root path checks for
    # the presence of this file as part of its runtime, so it is assumed that it always exists.
    pyproject_path: Path = project_root.joinpath("pyproject.toml")

    # Opens pyproject.toml and parses its contents.
    with pyproject_path.open(mode="rb") as toml_file:
        pyproject_data = tomllib.load(toml_file)

    # Extracts runtime dependencies from the main 'project' metadata section.
    project_data: dict[str, Any] = pyproject_data.get("project", {})
    dependencies: list[str] = project_data.get("dependencies", [])

    # Stores all platform-applicable runtime dependencies.
    runtime_dependencies: list[str] = []
    # Stores all platform-applicable development dependencies.
    development_dependencies: list[str] = []
    # Keeps track of duplicates to prevent double-listing.
    processed_dependencies: set[str] = set()

    # Processes runtime dependencies first. These are the core dependencies required for the project to function.
    for dependency in dependencies:
        _add_dependency(
            dependency=dependency,
            dependencies=runtime_dependencies,
            processed_dependencies=processed_dependencies,
        )

    # Extracts development dependencies. Prefers PEP 735 dependency groups over legacy optional-dependencies.
    dependency_groups: dict[str, Any] = pyproject_data.get("dependency-groups", {})
    if "dev" in dependency_groups:
        for dependency in dependency_groups["dev"]:
            # Skips PEP 735 include-group references (dict entries), only processes string dependencies.
            if isinstance(dependency, str):
                _add_dependency(
                    dependency=dependency,
                    dependencies=development_dependencies,
                    processed_dependencies=processed_dependencies,
                )
    else:
        # Falls back to legacy optional-dependencies for backward compatibility with unmigrated projects.
        optional_dependencies: dict[str, list[str]] = project_data.get("optional-dependencies", {})
        if "dev" in optional_dependencies:
            for dependency in optional_dependencies["dev"]:
                _add_dependency(
                    dependency=dependency,
                    dependencies=development_dependencies,
                    processed_dependencies=processed_dependencies,
                )

    # Merges the two dependency lists and returns the merged list to caller as a tuple.
    runtime_dependencies.extend(development_dependencies)
    return tuple(runtime_dependencies)


def _resolve_project_name(project_root: Path) -> str:
    """Extracts the project name from the pyproject.toml file.

    Args:
        project_root: The absolute path to the root directory of the processed project.

    Returns:
        The name of the project.

    Raises:
        ValueError: If the project name is not defined in the pyproject.toml file. Also, if the pyproject.toml file is
            corrupted or otherwise malformed.
    """
    # Resolves the path to the pyproject.toml file.
    pyproject_path: Path = project_root.joinpath("pyproject.toml")

    # Reads and parses the pyproject.toml file.
    try:
        with pyproject_path.open(mode="rb") as toml_file:
            pyproject_data: dict[str, Any] = tomllib.load(toml_file)
    except tomllib.TOMLDecodeError as error:
        message: str = (
            f"Unable to parse the pyproject.toml file. The file may be corrupted or contains invalid TOML syntax. "
            f"Error details: {error}."
        )
        raise ValueError(format_message(message=message)) from None

    # Extracts the project name from the [project] section.
    project_data: dict[str, Any] = pyproject_data.get("project", {})
    project_name: str | None = project_data.get("name")

    # Checks if the project name was successfully extracted. An empty name is rejected alongside a missing one, as it
    # would otherwise reach the uv commands as a blank operand and consume the flag that follows it.
    if not project_name:
        message = (
            "Unable to resolve the project name from the pyproject.toml file. The 'name' field is missing or "
            "empty in the [project] section of the file."
        )
        raise ValueError(format_message(message=message))

    return project_name


def _resolve_mamba_environments_directory() -> Path:
    """Returns the absolute path to the local mamba environments directory.

    Returns:
        The absolute path to the mamba environments directory.

    Raises:
        RuntimeError: If mamba (via miniforge) is not installed and/or initialized.
    """
    # First tries to use CONDA_PREFIX (mamba uses the same environment variables as conda).
    mamba_prefix = os.environ.get("CONDA_PREFIX")
    if mamba_prefix:
        mamba_prefix_path = Path(mamba_prefix)
        # If the 'base' environment is active, the prefix points to the root mamba manager folder and needs to be
        # extended with 'envs'.
        if os.environ.get("CONDA_DEFAULT_ENV") == "base":
            return mamba_prefix_path.joinpath("envs")

        # Otherwise, for named environments, the root /envs directory is one level above the named directory:
        # e.g., /path/to/miniforge3/envs/myenv -> /path/to/miniforge3/envs.
        return mamba_prefix_path.parent

    # The call above does not resolve the mamba environment when this method runs in a tox environment, which is the
    # intended runtime scenario. Therefore, attempts to find the mamba environments directory manually.

    # Method 1: Checks whether this script is executed from a miniforge-based python shell.
    python_executable = Path(sys.executable)

    if "miniforge" in str(python_executable).lower():
        # Navigates up until it finds the miniforge root.
        current = python_executable.parent
        while current != current.parent:  # Stops at root
            # If the 'envs' directory is found while ascending towards the root, returns the directory path to caller.
            if current.name == "envs":
                return current

            # A 'conda-meta' directory marks a conda-managed directory, which while ascending towards the filesystem
            # root is either the manager root or one of the named environments directly under its /envs folder. The
            # two cases are told apart by the checks below.
            if current.joinpath("conda-meta").exists():
                # In a mamba environment, the /envs folder will be found directly under the root.
                environments_path = current.joinpath("envs")
                if environments_path.exists():
                    return environments_path

                # Otherwise, navigates up to find envs.
                if current.parent.name == "envs":
                    return current.parent

            current = current.parent

    # Method 2: Tries to find mamba by locating mamba/conda executable (mamba uses CONDA_EXE).
    mamba_executable = os.environ.get("CONDA_EXE")
    if mamba_executable:
        executable_path = Path(mamba_executable)
        # The environments directory sits two levels above the executable, so a relative value or one with fewer than
        # two parent components cannot address it. Such a value is skipped in favor of the remaining methods, rather
        # than resolved against the current working directory or indexed out of range.
        if executable_path.is_absolute() and len(executable_path.parents) > 1:
            environments_directory = executable_path.parents[1].joinpath("envs")
            if environments_directory.exists():
                return environments_directory

    # Method 3: Checks the standard miniforge3 installation location.
    home = Path.home()

    # Standard miniforge3 location on Unix-like systems.
    miniforge_environments = home.joinpath("miniforge3", "envs")
    if miniforge_environments.exists():
        return miniforge_environments

    # On Windows, also checks the AppData location.
    if sys.platform == "win32":
        # First try: constructs the path from user's home directory.
        windows_miniforge_environments = home.joinpath("AppData", "Local", "miniforge3", "envs")
        if windows_miniforge_environments.exists():
            return windows_miniforge_environments

        # Fallback: uses LOCALAPPDATA environment variable.
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            windows_miniforge_environments = Path(local_appdata).joinpath("miniforge3", "envs")
            if windows_miniforge_environments.exists():
                return windows_miniforge_environments

    # If this point is reached, miniforge is not installed and/or initialized. Raises an error.
    message: str = (
        "Unable to resolve the path to the mamba environments directory. This version of ataraxis-automation expects "
        "that mamba is installed via miniforge3, following the deprecation of mambaforge. Make sure miniforge3 is "
        "installed and initialized before using ataraxis-automation cli. Install from: "
        "https://github.com/conda-forge/miniforge"
    )
    raise RuntimeError(format_message(message=message))


def _resolve_environment_files(project_root: Path, environment_base_name: str) -> tuple[str, Path]:
    """Determines the Operating System of the host platform and uses it to generate the absolute path to the
    os-specific mamba environment '.yml' file.

    Notes:
        Currently, this function supports the following Operating Systems: macOS (Darwin), Linux, and Windows. The
        resolution depends only on the value of sys.platform.

    Args:
        project_root: The absolute path to the root directory of the processed project.
        environment_base_name: The name of the environment excluding the os_suffix, e.g., 'axa_dev'.

    Returns:
        A tuple of two elements. The first element is the name of the environment with the os-suffix, suitable
        for local mamba commands. The second element is the absolute path to the os-specific environment's '.yml'
        file.

    Raises:
        RuntimeError: If the host OS does not match any of the supported operating systems.
    """
    # Obtains the host operating system name.
    os_name: str = sys.platform

    # If the os name is not one of the supported names, raises an error.
    if os_name not in _SUPPORTED_PLATFORMS:
        message: str = (
            f"Unable to resolve the operating-system-specific suffix to use for mamba environment file names. The "
            f"local machine is using an unsupported operating system '{os_name}'. Currently, only the following "
            f"operating systems are supported: {', '.join(_SUPPORTED_PLATFORMS.keys())}."
        )
        raise RuntimeError(format_message(message=message))

    # Resolves the absolute path to the 'envs' directory.
    environments_directory: Path = project_root.joinpath("envs")

    # Selects the environment name according to the host OS and constructs the path to the environment .yml file
    # using the generated name.
    os_suffix = _SUPPORTED_PLATFORMS[os_name]
    environment_name: str = f"{environment_base_name}{os_suffix}"
    yaml_path: Path = environments_directory.joinpath(f"{environment_name}.yml")

    return environment_name, yaml_path


def _check_package_engines() -> None:
    """Determines whether mamba and uv can be accessed from this script by silently calling 'COMMAND --version'.

    Raises:
        RuntimeError: If either mamba or uv is not accessible via subprocess call through the shell.
    """
    # Verifies that mamba is available for environment management operations.
    try:
        subprocess.run(
            "mamba --version",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        # If mamba is not available, raises an error as it is required.
        message: str = (
            "Unable to interface with mamba for environment management. Mamba is required for this automation "
            "module and provides significantly faster conda operations. Install mamba (e.g., via miniforge3) and "
            "ensure it is initialized and added to PATH."
        )
        raise RuntimeError(format_message(message=message)) from None

    # Verifies that uv is available for package installation operations.
    try:
        subprocess.run(
            "uv --version",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        # If uv is not available, raises an error as it is required.
        message = (
            "Unable to interface with uv for package installation. uv is required for this automation module and "
            "provides significantly faster pip operations. Install uv (e.g., 'pip install uv' or 'mamba install uv') "
            "in the active Python environment."
        )
        raise RuntimeError(format_message(message=message)) from None
