"""This module provides a Command Line Interface (CLI) that automates certain project building and development steps.

The functions exposed through this module are intended to be called through appropriate 'tox' pipelines and should not
be used directly. They are designed to work with Sun Lab 'tox' tasks and may require significant refactoring to work
with other tox configurations.
"""

# pragma: no cover
import re
import base64
import shutil
from pathlib import Path
import subprocess
from configparser import ConfigParser

import click

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


@click.group()
def cli() -> None:  # pragma: no cover
    """This command-line interface exposes the helper environment used to automate various project development and
    building steps.
    """


@cli.command()
def process_typed_markers() -> None:  # pragma: no cover
    """Crawls the library root directory and ensures that the 'py.typed' marker is found only at the highest level of
    the library hierarchy (the highest directory with __init__.py in it).

    This command should be called as part of the stub-generation tox command ('tox -e stubs') to mark the library as
    typed for static linters.
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

    This command is intended to be called after the /stubs directory has been generated and filled by 'stubgen' as part
    of the tox stub-generation command ('tox -e stubs').
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
    """Removes all existing stub (.pyi) files from the library source code directories.

    This command is intended to be called as part of the tox linting task ('tox -e lint'). If stub files are present
    during linting, mypy (type-checker) preferentially processes stub files and ignores source code files. Removing the
    stubs before running mypy ensures it runs on the source code.
    """
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
def acquire_pypi_token(replace_token: bool) -> None:  # pragma: no cover
    """Ensures that a validly formatted PyPI API token is contained in the .pypirc file stored in the root directory
    of the project.

    This command is intended to be called before the tox pip-uploading task ('tox -e upload') to ensure that twine is
    able to access the PyPI API token. If the token is available from the '.pypirc' file and appears valid, it is used.
    If the file or the API token is not available or the user provides the 'replace-token' flag, the command recreates
    the file and prompts the user to provide a new token. The token is then added to the file for future (re)uses. The
    '.pypirc' file is added to gitignore distributed with each Sun lab project, so the token will remain private unless
    gitignore configuration is compromised.

    This command is currently not able to verify that the token works. Instead, it can only ensure the token is
    formatted in a PyPI-specified way (that it includes the pypi-prefix). If the token is not active or otherwise
    invalid, there is no way to know this before failing a twine upload.
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
            and 100 <= len(token) <= 500  # Has a reasonable length
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
            except:
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
def install_project(environment_name: str) -> None:  # pragma: no cover
    """Builds and installs the project into the specified mamba environment as a library.

    This command is primarily used to support project development by compiling and installing the developed project into
    the target environment to support testing. Since tests have to be written to use the compiled package, rather
    than the source code, to support tox testing, the project has to be rebuilt each time source code is changed, which
    is conveniently performed by this command.
    """
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    # Resolves the project's mamba environment data and generates a list of commands to interface with the environment.
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root,
        environment_name=environment_name,
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
        raise RuntimeError(format_message(message))


@cli.command()
@click.option(
    "-e",
    "--environment_name",
    required=True,
    type=str,
    help="The name of the project's mamba environment without the os-suffix, e.g: 'project_dev'.",
)
def uninstall_project(environment_name: str) -> None:  # pragma: no cover
    """Uninstalls the project library from the specified mamba environment.

    This command is not used in most modern automation pipelines but is kept for backward compatibility with legacy
    projects. Previously, it was used to remove the project from its mamba environment before running tests, as
    installed projects used to interfere with tox re-building the testing wheels in some cases.
    """
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    # Resolves the project's mamba environment data and generates a list of commands to interface with the environment.
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root,
        environment_name=environment_name,
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
    "-p",
    "--python_version",
    required=True,
    type=str,
    help="The python version to use for the project's mamba environment, e.g. '3.13'.",
)
def create_environment(environment_name: str, python_version: str) -> None:  # pragma: no cover
    """Creates the project's mamba environment and installs the project dependencies into the created environment.

    This command is intended to be called as part of the initial project setup on new machines and / or operating
    systems. For most runtimes, it is advised to import ('tox -e import') an existing .yml file if it is available. To
    reset an already existing environment, use the provision ('tox -e provision') command instead, which inlines
    removing and (re)creating the environment.
    """
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    # Resolves the project's mamba environment data and generates a list of commands to interface with the environment.
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root,
        environment_name=environment_name,
        python_version=python_version,
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
        raise RuntimeError(format_message(message))

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
        raise RuntimeError(format_message(message))

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
def remove_environment(environment_name: str) -> None:  # pragma: no cover
    """Removes (deletes) the project's mamba environment if it exists.

    This command can be used to clean up the project's mamba environment that is no longer needed. To reset the
    environment, it is recommended to use the 'provision-environment' ('tox -e provision') command instead, which
    removes and (re)creates the environment as a single operation.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Resolves the project's mamba environment data and generates a list of commands to interface with the environment.
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root,
        environment_name=environment_name,
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
    "-p",
    "--python_version",
    required=True,
    type=str,
    help="The python version to use for the project's mamba environment, e.g. '3.13'.",
)
def provision_environment(environment_name: str, python_version: str) -> None:  # pragma: no cover
    """Recreates the project's mamba environment.

    This command inlines removing and (re)creating the project's mamba environment, which effectively resets the
    requested environment.
    """
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    # Resolves the project's mamba environment data and generates a list of commands to interface with the environment.
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root,
        environment_name=environment_name,
        python_version=python_version,
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
            raise RuntimeError(format_message(message))

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
        raise RuntimeError(format_message(message))

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
        raise RuntimeError(format_message(message))

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
def import_environment(environment_name: str) -> None:  # pragma: no cover
    """Creates or updates the existing project's mamba environment based on the operating-system-specific .yml file
    stored in the project /envs directory.

    If the .yml file does not exist, it aborts processing with an error. This command used to be preferred over the
    'de-novo' environment creation, but modern Sun lab dependency resolution strategies ensure that using the .yml file
    and pyproject.toml creation procedures yields identical results in most cases.
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Resolves the project's mamba environment data and generates a list of commands to interface with the environment.
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root,
        environment_name=environment_name,
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
            raise RuntimeError(format_message(message))

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
            raise RuntimeError(format_message(message))
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
def export_environment(environment_name: str) -> None:  # pragma: no cover
    """Exports the requested mamba environment as .yml and spec.txt files to the /envs directory.

    This command is intended to be called as part of the pre-release checkout before building the source distribution
    for the project (and releasing the new project version).
    """
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Gets the list of environment that can be used to carry out mamba environment operations. Since
    # python_version is not provided, this uses the default value (but the python_version argument is not needed for
    # this function).
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root,
        environment_name=environment_name,
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
        raise RuntimeError(format_message(message))

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
        raise RuntimeError(format_message(message))
