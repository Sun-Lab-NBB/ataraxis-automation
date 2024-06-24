"""This module provides a command-line interface for various project build and deployment automation tasks.

The methods exposed through this module are intended to be called through appropriate 'tox' pipelines and should not
be used directly.
"""

import configparser
import os
import re
import shutil
import subprocess
import sys
from os import PathLike
from typing import AnyStr, Optional

import click
import yaml

from .utilities import format_message


def resolve_project_directory() -> str:
    """This utility function gets the current working directory from the OS and verifies that it points to a valid
    python project.

    This function was introduced when automation moved to a separate package to decouple the behavior of this module's
    functions from the location of the module.

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
        message: str = format_message(
            f"Unable to confirm that automation module has been called from the root directory of a valid Python "
            f"project. This module is hardcoded to work with SunLab project organization template and is likely to "
            f"not work as intended for other projects. Additionally, it assumes the current working directory is set "
            f"to the root directory of the project. 'cd' into the root directory of the project and try again."
        )
        click.echo(message, err=True)
        raise click.Abort()
    else:
        return project_dir


def resolve_typed_markers(target_dir: AnyStr | PathLike[AnyStr]) -> None:
    """Crawls the input directory tree and resolves 'py.typed' marker file to match SunLab guidelines.

    Specifically, if the 'py.typed' is not found in the target directory, adds the marker file. If it is found in any
    subdirectory, removes the marker file.

    Note:
        The marker file has to be present in-addition to thy '.pyi' typing files to notify type-checkers, like mypy,
        that the library comes with type-annotations. This is necessary to allow other projects using type-checkers to
        verify this library API is accessed correctly.

    Args:
        target_dir: The path to the root level of the directory to crawl. Usually, this is the '/src' directory of the
        project.
    """
    # Loops over the target directory hierarchy.
    evaluated_roots: set[str] = set()
    level: int = 0
    for root, _, files in os.walk(target_dir):
        root_path = str(object=root)
        file_names = [str(object=member) for member in files]

        # Tracks the evaluated directory level.
        if root not in evaluated_roots:
            evaluated_roots.add(root_path)
            level += 1

        # If evaluated directory is the root directory and the py.typed marker is not found, adds the marker file.
        if "py.typed" not in file_names and level == 1:
            # Add py.typed to this package directory
            with open(os.path.join(root_path, "py.typed"), "w") as _:
                pass

        # Removes any py.typed instances from all directories except the root directory.
        elif level != 1:
            dir_py_typed = os.path.join(root_path, "py.typed")
            if os.path.exists(dir_py_typed):
                os.remove(dir_py_typed)


def move_stubs(src_dir: str, dst_dir: str) -> None:
    """Moves typing stubs from the source folder to appropriate level(s) of the destination directory.

    This procedure is intended to be executed after running stubgen on the compiled package instance, and it expects
    that the layout of the destination directory exactly matches the layout of the source directory (including all
    subdirectories!).

    Args:
        src_dir: The path to the source directory (usually, this is the stubgen output directory).
        dst_dir: The path to the destination directory. Usually, this is the '/src' or '/src/library' directory of the
            project, depending on project type (c-extension or pure-python).
    """

    # Iterates over all files of the input tree hierarchy
    for root, _, files in os.walk(src_dir):
        for file in files:
            # For any file with python stub extension that matches the pattern, moves it to a mirroring directory level
            # and name relative to the destination root.
            if file.endswith(".pyi"):
                stub_path = os.path.join(root, file)  # Parses the path to the stub file relative to the source root

                # Finds the index of 'stubs' in the path
                stubs_index: int = 0
                path_parts = stub_path.split(os.path.sep)
                try:
                    stubs_index = path_parts.index("stubs")
                except ValueError:
                    message: str = format_message(
                        f"Error: 'stubs' directory not found in path: {stub_path}. "
                        f"Cannot move stub file to destination."
                    )
                    click.echo(message, err=True)
                    click.Abort()

                # Replace 'stubs' and the following directory (LIBRARY_NAME) with dst_dir
                new_path_parts = [dst_dir] + path_parts[stubs_index + 2 :]
                # noinspection PyTypeChecker
                dst_path: str = os.path.join(*new_path_parts)

                # Removes old .pyi file if it already exists
                if os.path.exists(dst_path):
                    os.remove(dst_path)

                # Moves the stub to its destination directory
                shutil.move(stub_path, dst_path)

    # This loop is designed to solve a (so far) OSX-unique issue where this function results in multiple copies with
    # appended copy_counts, rather than a single copy of the .pyi file.
    for root, _, files in os.walk(dst_dir):
        # Groups files by their base name (without a space number)
        file_groups: dict[str, list[str]] = {}
        for file in files:
            if file.endswith(".pyi"):
                base_name = re.sub(r" \d+\.pyi$", ".pyi", file)
                if base_name not in file_groups:
                    file_groups[base_name] = []
                file_groups[base_name].append(file)

        # For each group, keeps only the file with the highest space number and renames it
        for base_name, group in file_groups.items():
            if len(group) > 1:
                # Sorts files by space number, in descending order
                sorted_files = sorted(
                    group,
                    key=lambda x: (int(re.findall(r" (\d+)\.pyi$", x)[0]) if re.findall(r" (\d+)\.pyi$", x) else 0),
                    reverse=True,
                )

                # Keeps the first file (highest space number), renames it, and removes the rest
                kept_file = sorted_files[0]
                kept_file_path = os.path.join(root, kept_file)
                new_file_path = os.path.join(root, base_name)

                # Removes the rest of the files
                for file_to_remove in sorted_files[1:]:
                    os.remove(os.path.join(root, file_to_remove))
                    message = format_message(f"Removed duplicate file: {file_to_remove}")
                    click.echo(message)

                # Renames the kept file to remove the space number
                os.rename(kept_file_path, new_file_path)
                message = format_message(f"Renamed file: {kept_file} -> {base_name}")
                click.echo(message)
            elif len(group) == 1:
                # If there's only one file in the group, rename it if it has a space number
                file = group[0]
                if file != base_name:
                    old_path = os.path.join(root, file)
                    new_path = os.path.join(root, base_name)
                    os.rename(old_path, new_path)
                    message = format_message(f"Renamed file: {file} -> {base_name}")
                    click.echo(message)


def delete_stubs(directory: str) -> None:
    """Removes all .pyi stub files from the given directory and its subdirectories.

    This function is intended to be used before linting as mypy tends to be biased to analyze the .pyi files, ignoring
    the source code. When .pyi files are not present, mypy reverts to properly analyzing the source code.

    Args:
        directory: The path to the root directory from which to start removing .pyi files.
    """
    removed_files: list[str] = []

    # Iterates over all files in the directory tree
    for root, _, files in os.walk(directory):
        for file in files:
            # Checks if the file is a .pyi stub file
            if file.endswith(".pyi"):
                file_path = os.path.join(root, file)

                # Removes the .pyi file
                os.remove(file_path)

                message: str = format_message(f"Removed {file_path}.")
                click.echo(message)


def resolve_library_root() -> str:
    """Determines the relative path to the library root directory inside the 'src' directory of the source code.

    This function is primarily used by the functions such as stub-generators that generate the necessary files in a
    temporary directory and then need to distribute them to source code directories. Since our c-extension and
    pure-python use a slightly different layout, this function allows using the same automation code for both project
    types.

    Returns:
        The path, relative to the 'src' directory, that points to the root directory of the LIBRARY (after it is
        built).

    Raises:
        RuntimeError: If the valid root candidate cannot be found based on the determination heuristics.
    """
    # Resolves the target directory
    project_dir: str = resolve_project_directory()
    src_path: str = os.path.join(project_dir, "src")

    error_message: str = format_message(
        "Unable to resolve the path to the (built) library root directory. Expected an __init__.py at the level of the "
        "'src' or a single sub-directory with an __init__.py, but discovered neither. C-extensions should use 'src' "
        "as the root directory and pure-python packages should have the python package stored directly under 'src'."
    )

    # If __init__.py is not found at the level of the src, this implies that the processed project is a pure python
    # project and, in this case, it is expected that there is a single library-directory under /src that is the
    # root.
    if "__init__.py" not in os.listdir(src_path):
        if len(os.listdir("src")) > 1:
            click.echo(error_message, err=True)
            raise click.Abort()

        directories: set[str] = set()
        for candidate_name in os.listdir(src_path):
            candidate_path: str = os.path.join(src_path, candidate_name)
            if os.path.isdir(candidate_path):
                directories.add(candidate_path)

        if len(directories) != 1:
            click.echo(error_message, err=True)
            raise click.Abort()

        if "__init__.py" not in os.listdir(directories.pop()):
            click.echo(error_message, err=True)
            raise click.Abort()

    # If __init__.py is found at the level of the src, this is used as a heuristic that this library
    # is a c-extension library and does not contain a 'root' package (instead, src is the root).
    else:
        candidate_path = src_path

    return candidate_path


@click.group()
def cli() -> None:
    """This CLI exposes helper commands used to automate various project management steps. See below for details
    about the available commands.
    """
    pass


@cli.command()
def process_typed_markers() -> None:
    """Crawls the '/src' directory and ensures that the 'py.typed' marker is found only at the highest level of the
    library hierarchy (the highest directory with __init__.py in it).

    This command should be called as part of the stub-generation tox command.

    Raises:
        RuntimeError: If root (highest) directory cannot be resolved. If the function runs into an error
            processing 'py.typed' markers. If 'src' directory does not exist.
    """
    # Resolves the target directory
    project_dir: str = resolve_project_directory()
    src_path: str = os.path.join(project_dir, "src")

    if not os.path.exists(src_path):
        message: str = format_message("Unable to resolve typed markers. Source directory does not exist.")
        click.echo(message, err=True)
        raise click.Abort()

    # Uses '__init__.py' presence and some additional heuristics to determine the root directory of the built library
    # (either src or the first python package). This depends on the project type (c-extension or pure-python).
    library_root: str = resolve_library_root()

    # This is only executed if the library root was discovered
    try:
        resolve_typed_markers(target_dir=library_root)
        message = format_message("Typed Markers: Resolved.")
        click.echo(message)
    except Exception as e:
        message = format_message(f"Error resolving typed markers: {str(e)}")
        click.echo(message, err=True)
        raise click.Abort()


@cli.command()
def process_stubs() -> None:
    """Distributes the stub files from the '/stubs' directory to the appropriate level of the '/src' or
     'src/library' directory (depending on the type of the processed project).

    Notes:
        This command should only be called after the /stubs directory has been generated using stubgen command from tox.

    Raises:
        RuntimeError: If root (highest) directory cannot be resolved. If the function runs into an error
            processing stubs. If 'src' or 'stubs directories do not exist.
    """
    # Resolves the target directory
    project_dir: str = resolve_project_directory()
    src_path: str = os.path.join(project_dir, "src")
    stubs_path: str = os.path.join(project_dir, "stubs")

    if not os.path.exists(src_path):
        message = format_message("Unable to move stub files. Source directory does not exist.")
        click.echo(message, err=True)
        raise click.Abort()
    if not os.path.exists(stubs_path):
        message = format_message("Unable to move stub files. Stubs directory does not exist.")
        click.echo(message, err=True)
        raise click.Abort()

    # Uses '__init__.py' presence and some additional heuristics to determine the root directory of the built library
    # (either src or the first python package). This depends on the project type (c-extension or pure-python).
    library_root: str = resolve_library_root()

    # Moves the stubs to the appropriate source code directories
    try:
        # Distributes the stubs across source directory
        move_stubs(src_dir=stubs_path, dst_dir=library_root)
        shutil.rmtree(stubs_path)  # Removes the directory
        message = format_message("Stubs: Distributed.")
        click.echo(message)
    except Exception as e:
        message = format_message(f"Error processing stubs: {str(e)}")
        click.echo(message, err=True)
        raise click.Abort()


@cli.command()
def purge_stubs() -> None:
    """Removes all existing stub (.pyi) files from the 'src' directory.

    This is a necessary step before running the linting task, as it forces mypy to type-check the source code instead
    of the stubs.

    Raises:
        RuntimeError: If root (highest) directory cannot be resolved. If the function runs into an error
            removing stubs. If 'src' directory does not exist.
    """

    # Resolves the target directory
    project_dir: str = resolve_project_directory()
    src_path: str = os.path.join(project_dir, "src")

    if not os.path.exists(src_path):
        message: str = format_message("Unable to purge existing stub files. Source directory does not exist.")
        click.echo(message, err=True)
        raise click.Abort()

    # Uses '__init__.py' presence and some additional heuristics to determine the root directory of the built library
    # (either src or the first python package). This depends on the project type (c-extension or pure-python).
    library_root: str = resolve_library_root()

    # Removes all stub files from the library source code.
    try:
        # Distributes the stubs across source directory
        delete_stubs(directory=library_root)
        message = format_message("Stubs: Purged.")
        click.echo(message)
    except Exception as e:
        message = format_message(f"Error removing stubs: {str(e)}")
        click.echo(message, err=True)
        raise click.Abort()


@cli.command()
def generate_recipe_folder() -> None:
    """Generates the recipe folder used by Grayskull.

    Since Grayskull does not generate output folders by itself, this task is 'outsourced' to this command instead.

    Raises:
        RuntimeError: If the recipe folder cannot be generated for any reason.
    """
    # Resolves the target directory
    project_dir: str = resolve_project_directory()
    recipe_path: str = os.path.join(project_dir, "recipe")

    if not os.path.exists(recipe_path):
        # If the folder does not exist, generates it from scratch
        try:
            os.makedirs(recipe_path)
            message = format_message("Recipe Directory: Generated.")
            click.echo(message)
        except Exception as e:
            message = format_message(f"Error generating recipe folder: {str(e)}")
            click.echo(message, err=True)
            raise click.Abort()
    else:
        # If the folder does exist, recreates it (to remove the potentially existing recipe)
        shutil.rmtree(recipe_path)
        os.makedirs(recipe_path)
        message = format_message("Recipe Directory: Recreated.")
        click.echo(message)


def is_valid_pypirc(file_path: str) -> bool:
    """Verifies that the .pypirc file pointed to by the input path contains valid options to support automatic
    authentication for pip uploads.

    Assumes that the file is used only to store the API token to upload compiled packages to pip. Does not verify any
    other information.

    Returns:
        True if the .pypirc is well-configured configured and False otherwise.
    """
    config_validator = configparser.ConfigParser()
    config_validator.read(file_path)
    return (
        config_validator.has_section("pypi")
        and config_validator.has_option("pypi", "username")
        and config_validator.has_option("pypi", "password")
        and config_validator.get("pypi", "username") == "__token__"
        and config_validator.get("pypi", "password").startswith("pypi-")
    )


@cli.command()
@click.option(
    "--replace-token",
    "-r",
    is_flag=True,
    help="If provided, this flag forces the method to replace the API token stored in the .pypirc file with a new one.",
)
def set_pypi_token(replace_token: bool) -> None:
    """Ensures the .pypirc file exists at the root of the project, asks for the user API token to upload compiled
    package to PIP and saves it to the file for future use.

    The '.pypirc' file is added to gitignore, so there should be no private information leaking unless
    gitignore is not included.

    Note:
        This function tries to verify the validity of the token, but can only verify it is intended for pypi (due to
        prefix). If the token is not active or otherwise invalid, only a failed twine upload will be able to determine
        that.

    Args:
        replace_token: Use this flag to force the function to overwrite the contents of the '.pypirc' file even if it
            already exists.

    Raises:
        ValueError: If the input token is not valid.
    """
    # Resolves target directory
    project_dir: str = resolve_project_directory()
    pypirc_path: str = os.path.join(project_dir, ".pypirc")

    # If file exists, recreating the file is not requested and the file appears well-formed, ends the runtime.
    if os.path.exists(pypirc_path) and is_valid_pypirc(pypirc_path) and not replace_token:
        message: str = format_message(f"PyPI Token: extracted from the '.pypirc' file.")
        click.echo(message)
        return

    # If the existing .pypirc file is not valid or does not contain the token, proceeds to generating a new file and
    # token.
    else:
        message = format_message(
            f"PyPI Token: '.pypirc' file does not exist, is invalid or doesn't contain a token. Proceeding to create "
            f"a new one."
        )
        click.echo(message)

    # Enters the while loop to iteratively ask for the token until a valid token entry is provided.
    while True:
        try:
            # Asks the user for the token.
            token = click.prompt(
                text=(
                    "Enter your PyPI (API) token. It will be stored inside the .pypirc "
                    "file for future use. Input is hidden:"
                ),
                hide_input=True,
            )

            # Catches and prevents entering incorrectly formatted tokens
            if not token.startswith("pypi-"):
                message = format_message("Invalid token format. PyPI tokens should start with 'pypi-'.")
                raise ValueError(message)

            # Generates the new .pypirc file and saves the valid token data to the file.
            config = configparser.ConfigParser()
            config["pypi"] = {"username": "__token__", "password": token}
            with open(pypirc_path, "w") as f:
                config.write(f)

            # Notifies the user and breaks out of the while loop
            message = format_message("PyPI Token: Valid token added to '.pypirc'.")
            click.echo(message)
            break

        # This block allows rerunning the token acquisition if an invalid token was provided, and the user has elected
        # to retry token input.
        except Exception as e:
            message = format_message(f"Error setting PyPI token: {str(e)}")
            click.echo(message, err=True)
            if not click.confirm("Do you want to try again?"):
                raise click.Abort()


def get_env_extension() -> str:
    """Determines the OS version used by the host platform and uses it to set the OS-postfix used in conda
    environment files.

    Currently, this command explicitly supports only 3 OS versions: OSx (Apple Silicon, Darwin), Linux and Windows.

    Returns: The postfix used to identify the Conda development environment for the host OS.

    Raises:
        BadParameter: If the host OS does not match any of the supported operating systems.
    """
    os_name: str = sys.platform
    if os_name == "win32":
        return "_win"
    elif os_name == "linux":
        return "_lin"
    elif os_name == "darwin":
        return "_osx"
    else:
        message: str = format_message(f"Unsupported host operating system: {os_name}.")
        raise click.BadParameter(message)


def get_conda_cmdlet() -> str:
    """Determines whether mamba or conda can be accessed from this script by silently calling 'command --version'.

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
            continue  # For failed command, cycles to the next command in the cycle or to the general error below.

    # If this point in the runtime is reached, this means neither conda nor mamba is installed or accessible.
    message = format_message(f"Unable to interface with either conda or mamba. Is it installed and added to Path?")
    click.echo(message, err=True)
    raise click.Abort()


@cli.command()
def import_env() -> None:
    """Creates or updates an existing Conda environment based on the operating system-specific .yml file stored in
    'envs' folder.

    Uses the fastest available engine to resolve environment data (prefers mamba over conda, if mamba is available).

    Raises:
        RuntimeError: If there is no .yml file for the desired base-name and OS-extension combination in the 'envs'
            folder. If creation and update commands both fail for any reason. If 'envs' folder does not exist
    """
    # Resolves target directory
    project_dir: str = resolve_project_directory()
    envs_path = os.path.join(project_dir, "envs")

    if not os.path.exists(envs_path):
        message: str = format_message(f"Unable to import conda environment. '/envs' directory does not exist.")
        click.echo(message, err=True)
        raise click.Abort()

    env_postfix: str = get_env_extension()  # Uses host OS name to generate the appropriate environment postfix.
    yml_file: str = f"{env_postfix}.yml"  # Concatenates the postfix with the .yml extension.

    # Scans the 'envs' directory and discovers the first file with the matching postfix and extension. If a match is
    # found, uses it to set the path to the .yml file and the name to use in string-reports.
    yml_path: Optional[str] = None
    env_name: Optional[str] = None
    for file in os.listdir(envs_path):
        if yml_file in file:
            yml_path = os.path.join(envs_path, file)
            env_name = file.split(".")[0]
            break

    # If the OS-specific .yml file is not found, raises an error
    if yml_path is None:
        message = format_message(
            f"No environment file found for the requested postfix and extension combination {yml_file}."
        )
        click.echo(message, err=True)
        raise click.Abort()

    # Gets the command name to use. Primarily, this is used to select the 'fastest' available command. Also ensures
    # the necessary cmdlet is accessible form this script.
    cmdlet_name: str = get_conda_cmdlet()

    # If the .yml file was found, attempts to create a new environment by calling appropriate cmdlet via subprocess.
    try:
        subprocess.run(f"{cmdlet_name} env create -f {yml_path}", shell=True, check=True)
        message = format_message(f"Environment '{env_name}' created successfully.")
        click.echo(message)
        return
    except subprocess.CalledProcessError:
        pass

    # If environment creation fails, this is likely due to the environment already existing. Therefore, upon the
    # first error, attempts to instead update the existing environment using the same.yml file
    try:
        subprocess.run(f"{cmdlet_name} env update -f {yml_path} --prune", shell=True, check=True)
        message = format_message(f"Environment '{env_name}' already exists and was instead updated successfully.")
        click.echo(message)
    # If the update attempt also fails, aborts with an error.
    except subprocess.CalledProcessError as e:
        message = format_message(f"Unable to create or update an environment. Last encountered error was: {str(e)}")
        click.echo(message, err=True)
        raise click.Abort()


def get_export_command(
    cmdlet_name: str,
    env_name: str,
    yml_path: str,
    spec_path: str,
) -> tuple[str, str]:
    """Resolves the appropriate environment .yml and spec.txt export commands based on the platform OS version.

    Supports the same set of OS versions as get_env_extension(). Primary reason for using separate commands is to
    make sure they remove the prefix from the exported .yml file (primarily for privacy reasons).

    Args:
        cmdlet_name: The name of the execution cmdlet, valid options are 'conda' and 'mamba'.
        env_name: The base-name of the environment to export.
        yml_path: The path to use for exporting the environment as a .yml file.
        spec_path: The path to use for exporting the environment as a spec.txt file.

    Returns: A tuple of two string-commands. The first command can be passed (via subprocess) to conda or mamba
        to export the environment for the current project to 'envs' folder as a .yml file. THe second exports the
        spec.txt list with revision history to the same folder.

    Raises:
        BadParameter: If the host OS does not match any of the supported operating systems.
    """
    os_name: str = sys.platform
    # Determines the OS-specific command to export the environment as a .yml file while removing the prefix.
    if os_name == "win32":
        yml_command: str = f'{cmdlet_name} env export --name {env_name} | findstr -v "prefix" > {yml_path}'
    elif os_name == "linux":
        yml_command = f"{cmdlet_name} env export --name {env_name} | head -n -1 > {yml_path}"
    elif os_name == "darwin":
        yml_command = f"{cmdlet_name} env export --name {env_name} | tail -r | tail -n +2 | tail -r > {yml_path}"
    else:
        message: str = format_message(f"Unsupported host operating system: {os_name}.")
        raise click.BadParameter(message)

    # Uses the same spec-command regardless of the OS-specific .yml command.
    spec_command: str = f"{cmdlet_name} list -n {env_name} --explicit -r > {spec_path}"

    return yml_command, spec_command


@cli.command()
@click.option(
    "--base-env",
    prompt="Enter the base environment name",
    required=True,
    help="The base name of the environment to export.",
)
def export_env(base_env: str) -> None:
    """Exports the OS-specific Conda environment as a .yml and as a spec.txt files.

    Args:
        base_env: The base name (e.g.: axt_dev) of the environment. The OS-specific postfix for the environment is
            resolved and appended automatically.

    Raises:
        RuntimeError: If 'envs' directory does not exist. If any environment export command fails for any reason.
    """
    # Resolves target directory
    project_dir: str = resolve_project_directory()
    envs_path = os.path.join(project_dir, "envs")

    if not os.path.exists(envs_path):
        message: str = format_message(f"Unable to export conda environment. '/envs' directory does not exist.")
        click.echo(message, err=True)
        raise click.Abort()

    # Selects the environment name according to the host OS and constructs the path to the environment .yml and spec
    # files using the generated name.
    env_extension: str = get_env_extension()
    env_name: str = f"{base_env}{env_extension}"
    yml_path: str = os.path.join(envs_path, f"{env_name}.yml")
    spec_path: str = os.path.join(envs_path, f"{env_name}_spec.txt")

    # Gets the command name to use. Primarily, this is used to select the 'fastest' available command. Also ensures
    # the necessary cmdlet is accessible form this script.
    cmdlet_name: str = get_conda_cmdlet()

    # Resolves the commands to execute for exporting the environment as a .yml and a spec.txt files.
    yml_export_command: str
    spec_export_command: str
    # noinspection PyTypeChecker
    yml_export_command, spec_export_command = get_export_command(cmdlet_name, env_name, yml_path, spec_path)

    # Handles environment export using the commands obtained above
    try:
        subprocess.run(yml_export_command, shell=True, check=True)
        message = format_message(f"Environment exported to {yml_path}.")
        click.echo(message)
        subprocess.run(spec_export_command, shell=True, check=True)
        message = format_message(f"Environment spec-file exported to {spec_path}")
        click.echo(message)

    except subprocess.CalledProcessError as e:
        message = format_message(f"Error exporting environment: {str(e)}")
        click.echo(message, err=True)
        raise click.Abort()


def rename_all_envs(new_name: str) -> None:
    """Loops over the contents of the 'envs' directory and replaces base environment names with the input name.

    Also updates the 'name' filed of the .yml files before renaming the files. This function is mainly designed to be
    used during template project adoption, but also can be used as part of tox-automation to rename all environments
    in the folder (for example, when changing the environment naming pattern for the project).

    Notes:
        This does not rename any active conda environments! This behavior is intentional, you have to manually rename
        conda environments as needed for your project.

    Args:
        new_name: The new base-name to use for all environment files.

    Raises:
        RuntimeError: If the 'envs' directory does not exist.
    """
    # Resolves target directory
    project_dir: str = resolve_project_directory()
    envs_dir: str = os.path.join(project_dir, "envs")

    # If environments directory does not exist, aborts the runtime.
    if not os.path.exists(envs_dir):
        message: str = format_message(f"Unable to export conda environment. '/envs' directory does not exist.")
        click.echo(message, err=True)
        raise click.Abort()

    # Loops over every file inside 'envs' directory
    for file in os.listdir(envs_dir):
        # For .yml file, finds the last underscore
        if file.endswith(".yml"):
            last_underscore_index = file.rfind("_")

            # If there are no underscores in the yml name, skips processing the file.
            if last_underscore_index == -1:
                continue

            # Uses the last underscore index to strip the base-name from each yml file while keeping the OS-postfix and
            # '.yml' extension.
            os_suffix_and_ext = file[last_underscore_index:]
            new_file_name = f"{new_name}{os_suffix_and_ext}"  # Underscore from suffix is kept
            old_file_path = os.path.join(envs_dir, file)
            new_file_path = os.path.join(envs_dir, new_file_name)

            # Reads the YAML file.
            with open(old_file_path, "r") as f:
                yaml_data = yaml.safe_load(f)

            # Updates the environment name inside the YAML file (changes the value of the 'name' field).
            if "name" in yaml_data:
                yaml_data["name"] = new_file_name[:-4]  # Removes the '.yml' extension

            # Writes the updated YAML data to the new file. Does not sort the keys to prevent altering file order.
            with open(new_file_path, "w") as f:
                yaml.safe_dump(yaml_data, f, sort_keys=False)

            # Remove the old file.
            os.remove(old_file_path)

            click.echo(f"Renamed environment file: {file} -> {new_file_name}")

        # For spec-files, executes a slightly different process
        elif file.endswith("_spec.txt"):
            # Finds the first underscore starting from _spec.txt (excludes the spec underscore)
            last_underscore_index = file.rfind("_", 0, file.rfind("_spec.txt"))

            # If there are no underscores in the spec name, skips processing the file.
            if last_underscore_index == -1:
                continue

            # Otherwise renames the file (replaces the old file with a new one)
            os_suffix_and_ext = file[last_underscore_index:]
            new_file_name = f"{new_name}{os_suffix_and_ext}"
            old_file_path = os.path.join(envs_dir, file)
            new_file_path = os.path.join(envs_dir, new_file_name)
            os.rename(old_file_path, new_file_path)

            click.echo(f"Renamed environment file: {file} -> {new_file_name}")


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
        message: str = format_message("Library name should contain only letters, numbers, and underscores.")
        raise click.BadParameter(message)
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
        message: str = format_message("Project name should contain only letters, numbers, or dashes.")
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
        message: str = format_message(
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
        message: str = format_message("Invalid email address.")
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
        message: str = format_message("Environment name should contain only letters, numbers, and underscores.")
        raise click.BadParameter(message)
    return value


@cli.command()
@click.option(
    "--new-name",
    prompt="Enter the new base environment name to use:",
    callback=validate_env_name,
)
def rename_environments(new_name: str) -> None:
    """Iteratively renames environment files inside the 'envs' directory to use the input new_name as the base-name."""

    # This is basically the wrapper for the shared method.
    rename_all_envs(new_name=new_name)


def replace_markers_in_file(file_path: str, markers: dict[str, str]) -> int:
    """Replaces all occurrences of every marker in the input file contents with the appropriate replacement value.

    This method opens the file and scans through file contents searching for any of 'markers' dictionary keys. If keys
    are found, they are replaced with the corresponding value from the dictionary. This is used to replace the
    placeholder values used in template projects with user-defined values during project adoption.

    Args:
        file_path: The path to file in which to replace the markers.
        markers: A shallow dictionary that contains markers to replace as keys and replacement values as values.

    Returns:
        The number of placeholder values modified during this method's runtime. Minimum number is 0 for no
        modifications.
    """
    # Opens the file and reads its contents using utf-8 decoding.
    with open(file_path, "r") as f:
        content: str = f.read()

    # Loops over markers and replaces any occurrence of any marker inside the file contents with the corresponding
    # replacement value.
    modification_count: int = 0
    marker: str
    value: str
    for marker, value in markers.items():
        if marker in content:
            content = content.replace(marker, value)
            modification_count += 1

    # If any markers were modified, writes the modified contents back to file and notifies the user that the file has
    # been modified.
    if modification_count != 0:
        with open(file_path, "w") as f:
            f.write(content)
        click.echo(f"Replaced markers in {file_path}")
        return modification_count  # Returns the total number of positive modifications

    # If no markers were modified, returns 0.
    return modification_count


@cli.command()
@click.option(
    "--library-name",
    prompt="Enter the desired library name. This is what end-users will 'import'",
    callback=validate_library_name,
)
@click.option(
    "--project-name",
    prompt="Enter the desired project name. This is what end-users will 'pip install'",
    callback=validate_project_name,
)
@click.option(
    "--author-name",
    prompt="Enter the author name. The name can optionally include (GitHub Username)",
    callback=validate_author_name,
)
@click.option(
    "--email",
    prompt="Enter the email address. Has to be a well-formed email address",
    callback=validate_email,
)
@click.option(
    "--env-name",
    prompt="Enter the base environment name. Do not include _OStag, it is generated automatically",
    callback=validate_env_name,
)
def adopt_project(library_name: str, project_name: str, author_name: str, email: str, env_name: str) -> None:
    """Adopts a new project initialized from a standard Sun Lab template, by replacing placeholders in metadata and
    automation files with user-defined data.

    In addition to replacing placeholders inside a predefined set of files, this function also renames any files whose
    names match any of the markers. At this time, the function is used to set: project name, library name, development
    (conda) environment BASE-name, author name and author email. In the future, more markers may be added as needed.

    Note:
        Manual validation of all automation files is highly advised. This function is not intended to replace manual
        configuration, but only to expedite it in critical bottlenecks. It is very likely that your project will not
        work as expected without additional configuration.

    Args:
        library_name: The name of the library. This is what the end-users will 'import' when they use the library.
        project_name: The name of the project. This is what the end-users will 'pip install'.
        author_name: The name of the author. If more than one author works on the library, you will need to manually
            add further authors through pyproject.toml. Can include (GitHubUsername).
        email: The email address of the author. For multiple authors, see above.
        env_name: The base name to use for the conda (or mamba) environment used by the project. This primarily
            controls the name automatically given to all exported conda files (via export-env automation command).

    Raises:
        RuntimeError: If the adoption process fails for any reason.
    """
    # Sets the initial scanning directory to the current active directory.
    project_dir: str = resolve_project_directory()

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
        "utilities_test.py",
    )

    # Uses the input environment name to rename all environment files inside the 'envs' folder. This renames both file
    # names and the 'name' field values inside the .yml files. This step has to be done first as the loop below can
    # and does rename files, but not in the specific way required for this step.
    rename_all_envs(env_name)

    try:
        # Loops over all files inside the script directory, which should be project root directory.
        total_markers: int = 0  # Tracks the number of replaced markers.
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                # Gets the absolute path to each scanned file.
                # noinspection PyTypeChecker
                file_path: str = os.path.join(root, file)

                # If the file is inside the list of files ot be content-checks, removes markers from file contents.
                if file in file_names:
                    total_markers += replace_markers_in_file(file_path, markers)

                # Also processes file names in case they match any of the placeholders.
                file_base, file_ext = os.path.splitext(file)
                if file_base in markers:
                    new_file_name = markers[file_base] + file_ext
                    os.rename(file_path, os.path.join(root, new_file_name))
                    click.echo(f"Renamed file: {file_path} -> {new_file_name}")

            for directory in dirs:
                # Gets the absolute path to each scanned directory.
                # noinspection PyTypeChecker
                dir_path: str = os.path.join(root, directory)

                # If directory name matches one of the markers, renames the directory.
                if directory in markers:
                    new_dir_name = markers[directory]
                    new_dir_path = os.path.join(root, new_dir_name)
                    os.rename(dir_path, new_dir_path)
                    click.echo(f"Renamed directory: {dir_path} -> {new_dir_path}")

                    # Update the directory name in the dirs list to avoid potential issues with os.walk
                    dirs[dirs.index(directory)] = new_dir_name

        # Provides the final reminder
        message: str = format_message(
            f"Project Adoption: Complete. Be sure to manually verify critical files such as pyproject.toml before "
            f"proceeding to the next step. Overall, found and replaced {total_markers} markers in scanned file "
            f"contents."
        )
        click.echo(message)

    except Exception as e:
        message = format_message(f"Error replacing markers: {str(e)}")
        click.echo(message, err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
