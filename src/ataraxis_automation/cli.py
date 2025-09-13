"""This module provides a Command Line Interface (CLI) that automates certain project building and development steps."""

import re  # pragma: no cover
import base64  # pragma: no cover
import shutil  # pragma: no cover
from pathlib import Path  # pragma: no cover
import subprocess  # pragma: no cover
from configparser import ConfigParser  # pragma: no cover

import click  # pragma: no cover

from .automation import (  # pragma: no cover
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

# Defines minimum and maximum token lengths used when verifying PYPI tokens.
_MINIMUM_PYPI_TOKEN_LENGTH = 100  # pragma: no cover
_MAXIMUM_PYPI_TOKEN_LENGTH = 500  # pragma: no cover

# Ensures that displayed CLICK help messages are formatted according to the lab standard.
CONTEXT_SETTINGS = {"max_content_width": 120}  # pragma: no cover


@click.group(context_settings=CONTEXT_SETTINGS)
def cli() -> None:  # pragma: no cover
    """This command-line interface exposes the helper environment used to automate various project development and
    building steps. Commands exposed by this interface are intended to be called via the 'tox' automation manager and
    should not be used directly by end-users.
    """


@cli.command()
def process_typed_markers() -> None:  # pragma: no cover
    """Crawls the library root directory and ensures that the 'py.typed' marker is found only at the highest level of
    the library hierarchy (the highest directory with __init__.py in it).
    """
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    # Resolves (finds) the root library directory (typically one level down under 'src').
    library_root: Path = resolve_library_root(project_root=project_root)

    # Ensures that the py.typed marker file is only found inside the library root directory.
    generate_typed_marker(library_root=library_root)
    message: str = "Typed (py.typed) marker(s) successfully processed."
    click.echo(colorize_message(message, color="green"))


@cli.command()
def process_stubs() -> None:  # pragma: no cover
    """Distributes the stub files from the /stubs directory to the appropriate level of the /src or src/library_name
    directory (depending on the type of the processed project).
    """
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    # Resolves (finds) the root library directory (typically one level down under 'src').
    library_root: Path = resolve_library_root(project_root=project_root)

    # Generates the path to the 'stubs' folder, which is expected to be a subdirectory under the project root directory.
    stubs_path: Path = project_root.joinpath("stubs")

    if not stubs_path.exists():
        message: str = (
            f"Unable to move generated stub (.pyi) files from {stubs_path} to {library_root}. Stubs directory does "
            f"not exist under the project root directory."
        )
        raise RuntimeError(format_message(message))

    # Moves the stubs to the appropriate source code directories
    move_stubs(stubs_dir=stubs_path, library_root=library_root)
    shutil.rmtree(stubs_path)  # Removes the /stubs directory once all stubs are moved
    message = "Stubs successfully distributed to appropriate source code directories."
    click.echo(colorize_message(message, color="green"))


@cli.command()
def purge_stubs() -> None:  # pragma: no cover
    """Removes all existing stub (.pyi) files from the library source code directories."""
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    # Resolves (finds) the root library directory (typically one level down under 'src').
    library_root: Path = resolve_library_root(project_root=project_root)

    # Removes all stub files from the library source code folder.
    delete_stubs(library_root=library_root)
    message: str = "Existing stub (.pyi) files purged from all source code directories."
    click.echo(colorize_message(message, color="green"))


@cli.command()
@click.option(
    "-rt",
    "--replace-token",
    is_flag=True,
    help="If this flag is provided, the command recreates the .pypirc file even if it already contains an API token.",
)
def acquire_pypi_token(*, replace_token: bool) -> None:  # pragma: no cover
    """Ensures that a validly formatted PyPI API token is contained in the .pypirc file stored in the root directory
    of the project.
    """
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    # Generates the path to the .pypirc file. The file is expected to be found inside the root directory of the project.
    pypirc_path: Path = project_root.joinpath(".pypirc")

    # If the file exists, recreating the file is not requested, and the file appears well-formed, ends the runtime.
    if verify_pypirc(pypirc_path) and not replace_token:
        message: str = "Existing PyPI token found inside the '.pypirc' file."
        click.echo(colorize_message(message, color="green"))
        return

    # Otherwise, proceeds to generating a new file and token entry.
    message = (
        "Unable to use the existing PyPI token: the project's '.pypirc' file does not exist, is invalid, or "
        "does not contain a valid PyPI API token. Proceeding to new token acquisition."
    )
    click.echo(colorize_message(message, color="white"))

    # Enters the while loop to iteratively ask for the token until a valid token entry is provided.
    while True:
        prompt: str = format_message(
            message="Enter the PyPI (API) token. It will be stored inside the .pypirc file for future use. "
            "Input is hidden: ",
        )
        # Asks the user for the token.
        token: str = click.prompt(text=prompt, hide_input=True, type=str)

        # Strips whitespaces from the input string
        token = token.strip()

        # Validates the token using multiple heuristic for what a well-formed PyPI token should look like
        valid = (
            token  # Not empty
            and token.startswith("pypi-")  # Has the correct prefix
            and _MINIMUM_PYPI_TOKEN_LENGTH <= len(token) <= _MAXIMUM_PYPI_TOKEN_LENGTH  # Has a reasonable length
            and len(token[5:]) > 0  # Has body after the prefix
            and re.match(r"^[A-Za-z0-9\-_]+=*$", token[5:])  # Uses valid base64 URL-safe chars
            and " " not in token  # Contains no spaces
            and "\n" not in token
            and "\r" not in token
            and "\t" not in token  # Does not have whitespace characters
        )

        # Additional base64 validation
        if valid:
            try:
                token_body = token[5:]
                padding_needed = (4 - len(token_body) % 4) % 4
                base64.urlsafe_b64decode(token_body + ("=" * padding_needed))
            except Exception:
                valid = False

        # Handles invalid token inputs
        if not valid:
            message = "The input token does not appear to be a valid PyPI token."
            click.echo(colorize_message(message, color="red"))
            if not click.confirm("Do you want to try entering another token?"):
                message = "PyPI token acquisition: aborted by user."
                raise RuntimeError(format_message(message))
            continue

        # Generates the new .pypirc file and saves the valid token data to the file.
        config = ConfigParser()
        config["pypi"] = {"username": "__token__", "password": token}
        with pypirc_path.open("w") as config_file:
            # noinspection PyTypeChecker
            config.write(config_file)

        # Notifies the user and breaks out of the while loop
        message = "Valid PyPI token acquired and added to the project's '.pypirc' file for future use."
        click.echo(colorize_message(message, color="green"))
        break


@cli.command()
@click.option(
    "-e",
    "--environment_name",
    required=True,
    type=str,
    help="The name of the project's mamba environment without the os-suffix, e.g: 'project_dev'.",
)
@click.option(
    "-ed",
    "--environment-directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the local conda / mamba environments directory. This optional argument allows overriding "
        "the default environment detection procedure when it fails."
    ),
)
def install_project(environment_name: str, environment_directory: Path | None) -> None:  # pragma: no cover
    """Builds and installs the project into the specified mamba environment as a library."""
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    # Resolves the project's mamba environment data and generates a list of commands to interface with the environment.
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root,
        environment_name=environment_name,
        environment_directory=environment_directory,
    )

    # Checks if the project's mamba environment is accessible via subprocess activation call. If not, it raises an
    # error.
    if not environment.environment_exists():
        message = (
            f"Unable to activate the requested mamba environment '{environment.environment_name}', which likely means "
            f"that it does not exist. Use 'create-environment' ('tox -e create') command to create the environment."
        )
        raise RuntimeError(format_message(message))

    # Installs the project into the mamba environment.
    try:
        command: str = f"{environment.activate_command} && {environment.install_project_command}"
        subprocess.run(command, shell=True, check=True)
        message = (
            f"Project successfully installed into the requested mamba environment '{environment.environment_name}'."
        )
        click.echo(colorize_message(message, color="green"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to build and install the project into the requested mamba environment "
            f"'{environment.environment_name}'. See uv-generated error messages for specific details about the "
            f"errors that prevented the installation."
        )
        raise RuntimeError(format_message(message)) from None


@cli.command()
@click.option(
    "-e",
    "--environment_name",
    required=True,
    type=str,
    help="The name of the project's mamba environment without the os-suffix, e.g: 'project_dev'.",
)
@click.option(
    "-ed",
    "--environment-directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the local conda / mamba environments directory. This optional argument allows overriding "
        "the default environment detection procedure when it fails."
    ),
)
def uninstall_project(environment_name: str, environment_directory: Path | None) -> None:  # pragma: no cover
    """Uninstalls the project library from the specified mamba environment."""
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    # Resolves the project's mamba environment data and generates a list of commands to interface with the environment.
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root, environment_name=environment_name, environment_directory=environment_directory
    )

    # Attempts to activate the target mamba environment. If activation fails, concludes that the environment does not
    # exist and aborts the runtime.
    if not environment.environment_exists():
        message: str = (
            f"Requested mamba environment '{environment.environment_name}' is not accessible (likely does not exist). "
            f"Uninstallation process aborted without further actions."
        )
        click.echo(colorize_message(message, color="yellow"))
        return

    try:
        command: str = f"{environment.activate_command} && {environment.uninstall_project_command}"
        subprocess.run(command, shell=True, check=True)
        message = (
            f"Project successfully uninstalled from the requested mamba environment '{environment.environment_name}'."
        )
        click.echo(colorize_message(message, color="green"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to uninstall the project from the requested mamba environment '{environment.environment_name}'. "
            f"See uv-generated error messages for specific details about the errors that prevented the uninstallation."
        )
        raise RuntimeError(format_message(message)) from None


@cli.command()
@click.option(
    "-e",
    "--environment_name",
    required=True,
    type=str,
    help="The name of the project's mamba environment without the os-suffix, e.g: 'project_dev'.",
)
@click.option(
    "-p",
    "--python_version",
    required=True,
    type=str,
    help="The python version to use for the project's mamba environment, e.g. '3.13'.",
)
@click.option(
    "-ed",
    "--environment-directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the local conda / mamba environments directory. This optional argument allows overriding "
        "the default environment detection procedure when it fails."
    ),
)
def create_environment(
    environment_name: str, python_version: str, environment_directory: Path | None
) -> None:  # pragma: no cover
    """Creates the project's mamba environment and installs the project dependencies into the created environment."""
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    # Resolves the project's mamba environment data and generates a list of commands to interface with the environment.
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root,
        environment_name=environment_name,
        python_version=python_version,
        environment_directory=environment_directory,
    )

    # Checks if the project's mamba environment is accessible via subprocess activation call. If it is accessible
    # (exists), notifies the user that the environment already exists and concludes the runtime.
    if environment.environment_exists():
        message = (
            f"Requested mamba environment '{environment.environment_name}' already exists. Creation process aborted "
            f"without further actions. To recreate the environment, run 'provision-environment' ('tox -e provision') "
            f"command instead."
        )
        click.echo(colorize_message(message, color="yellow"))
        return

    # Creates the new environment
    try:
        subprocess.run(environment.create_command, shell=True, check=True)
        message = f"Created '{environment.environment_name}' conda environment."
        click.echo(colorize_message(message, color="white"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to create the project's mamba environment '{environment.environment_name}'. See the mamba-issued "
            f"error-messages above for more information."
        )
        raise RuntimeError(format_message(message)) from None

    # If the environment was successfully created, installs project dependencies.
    try:
        command = f"{environment.activate_command} && {environment.install_dependencies_command}"
        subprocess.run(command, shell=True, check=True)
        message = f"Installed project dependencies into created '{environment.environment_name}' mamba environment."
        click.echo(colorize_message(message, color="white"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to install project dependencies into created '{environment.environment_name}' mamba environment. "
            f"See uv-generated error messages above for more information."
        )
        raise RuntimeError(format_message(message)) from None

    # Displays the final success message.
    message = (
        f"Created '{environment.environment_name}' mamba environment and installed all project dependencies into the "
        f"environment."
    )
    click.echo(colorize_message(message, color="green"))


@cli.command()
@click.option(
    "-e",
    "--environment_name",
    required=True,
    type=str,
    help="The name of the project's mamba environment without the os-suffix, e.g: 'project_dev'.",
)
@click.option(
    "-ed",
    "--environment-directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the local conda / mamba environments directory. This optional argument allows overriding "
        "the default environment detection procedure when it fails."
    ),
)
def remove_environment(environment_name: str, environment_directory: Path | None) -> None:  # pragma: no cover
    """Removes (deletes) the project's mamba environment if it exists."""
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Resolves the project's mamba environment data and generates a list of commands to interface with the environment.
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root, environment_name=environment_name, environment_directory=environment_directory
    )

    # If the environment cannot be activated, it likely does not exist and no further processing is needed.
    environment_exists = environment.environment_exists()
    directory_exists = environment.environment_directory.exists()
    if not environment_exists and not directory_exists:
        message: str = (
            f"Unable to find the requested mamba environment '{environment.environment_name}'. This indicates that the "
            f"environment does not exist. Removal process aborted without further actions."
        )
        click.echo(colorize_message(message, color="yellow"))
        return

    # Handles a rare case where the environment does not exist, but its directory exists. In this case, removes the
    # directory and ends the runtime.
    if not environment_exists and directory_exists:
        shutil.rmtree(environment.environment_directory)
        message = f"Removed mamba environment '{environment.environment_name}'."
        click.echo(colorize_message(message, color="green"))

    # Otherwise, ensures the environment is not active and carries out the full removal procedure.
    try:
        command: str = f"{environment.deactivate_command} && {environment.remove_command}"
        subprocess.run(command, shell=True, check=True)
        # Ensures the environment directory is deleted.
        if environment.environment_directory.exists():
            shutil.rmtree(environment.environment_directory)
        message = f"Removed mamba environment '{environment.environment_name}'."
        click.echo(colorize_message(message, color="green"))

    except subprocess.CalledProcessError:
        message = (
            f"Unable to remove the requested mamba environment '{environment.environment_name}'. See the mamba-issued "
            f"error-messages above for more information."
        )
        raise RuntimeError(format_message(message)) from None


@cli.command()
@click.option(
    "-e",
    "--environment_name",
    required=True,
    type=str,
    help="The name of the project's mamba environment without the os-suffix, e.g: 'project_dev'.",
)
@click.option(
    "-p",
    "--python_version",
    required=True,
    type=str,
    help="The python version to use for the project's mamba environment, e.g. '3.13'.",
)
@click.option(
    "-ed",
    "--environment-directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the local conda / mamba environments directory. This optional argument allows overriding "
        "the default environment detection procedure when it fails."
    ),
)
def provision_environment(
    environment_name: str, python_version: str, environment_directory: Path | None
) -> None:  # pragma: no cover
    """Recreates the project's mamba environment."""
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    # Resolves the project's mamba environment data and generates a list of commands to interface with the environment.
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root,
        environment_name=environment_name,
        python_version=python_version,
        environment_directory=environment_directory,
    )

    # Checks if the project's mamba environment is accessible via subprocess activation call. If it is not accessible
    # (does not exist), skips the environment removal step.
    if not environment.environment_exists():
        # Ensures the environment directory also does not exist.
        if environment.environment_directory.exists():
            shutil.rmtree(environment.environment_directory)
    else:
        # Otherwise, removes the existing environment
        try:
            command: str = f"{environment.deactivate_command} && {environment.remove_command}"
            subprocess.run(command, shell=True, check=True)
            # Ensures the environment directory is deleted.
            if environment.environment_directory.exists():
                shutil.rmtree(environment.environment_directory)
            message = f"Removed mamba environment '{environment.environment_name}'."
            click.echo(colorize_message(message, color="green"))

        except subprocess.CalledProcessError:
            message = (
                f"Unable to provision the requested mamba environment '{environment.environment_name}'. The process "
                f"failed at the environment removal step. See the mamba-issued error-messages above for more "
                f"information."
            )
            raise RuntimeError(format_message(message)) from None

    # Recreates the environment
    try:
        subprocess.run(environment.create_command, shell=True, check=True)
        message = f"Created fresh '{environment.environment_name}' mamba environment."
        click.echo(colorize_message(message, color="white"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to provision the requested mamba environment '{environment.environment_name}'. See the "
            f"mamba-issued error-messages above for more information."
        )
        raise RuntimeError(format_message(message)) from None

    # Installs all project dependencies using uv into the newly created environment.
    try:
        command = f"{environment.activate_command} && {environment.install_dependencies_command}"
        subprocess.run(command, shell=True, check=True)
        message = (
            f"Installed all project dependencies into the provisioned '{environment.environment_name}' mamba "
            f"environment."
        )
        click.echo(colorize_message(message, color="white"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to install project dependencies into the provisioned '{environment.environment_name}' mamba "
            f"environment. See uv-generated error messages above for more information."
        )
        raise RuntimeError(format_message(message)) from None

    # Displays the final success message.
    message = f"Successfully provisioned '{environment.environment_name}' mamba environment."
    click.echo(colorize_message(message, color="green"))


@cli.command()
@click.option(
    "-e",
    "--environment_name",
    required=True,
    type=str,
    help="The name of the project's mamba environment without the os-suffix, e.g: 'project_dev'.",
)
@click.option(
    "-ed",
    "--environment-directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the local conda / mamba environments directory. This optional argument allows overriding "
        "the default environment detection procedure when it fails."
    ),
)
def import_environment(environment_name: str, environment_directory: Path | None) -> None:  # pragma: no cover
    """Creates or updates the existing project's mamba environment based on the operating-system-specific .yml file
    stored in the project /envs directory.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Resolves the project's mamba environment data and generates a list of commands to interface with the environment.
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root, environment_name=environment_name, environment_directory=environment_directory
    )

    # If the environment cannot be activated (likely does not exist) and the environment .yml file is found inside /envs
    # directory, uses .yml file to create a new environment.
    if not environment.environment_exists() and environment.create_from_yml_command is not None:
        try:
            subprocess.run(environment.create_from_yml_command, shell=True, check=True)
            message: str = (
                f"'{environment.environment_name}' mamba environment imported (created) from existing .yml file."
            )
            click.echo(colorize_message(message, color="green"))
        except subprocess.CalledProcessError:
            message = (
                f"Unable to import (create) the mamba environment'{environment.environment_name}' from existing .yml "
                f"file. See mamba-issued error-message above for more information."
            )
            raise RuntimeError(format_message(message)) from None

    # If the mamba environment already exists and the .yml file exists, updates the environment using the .yml file.
    elif environment.update_command is not None:
        try:
            subprocess.run(environment.update_command, shell=True, check=True)
            message = f"Existing '{environment.environment_name}' mamba environment updated from .yml file."
            click.echo(colorize_message(message, color="green"))
        except subprocess.CalledProcessError:
            message = (
                f"Unable to update the existing mamba environment '{environment.environment_name}' from .yml file. "
                f"See mamba-issued error-message above for more information."
            )
            raise RuntimeError(format_message(message)) from None
    # If the .yml file does not exist, aborts with error.
    else:
        message = (
            f"Unable to import or update the '{environment.environment_name}' mamba environment as there is no valid "
            f".yml file inside the /envs directory for the given project and operating system combination. Use the "
            f"'create-environment' ('tox -e create') command to create the environment from the pyproject.toml file."
        )
        raise RuntimeError(format_message(message))


@cli.command()
@click.option(
    "-e",
    "--environment_name",
    required=True,
    type=str,
    help="The name of the project's mamba environment without the os-suffix, e.g: 'project_dev'.",
)
@click.option(
    "-ed",
    "--environment-directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the local conda / mamba environments directory. This optional argument allows overriding "
        "the default environment detection procedure when it fails."
    ),
)
def export_environment(environment_name: str, environment_directory: Path | None) -> None:  # pragma: no cover
    """Exports the requested mamba environment as .yml and spec.txt files to the /envs directory."""
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Gets the list of environment that can be used to carry out mamba environment operations. Since
    # python_version is not provided, this uses the default value (but the python_version argument is not needed for
    # this function).
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root,
        environment_name=environment_name,
        environment_directory=environment_directory,
    )

    if not environment.environment_exists():
        message = (
            f"Unable to activate the requested mamba environment '{environment.environment_name}', which likely "
            f"indicates that it does not exist. Create the environment with 'create-environment' ('tox -e create') "
            f"before attempting to export it."
        )
        raise RuntimeError(format_message(message))

    # Exports environment as a .yml file
    try:
        subprocess.run(environment.export_yml_command, shell=True, check=True)
        message = f"'{environment.environment_name}' mamba environment exported to /envs as a .yml file."
        click.echo(colorize_message(message, color="green"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to export the '{environment.environment_name}' mamba environment to .yml file. See mamba-issued "
            f"error-message above for more information."
        )
        raise RuntimeError(format_message(message)) from None

    # Exports environment as a spec.txt file
    try:
        subprocess.run(environment.export_spec_command, shell=True, check=True)
        message = f"'{environment.environment_name}' mamba environment exported to /envs as a spec.txt file."
        click.echo(colorize_message(message, color="green"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to export the '{environment.environment_name}' mamba environment to spec.txt file. See "
            f"mamba-issued error-message above for more information."
        )
        raise RuntimeError(format_message(message)) from None
