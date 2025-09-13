"""This module provides the assets that support various project development automation Command Line Interface (CLI)
commands exposed by the 'cli' module. It implements the logic of all automation tasks.
"""

import os
import re
import sys
from typing import Any
from pathlib import Path
import textwrap
import subprocess
from dataclasses import dataclass
from configparser import ConfigParser

import click
import tomli

# Stores supported platform (OS) names together with their suffixes. This library is designed to work only with these
# listed operating systems.
_SUPPORTED_PLATFORMS: dict[str, str] = {
    "win32": "_win",
    "linux": "_lin",
    "darwin": "_osx",
}

# Stores the Module-level compiled regex pattern for extracting package base names
_BASE_NAME_PATTERN = re.compile(r"^([a-zA-Z0-9_.-]+)")


def format_message(message: str) -> str:
    """Formats input message strings to follow the general Sun lab and project Ataraxis style.

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
    at 120 lines.

    Args:
        message: The input message string to format and colorize.
        color: The ANSI color code to use for coloring the message.
        wrap: Determines whether to format the message by wrapping it at 120 lines.

    Returns:
        The colorized and wrapped (if requested) message string.
    """
    if wrap:
        message = format_message(message)

    return click.style(message, fg=color)


def resolve_project_directory() -> Path:
    """Resolves the current working directory and verifies that it points to a valid Sun lab project.

    Returns:
        The absolute path to the current working directory, if it points to a valid Sun lab project.

    Raises:
        RuntimeError: If the current working directory does not point to a valid Sun lab project.
    """
    # Gets current working directory
    project_dir = Path.cwd()

    # Checks if the current working directory points to a valid Sun lab project based on the presence of required
    # files in the root directory.
    required_items = {
        project_dir.joinpath("src"),
        project_dir.joinpath("envs"),
        project_dir.joinpath("pyproject.toml"),
        project_dir.joinpath("tox.ini"),
    }
    if not all(item.exists() for item in required_items):
        message: str = (
            f"Unable to confirm that ataraxis automation CLI has been called from the root directory of a valid Python "
            f"project. This CLI expects that the current working directory is set to the root directory of the "
            f"project, judged by the presence of '/src', '/envs', 'pyproject.toml' and 'tox.ini'. Current working "
            f"directory is set to {project_dir}, which does not contain at least one of the required files."
        )
        raise RuntimeError(format_message(message))

    return project_dir


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
    # Resolves the target directory
    src_path: Path = project_root.joinpath("src")

    # If the __init__.py is found inside the /src directory, this indicates /src is the library root. This is typically
    # true for C-extension projects, but not for pure Python project.
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
        raise RuntimeError(format_message(message))

    return candidates.pop()


def _get_base_name(dependency: str) -> str:
    """Extracts the base name of a dependency, removing versions, extras, and platform markers.

    Args:
        dependency: The dependency name to process.

    Returns:
        The process dependency name, stripped of version, platform, and any other modifiers.
    """
    # Strips quotes if present
    dependency = dependency.strip("\"'")

    # Strips platform markers first (anything after semicolon)
    dependency = dependency.split(";")[0].strip()

    # Uses regex to extract the base package name, removing extras and version specifiers in one operation
    match = _BASE_NAME_PATTERN.match(dependency)
    return match.group(1) if match else dependency.strip()


def _add_dependency(dependency: str, dependencies: list[str], processed_dependencies: set[str]) -> None:
    """Verifies that dependency base-name is not already added to the input list and, if not, adds it to the list.

    This method ensures that each dependency only appears in a single pyproject.toml dependency list, preventing
    listing dependencies as both required and optional.

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
    # Strips the version, extras, and platform markers from dependencies to verify they are not duplicates
    stripped_dependency: str = _get_base_name(dependency=dependency)
    if stripped_dependency in processed_dependencies:
        message: str = (
            f"Unable to resolve project dependencies. Found a duplicate dependency for '{dependency}', listed in the "
            f"pyproject.toml file. A dependency should only be found once across the 'dependencies' and "
            f"'optional-dependencies' lists."
        )
        raise ValueError(format_message(message))

    # Wraps dependency in quotes to properly handle version specifiers and platform markers when dependencies are
    # installed via uv. This is needed for 'special' version specifications that use < or > and similar notations,
    # as well as for platform markers containing spaces.
    dependencies.append(f'"{dependency}"')
    processed_dependencies.add(stripped_dependency)


def _resolve_dependencies(project_root: Path) -> tuple[str, ...]:
    """Extracts project dependencies from all pyproject.toml lists as a tuple of all dependencies (runtime and
    development).

    Notes:
        As part of its runtime, this function also ensures that dependencies appear exclusively in the main
        'dependencies' list or the 'optional-dependencies' list.

    Args:
        project_root: The absolute path to the root directory of the processed project.

    Returns:
        A tuple that stores the extracted and verified dependencies.

    Raises:
        ValueError: If duplicate dependencies (based on versionless dependency names) are found in different pyproject
            dependency lists.
    """
    # Resolves the paths to the .toml file. The function that generates the project root path checks for
    # the presence of this file as part of its runtime, so it is assumed that it always exists.
    pyproject_path: Path = project_root.joinpath("pyproject.toml")

    # Opens pyproject.toml and parses its contents
    with Path.open(pyproject_path, "rb") as f:
        pyproject_data = tomli.load(f)

    # Extracts dependencies and optional-dependencies from the main 'project' metadata section.
    project_data: dict[str, Any] = pyproject_data.get("project", {})
    dependencies: list[str] = project_data.get("dependencies", [])
    optional_dependencies: dict[str, list[str]] = project_data.get("optional-dependencies", {})

    runtime_dependencies: list[str] = []  # Stores all platform-applicable runtime dependencies
    development_dependencies: list[str] = []  # Stores all platform-applicable development dependencies
    processed_dependencies: set[str] = set()  # Keeps track of duplicates to prevent double-listing

    # Processes runtime dependencies first. These are the core dependencies required for the project to function.
    # Filters them based on platform markers if present.
    for dependency in dependencies:
        _add_dependency(
            dependency=dependency,
            dependencies=runtime_dependencies,
            processed_dependencies=processed_dependencies,
        )

    # Processes development dependencies if they exist. These include testing, linting, documentation, and build tools.
    # Also filters based on platform markers.
    if "dev" in optional_dependencies:
        for dependency in optional_dependencies["dev"]:
            _add_dependency(
                dependency=dependency,
                dependencies=development_dependencies,
                processed_dependencies=processed_dependencies,
            )

    # Merges the two dependency lists and returns the merged list to caller as a tuple
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
    # Resolves the path to the pyproject.toml file
    pyproject_path: Path = project_root.joinpath("pyproject.toml")

    # Reads and parses the pyproject.toml file
    try:
        with Path.open(pyproject_path, "rb") as f:
            pyproject_data: dict[str, Any] = tomli.load(f)
    except tomli.TOMLDecodeError as e:
        message: str = (
            f"Unable to parse the pyproject.toml file. The file may be corrupted or contains invalid TOML syntax."
            f"Error details: {e}."
        )
        raise ValueError(format_message(message)) from None

    # Extracts the project name from the [project] section
    project_data: dict[str, Any] = pyproject_data.get("project", {})
    project_name: str | None = project_data.get("name")

    # Checks if the project name was successfully extracted
    if project_name is None:
        message = (
            "Unable to resolve the project name from the pyproject.toml file. The 'name' field is missing or "
            "empty in the [project] section of the file."
        )
        raise ValueError(format_message(message))

    return project_name


def generate_typed_marker(library_root: Path) -> None:
    """Crawls the library directory tree and ensures that the py.typed marker exists only at the root level of the
    directory.

    If the 'py.typed' is not found in the root directory, adds the marker file. If it is found in any subdirectory,
    removes the marker file.

    Args:
        library_root: The path to the root level of the library directory.
    """
    # Adds py.typed to the root directory if it doesn't exist
    root_py_typed = library_root.joinpath("py.typed")
    if not root_py_typed.exists():
        root_py_typed.touch()
        message: str = f"Added py.typed marker to library root ({library_root})."
        click.echo(colorize_message(message, color="white"), color=True)

    # Removes py.typed from all subdirectories
    for path in library_root.rglob("py.typed"):
        if path != root_py_typed:
            path.unlink()
            message = f"Removed no longer needed py.typed marker file {path}."
            click.echo(colorize_message(message, color="white"), color=True)


def move_stubs(stubs_dir: Path, library_root: Path) -> None:
    """Moves typing stub (.pyi) files from the 'stubs' directory to the appropriate level(s) of the library directory
    tree.

    This function should be called after running stubgen on the built library package (wheel). It distributes the stubs
    generated by stubgen to their final destinations in the library source code.

    Notes:
        This function expects that the 'stubs' directory has exactly one subdirectory, which contains an __init__.pyi
        file. This subdirectory is considered to be the library root in the 'stubs' directory structure.

    Args:
        stubs_dir: The absolute path to the project's "stubs" directory.
        library_root: The absolute path to the root library directory.
    """
    # Compiles regex patterns once to optimize the cycles below
    copy_pattern = re.compile(r" (\d+)\.pyi$")
    base_name_pattern = re.compile(r" \d+\.pyi$")

    # Verifies the 'stubs' directory structure and finds the library name. To do so, first generates a set of all
    # subdirectories under /stubs that also have an __init__.pyi file.
    valid_subdirectories = [
        sub_dir for sub_dir in stubs_dir.iterdir() if sub_dir.is_dir() and sub_dir.joinpath("__init__.pyi").exists()
    ]

    # Expects that the process above yields a single output directory. Otherwise, raises a RuntimeError.
    if len(valid_subdirectories) != 1:
        message: str = (
            f"Unable to move the generated stub files to appropriate levels of the library source code directory. "
            f"Expected exactly one subdirectory with __init__.pyi in '{stubs_dir}', but found "
            f"{len(valid_subdirectories)}."
        )
        raise RuntimeError(format_message(message))

    # Extracts the single valid directory and uses it as the source for .pyi files.
    source_directory = valid_subdirectories[0]

    # Moves .pyi files from source to destination and tracks moved files for duplicate handling.
    # Assumes that the structure of the source_directory exactly matches the structure of the library_root.
    moved_files: dict[Path, list[Path]] = {}

    for stub_path in source_directory.rglob("*.pyi"):
        relative_path = stub_path.relative_to(source_directory)
        destination_path = library_root.joinpath(relative_path)

        # Ensures the destination directory exists
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        # Removes the old .pyi file if it already exists
        destination_path.unlink(missing_ok=True)

        # Moves the stub file to its destination directory using rename (this is more efficient than shutil.move)
        stub_path.rename(destination_path)

        message = f"Moved stub file from /stubs to /src: {destination_path.name}."
        click.echo(colorize_message(message, color="white"), color=True)

        # Tracks moved files by directory for duplicate handling
        moved_files.setdefault(destination_path.parent, []).append(destination_path)

    # This section handles an OSX-unique issue, where this function produces multiple copies that
    # have space+copy_number appended to each file name, rather than a single copy of the .pyi file.

    # Processes each directory that received stub files
    for directory_path, files in moved_files.items():
        # Groups files by their base name (without space and number)
        file_groups: dict[str, list[Path]] = {}
        for file_path in files:
            # Extracts base name without copy number
            base_name = base_name_pattern.sub(".pyi", file_path.name)
            file_groups.setdefault(base_name, []).append(file_path)

        # Handles duplicates within each group
        for base_name, group in file_groups.items():
            # If the group only has a single file, renames it if it has a copy number
            if len(group) == 1:
                file_path = group[0]
                if file_path.name != base_name:
                    new_path = file_path.with_name(base_name)
                    file_path.rename(new_path)
                    message = f"Renamed stub file in {directory_path}: {file_path.name} -> {base_name}."
                    click.echo(colorize_message(message, color="white"), color=True)
            # If the group has multiple files, keeps the one with the highest copy number
            else:
                # Extracts copy number for sorting (assigns 0 if no number is present)
                def get_copy_number(path: Path) -> int:
                    match = copy_pattern.search(path.name)
                    return int(match.group(1)) if match else 0

                # Sorts by copy number in the descending order and keeps the first item
                group.sort(key=get_copy_number, reverse=True)
                kept_file = group[0]

                # Removes all duplicates
                for file_to_remove in group[1:]:
                    file_to_remove.unlink()
                    message = f"Removed duplicate .pyi file in {directory_path}: {file_to_remove.name}."
                    click.echo(colorize_message(message, color="white"), color=True)

                # Renames the kept file to remove copy number if needed
                if kept_file.name != base_name:
                    new_path = kept_file.with_name(base_name)
                    kept_file.rename(new_path)
                    message = f"Renamed stub file in {directory_path}: {kept_file.name} -> {base_name}."
                    click.echo(colorize_message(message, color="white"), color=True)


def delete_stubs(library_root: Path) -> None:
    """Removes all .pyi stub files from the root library directory and its subdirectories.

    Args:
        library_root: The absolute path to the root library directory.
    """
    # Iterates over all .pyi files in the directory tree and removes them.
    pyi_file: Path
    for pyi_file in library_root.rglob("*.pyi"):
        pyi_file.unlink()
        click.echo(colorize_message(f"Removed stub file: {pyi_file.name}.", color="white"), color=True)


def verify_pypirc(file_path: Path) -> bool:
    """Verifies that the target .pypirc file contains valid PyPI authentication credentials (API token).

    Notes:
        This function is not able to verify whether the token is currently active.

    Args:
        file_path: The absolute path to the .pypirc file to verify.

    Returns:
        True if the .pypirc file appears to contain a well-configured API token and False otherwise.
    """
    config_validator: ConfigParser = ConfigParser()
    config_validator.read(file_path)
    return (
        config_validator.has_section("pypi")
        and config_validator.has_option("pypi", "username")
        and config_validator.has_option("pypi", "password")
        and config_validator.get("pypi", "username") == "__token__"
        and config_validator.get("pypi", "password").startswith("pypi-")
    )


def _resolve_mamba_environments_directory() -> Path:
    """Returns the absolute path to the local mamba environments directory.

    Raises:
        RuntimeError: If mamba (via miniforge) is not installed and/or initialized.
    """
    # First tries to use CONDA_PREFIX (mamba uses the same environment variables as conda)
    mamba_prefix = os.environ.get("CONDA_PREFIX")
    if mamba_prefix:
        mamba_prefix_path = Path(mamba_prefix)
        # If the 'base' environment is active, the prefix points to the root mamba manager folder and needs to be
        # extended with 'envs'.
        if os.environ.get("CONDA_DEFAULT_ENV") == "base":
            return mamba_prefix_path.joinpath("envs")

        # Otherwise, for named environments, the root /envs directory is one level below the named directory:
        # e.g., /path/to/miniforge3/envs/myenv -> /path/to/miniforge3/envs
        return mamba_prefix_path.parent

    # The call above does not resolve the mamba environment when this method runs in a tox environment, which is the
    # intended runtime scenario. Therefore, attempts to find the mamba environments directory manually.

    # Method 1: Checks whether this script is executed from a miniforge-based python shell.
    python_exe = Path(sys.executable)

    if "miniforge" in str(python_exe).lower():
        # Navigates up until it finds the miniforge root.
        current = python_exe.parent
        while current != current.parent:  # Stops at root
            # If the 'envs' directory is found while ascending towards the root, returns the directory path to caller
            if current.name == "envs":
                return current

            # If the 'conda-meta' directory is found while ascending towards the root, this indicates that this is the
            # root of a mamba environment manager.
            if current.joinpath("conda-meta").exists():
                # In a mamba environment, the /envs folder will be found directly under the root
                envs_path = current.joinpath("envs")
                if envs_path.exists():
                    return envs_path

                # Otherwise, navigates up to find envs
                if current.parent.name == "envs":
                    return current.parent

            current = current.parent

    # Method 2: Tries to find mamba by locating mamba/conda executable (mamba uses CONDA_EXE).
    mamba_exe = os.environ.get("CONDA_EXE")
    if mamba_exe:
        envs_dir = Path(mamba_exe).parents[1].joinpath("envs")
        if envs_dir.exists():
            return envs_dir

    # Method 3: Checks the standard miniforge3 installation location.
    home = Path.home()

    # Standard miniforge3 location on Unix-like systems
    miniforge_envs = home.joinpath("miniforge3", "envs")
    if miniforge_envs.exists():
        return miniforge_envs

    # On Windows, also checks the AppData location
    if sys.platform == "win32":
        # First try: constructs the path from user's home directory
        windows_miniforge_envs = home.joinpath("AppData", "Local", "miniforge3", "envs")
        if windows_miniforge_envs.exists():
            return windows_miniforge_envs

        # Fallback: uses LOCALAPPDATA environment variable
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            windows_miniforge_envs = Path(local_appdata).joinpath("miniforge3", "envs")
            if windows_miniforge_envs.exists():
                return windows_miniforge_envs

    # If this point is reached, miniforge is not installed and/or initialized. Raises an error.
    message: str = (
        "Unable to resolve the path to the mamba environments directory. This version of ataraxis-automation expects "
        "that mamba is installed via miniforge3, following the deprecation of mambaforge. Make sure miniforge3 is "
        "installed and initialized before using ataraxis-automation cli. Install from: "
        "https://github.com/conda-forge/miniforge"
    )
    raise RuntimeError(format_message(message))


def _resolve_environment_files(project_root: Path, environment_base_name: str) -> tuple[str, Path, Path]:
    """Determines the Operating System of the host platform and uses it to generate the absolute paths to the
    os-specific mamba environment '.yml' and 'spec.txt' files.

    Notes:
        Currently, this command supports the following Operating Systems: macOS (ARM64: Darwin), Linux (AMD64), and
        Windows (AMD64).

    Args:
        project_root: The absolute path to the root directory of the processed project.
        environment_base_name: The name of the environment excluding the os_suffix, e.g.: 'axa_dev'.

    Returns:
        A tuple of three elements. The first element is the name of the environment with the os-suffix, suitable
        for local mamba commands. The second element is the absolute path to the os-specific environment's '.yml'
        file. The third element is the absolute path to the os-specific environment's 'spec.txt' file.

    Raises:
        RuntimeError: If the host OS does not match any of the supported operating systems.
    """
    os_name: str = sys.platform  # Obtains host os name

    # If the os name is not one of the supported names, raises an error
    if os_name not in _SUPPORTED_PLATFORMS:
        message: str = (
            f"Unable to resolve the operating-system-specific suffix to use for mamba environment file names. The "
            f"local machine is using an unsupported operating system '{os_name}'. Currently, only the following "
            f"operating systems are supported: {', '.join(_SUPPORTED_PLATFORMS.keys())}."
        )
        raise RuntimeError(format_message(message))

    # Resolves the absolute path to the 'envs' directory.
    envs_dir: Path = project_root.joinpath("envs")

    # Selects the environment name according to the host OS and constructs the path to the environment .yml and spec
    # files using the generated name.
    os_suffix = _SUPPORTED_PLATFORMS[os_name]
    env_name: str = f"{environment_base_name}{os_suffix}"
    yml_path: Path = envs_dir.joinpath(f"{env_name}.yml")
    spec_path: Path = envs_dir.joinpath(f"{env_name}_spec.txt")

    return env_name, yml_path, spec_path


def _check_package_engines() -> None:
    """Determines whether mamba and uv can be accessed from this script by silently calling 'COMMAND --version'.

    Raises:
        RuntimeError: If either mamba or uv is not accessible via subprocess call through the shell.
    """
    # Verifies that mamba is available for environment management operations
    try:
        subprocess.run(
            "mamba --version",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        # If mamba is not available, raises an error as it is now required
        message: str = (
            "Unable to interface with mamba for environment management. Mamba is required for this automation "
            "module and provides significantly faster conda operations. Install mamba (e.g., via miniforge3) and "
            "ensure it is initialized and added to PATH."
        )
        raise RuntimeError(format_message(message)) from None

    # Verifies that uv is available for package installation operations
    try:
        subprocess.run(
            "uv --version",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        # If uv is not available, raises an error as it is now required
        message = (
            "Unable to interface with uv for package installation. uv is required for this automation module and "
            "provides significantly faster pip operations. Install uv (e.g., 'pip install uv' or 'mamba install uv') "
            "in the active Python environment."
        )
        raise RuntimeError(format_message(message)) from None


@dataclass
class ProjectEnvironment:
    """Encapsulates the data used to interface with the project's mamba environment.

    This class resolves and stores executable commands used to manage the project environment and important metadata
    information used by these commands.

    Notes:
        This class should not be instantiated directly. Instead, use the `resolve_environment_commands()` class method
        to get an instance of this class.
    """

    activate_command: str
    """
    Stores the command used to activate the project's mamba environment.
    """
    deactivate_command: str
    """
    Stores the command used to deactivate any current environment and switch to the base environment.
    """
    create_command: str
    """
    Stores the command used to generate a minimally-configured mamba environment.
    """
    create_from_yml_command: str | None
    """
    Stores the command used to create a new mamba environment from an existing .yml file. If valid .yml files do not 
    exist inside the 'envs' project directory, this command is set to None.
    """
    remove_command: str
    """
    Stores the command used to remove (delete) the project's mamba environment.
    """
    install_dependencies_command: str
    """
    Stores the command used to install all project dependencies (runtime and development) into the project's mamba 
    environment using uv.
    """
    update_command: str | None
    """
    Stores the command used to update an already existing mamba environment using an existing .yml file. If the .yml 
    file for the environment does not exist inside the 'envs' project folder, this command is set to None.
    """
    export_yml_command: str
    """
    Stores the command used to export the project's mamba environment to a .yml file.
    """
    export_spec_command: str
    """
    Stores the command used to export the project's mamba environment to a spec.txt file with revision history.
    """
    install_project_command: str
    """
    Stores the command used to build and install the project as a library into the project's mamba environment.
    """
    uninstall_project_command: str
    """
    Stores the command used to uninstall the project library from the project's mamba environment.
    """
    environment_name: str
    """
    Stores the name of the project's mamba environment with the appended os-suffix. This name is used by all other 
    commands to target the project's environment.
    """
    environment_directory: Path
    """Stores the path to the project's mamba environment directory."""

    @classmethod
    def resolve_project_environment(
        cls,
        project_root: Path,
        environment_name: str,
        python_version: str = "3.13",
        environment_directory: Path | None = None,
    ) -> "ProjectEnvironment":
        """Generates the mamba and uv commands used to manipulate the project- and os-specific mamba
        environment and packages them into a ProjectEnvironment instance.

        Args:
            project_root: The absolute path to the root directory of the processed project.
            environment_name: The base-name of the project's mamba environment.
            python_version: The Python version to use as part of the new environment creation or provisioning runtimes.
            environment_directory: Optional. The absolute path to the directory used by the mamba / conda manager to
                store Python environments. This argument only needs to be provided if the automatic (default)
                environment resolution fails.

        Returns:
            The resolved ProjectEnvironment instance.
        """
        # Gets the environment name with the appropriate os-extension and the paths to the .yml and /spec files.
        extended_environment_name, yml_path, spec_path = _resolve_environment_files(project_root, environment_name)

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

        # Generates commands that depend on the host OS type. Relies on resolve_environment_files() method to err if the
        # host is running an unsupported OS, as the OS versions evaluated below are the same as used by
        # resolve_environment_files(). Also generates the list of platform-specific dependencies.

        # WINDOWS
        if "_win" in extended_environment_name:
            # .yml export
            export_yml_command = (
                f'mamba env export --name {extended_environment_name} --use-uv | findstr -v "prefix" > {yml_path}'
            )

            # Mamba environment activation and deactivation commands. Still uses 'conda' for activation due to more
            # streamlined behavior and no performance downsides.
            conda_init = "call conda.bat >NUL 2>&1"  # Redirects stdout and stderr to null to remove unnecessary text

        # LINUX
        elif "_lin" in extended_environment_name:
            # .yml export
            export_yml_command = (
                f"mamba env export --name {extended_environment_name} --use-uv | head -n -1 > {yml_path}"
            )

            # Conda environment activation command
            conda_init = ". $(conda info --base)/etc/profile.d/conda.sh"

        # OSx
        else:
            # .yml export
            export_yml_command = (
                f"mamba env export --name {extended_environment_name} --use-uv | tail -r | "
                f"tail -n +2 | tail -r > {yml_path}"
            )

            # Conda environment activation command.
            conda_init = ". $(conda info --base)/etc/profile.d/conda.sh"

        # Resolves activation and deactivation commands using the resolved 'conda_init' command.
        activate_command = f"{conda_init} && conda activate {target_environment_directory}"
        deactivate_command = f"{conda_init} && conda deactivate"

        # Generates the spec.txt export command, which is the same for all OS versions (unlike .yml export).
        export_spec_command = f"mamba list -n {extended_environment_name} --use-uv --explicit > {spec_path}"

        # Generates dependency installation commands using uv:
        install_dependencies_command = (
            f"uv pip install {' '.join(_resolve_dependencies(project_root))} --resolution highest "
            f"--refresh --compile-bytecode --python={target_environment_directory} --strict --exact"
        )
        uninstall_project_command = f"uv pip uninstall {project_name} --python={target_environment_directory}"
        install_project_command = (
            f"uv pip install . --resolution highest --refresh --reinstall-package {project_name} --compile-bytecode "
            f"--python={target_environment_directory} --strict"
        )

        # Generates mamba environment manipulation commands.
        # Creation (base) generates a minimal mamba environment. It is expected that mamba and uv dependencies are added
        # via separate dependency commands generated above. Note, installs the latest versions of tox, uv, and tox-uv
        # with the expectation that dependency installation commands use --reinstall to override the versions of these
        # packages as necessary.
        create_command: str = (
            f"mamba create -n {extended_environment_name} python={python_version} uv tox tox-uv --yes "
            f"--retry-clean-cache --pyc --use-uv"
        )
        remove_command: str = f"mamba remove -n {extended_environment_name} --all --yes"

        # Resolves .yml based commands. These commands are set to valid string-commands only if the .yml file for the
        # project's environment exists and to None otherwise.
        yml_create_command: str | None = None
        update_command: str | None = None
        if yml_path.exists():
            yml_create_command = f"mamba env create -f {yml_path} --yes --retry-clean-cache --pyc --use-uv"
            update_command = f"mamba env update -n {extended_environment_name} -f {yml_path}  --yes --prune --use-uv"

        return cls(
            activate_command=activate_command,
            deactivate_command=deactivate_command,
            export_yml_command=export_yml_command,
            export_spec_command=export_spec_command,
            create_command=create_command,
            create_from_yml_command=yml_create_command,
            remove_command=remove_command,
            install_dependencies_command=install_dependencies_command,
            update_command=update_command,
            environment_name=extended_environment_name,
            install_project_command=install_project_command,
            uninstall_project_command=uninstall_project_command,
            environment_directory=target_environment_directory,
        )

    def environment_exists(self) -> bool:
        """Returns True if the environment can be activated (exists) and False otherwise."""
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
            return False
        else:
            return True
