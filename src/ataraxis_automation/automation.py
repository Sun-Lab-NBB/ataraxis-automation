"""This module provides a command-line interface that automates certain project building and development steps by
calling appropriate sub-functions.

The functions exposed through this module are intended to be called through appropriate 'tox' pipelines and should not
be used directly. They are designed to work with Sun Lab 'tox' tasks and may require significant refactoring to work
with other tox configurations.
"""

import os
import re
import sys
import shutil
from typing import Any, Optional
from pathlib import Path
import textwrap
import subprocess
from dataclasses import dataclass
from configparser import ConfigParser

import yaml
import click
import tomli


def _format_message(message: str) -> str:
    """Formats input message strings to follow the general Ataraxis style.

    This function uses the same parameters as the default Console class implementation available through
    the ataraxis-base-utilities library. This function is used to decouple the ataraxis-automation library from
    the ataraxis-base-utilities library, removing the circular dependency introduced for these libraries in versions 2
    and 3 and allows mimicking the output of console.error() method.

    Args:
        message: The input message string to format.

    Returns:
        Formatted message string with appropriate line breaks.
    """
    return textwrap.fill(
        text=message,
        width=120,
        break_long_words=False,
        break_on_hyphens=False,
    )


def _colorize_message(message: str, color: str, format_message: bool = True) -> str:
    """Modifies the input string to include an ANSI color code and, if necessary, formats the message by wrapping it
    at 120 lines.

    This function uses the same parameters as the default Console class implementation available through
    the ataraxis-base-utilities library. This function is used to decouple the ataraxis-automation library from
    ataraxis-base-utilities and, together with click.echo, allows mimicking the output of console.echo() method.

    Args:
        message: The input message string to format and colorize.
        color: The ANSI color code to use for coloring the message.
        format_message: If True, the message will be formatted by wrapping it at 120 lines.

    Returns:
        Colorized and formatted (if requested) message string.
    """

    if format_message:
        message = _format_message(message)

    return click.style(message, fg=color)


@dataclass
class EnvironmentCommands:
    """Provides a convenient interface for storing conda environment commands.

    Specifically, after commands are resolved as part of resolve_environment_commands() function runtime, they are
    packaged into an instance of this class to be used by all upstream functions.
    """

    activate_command: str
    """
    The command used to activate conda environment. It includes conda initialization step prior to activating the 
    environment, as subprocess.run() does not respect user-defined shell configuration.
    """
    deactivate_command: str
    """
    The command to deactivate any current environment and switch to the base environment. This command is a 
    prerequisite for some operations, such as environment removal. It includes conda initialization step prior to 
    deactivating the environment.
    """
    create_command: str
    """
    The command used to generate a minimally-configured conda environment. This command is specifically designed 
    to have minimal footprint, only installing necessary components for other automation commands to work as expected.
    Currently, this includes: python, tox, pip and uv.
    """
    create_from_yml_command: Optional[str]
    """
    Same as create_command, but creates a new conda environment from an existing .yml file. If valid .yml file does 
    not exist inside /envs directory, this command is set to None.
    """
    remove_command: str
    """
    The command used to remove (delete) a conda environment.
    """
    conda_dependencies_command: Optional[str]
    """
    The command used to install all dependencies that can be installed from conda. It specifically works with 
    'conda' and 'condarun' lists in the pyproject.toml. If there are no conda-installable dependencies, this command 
    is set to None.
    """
    pip_dependencies_command: Optional[str]
    """
    The command used to install all dependencies that can be installed from pip. It specifically works with 
    'noconda' list and any runtime dependencies not covered by 'condarun'. If there are no pip-installable 
    dependencies, this command is set to None.
    """
    update_command: Optional[str]
    """
    The command used to update an already existing conda environment using an existing .yml file. If the .yml file for 
    the environment does not exist inside /envs folder, this command is set to None.
    """
    export_yml_command: str
    """
    The command used to export a conda environment to a .yml file.
    """
    export_spec_command: str
    """
    The command used to export ta conda environment to a spec.txt file with revision history.
    """
    environment_name: str
    """
    The name of the project-specific conda environment with the appended os-suffix. This name is used by all other 
    commands to specifically target the project environment.
    """
    install_project_command: str
    """
    The command that builds and installs the project as a library into a conda environment. For 'uv' engine, does not 
    use cache, as it interferes with reinstalling locally-modified projects.
    """
    uninstall_project_command: str
    """
    The command that uninstalls the project from a conda environment.
    """
    provision_command: str
    """
    The command that provisions a conda environment by uninstalling all packages, but keeping the environment. This 
    command is designed to be followed by pip- and conda- dependency installation commands to reinstall the 
    dependencies. Overall, this 'actualizes' the local environment to exactly match th pyproject.toml without altering
    any environment references.
    """
    environment_directory: Path
    """ The path to the directory that stores the target conda environment. This path is used to force uv to target the 
    desired conda environment and to ensure the environment directory is removed when the environment is deleted. 
    This avoids problems with certain OSes where removing and environment does not remove teh directory, which, in
    turn, interferes with environment re-creation."""


def resolve_project_directory() -> Path:
    """Gets the current working directory from the OS and verifies that it points to a valid python project.

    This function was introduced when automation moved to a separate package to decouple the behavior of this module's
    functions from the physical location of the module source code.

    Returns:
        The absolute path to the project root directory.

    Raises:
        RuntimeError: If the current working directory does not point to a valid Python project.
    """
    project_dir: str = os.getcwd()
    files_in_dir: list[str] = os.listdir(project_dir)
    if (
        "src" not in files_in_dir
        or "envs" not in files_in_dir
        or "pyproject.toml" not in files_in_dir
        or "tox.ini" not in files_in_dir
    ):
        # If the console is enabled, raises the error through the console. Otherwise, raises the error using standard
        # python exception functionality
        message: str = (
            f"Unable to confirm that ataraxis automation module has been called from the root directory of a valid "
            f"Python project. This function expects that the current working directory is set to the root directory of "
            f"the project, judged by the presence of '/src', '/envs', 'pyproject.toml' and 'tox.ini'. Current working "
            f"directory is set to {project_dir}, which does not contain at least one of the required files."
        )
        raise RuntimeError(_format_message(message))

    return Path(project_dir)


def resolve_library_root(project_root: Path) -> Path:
    """Determines the absolute path to the library root directory.

    Library root differs from project root. Library root is the root folder that will be included in the binary
    distribution of the project and is typically either the 'src' directory or the folder directly under 'src'.

    Notes:
        Since C-extension and pure-Python projects in Sun Lab use a slightly different layout, this function is
        used to resolve whether /src or /src/library is used as a library root. To do so, it uses a simple heuristic:
        library root is a directory at most one level below /src with __init__.py. There can only be one library root.

    Args:
        project_root: The absolute path to the root directory of the processed project.

    Returns:
        The absolute path to the root directory of the library.

    Raises:
        RuntimeError: If the valid root directory candidate cannot be found based on the determination heuristics.
    """
    # Resolves the target directory
    src_path: Path = project_root.joinpath("src")

    # If the __init__.py is found inside the /src directory, this indicates /src is the library root. This is typically
    # true for C-extension projects, but not for pure Python project.
    for path in src_path.iterdir():
        if path.match("__init__.py"):
            return src_path

    # If __init__.py is not found at the level of the src, this implies that the processed project is a pure python
    # project and, in this case, it is expected that there is a single library-directory under /src that is the
    # root.

    # Discovers all candidates for library root directory. Candidates are expected to be directories directly under
    # /src that also contain an __init__.py file. To optimize runtime, breaks the second loop as soon as a valid
    # candidate is found.
    candidates: set[Path] = set()
    for candidate_path in src_path.iterdir():
        if candidate_path.is_dir():
            for sub_path in candidate_path.iterdir():
                if sub_path.match("__init__.py"):
                    candidates.add(candidate_path)
                    break

    # The expectation is that there is exactly one candidate that fits the requirements. if this is not true, the
    # project structure is not well-configured and should not be processed.
    if len(candidates) != 1:
        message: str = (
            f"Unable to resolve the path to the library root directory from the project root path {project_root}. "
            f"Specifically, did not find an __init__.py inside the /src directory and found {len(candidates)} "
            f"sub-directories with __init__.py inside the /src directory. Make sure there is an __init__.py "
            f"inside /src or ONE of the sub-directories under /src."
        )
        raise RuntimeError(_format_message(message))

    # If (as expected), there is only one candidate, returns it as the library root
    return candidates.pop()


def resolve_environment_files(project_root: Path, environment_base_name: str) -> tuple[str, Path, Path]:
    """Determines the OS of the host platform and uses it to generate the absolute paths to os-specific conda
    environment '.yml' and 'spec.txt' files.

    Currently, this command explicitly supports only 3 OSes: OSx (ARM64, Darwin), Linux (AMD64) and Windows (AMD64).

    Args:
        project_root: The absolute path to the root directory of the processed project.
        environment_base_name: The name of the environment excluding the os_suffix, e.g.: 'axa_dev'. This function
            modifies this base name by appending the os-suffix matching the host platform OS and any necessary
            extensions to generate environment file names and paths.

    Returns:
        A tuple of three elements. The first element is the name of the environment with os-suffix, suitable
        for local conda commands. The second element is the absolute path to the os-specific conda environment '.yml'
        file. The third element is the absolute path to the os-specific environment conda 'spec.txt' file.

    Raises:
        RuntimeError: If the host OS does not match any of the supported operating systems.
    """
    # Stores supported platform names together with their suffixes
    supported_platforms: dict[str, str] = {
        "win32": "_win",
        "linux": "_lin",
        "darwin": "_osx",
    }
    os_name: str = sys.platform  # Obtains host os name

    # If the os name is not one of the supported names, issues an error
    if os_name not in supported_platforms.keys():
        message: str = (
            f"Unable to resolve the os-specific suffix to use for conda environment file(s). Unsupported host OS "
            f"detected: {os_name}. Currently, supported OS options are are: {', '.join(supported_platforms.keys())}."
        )
        raise RuntimeError(_format_message(message))

    # Resolves the absolute path to the 'envs' directory. The function that generates the project root path checks for
    # the presence of this directory as part of its runtime, so it is assumed that it always exists.
    envs_dir: Path = project_root.joinpath("envs")

    # Selects the environment name according to the host OS and constructs the path to the environment .yml and spec
    # files using the generated name.
    os_suffix = supported_platforms[os_name]
    env_name: str = f"{environment_base_name}{os_suffix}"
    yml_path: Path = envs_dir.joinpath(f"{env_name}.yml")
    spec_path: Path = envs_dir.joinpath(f"{env_name}_spec.txt")

    # Returns the absolute path to yml and spec files.
    return env_name, yml_path, spec_path


def resolve_conda_engine() -> str:
    """Determines whether mamba or conda can be accessed from this script by silently calling 'COMMAND --version'.

    If mamba is available, it is used over conda. This process optimizes conda-related operations
    (especially de novo environment creation) to use the fastest available engine.

    Returns:
        The string-name of the cmdlet to use for all conda (or mamba) related commands.

    Raises:
        RuntimeError: If neither conda nor mamba is accessible via subprocess call through the shell.
    """
    command: str
    commands: tuple[str, str] = ("mamba", "conda")
    for command in commands:
        try:
            subprocess.run(
                f"{command} --version",
                shell=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return command  # If the command above runs, returns the cmdlet name
        except subprocess.CalledProcessError:
            continue  # For failed commands, cycles to the next command in the cycle or to the general error below.

    # If this point in the runtime is reached, this means neither conda nor mamba is installed or accessible.
    message: str = (
        f"Unable to determine the conda / mamba engine to use for 'conda' commands. Specifically, unable "
        f"to interface with either conda or mamba. Is conda or supported equivalent installed, initialized "
        f"and added to Path?"
    )
    raise RuntimeError(_format_message(message))


def resolve_pip_engine() -> str:
    """Determines whether uv or pip can be accessed from this script by silently calling 'command --version'.

    If uv is available, it is used over pip. This process optimizes pip-related operations
    (especially package installation) to use the fastest available engine.

    Returns:
        The string-name of the cmdlet to use for all pip (or uv) related commands.

    Raises:
        RuntimeError: If neither pip nor uv is accessible via subprocess call through the shell.
    """
    command: str
    commands: tuple[str, str] = ("uv pip", "pip")
    for command in commands:
        try:
            subprocess.run(
                f"{command} --version",
                shell=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return command  # If the command above runs, returns the cmdlet name
        except subprocess.CalledProcessError:
            continue  # For failed command, cycles to the next command in the cycle or to the general error below.

    # If this point in the runtime is reached, this means neither conda nor mamba is installed or accessible.
    message: str = (
        f"Unable to determine the engine to use for pip commands. Specifically, was not able to interface with any of "
        f"the supported pip-engines. Is pip, uv or supported equivalent installed in the currently active "
        f"virtual / conda environment?"
    )
    raise RuntimeError(_format_message(message))


def get_base_name(dependency: str) -> str:
    """Extracts the base name of a dependency, removing versions and extras.

    This helper function is used by the main resolve_dependencies() function to match tox.ini dependencies with
    pyproject.toml dependencies.

    Args:
        dependency: The name of the dependency that can include [extras] and version data that needs to be
            stripped from the base name.

    Returns:
        The base name of the dependency.
    """
    return dependency.split("[")[0].split("==")[0].split(">=")[0].split("<=")[0].split("<")[0].split(">")[0].strip()


def add_dependency(
    dependency: str, dependencies_list: list[str], processed_dependencies: set[str]
) -> tuple[list[str], set[str]]:
    """Verifies that dependency base-name is not already added to the input list and, if not, adds it to list.

    Primarily, this method is used to ensure that duplicate dependencies are not stored inside the same
    pyproject.toml list (e.g.: conda and noconda).

    Args:
        dependency: The name of the evaluated dependency. Can contain extras and version, but these
            details will be stripped before the check.
        dependencies_list: The list (conda or pip) to add the dependency to if it passes verification.
        processed_dependencies: The set used to store already processed dependencies to filter duplicates.

    Returns:
        A tuple with two elements. The first element is the updated dependencies_list that includes the verified
        dependency name (with extras / version). The second element is the updated processed_dependencies set that
        includes the stripped name of the processed dependency.

    Raises:
        ValueError: If the extracted dependency is found in multiple major pyproject.toml dependency lists
            (conda, noconda, and condarun).
    """
    # Strips version and extras from dependencies to verify they are not duplicates
    stripped_dependency: str = get_base_name(dependency=dependency)
    if stripped_dependency in processed_dependencies:
        message: str = (
            f"Unable to resolve conda-installable and pip-installable project dependencies. Found a duplicate "
            f"dependency for '{dependency}', listed in pyproject.toml. A dependency should only "
            f"be found in one of the supported  pyproject.toml lists: conda, noconda or condarun."
        )
        raise ValueError(_format_message(message))

    # Wraps dependency in "" to properly handle version specifiers when dependencies are installed via mamba or pip.
    # Technically, this is only needed for 'special' version specifications that use < or > and similar notations. It
    # is assumed that most of the projects that use this library will be specifying dependencies using at least '>='
    # notation though.
    dependencies_list.append(f'"{dependency}"')
    processed_dependencies.add(stripped_dependency)

    return dependencies_list, processed_dependencies


def resolve_dependencies(project_root: Path) -> tuple[list[str], list[str]]:
    """Extracts dependencies from pyproject.toml, verifies that they cover all dependencies listed in tox.ini file and
    separates them into conda-installable and pip-installable lists.

    This function is used as a standard checkout step to ensure metadata integrity and to automate environment
    manipulations. Specifically, it is used to resolve dependencies that are then used to create / update existing
    project-specific conda environment(s).

    Args:
        project_root: The absolute path to the root directory of the processed project.

    Returns:
        A tuple containing two elements. The first element is a list of dependencies that can be installed with conda
        or pip. The second element is a list of dependencies only installable with pip (at least for some of the
        supported platforms).

    Raises:
        ValueError: If duplicate version-less dependencies are found in different pyproject optional dependency lists
            or if tox.ini contains dependencies (disregarding version and extras) not in pyproject.toml.
    """
    # Resolves the paths to the .toml and tox.ini files. The function that generates the project root path checks for
    # the presence of these files as part of its runtime, so it is assumed that they always exist.
    pyproject_path: Path = project_root.joinpath("pyproject.toml")
    tox_path: Path = project_root.joinpath("tox.ini")

    # Opens pyproject.toml and parses its contents
    with open(pyproject_path, "rb") as f:
        pyproject_data = tomli.load(f)

    # Extracts dependencies and optional-dependencies from the main 'project' metadata section.
    project_data: dict[str, Any] = pyproject_data.get("project", {})
    dependencies: list[str] = project_data.get("dependencies", [])
    optional_dependencies: dict[str, list[str]] = project_data.get("optional-dependencies", {})

    conda_dependencies: list[str] = []  # Stores conda and pip dependencies
    pip_dependencies: list[str] = []  # Stores pip-only dependencies
    processed_dependencies: set[str] = set()  # Keeps track of duplicates

    # Processes condarun and conda sections first. It is generally expected that these sections should never overlap
    # in terms of the listed dependencies. Adds all dependencies from this section to the conda_dependencies list.
    section: str
    dependency: str
    for section in ["condarun", "conda"]:
        if section in optional_dependencies:
            for dependency in optional_dependencies[section]:
                add_dependency(
                    dependency=dependency,
                    dependencies_list=conda_dependencies,
                    processed_dependencies=processed_dependencies,
                )

    # Processes project run dependencies. Adds extracted dependencies that are not already processed as part of the
    # 'condarun' list to the pip_dependencies list.
    for dependency in dependencies:
        # Adds dependency to the pip list if it has not been processed as part of conda dependencies
        if get_base_name(dependency=dependency) not in processed_dependencies:
            add_dependency(
                dependency=dependency,
                dependencies_list=pip_dependencies,
                processed_dependencies=processed_dependencies,
            )

    # Adds any missing noconda dependencies to the pip_dependencies list.
    if "noconda" in optional_dependencies:
        for dependency in optional_dependencies["noconda"]:
            add_dependency(
                dependency=dependency,
                dependencies_list=pip_dependencies,
                processed_dependencies=processed_dependencies,
            )

    # Ignores any other optional dependencies

    # Parses tox.ini and extract dependencies
    config: ConfigParser = ConfigParser()
    config.read(tox_path)
    tox_dependencies: set[str] = set()

    # Extracts dependencies from 'deps' and 'requires' sections inside tox.ini. This process strips conda version and
    # specialization, since duplicates with different versions are expected to be used by tox, but not pyproject.toml.
    for section in config.sections():
        if "deps" in config[section]:
            tox_dependencies.update(
                get_base_name(dependency) for dependency in config[section]["deps"].split("\n") if dependency
            )
        if "requires" in config[section]:
            tox_dependencies.update(
                get_base_name(dependency) for dependency in config[section]["requires"].split("\n") if dependency
            )

    # Checks if all tox.ini dependencies are in pyproject.toml. This only uses base name, so the only way to fail this
    # step would be to have a 'tox' dependency not listed in any of the evaluated pyproject.toml sections
    pyproject_dependencies = {get_base_name(dependency) for dependency in processed_dependencies}
    missing_dependencies = tox_dependencies - pyproject_dependencies

    # If any tox dependency is missing, raises a ValueError
    if missing_dependencies:
        message: str = (
            f"Unable to resolve conda-installable and pip-installable project dependencies. The following "
            f"dependencies in tox.ini are not found in pyproject.toml: {', '.join(missing_dependencies)}. Add them to "
            f"one of the pyproject.toml dependency lists: condarun, conda or noconda."
        )
        raise ValueError(_format_message(message))

    return conda_dependencies, pip_dependencies


def resolve_project_name(project_root: Path) -> str:
    """Extracts the project name from the pyproject.toml file.

    This function reads the pyproject.toml file and extracts the project name from the [project] section. The project
    name is useful for some operations, such as uninstalling or reinstalling the project into a conda environment.

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
        with open(pyproject_path, "rb") as f:
            pyproject_data: dict[str, Any] = tomli.load(f)
    except tomli.TOMLDecodeError as e:
        message: str = (
            f"Unable to parse the pyproject.toml file. The file may be corrupted or contain invalid TOML syntax. "
            f"Error details: {e}."
        )
        raise ValueError(_format_message(message))

    # Extracts the project name from the [project] section
    project_data: dict[str, Any] = pyproject_data.get("project", {})
    project_name: Optional[str] = project_data.get("name")

    # Checks if the project name was successfully extracted
    if not project_name:
        message = (
            f"Unable to resolve the project name from the pyproject.toml file. The 'name' field is missing or empty in "
            f"the [project] section of the file. Ensure that the project name is correctly defined."
        )
        raise ValueError(_format_message(message))

    elif project_name is not None:
        return project_name


def generate_typed_marker(library_root: Path) -> None:
    """Crawls the library directory tree and ensures py.typed marker exists only at the root level of the directory.

    Specifically, if the 'py.typed' is not found in the root directory, adds the marker file. If it is found in any
    subdirectory, removes the marker file.

    Notes:
        The marker file has to be present in-addition to the '.pyi' typing files to notify type-checkers, like mypy,
        that the library contains type-annotations. This is necessary to allow other projects using type-checkers to
        verify this library API is accessed correctly.

    Args:
        library_root: The path to the root level of the library directory.
    """
    # Adds py.typed to the root directory if it doesn't exist
    root_py_typed = library_root / "py.typed"
    if not root_py_typed.exists():
        root_py_typed.touch()
        message: str = f"Added py.typed marker to library root ({library_root})."
        click.echo(_colorize_message(message, color="white"), color=True)

    # Removes py.typed from all subdirectories
    for path in library_root.rglob("py.typed"):
        if path != root_py_typed:
            path.unlink()
            message = f"Removed no longer needed py.typed marker file {path}."
            click.echo(_colorize_message(message, color="white"), color=True)


def move_stubs(stubs_dir: Path, library_root: Path) -> None:
    """Moves typing stubs from the 'stubs' directory to appropriate level(s) of the library directory tree.

    This function should be called after running stubgen on the built library package. It distributes the stubs
    generated by stubgen to their final destinations.

    Notes:
        This function expects that the 'stubs' directory has exactly one subdirectory, which contains an __init__.pyi
        file. This subdirectory is considered to be the library root in the stubs' structure.

    Args:
        stubs_dir: The absolute path to the "stubs" directory, expected to be found under the project root directory.
        library_root: The absolute path to the library root directory.
    """
    # Verifies the stubs' directory structure and finds the library name. To do so, first generates a set of all
    # subdirectories under /stubs that also have an __init__.pyi file.
    valid_sub_dirs: set[Path] = {
        sub_dir for sub_dir in stubs_dir.iterdir() if sub_dir.is_dir() and (sub_dir / "__init__.pyi").exists()
    }

    # Expects that the process above yields a single output directory. Otherwise, raises a RuntimeError.
    if len(valid_sub_dirs) != 1:
        message: str = (
            f"Unable to move the generated stub files to appropriate levels of the library directory. Expected exactly "
            f"one subdirectory with __init__.pyi in '{stubs_dir}', but found {len(valid_sub_dirs)}."
        )
        raise RuntimeError(_format_message(message))

    # Gets the single valid directory and uses it as the source for .piy files.
    src_dir: Path = valid_sub_dirs.pop()

    # Moves .pyi files from source to destination. Assumes that the structure of the src_dir exactly matches the
    # structure of the library_root.
    stub_path: Path
    for stub_path in src_dir.rglob("*.pyi"):
        relative_path: Path = stub_path.relative_to(src_dir)
        dst_path: Path = library_root.joinpath(relative_path)

        # Ensures the destination directory exists
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        # Removes the old .pyi file if it already exists
        if dst_path.exists():
            dst_path.unlink()

        # Moves the stub to its destination directory
        shutil.move(str(stub_path), str(dst_path))

        message = f"Moved stub file from /stubs to /src: {dst_path.name}."
        click.echo(_colorize_message(message, color="white"), color=True)

    # This loop is designed to solve an OSX-unique issue, where this function produces multiple copies that
    # have space+copy_number appended to each file name, rather than a single copy of the .pyi file.

    # Groups files by their base name (without a space number)
    # To do so, first generates a dictionary that groups file paths that use the same file base name. Does this within
    # each library directory to avoid false-positive tagging of __init__ files across directories as global duplicates.
    file_groups: dict[Path, dict[str, list[Path]]] = {}
    for pyi_file in library_root.rglob("*.pyi"):
        dir_path = pyi_file.parent
        base_name = re.sub(r" \d+\.pyi$", ".pyi", pyi_file.name)
        file_groups.setdefault(dir_path, {}).setdefault(base_name, []).append(pyi_file)

    # For each group, keeps only the file with the highest copy_number and renames it to remove space+copy_number after
    # removing all extra copies.
    for dir_path, dir_groups in file_groups.items():
        for base_name, group in dir_groups.items():
            if len(group) > 1:
                # Sorts files by copy number, in descending order
                sorted_files = sorted(
                    group,
                    key=lambda x: (
                        int(re.findall(r" (\d+)\.pyi$", x.name)[0]) if re.findall(r" (\d+)\.pyi$", x.name) else 0
                    ),
                    reverse=True,
                )

                # Keeps the first file (highest copy number), rename it, and remove the rest
                kept_file = sorted_files[0]
                new_file_path = kept_file.with_name(base_name)

                # Removes duplicate files
                for file_to_remove in sorted_files[1:]:
                    file_to_remove.unlink()
                    message = f"Removed duplicate .pyi file in {dir_path}: {file_to_remove.name}."
                    click.echo(_colorize_message(message, color="white"), color=True)

                # Renames the kept file to remove the copy number
                kept_file.rename(new_file_path)
                message = f"Renamed stub file in {dir_path}: {kept_file.name} -> {base_name}."
                click.echo(_colorize_message(message, color="white"), color=True)

            # If there's only one file, renames it if it has a copy number
            elif len(group) == 1 and group[0].name != base_name:
                file = group[0]
                new_path = file.with_name(base_name)
                file.rename(new_path)
                message = f"Renamed stub file in {dir_path}: {file.name} -> {base_name}."
                click.echo(_colorize_message(message, color="white"), color=True)


def delete_stubs(library_root: Path) -> None:
    """Removes all .pyi stub files from the library root directory and its subdirectories.

    This function is intended to be used before running the linting task, as mypy tends to be biased to analyze the
    .pyi files, ignoring the source code. When .pyi files are not present, mypy reverts to properly analyzing the
    source code.

    Args:
        library_root: The absolute path to the library root directory.
    """
    # Iterates over all .pyi files in the directory tree
    pyi_file: Path
    for pyi_file in library_root.rglob("*.pyi"):
        # Removes the .pyi files
        pyi_file.unlink()
        message: str = f"Removed stub file: {pyi_file.name}."
        click.echo(_colorize_message(message, color="white"), color=True)


def verify_pypirc(file_path: Path) -> bool:
    """Verifies that the .pypirc file located at the input path contains valid options to support automatic
    authentication for pip uploads.

    Assumes that the file is used only to store the API token to upload compiled packages to pip. Does not verify any
    other information.

    Returns:
        True if the .pypirc is well-configured and False otherwise.
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


def rename_all_envs(project_root: Path, new_name: str) -> None:
    """Loops over the contents of the /envs directory and replaces base environment names with the input name.

    Also updates the 'name' filed of the .yml files before renaming the files. This function is mainly designed to be
    used during template project adoption. However, it also can be used as part of tox-task to rename all
    environments in the folder (for example, when changing the environment naming pattern for the whole project).

    Notes:
        This method does not rename any existing conda environments. Manually rename any existing environments as
        needed for your project.

    Args:
        project_root: The absolute path to the root directory of the processed project.
        new_name: The new base-name to use for all environment files.
    """
    # Gets the path to the /envs directory. Since the function that generates the project_root path checks for the
    # presence of the /envs directory, this function assumes it exists.
    envs_dir: Path = project_root.joinpath("envs")

    # Loops over every file inside /envs directory
    file_path: Path
    for file_path in envs_dir.iterdir():
        file_name: str = file_path.name  # Gets the base name of the file

        # If the file has a .yml extension, renames the file and changes the value of the 'name' filed inside the
        # file.
        if file_path.suffix == ".yml" and ("_lin" in file_name or "_win" in file_name or "_osx" in file_name):
            last_underscore_index: int = file_name.rfind("_")

            os_suffix_and_ext: str = file_name[last_underscore_index:]
            new_file_name: str = f"{new_name}{os_suffix_and_ext}"
            new_file_path: Path = file_path.with_name(new_file_name)

            # Reads and updates the YAML file 'name' field
            yaml_data: dict[str, Any] = yaml.safe_load(file_path.read_text())

            if "name" in yaml_data:
                yaml_data["name"] = new_file_name[:-4]  # Removes the '.yml' extension

            # Writes the updated YAML data to the new file
            new_file_path.write_text(yaml.safe_dump(yaml_data, sort_keys=False))

            # Removes the old file
            file_path.unlink()

            message: str = f"Renamed environment .yml file: {file_name} -> {new_file_name}."
            click.echo(_colorize_message(message, color="white"), color=True)

        # if the file is a _spec.txt file, just renames the file. Spec files to not include environment names.
        elif file_name.endswith("_spec.txt") and ("_lin" in file_name or "_win" in file_name or "_osx" in file_name):
            last_underscore_index = file_name.rfind("_", 0, file_name.rfind("_spec.txt"))

            os_suffix_and_ext = file_name[last_underscore_index:]
            new_file_name = f"{new_name}{os_suffix_and_ext}"
            new_file_path = file_path.with_name(new_file_name)

            # Renames the file
            file_path.rename(new_file_path)

            message = f"Renamed environment spec.txt file: {file_name} -> {new_file_name}."
            click.echo(_colorize_message(message, color="white"), color=True)

        else:
            # Skips files that don't match either pattern
            continue


def replace_markers_in_file(file_path: Path, markers: dict[str, str]) -> int:
    """Replaces all occurrences of every input marker in the contents of the provided file with the appropriate
    replacement value.

    This method opens the file and scans through file contents searching for any 'markers' dictionary keys. If keys
    are found, they are replaced with the corresponding value from the dictionary. This is used to replace the
    placeholder values used in template projects with user-defined values during project adoption.

    Args:
        file_path: The path to file in which to replace the markers.
        markers: The shallow dictionary that contains markers to replace as keys and replacement values as values.

    Returns:
        The number of placeholder values modified during this method's runtime. Minimum number is 0 for no
        modifications.
    """
    # Reads the file contents using utf-8 decoding.
    content: str = file_path.read_text(encoding="utf-8")

    # Loops over markers and replaces any occurrence of any marker inside the file contents with the corresponding
    # replacement value.
    modification_count: int = 0
    for marker, value in markers.items():
        if marker in content:
            content = content.replace(marker, value)
            modification_count += 1

    # If any markers were modified, writes the modified contents back to file and notifies the user that the file has
    # been modified.
    if modification_count != 0:
        file_path.write_text(content, encoding="utf-8")
        message: str = f"Replaced markers in {file_path}."
        click.echo(_colorize_message(message, color="white"), color=True)

    # Returns the total number of modifications (0 if no modifications were made)
    return modification_count


def validate_library_name(_ctx: click.Context, _param: click.Parameter, value: str) -> str:
    """Verifies that the input library name contains only letters, numbers, and underscores.

    Args:
        _ctx: Not used. Provided by click automatically.
        _param: Not used. Provided by click automatically.
        value: The string-value to check

    Raises:
        BadParameter: If the input value contains invalid characters.
    """
    if not re.match(r"^[a-zA-Z0-9_]*$", value):
        message: str = "Library name should contain only letters, numbers, and underscores."
        raise click.BadParameter(_format_message(message))
    return value


def validate_project_name(_ctx: click.Context, _param: click.Parameter, value: str) -> str:
    """Verifies that the input project name contains only letters, numbers, and dashes.

    Args:
        _ctx: Not used. Provided by click automatically.
        _param: Not used. Provided by click automatically.
        value: The string-value to check

    Raises:
        BadParameter: If the input value contains invalid characters.
    """
    if not re.match(r"^[a-zA-Z0-9-]+$", value):
        message: str = _format_message("Project name should contain only letters, numbers, or dashes.")
        raise click.BadParameter(message)
    return value


def validate_author_name(_ctx: click.Context, _param: click.Parameter, value: str) -> str:
    """Verifies that the input author name contains a valid human name and an optional GitHub username in parentheses.

    Args:
        _ctx: Not used. Provided by click automatically.
        _param: Not used. Provided by click automatically.
        value: The string-value to check

    Raises:
        BadParameter: If the input value does not match the expected format.
    """
    pattern = r"^([a-zA-Z\s\-']+)(\s*\([a-zA-Z0-9\-]+\))?$"
    if not re.match(pattern, value):
        message: str = _format_message(
            f"Author name should be in the format 'Human Name' or 'Human Name (GitHubUsername)'. "
            f"The name can contain letters, spaces, hyphens, and apostrophes. The GitHub username "
            f"(if provided) should be in parentheses and can contain letters, numbers, and hyphens."
        )
        raise click.BadParameter(message)
    return value


def validate_email(_ctx: click.Context, _param: click.Parameter, value: str) -> str:
    """Verifies that the input email address contains only valid characters.

    Args:
        _ctx: Not used. Provided by click automatically.
        _param: Not used. Provided by click automatically.
        value: The string-value to check

    Raises:
        BadParameter: If the input value contains invalid characters.
    """
    if not re.match(r"^[\w.-]+@[\w.-]+\.\w+$", value):
        message: str = _format_message("Invalid email address.")
        raise click.BadParameter(message)

    return value


def validate_env_name(_ctx: click.Context, _param: click.Parameter, value: str) -> str:
    """Verifies that the input environment name contains only letters, numbers, and underscores.

    Args:
        _ctx: Not used. Provided by click automatically.
        _param: Not used. Provided by click automatically.
        value: The string-value to check

    Raises:
        BadParameter: If the input value contains invalid characters.
    """
    if not re.match(r"^[a-zA-Z0-9_]*$", value):
        message: str = _format_message("Environment name should contain only letters, numbers, and underscores.")
        raise click.BadParameter(message)
    return value


def resolve_conda_environments_directory() -> Path:
    """Returns the path to the conda / mamba environments directory.

    Raises:
        RuntimeError: If conda is not installed and / or not initialized.
    """
    conda_prefix = os.environ.get("CONDA_PREFIX")

    # The call above will not resolve Conda environment when this method runs in a tox environment, which is the
    # intended runtime scenario. Therefore, attempts to find the conda environments directory manually if the prefix is
    # None.
    if not conda_prefix:
        # Method 1: Checks whether this script is executed from a conda-based python.
        python_exe = Path(sys.executable)

        # This assumes that conda is provided by one of the major managers: miniforge, mambaforge or conda.
        if any(name in str(python_exe).lower() for name in ("conda", "miniforge", "mambaforge")):
            # Navigates up until it finds the conda root.
            current = python_exe.parent
            while current.parent != current:  # Stops at root
                if (current / "conda-meta").exists():
                    # Found conda root. Then, the /envs folder will be found directly under root
                    return current / "envs"

                if current.name == "envs":
                    # Found envs directory directly
                    return current

                current = current.parent

        # Method 2: Tries to find conda by locating conda executable. This would work if conda executable is in PATH.
        conda_exe = os.environ.get("CONDA_EXE")
        if conda_exe:
            conda_root = Path(conda_exe).parent.parent
            envs_dir = conda_root / "envs"
            if envs_dir.exists():
                return envs_dir

        # Method 3: Checks common installation locations for the presence of conda manager and environments. This is
        # pretty evil and will fail if multiple managers are installed at the same time. It is written in a way to
        # prefer miniforge though.
        possible_locations = [
            Path.home() / "miniforge3" / "envs",
            Path.home() / "mambaforge" / "envs",
            Path.home() / "miniconda3" / "envs",
            Path.home() / "anaconda3" / "envs",
        ]

        # On Windows, also checks the AppData location
        if sys.platform == "win32":
            possible_locations.extend(
                [
                    Path(os.environ.get("LOCALAPPDATA", "")) / "miniforge3" / "envs",
                    Path(os.environ.get("LOCALAPPDATA", "")) / "mambaforge" / "envs",
                    Path(os.environ.get("LOCALAPPDATA", "")) / "miniconda3" / "envs",
                    Path(os.environ.get("LOCALAPPDATA", "")) / "anaconda3" / "envs",
                ]
            )

        for location in possible_locations:
            if location.exists():
                return location

    # If conda is not installed and (or) initialized, conda prefix will be None.
    if not conda_prefix:
        message: str = (
            f"Unable to resolve the path to the conda / mamba environments directory. Usually, this error is seen "
            f"when conda is not activated or installed. Make sure conda is installed and initialized before "
            f"using ataraxis-automation cli."
        )
        raise RuntimeError(_format_message(message))

    # If the 'base' environment is active, the prefix points to the root conda manager folder and needs to be
    # extended with 'envs'.
    if os.environ.get("CONDA_DEFAULT_ENV") == "base":
        return Path(os.path.join(conda_prefix, "envs"))

    # Otherwise, for named environments, the root /envs directory is one level below the named directory:
    # e.g., /path/to/conda/envs/myenv -> /path/to/conda/envs
    return Path(os.path.dirname(os.path.dirname(conda_prefix)))


def resolve_environment_commands(
    project_root: Path, environment_name: str, python_version: str = "3.13"
) -> EnvironmentCommands:
    """Generates the list of conda and pip commands used to manipulate the project- and os-specific conda environment
    and packages it into EnvironmentCommands class.

    This function is a prerequisite for all environment-related cli commands, as it is used to resolve and generate
    all necessary commands in a project-, os- and engine(backend)-specific fashion.

    Args:
        project_root: The absolute path to the root directory of the processed project.
        environment_name: The base-name of the (project) conda environment.
        python_version: The Python version to use as part of the new environment creation process. This is also
            used during environment provisioning to modify the python version in the environment.

    Returns:
        EnvironmentCommands class instance that includes all resolved commands as class attributes.
    """
    # Gets the environment name with the appropriate os-extension and the paths to the .yml and /spec files.
    extended_environment_name: str
    yml_path: Path
    spec_path: Path
    extended_environment_name, yml_path, spec_path = resolve_environment_files(project_root, environment_name)

    # Gets the name of the project from the pyproject.toml file.
    project_name: str = resolve_project_name(project_root=project_root)

    # Gets the list of conda-installable and pip-installable dependencies using 'dependencies', 'conda', 'condarun'
    # and 'noconda' lists from pyproject.toml
    conda_list, pip_list = resolve_dependencies(project_root)

    # Determines the cmdlets to use for conda and pip operations.
    conda_command: str = resolve_conda_engine()
    pip_command: str = resolve_pip_engine()

    # Resolves the physical path to the target conda environment directory.
    environment_directory = resolve_conda_environments_directory()
    target_environment_directory = environment_directory.joinpath(extended_environment_name)

    # Generates commands that depend on the host OS type. Relies on resolve_environment_files() method to err if the
    # host is running an unsupported OS, as the OS versions evaluated below are the same as used by
    # resolve_environment_files().
    export_yml_command: str = ""
    activate_command: str = ""
    deactivate_command: str = ""
    # WINDOWS
    if "_win" in extended_environment_name:
        # .yml export
        export_yml_command = (
            f'{conda_command} env export --name {extended_environment_name} | findstr -v "prefix" > {yml_path}'
        )

        # Conda environment activation and deactivation commands
        conda_init = "call conda.bat >NUL 2>&1"  # Redirects stdout and stderr to null to remove unnecessary text
        activate_command = f"{conda_init} && conda activate {target_environment_directory}"
        deactivate_command = f"{conda_init} && conda deactivate"
    elif "_lin" in extended_environment_name:
        # .yml export
        export_yml_command = f"{conda_command} env export --name {extended_environment_name} | head -n -1 > {yml_path}"

        # Conda environment activation command
        conda_init = ". $(conda info --base)/etc/profile.d/conda.sh"
        activate_command = f"{conda_init} && conda activate {target_environment_directory}"
        deactivate_command = f"{conda_init} && conda deactivate"
    elif "_osx" in extended_environment_name:
        # .yml export
        export_yml_command = (
            f"{conda_command} env export --name {extended_environment_name} | tail -r | "
            f"tail -n +2 | tail -r > {yml_path}"
        )

        # Conda environment activation command.
        conda_init = ". $(conda info --base)/etc/profile.d/conda.sh"
        activate_command = f"{conda_init} && conda activate {target_environment_directory}"
        deactivate_command = f"{conda_init} && conda deactivate"

    # Generates the spec.txt export command, which is the same for all OS versions (unlike .yml export)
    export_spec_command: str = f"{conda_command} list -n {extended_environment_name} --explicit -r > {spec_path}"

    # Generates dependency installation commands. These are used during de-novo environment creation. If a particular
    # kind of dependencies is not used (there are no conda or pip dependencies to install), the command is set to None.
    conda_dependencies_command: Optional[str]
    if len(conda_list) == 0:
        conda_dependencies_command = None
    else:
        conda_dependencies_command = (
            f"{conda_command} install -n {extended_environment_name} {' '.join(conda_list)} --yes"
        )

    pip_dependencies_command: Optional[str]
    if len(pip_list) == 0:
        pip_dependencies_command = None
    else:
        pip_dependencies_command = f"{pip_command} install {' '.join(pip_list)}"

    # Generates commands to install and uninstall the project (library) from the conda environment. This is
    # primarily used together with tox to ensure tox-dependent installation does not clash with existing project
    # installation during development.
    pip_uninstall_command: str = f"{pip_command} uninstall {project_name}"
    pip_reinstall_command: str = f"{pip_command} install ."

    # Modifies some pip commands with additional, engine-specific flags. This is needed because pip and uv pip (the two
    # supported engines) use slightly different flags for certain commands.
    if "uv" in pip_command:
        # Forces the command to run in the target conda environment instead of the virtual environment created by tox
        pip_uninstall_command += f" --python={target_environment_directory}"

        # Refreshes cache to ensure latest compatible versions are installed, compiles to bytecode and forces uv to
        # use conda environment
        pip_reinstall_command += (
            f" --resolution highest --refresh --compile-bytecode --python={target_environment_directory} --strict"
        )

        if pip_dependencies_command is not None:
            # Forces compilation and forces uv to use conda environment
            pip_dependencies_command += (
                f" --resolution highest --refresh --compile-bytecode --python={target_environment_directory} --strict"
            )
    else:
        # Suppresses confirmation dialogs
        pip_uninstall_command += f" --yes"
        # Compiles to bytecode
        pip_reinstall_command += f" --compile"
        if pip_dependencies_command is not None:
            pip_dependencies_command += f" --compile"  # Forces compilation

    # Generates conda environment manipulation commands.
    # Creation (base) generates a minimal conda environment. It is expected that conda and pip dependencies are added
    # via separate dependency commands generated above. Note, installs the latest versions of tox, uv and pip with the
    # expectation that dependency installation command use --reinstall to override the versions of these packages as
    # necessary.
    create_command: str = (
        f"{conda_command} create -n {extended_environment_name} python={python_version} pip tox uv --yes"
    )

    remove_command: str = f"{conda_command} remove -n {extended_environment_name} --all --yes"

    # A special command that removes all packages and then re-installs base dependencies to 'reset' the environment to
    # the state described in pyproject.toml file. Note, this HAS to use conda, as mamba does not respect --keep-env
    # at the time of writing. Luckily, there is a minimum performance impact.
    provision_command: str = (
        f"conda remove -n {extended_environment_name} --keep-env --all --yes "
        f"&& {conda_command} install -n {extended_environment_name} python={python_version} tox uv pip --yes"
    )

    # Resolves .yml based commands. These commands are set to valid string-commands if .yml file exists and to None
    # otherwise (as they do require a valid .yml file).
    yml_create_command: Optional[str]
    update_command: Optional[str]
    if yml_path.exists():
        yml_create_command = f"{conda_command} env create -f {yml_path} --yes"
        update_command = f"{conda_command} env update -n {extended_environment_name} -f {yml_path} --prune"
    else:
        yml_create_command = None
        update_command = None

    command_class: EnvironmentCommands = EnvironmentCommands(
        activate_command=activate_command,
        deactivate_command=deactivate_command,
        export_yml_command=export_yml_command,
        export_spec_command=export_spec_command,
        create_command=create_command,
        create_from_yml_command=yml_create_command,
        remove_command=remove_command,
        conda_dependencies_command=conda_dependencies_command,
        pip_dependencies_command=pip_dependencies_command,
        update_command=update_command,
        environment_name=extended_environment_name,
        install_project_command=pip_reinstall_command,
        uninstall_project_command=pip_uninstall_command,
        provision_command=provision_command,
        environment_directory=target_environment_directory,
    )
    return command_class


def environment_exists(commands: EnvironmentCommands) -> bool:
    """Checks whether the project-specific conda environment can be activated.

    This function is used by most environment-related cli commands to ensure the project-specific environment exists.
    In turn, knowing whether an environment exists is used to inform the behavior of multiple other functions, such
    as those used to carry out environment creation or removal.

    Args:
        commands: The EnvironmentCommands class instance that stores project-specific conda environment commands. The
            instance is configured by the resolve_environment_commands() function.

    Returns:
        True if the environment can be activated (and, implicitly, exists) and False if it cannot be activated.
    """

    # Verifies that the project- and os-specific conda environment can be activated.
    try:
        subprocess.run(
            commands.activate_command,
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


@click.group()
def cli() -> None:  # pragma: no cover
    """This command-line interface exposes helper commands used to automate various project development and building
    steps."""


@cli.command()
def process_typed_markers() -> None:  # pragma: no cover
    """Crawls the library root directory and ensures that the 'py.typed' marker is found only at the highest level of
    the library hierarchy (the highest directory with __init__.py in it).

    This command is intended to be called as part of the stub-generation tox command ('tox -e stubs').

    Raises:
        RuntimeError: If root (highest) directory cannot be resolved for the project or library source code.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Resolves (finds) the root directory of the library.
    library_root: Path = resolve_library_root(project_root=project_root)

    # Resolves typed markers.
    generate_typed_marker(library_root=library_root)
    message: str = "Typed (py.typed) marker(s) successfully processed."
    click.echo(_colorize_message(message, color="green"))


@cli.command()
def process_stubs() -> None:  # pragma: no cover
    """Distributes the stub files from the /stubs directory to the appropriate level of the /src or
    src/library directory (depending on the type of the processed project).

    Notes:
        This command is intended to be called after the /stubs directory has been generated using tox stub-generation
        command ('tox -e stubs').

    Raises:
        RuntimeError: If root (highest) directory cannot be resolved for the project or library source code. If
        /stubs directory does not exist.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Resolves (finds) the root directory of the library.
    library_root: Path = resolve_library_root(project_root=project_root)

    # Generates the path to the 'stubs' folder, which is expected to be a subdirectory of the project root directory.
    stubs_path: Path = project_root.joinpath("stubs")

    if not stubs_path.exists():
        message: str = (
            f"Unable to move generated stub files from {stubs_path} to {library_root}. Stubs directory does not exist."
        )
        raise RuntimeError(_format_message(message))

    # Moves the stubs to the appropriate source code directories
    move_stubs(stubs_dir=stubs_path, library_root=library_root)
    shutil.rmtree(stubs_path)  # Removes the /stubs directory once all stubs are moved
    message = "Stubs successfully distributed to appropriate source directories."
    click.echo(_colorize_message(message, color="green"))


@cli.command()
def purge_stubs() -> None:  # pragma: no cover
    """Removes all existing stub (.pyi) files from the library source code directory.

    This command is intended to be called as part of the tox linting task ('tox -e lint'). If stub files are present
    during linting, mypy (type-checker) preferentially processes stub files and ignores source code files. Removing the
    stubs before running mypy ensures it runs on the source code.

    Raises:
        RuntimeError: If root (highest) directory cannot be resolved for the project or library source code.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_dir: Path = resolve_project_directory()

    # Resolves (finds) the root directory of the library.
    library_root: Path = resolve_library_root(project_root=project_dir)

    # Removes all stub files from the library source code folder.
    delete_stubs(library_root=library_root)
    message: str = "Existing stub files purged."
    click.echo(_colorize_message(message, color="green"))


@cli.command()
def generate_recipe_folder() -> None:  # pragma: no cover
    """Generates the /recipe directory inside project root directory.

    This command is intended to be called before using Grayskull via the tox recipe-generation task ('tox -e recipe')
    to generate the conda-forge recipe for the project. Since Grayskull does not generate output directories by itself,
    this task is 'outsourced' to this command instead.

    Raises:
        RuntimeError: If root (highest) directory cannot be resolved for the project.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Generates the path to the 'recipe' directory. This directory is created inside the project root directory
    recipe_path: Path = project_root.joinpath("recipe")

    # If recipe directory already exists, removes the directory with all existing contents
    if recipe_path.exists():
        shutil.rmtree(recipe_path)
        message: str = "Existing recipe folder removed."
        click.echo(_colorize_message(message, color="white"))

    # Creates the recipe directory
    os.makedirs(recipe_path)
    message = "Recipe folder created."
    click.echo(_colorize_message(message, color="green"))


@cli.command()
@click.option(
    "-rt",
    "--replace-token",
    is_flag=True,
    help="If provided, recreates the .pypirc file even if it already contains an API token.",
)
def acquire_pypi_token(replace_token: bool) -> None:  # pragma: no cover
    """Ensures that a validly formatted PyPI API token is available from the .pypirc file stored in the root directory
    of the project.

    This command is intended to be called before the tox pip-uploading task ('tox -e upload') to ensure that twine is
    able to access the PyPI API token. If the token is available from the '.pypirc' file and appears valid, it is used.
    If the file or the API token is not available or the user provides 'replace-token' flag, the command recreates the
    file and prompts the user to provide a new token. The token is then added to the file for future (re)uses.

    Notes:
        The '.pypirc' file is added to gitignore, so the token will remain private unless gitignore is compromised.

        This function is currently not able to verify that the token works. Instead, it can only ensure the token
        is formatted in a PyPI-specified way (specifically, that it includes the pypi-prefix). If the token is not
        active or otherwise invalid, only a failed twine upload will be able to determine that.

    Raises:
        ValueError: If the token provided by the user is not valid.
        RuntimeError: If the user aborts the token acquisition process without providing a valid token.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Generates the path to the .pypirc file. The file is expected to be found inside the root directory of the project.
    pypirc_path: Path = project_root.joinpath(".pypirc")

    # If file exists, recreating the file is not requested and the file appears well-formed, ends the runtime.
    if verify_pypirc(pypirc_path) and not replace_token:
        message: str = f"Existing PyPI token found inside the '.pypirc' file."
        click.echo(_colorize_message(message, color="green"))
        return

    # Otherwise, proceeds to generating a new file and token entry.
    else:
        message = (
            f"Unable to use the existing PyPI token: '.pypirc' file does not exist, is invalid or doesn't contain a "
            f"valid token. Proceeding to new token acquisition."
        )
        click.echo(_colorize_message(message, color="white"))

    # Enters the while loop to iteratively ask for the token until a valid token entry is provided.
    while True:
        try:
            prompt: str = _format_message(
                message="Enter your PyPI (API) token. It will be stored inside the .pypirc file for future use. "
                "Input is hidden:"
            )
            # Asks the user for the token.
            token: str = click.prompt(text=prompt, hide_input=True, type=str)

            # Catches and prevents entering incorrectly formatted tokens
            if not token.startswith("pypi-"):
                message = "Acquired invalidly-formatted PyPI token. PyPI tokens should start with 'pypi-'."
                # This both logs and re-raises the error. Relies on the error being caught below and converted to a
                # prompt instead.
                raise ValueError(_format_message(message))

            # Generates the new .pypirc file and saves the valid token data to the file.
            config = ConfigParser()
            config["pypi"] = {"username": "__token__", "password": token}
            with pypirc_path.open("w") as config_file:
                # noinspection PyTypeChecker
                config.write(config_file)

            # Notifies the user and breaks out of the while loop
            message = f"Valid PyPI token acquired and added to '.pypirc' for future uses."
            click.echo(_colorize_message(message, color="green"))
            break

        # This block allows rerunning the token acquisition if an invalid token was provided, and the user has elected
        # to retry token input.
        except Exception:
            if not click.confirm("Do you want to try again?"):
                message = "PyPI token acquisition: aborted by user."
                raise RuntimeError(_format_message(message))


@cli.command()
@click.option(
    "-en",
    "--environment-name",
    prompt="Enter the project conda environment name, without the os-suffix:",
    required=True,
    type=str,
    help="The 'base' name of the project conda environment, e.g: 'project_dev'.",
)
def install_project(environment_name: str) -> None:  # pragma: no cover
    """Builds and installs the project into the specified conda environment.

    This command is primarily used to support project developing by compiling and installing the developed project into
    the environment to allow manual project testing. Since tests have to be written to use compiled package, rather than
    the source code to support tox testing, the project has to be rebuilt each time source code is changed, which is
    conveniently performed by this command.

    Raises:
        RuntimeError: If project installation fails. If project environment does not exist.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Gets the list of commands that can be used to carry out conda environment operations.
    commands: EnvironmentCommands = resolve_environment_commands(
        project_root=project_root,
        environment_name=environment_name,
    )

    # Checks if project conda environment is accessible via subprocess activation call. If not, raises an error.
    if not environment_exists(commands=commands):
        message = (
            f"Unable to activate the target conda environment '{commands.environment_name}', which likely means "
            f"that it does not exist. If you need to create the environment, run 'create-env' ('tox -e create')."
        )
        raise RuntimeError(_format_message(message))

    # Installs the project into the activated conda environment by combining environment activation and project
    # installation commands.
    try:
        command: str = f"{commands.activate_command} && {commands.install_project_command}"
        subprocess.run(command, shell=True, check=True)
        message = f"Project successfully installed into the requested conda environment '{commands.environment_name}'."
        click.echo(_colorize_message(message, color="green"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to build and install the project into the conda environment '{commands.environment_name}'. See "
            f"uv/pip-generated error messages for specific details about the failed operation."
        )
        raise RuntimeError(_format_message(message))


@cli.command()
@click.option(
    "-en",
    "--environment-name",
    prompt="Enter the project conda environment name, without the os-suffix:",
    required=True,
    type=str,
    help="The 'base' name of the project conda environment, e.g: 'project_dev'.",
)
def uninstall_project(environment_name: str) -> None:  # pragma: no cover
    """Uninstalls the project library from the specified conda environment.

    This command is not used in most modern automation pipelines, but is kept for backward compatibility with legacy
    projects. Previously, it was used to remove the project from its conda environment before running tests, as
    installed projects used to interfere with tox re-building the wheels for testing.

    Notes:
        If the environment does not exist or is otherwise not accessible, the function returns without attempting to
        uninstall the project.

    Raises:
        RuntimeError: If any of the environment-manipulation subprocess calls fail.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Gets the list of commands that can be used to carry out conda environment operations.
    commands: EnvironmentCommands = resolve_environment_commands(
        project_root=project_root,
        environment_name=environment_name,
    )

    # Attempts to activate the input conda environment. If activation fails, concludes that environment does not exist
    # and aborts the runtime.
    if not environment_exists(commands=commands):
        message: str = (
            f"Requested conda environment '{commands.environment_name}' is not accessible (likely does not exist). "
            f"Uninstallation process aborted. If you need to create the environment, run 'create-env' "
            f"('tox -e create')."
        )
        click.echo(_colorize_message(message, color="yellow"))
        return

    try:
        command: str = f"{commands.activate_command} && {commands.uninstall_project_command}"
        subprocess.run(command, shell=True, check=True)
        message = (
            f"Project successfully uninstalled from the requested conda environment '{commands.environment_name}'."
        )
        click.echo(_colorize_message(message, color="green"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to uninstall the project from the conda environment '{commands.environment_name}'. See "
            f"uv/pip-generated error messages for specific details about the failed operation."
        )
        raise RuntimeError(_format_message(message))


@cli.command()
@click.option(
    "-en",
    "--environment-name",
    prompt="Enter the project conda environment name, without the os-suffix:",
    required=True,
    type=str,
    help="The 'base' name of the project conda environment, e.g: 'project_dev'.",
)
@click.option(
    "-pv",
    "--python-version",
    prompt="Enter the python version of the project conda environment. Has to be different from tox 'basepython':",
    required=True,
    type=str,
    help="The python version of the project conda environment, e.g. '3.12'. Has to be different from tox 'basepython'.",
)
def create_env(environment_name: str, python_version: str) -> None:  # pragma: no cover
    """Creates the project conda environment and installs project dependencies into the created environment.

    This command is intended to be called during initial project setup for new platforms (OSes) or when the environment
    needs to be hard-reset. For most runtimes, it is advised to import ('tox -e import') an existing .yml file if it is
    available. If you need to reset an already existing environment, it is advised to use the provision
    ('tox -e provision') command instead, which re-installs environment packages without deleting the environment
    itself.

    Raises:
        RuntimeError: If any environment creation steps fail for any reason.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Gets the list of commands that can be used to carry out conda environment operations.
    commands: EnvironmentCommands = resolve_environment_commands(
        project_root=project_root,
        environment_name=environment_name,
        python_version=python_version,
    )

    # Checks if the project-specific environment is accessible via subprocess activation call. If it is accessible
    # (exists), notifies the end-user that the environment already exists and concludes the runtime.
    if environment_exists(commands=commands):
        message = (
            f"The requested environment '{commands.environment_name}' already exists. If you need to recreate the "
            f"environment, run 'remove-env' ('tox -e remove') command and try again. If you need to reinstall "
            f"environment packages, run 'provision-env' ('tox -e provision') command instead."
        )
        click.echo(_colorize_message(message, color="yellow"))
        return

    # Creates the new environment
    try:
        subprocess.run(commands.create_command, shell=True, check=True)
        message = f"Created '{commands.environment_name}' conda environment."
        click.echo(_colorize_message(message, color="white"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to create a new conda environment '{commands.environment_name}'. See the conda-issued "
            f"error-message above for more information."
        )
        raise RuntimeError(_format_message(message))

    # If environment was successfully created, installs conda-installable dependencies if there are any.
    try:
        if commands.conda_dependencies_command is not None:
            subprocess.run(commands.conda_dependencies_command, shell=True, check=True)
            message = (
                f"Installed project dependencies available from conda into created '{commands.environment_name}' "
                f"conda environment."
            )
            click.echo(_colorize_message(message, color="white"))
        else:
            message = (
                f"Skipped installing project dependencies available from conda into created "
                f"'{commands.environment_name}' conda environment. Project has no conda-installable dependencies."
            )
            click.echo(_colorize_message(message, color="white"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to install project dependencies available from conda into created '{commands.environment_name}' "
            f"conda environment. See conda-generated error message above for more information."
        )
        raise RuntimeError(_format_message(message))

    # After resolving conda-dependencies, installs pip-installable dependencies, if there are any.
    try:
        if commands.pip_dependencies_command is not None:
            command = f"{commands.activate_command} && {commands.pip_dependencies_command}"
            subprocess.run(command, shell=True, check=True)
            message = (
                f"Installed project dependencies available from PyPI (pip) into created '{commands.environment_name}' "
                f"conda environment."
            )
            click.echo(_colorize_message(message, color="white"))
        else:
            message = (
                f"Skipped installing project dependencies available from PyPI (pip) into created "
                f"'{commands.environment_name}' conda environment. Project has no pip-installable dependencies."
            )
            click.echo(_colorize_message(message, color="white"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to install project dependencies available from PyPI (pip) into created "
            f"'{commands.environment_name}' conda environment. See pip-generated error message above for more "
            f"information."
        )
        raise RuntimeError(_format_message(message))

    # Displays the final success message.
    message = (
        f"Created '{commands.environment_name}' conda environment and installed all project dependencies into the "
        f"environment."
    )
    click.echo(_colorize_message(message, color="green"))


@cli.command()
@click.option(
    "-en",
    "--environment-name",
    prompt="Enter the project conda environment name, without the os-suffix:",
    required=True,
    type=str,
    help="The 'base' name of the project conda environment, e.g: 'project_dev'.",
)
def remove_env(environment_name: str) -> None:  # pragma: no cover
    """Removes (deletes) the specified conda environment if it exists.

    This command can be used to clean up local conda distribution when conda environment is no longer needed.
    Alternatively, this command can also be used to clear an existing environment before recreating it with create-env
    ('tox -e create') command. If your main goal is to reset the environment, however, it is recommended to use the
    'provision-env' ('tox -e provision') command instead, which removes and (re)installs all packages without altering
    the environment itself.

    Raises:
        RuntimeError: If environment removal fails for any reason.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # # Obtains the list of commands that can be used to carry out conda environment operations. Since
    # python_version is not provided, this uses the default value (but the python_version argument is not needed for
    # this function).
    commands: EnvironmentCommands = resolve_environment_commands(
        project_root=project_root, environment_name=environment_name
    )

    # If the environment cannot be activated, it likely does not exist and, therefore, there is nothing to remove.
    if not environment_exists(commands=commands) and not commands.environment_directory.exists():
        message: str = (
            f"Unable to find '{commands.environment_name}' conda environment. Likely, this indicates that the "
            f"environment already does not exist. Environment removal procedure aborted."
        )
        click.echo(_colorize_message(message, color="yellow"))
        return

    # Otherwise, ensures the environment is not active and carries out the removal procedure.
    try:
        command: str = f"{commands.deactivate_command} && {commands.remove_command}"
        subprocess.run(command, shell=True, check=True)
        commands.environment_directory.unlink(missing_ok=True)  # Ensures the environment directory is deleted.
        message = f"Removed '{commands.environment_name}' conda environment."
        click.echo(_colorize_message(message, color="green"))

    except subprocess.CalledProcessError:
        message = (
            f"Unable to remove '{commands.environment_name}' conda environment. See the conda-issued error-message "
            f"above for more information."
        )
        raise RuntimeError(_format_message(message))


@cli.command()
@click.option(
    "-en",
    "--environment-name",
    prompt="Enter the project conda environment name, without the os-suffix:",
    required=True,
    type=str,
    help="The 'base' name of the project conda environment, e.g: 'project_dev'.",
)
@click.option(
    "-pv",
    "--python-version",
    prompt="Enter the python version of the project conda environment. Has to be different from tox 'basepython':",
    required=True,
    type=str,
    help="The python version of the project conda environment, e.g. '3.12'. Has to be different from tox 'basepython'.",
)
def provision_env(environment_name: str, python_version: str) -> None:  # pragma: no cover
    """Removes all packages from the target conda environment (including python) and then re-installs project
    dependencies specified in pyproject.toml file.

    This command is intended to be called when the project has a configured environment referenced by IDEs and other
    tools. Instead of removing the environment, this acts as a 'soft' reset mechanism that actualizes environment
    contents without breaking any references.

    Raises:
        RuntimeError: If any environment modification steps fail for any reason.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Gets the list of commands that can be used to carry out conda environment operations.
    commands: EnvironmentCommands = resolve_environment_commands(
        project_root=project_root,
        environment_name=environment_name,
        python_version=python_version,
    )

    # Checks if the project-specific environment is accessible via subprocess activation call. If it is not accessible
    # (does not exist), ends runtime with an error message.
    if not environment_exists(commands=commands):
        message = (
            "Unable to provision '{commands.environment_name}' conda environment, as environment does not exist. If "
            "you want to create a new environment, use 'create-env' ('tox -e create') command instead."
        )
        raise RuntimeError(_format_message(message))

    # Otherwise, uses 'provision' command to remove all packages and re-installs project dependencies.
    try:
        command = f"{commands.deactivate_command} && {commands.provision_command}"
        subprocess.run(command, shell=True, check=True)
        message = (
            f"Removed all packages from '{commands.environment_name}' conda environment and "
            f"reinstalled base dependencies (Python, uv, tox and pip)."
        )
        click.echo(_colorize_message(message, color="white"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to provision '{commands.environment_name}' conda environment. See conda-issued error-message "
            f"above for more information."
        )
        raise RuntimeError(_format_message(message))

    # If environment was successfully provisioned (reset), installs conda-installable dependencies if there are any.
    try:
        if commands.conda_dependencies_command is not None:
            subprocess.run(commands.conda_dependencies_command, shell=True, check=True)
            message = (
                f"Installed project dependencies available from conda into provisioned '{commands.environment_name}' "
                f"conda environment."
            )
            click.echo(_colorize_message(message, color="white"))
        else:
            message = (
                f"Skipped installing project dependencies available from conda into provisioned "
                f"'{commands.environment_name}' conda environment. Project has no conda-installable dependencies."
            )
            click.echo(_colorize_message(message, color="white"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to install project dependencies available from conda into provisioned "
            f"'{commands.environment_name}' conda environment . See conda-generated error message above for more "
            f"information."
        )
        raise RuntimeError(_format_message(message))

    # After resolving conda-dependencies, installs pip-installable dependencies, if there are any.
    try:
        if commands.pip_dependencies_command is not None:
            command = f"{commands.activate_command} && {commands.pip_dependencies_command}"
            subprocess.run(command, shell=True, check=True)
            message = (
                f"Installed project dependencies available from PyPI (pip) into provisioned "
                f"'{commands.environment_name}' conda environment."
            )
            click.echo(_colorize_message(message, color="white"))
        else:
            message = (
                f"Skipped installing project dependencies available from PyPI (pip) into provisioned "
                f"'{commands.environment_name}' conda environment. Project has no pip-installable dependencies."
            )
            click.echo(_colorize_message(message, color="white"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to install project dependencies available from PyPI (pip) into provisioned "
            f"'{commands.environment_name}'  conda environment. See pip-generated error message above for more "
            f"information."
        )
        raise RuntimeError(_format_message(message))

    # Displays the final success message.
    message = f"Provisioned '{commands.environment_name}' conda environment."
    click.echo(_colorize_message(message, color="green"))


@cli.command()
@click.option(
    "-en",
    "--environment-name",
    prompt="Enter the project conda environment name, without the os-suffix:",
    required=True,
    type=str,
    help="The 'base' name of the project conda environment, e.g: 'project_dev'.",
)
def import_env(environment_name: str) -> None:  # pragma: no cover
    """Creates or updates an existing conda environment based on the operating-system-specific .yml file stored in
    /envs directory.

    If the .yml file does not exist, aborts processing with error. Generally, this command is preferred over
    'create-env' ('tox -e create') whenever a valid .yml file for the current platform is available.
    OS-specific .yml files are what the developers use and are guaranteed to work for all supported platforms.

    Raises:
        RuntimeError: If there is no .yml file for the desired base-name and OS-extension combination in the /envs/
        directory. If creation and update commands both fail for any reason.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Gets the list of commands that can be used to carry out conda environment operations. Since
    # python_version is not provided, this uses the default value (but the python_version argument is not needed for
    # this function).
    commands: EnvironmentCommands = resolve_environment_commands(
        project_root=project_root, environment_name=environment_name
    )

    # If environment cannot be activated (likely does not exist) and the environment .yml file is found inside /envs
    # directory, uses .yml file to create a new environment.
    if not environment_exists(commands=commands) and commands.create_from_yml_command is not None:
        try:
            subprocess.run(commands.create_from_yml_command, shell=True, check=True)
            message: str = (
                f"'{commands.environment_name}' conda environment imported (created) from existing .yml file."
            )
            click.echo(_colorize_message(message, color="green"))
        except subprocess.CalledProcessError:
            message = (
                f"Unable to import (create) '{commands.environment_name}' conda environment from existing .yml file. "
                f"See conda-issued error-message above for more information."
            )
            raise RuntimeError(_format_message(message))

    # If conda environment already exists and .yml file exists, updates the environment using the .yml file.
    elif commands.update_command is not None:
        try:
            subprocess.run(commands.update_command, shell=True, check=True)
            message = f"Existing '{commands.environment_name}' conda environment updated from .yml file."
            click.echo(_colorize_message(message, color="green"))
        except subprocess.CalledProcessError:
            message = (
                f"Unable to update existing conda environment '{commands.environment_name}' from .yml file. "
                f"See conda-issued error-message above for more information."
            )
            raise RuntimeError(_format_message(message))
    # If the .yml file does not exist, aborts with error.
    else:
        message = (
            f"Unable to import or update '{commands.environment_name}' conda environment as there is no valid .yml "
            f"file inside the /envs directory for the given project and host-OS combination. Try creating the "
            f"environment using pyproject.toml dependencies by using 'create-env' ('tox -e create')."
        )
        raise RuntimeError(_format_message(message))


@cli.command()
@click.option(
    "-en",
    "--environment-name",
    prompt="Enter the project conda environment name, without the os-suffix:",
    required=True,
    type=str,
    help="The 'base' name of the project conda environment, e.g: 'project_dev'.",
)
def export_env(environment_name: str) -> None:  # pragma: no cover
    """Exports the requested conda environment as a .yml and as a spec.txt file to the /envs directory.

    This command is intended to be called as part of the pre-release checkout, before building the source distribution
    for the project (and releasing the new project version).

    Raises:
        RuntimeError: If the environment export process fails for any reason. If the conda environment to export does
        not exist.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Gets the list of commands that can be used to carry out conda environment operations. Since
    # python_version is not provided, this uses the default value (but the python_version argument is not needed for
    # this function).
    commands: EnvironmentCommands = resolve_environment_commands(
        project_root=project_root, environment_name=environment_name
    )

    if not environment_exists(commands):
        message = (
            f"Unable to activate '{commands.environment_name}' conda environment, which likely indicates that it does "
            f"not exist. Create the environment with 'create-env' ('tox -e create') before attempting to export it."
        )
        raise RuntimeError(_format_message(message))

    # Exports environment as a .yml file
    try:
        subprocess.run(commands.export_yml_command, shell=True, check=True)
        message = f"'{commands.environment_name}' conda environment exported to /envs as a .yml file."
        click.echo(_colorize_message(message, color="green"))

    except subprocess.CalledProcessError:
        message = (
            f"Unable to export '{commands.environment_name}' conda environment to .yml file. See conda-issued "
            f"error-message above for more information."
        )
        raise RuntimeError(_format_message(message))

    # Exports environment as a spec.txt file
    try:
        subprocess.run(commands.export_spec_command, shell=True, check=True)
        message = f"'{commands.environment_name}' conda environment exported to /envs as a spec.txt file."
        click.echo(_colorize_message(message, color="green"))

    except subprocess.CalledProcessError:
        message = (
            f"Unable to export '{commands.environment_name}' conda environment to spec.txt file. See conda-issued "
            f"error-message above for more information."
        )
        raise RuntimeError(_format_message(message))


@cli.command()
@click.option(
    "-ne",
    "--new-name",
    prompt="Enter the new 'base' environment name to use. Should not contain the os-suffix:",
    callback=validate_env_name,
    help="The new 'base' name to use for the project conda environment, e.g: 'project_dev'.",
)
def rename_environments(new_name: str) -> None:  # pragma: no cover
    """Iteratively renames environment files inside the 'envs' directory to use the provided name as the base-name.

    Notes:
        This function does not rename any existing conda environments. This behavior is intentional. It is advised to
        first export the environment via 'export-env' ('tox -e export'). Then to use 'remove-env' ('tox -e remove') to
        remove the existing environment, followed by this function to rename the .yml and spec.txt files. Finally,
        re-import the environment via 'import-env' ('tox -e import').

    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # This method handles the renaming
    rename_all_envs(new_name=new_name, project_root=project_root)

    # Issues a success message
    message = f"Renamed all supported environment files inside the /envs directory to use the new base name {new_name}."
    click.echo(_colorize_message(message, color="green"))


@cli.command()
@click.option(
    "--library-name",
    prompt="Enter the desired library name. This is what end-users will 'import'",
    callback=validate_library_name,
    help="The name to use for the library end-users will import into their projects, e.g: 'my_library'.",
)
@click.option(
    "--project-name",
    prompt="Enter the desired project name. This is what end-users will 'pip install'",
    callback=validate_project_name,
    help="The name to use for the project end-users will pip-install into their environments, e.g: 'my_library'.",
)
@click.option(
    "--author-name",
    prompt="Enter the author name. The name can optionally include (GitHub Username)",
    callback=validate_author_name,
    help="The name is used to populate pyproject.toml and conf.py metadata files. Currently, only "
    "one author can be added during this step. Manually add any additional authors as needed after adopting the "
    "project.",
)
@click.option(
    "--email",
    prompt="Enter the email address. Has to be a well-formed email address",
    callback=validate_email,
    help="The email is used to populate the pyproject.toml metadata file. It is used together with the author name.",
)
@click.option(
    "--env-name",
    prompt="Enter the base environment name. Do not include _OStag, it is generated automatically",
    callback=validate_env_name,
    help="The name that will be given to the conda environments used by the project. The name will be automatically "
    "modified to include the platform-suffix (e.g: _win).",
)
def adopt_project(
    library_name: str, project_name: str, author_name: str, email: str, env_name: str
) -> None:  # pragma: no cover
    """Adopts a new project initialized from a standard Sun Lab template, by replacing placeholders in metadata and
    automation files with user-defined data.

    In addition to replacing placeholders inside a predefined set of files, this function also renames any files whose
    names match any of the markers. At this time, the function is used to set: project name, library name, development
    (conda) environment base-name, author name, and author email. In the future, more markers may be added as needed.

    Notes:
        Manual validation of all automation files is highly advised. This function is not intended to replace manual
        configuration, but only to expedite it in critical bottlenecks. It is very likely that your project will not
        work as expected without additional configuration.

    Raises:
        RuntimeError: If the adoption process fails for any reason.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Stores the placeholder markers alongside their replacement values.
    markers: dict[str, str] = {
        "YOUR_LIBRARY_NAME": library_name,  # Library name placeholder
        "YOUR-PROJECT-NAME": project_name,  # Project name placeholder
        "YOUR_AUTHOR_NAME": author_name,  # Author name placeholder
        "YOUR_EMAIL": email,  # Author email placeholder
        "YOUR_ENV_NAME": env_name,  # Environment base-name placeholder
        "template_ext": env_name,  # The initial environment base-name used by c-extension projects
        "template_pure": env_name,  # The initial environment base-name used by pure-python projects
    }

    # A tuple that stores the files whose content will be scanned for the presence of markers. All other files will not
    # be checked for content, but their names will be checked and replaced if they match any markers. Note, the files
    # in this list can be anywhere inside the root project directory, the loop below will find and process them all.
    file_names = (
        "pyproject.toml",
        "Doxyfile",
        "CMakeLists.txt",
        "tox.ini",
        "conf.py",
        "README.md",
        "api.rst",
        "welcome.rst",
    )

    # Uses the input environment name to rename all environment files inside the 'envs' folder. This renames both file
    # names and the 'name' field values inside the .yml files. This step has to be done first as the loop below can
    # and will rename files, but not in the specific way required for environment files.
    rename_all_envs(project_root=project_root, new_name=env_name)

    # Loops over all files inside the script directory, which should be project root directory.
    total_markers: int = 0  # Tracks the number of replaced markers.
    root: Path
    dirs: list[str]
    files: list[str]
    for root, dirs, files in project_root.walk():  # type: ignore
        for file in files:
            # Gets the absolute path to each scanned file.
            file_path: Path = root.joinpath(file)

            # If the file is in the list of files to be content-checked, removes markers from file contents.
            if file in file_names:
                total_markers += replace_markers_in_file(file_path=file_path, markers=markers)

            # Also processes file names in case they match any of the placeholders.
            if file_path.name in markers:
                new_file_name = markers[file_path.stem] + file_path.suffix
                new_path = file_path.with_name(new_file_name)
                file_path.rename(new_path)
                message: str = f"Renamed file: {file_path} -> {new_path}."
                click.echo(_colorize_message(message, color="white"))

        for directory in dirs:
            # Gets the absolute path to each scanned directory.
            dir_path: Path = root.joinpath(directory)

            # If directory name matches one of the markers, renames the directory.
            if directory in markers:
                new_dir_name = markers[directory]
                new_path = dir_path.with_name(new_dir_name)
                dir_path.rename(new_path)
                message = f"Renamed directory: {dir_path} -> {new_path}."
                click.echo(_colorize_message(message, color="white"))

                # Update the directory name in the dirs list to avoid potential issues
                dirs[dirs.index(directory)] = new_dir_name

    # Provides the final reminder
    message = (
        f"Project Adoption: Complete. Be sure to manually verify critical files such as pyproject.toml before "
        f"proceeding to the next step. Overall, found and replaced {total_markers} markers in scanned file "
        f"contents."
    )
    click.echo(_colorize_message(message, color="green"))
