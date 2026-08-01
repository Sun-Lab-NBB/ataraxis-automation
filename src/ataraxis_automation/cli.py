"""Provides a Command Line Interface (CLI) that automates certain project building and development steps."""

import re  # pragma: no cover
import base64  # pragma: no cover
from pathlib import Path  # pragma: no cover
import subprocess  # pragma: no cover
from configparser import ConfigParser  # pragma: no cover

import click  # pragma: no cover

from .automation import (  # pragma: no cover
    ProjectEnvironment,
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
    resolve_documented_project_directory,
)

_MINIMUM_PYPI_TOKEN_LENGTH: int = 100  # pragma: no cover
"""Stores the minimum length, in characters, that a valid PyPI API token may have."""  # pragma: no cover
_MAXIMUM_PYPI_TOKEN_LENGTH: int = 500  # pragma: no cover
"""Stores the maximum length, in characters, that a valid PyPI API token may have."""  # pragma: no cover
_MINIMUM_NETLIFY_TOKEN_LENGTH: int = 20  # pragma: no cover
"""Stores the minimum length, in characters, that a valid Netlify API token may have."""  # pragma: no cover
_MAXIMUM_NETLIFY_TOKEN_LENGTH: int = 500  # pragma: no cover
"""Stores the maximum length, in characters, that a valid Netlify API token may have."""  # pragma: no cover

# Ensures that displayed CLICK help messages are formatted according to the lab standard.
CONTEXT_SETTINGS: dict[str, int] = {"max_content_width": 120}  # pragma: no cover


@click.group(context_settings=CONTEXT_SETTINGS)
def cli() -> None:  # pragma: no cover
    """Exposes the helper commands used to automate various project development and building steps.

    Commands exposed by this interface are intended to be called via the 'tox' automation manager and should not be
    used directly by end-users.
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
    click.echo(colorize_message(message=message, color="green"))


@cli.command()
def process_stubs() -> None:  # pragma: no cover
    """Distributes the stub files from the /stubs directory to the appropriate level of the /src or src/library_name
    directory (depending on the type of the processed project).

    Once all stub files are distributed, removes the /stubs directory.
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
        raise RuntimeError(format_message(message=message))

    # Moves the stubs to the appropriate source code directories.
    move_stubs(stubs_directory=stubs_path, library_root=library_root)
    # Removes the /stubs directory once all stubs are moved.
    robust_rmtree(path=stubs_path)
    message = "Stubs successfully distributed to appropriate source code directories."
    click.echo(colorize_message(message=message, color="green"))


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
    click.echo(colorize_message(message=message, color="green"))


@cli.command()
@click.option(
    "-rt",
    "--replace-token",
    is_flag=True,
    help=(
        "If this flag is provided, the command replaces the API token stored in the shared .pypirc file even if "
        "that file already contains a valid token."
    ),
)
def acquire_pypi_token(*, replace_token: bool) -> None:  # pragma: no cover
    """Ensures that a validly formatted PyPI API token is contained in the .pypirc file stored in the shared
    application directory.
    """
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    # The token is the same for every project uploaded from this machine, so it is stored in the shared application
    # directory instead of the root directory of each project.
    pypirc_path: Path = resolve_pypirc_path()

    if migrate_legacy_pypirc(project_root=project_root):
        message: str = (
            f"Existing PyPI token migrated from the project's '.pypirc' file to the shared '.pypirc' file stored "
            f"under {pypirc_path.parent}. The project-local file is no longer used and can be deleted."
        )
        click.echo(colorize_message(message=message, color="yellow"))

    # If the file exists, recreating the file is not requested, and the file appears well-formed, ends the runtime.
    if verify_pypirc(file_path=pypirc_path) and not replace_token:
        message = "Existing PyPI token found inside the shared '.pypirc' file."
        click.echo(colorize_message(message=message, color="green"))
        return

    # Otherwise, proceeds to generating a new file and token entry.
    message = (
        "Unable to use the existing PyPI token: the shared '.pypirc' file does not exist, is invalid, or "
        "does not contain a valid PyPI API token. Proceeding to new token acquisition."
    )
    click.echo(colorize_message(message=message, color="white"))

    # Enters the while loop to iteratively ask for the token until a valid token entry is provided.
    while True:
        prompt: str = format_message(
            message="Enter the PyPI (API) token. It will be stored inside the shared .pypirc file and reused by all "
            "projects managed on this machine. Input is hidden",
        )
        # Asks the user for the token.
        token: str = click.prompt(text=prompt, hide_input=True, type=str)

        token = token.strip()

        # Validates the token using multiple heuristics for what a well-formed PyPI token should look like.
        # Checks non-emptiness, prefix, length constraints, base64 URL-safe character set, and absence of whitespace.
        valid = (
            token
            and token.startswith("pypi-")
            and _MINIMUM_PYPI_TOKEN_LENGTH <= len(token) <= _MAXIMUM_PYPI_TOKEN_LENGTH
            and token[5:]
            and re.match(r"^[A-Za-z0-9\-_]+=*$", token[5:])
            and " " not in token
            and "\n" not in token
            and "\r" not in token
            and "\t" not in token
        )

        # Additional base64 validation.
        if valid:
            try:
                token_body = token[5:]
                padding_needed = (4 - len(token_body) % 4) % 4
                base64.urlsafe_b64decode(token_body + ("=" * padding_needed))
            except Exception:
                valid = False

        # Handles invalid token inputs.
        if not valid:
            message = "The input token does not appear to be a valid PyPI token."
            click.echo(colorize_message(message=message, color="red"))
            if not click.confirm("Do you want to try entering another token?"):
                message = "PyPI token acquisition: aborted by user."
                raise RuntimeError(format_message(message=message))
            continue

        # Generates the new .pypirc file and saves the valid token data to the file.
        config = ConfigParser()
        config["pypi"] = {"username": "__token__", "password": token}
        with pypirc_path.open(mode="w") as config_file:
            config.write(config_file)

        # Notifies the user and breaks out of the while loop.
        message = f"Valid PyPI token acquired and added to the shared '.pypirc' file stored under {pypirc_path.parent}."
        click.echo(colorize_message(message=message, color="green"))
        break


@cli.command()
@click.option(
    "-rt",
    "--replace-token",
    is_flag=True,
    help=(
        "If this flag is provided, the command replaces the API token stored in the shared .netlifyrc file even if "
        "that file already contains a valid token."
    ),
)
@click.option(
    "-rs",
    "--replace-site",
    is_flag=True,
    help=(
        "If this flag is provided, the command replaces the site identifier stored in the project's .netlify-site "
        "file even if that file already contains an identifier."
    ),
)
def acquire_netlify_token(*, replace_token: bool, replace_site: bool) -> None:  # pragma: no cover
    """Ensures that the project's .netlify-site file contains the Netlify site identifier and that the shared
    .netlifyrc file contains a validly formatted Netlify API token.
    """
    # Verifies that the working directory is pointing to a project that builds API documentation and resolves the
    # absolute path to the project's root directory.
    project_root: Path = resolve_documented_project_directory()

    # The token authenticates the account that owns every deployed site, so it is stored in the shared application
    # directory. The site identifier differs for each project, so it is stored in the project's root directory.
    netlifyrc_path: Path = resolve_netlifyrc_path()

    if migrate_legacy_netlifyrc(project_root=project_root):
        message: str = (
            f"Existing Netlify credentials migrated from the project's '.netlifyrc' file to the shared '.netlifyrc' "
            f"file stored under {netlifyrc_path.parent} and to the project's '.netlify-site' file. The project-local "
            f"'.netlifyrc' file is no longer used and can be deleted."
        )
        click.echo(colorize_message(message=message, color="yellow"))

    stored_site: str | None = read_netlify_site(project_root=project_root)
    if stored_site is not None and not replace_site:
        message = f"Existing Netlify site identifier '{stored_site}' found inside the project's '.netlify-site' file."
        click.echo(colorize_message(message=message, color="green"))
    else:
        # Enters the while loop to iteratively ask for the site identifier until a valid identifier is provided.
        while True:
            prompt: str = format_message(
                message="Enter the Netlify site domain name or API (UUID) identifier",
            )
            # Nearly all projects follow the shared site naming convention, so the derived identifier is offered as
            # the default and only has to be overridden by the projects that deviate from the convention.
            site: str = click.prompt(text=prompt, type=str, default=derive_netlify_site(project_root=project_root))

            # Accepts full site URLs by reducing them to the bare identifier expected by the Netlify API.
            site = site.strip().removeprefix("https://").removeprefix("http://").rstrip("/")

            # Validates that the identifier is not empty and does not contain characters that would corrupt the API
            # request path.
            if site and " " not in site and "/" not in site:
                break

            message = "The input identifier does not appear to be a valid Netlify site domain name or UUID."
            click.echo(colorize_message(message=message, color="red"))
            if not click.confirm("Do you want to try entering another site identifier?"):
                message = "Netlify credential acquisition: aborted by user."
                raise RuntimeError(format_message(message=message))

        write_netlify_site(project_root=project_root, site=site)
        message = (
            f"Netlify site identifier '{site}' added to the project's '.netlify-site' file. Commit the file, as it "
            f"identifies the site that serves this project's API documentation."
        )
        click.echo(colorize_message(message=message, color="green"))

    if verify_netlifyrc(file_path=netlifyrc_path) and not replace_token:
        message = "Existing Netlify API token found inside the shared '.netlifyrc' file."
        click.echo(colorize_message(message=message, color="green"))
        return

    message = (
        "Unable to use the existing Netlify token: the shared '.netlifyrc' file does not exist, is invalid, or does "
        "not contain a valid Netlify API token. Proceeding to new token acquisition."
    )
    click.echo(colorize_message(message=message, color="white"))

    # Enters the while loop to iteratively ask for the token until a valid token entry is provided.
    while True:
        token_prompt: str = format_message(
            message="Enter the Netlify (API) token. It will be stored inside the shared .netlifyrc file and reused by "
            "all projects managed on this machine. Input is hidden",
        )
        token: str = click.prompt(text=token_prompt, hide_input=True, type=str)

        token = token.strip()

        # Netlify tokens carry no prefix and no checksum, so the validation is limited to the length bounds and the
        # character set shared by all issued tokens.
        valid: bool = bool(
            token
            and _MINIMUM_NETLIFY_TOKEN_LENGTH <= len(token) <= _MAXIMUM_NETLIFY_TOKEN_LENGTH
            and re.match(r"^[A-Za-z0-9\-_]+$", token)
        )

        if valid:
            break

        message = "The input token does not appear to be a valid Netlify token."
        click.echo(colorize_message(message=message, color="red"))
        if not click.confirm("Do you want to try entering another token?"):
            message = "Netlify credential acquisition: aborted by user."
            raise RuntimeError(format_message(message=message))

    config: ConfigParser = ConfigParser()
    config["netlify"] = {"token": token}
    with netlifyrc_path.open(mode="w") as config_file:
        config.write(config_file)

    message = (
        f"Valid Netlify token acquired and added to the shared '.netlifyrc' file stored under {netlifyrc_path.parent}."
    )
    click.echo(colorize_message(message=message, color="green"))


@cli.command()
def deploy_docs() -> None:  # pragma: no cover
    """Deploys the API documentation built by the 'docs' task to the project's Netlify site."""
    # Verifies that the working directory is pointing to a project that builds API documentation and resolves the
    # absolute path to the project's root directory.
    project_root: Path = resolve_documented_project_directory()

    netlifyrc_path: Path = resolve_netlifyrc_path()

    if not verify_netlifyrc(file_path=netlifyrc_path):
        message: str = (
            "Unable to deploy the API documentation. The shared '.netlifyrc' file does not exist, is invalid, or does "
            "not contain the Netlify API token. Use the 'acquire-netlify-token' command to configure the file."
        )
        raise RuntimeError(format_message(message=message))

    site: str | None = read_netlify_site(project_root=project_root)
    if site is None:
        message = (
            "Unable to deploy the API documentation. The project's '.netlify-site' file does not exist or does not "
            "contain the Netlify site identifier. Use the 'acquire-netlify-token' command to configure the file."
        )
        raise RuntimeError(format_message(message=message))

    credentials: ConfigParser = ConfigParser()
    credentials.read(netlifyrc_path)

    website_url: str = deploy_documentation(
        documentation_directory=project_root.joinpath("docs", "build", "html"),
        site=site,
        token=credentials.get(section="netlify", option="token").strip(),
    )

    message = f"API documentation successfully deployed to {website_url}."
    click.echo(colorize_message(message=message, color="green"))


@cli.command()
def upload_project() -> None:  # pragma: no cover
    """Uploads the distributions built by the 'build' task to PyPI.

    This command resolves the PyPI API token from the shared application directory, so the project does not have to
    store the token in its root directory.
    """
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    pypirc_path: Path = resolve_pypirc_path()
    if not verify_pypirc(file_path=pypirc_path):
        message: str = (
            "Unable to upload the project to PyPI. The shared '.pypirc' file does not exist, is invalid, or does not "
            "contain a valid PyPI API token. Use the 'acquire-pypi-token' command to configure the file."
        )
        raise RuntimeError(format_message(message=message))

    distributions: list[str] = sorted(str(path) for path in project_root.joinpath("dist").glob("*") if path.is_file())
    if not distributions:
        message = (
            "Unable to upload the project to PyPI. The project's 'dist' directory does not exist or contains no "
            "distribution files. Build the distributions with the 'build' ('tox -e build') task before uploading "
            "them."
        )
        raise RuntimeError(format_message(message=message))

    try:
        subprocess.run(  # noqa: S603 - Every command element is generated by this library, not by user input.
            ["twine", "upload", *distributions, "--skip-existing", "--config-file", str(pypirc_path)],
            check=True,
        )
    except subprocess.CalledProcessError:
        message = (
            "Unable to upload the project to PyPI. See twine-generated error messages for specific details about the "
            "errors that prevented the upload."
        )
        raise RuntimeError(format_message(message=message)) from None

    message = "Project distributions successfully uploaded to PyPI."
    click.echo(colorize_message(message=message, color="green"))


@cli.command()
@click.option(
    "-e",
    "--environment-name",
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
@click.option(
    "--prerelease",
    is_flag=True,
    default=False,
    help="Determines whether uv is allowed to install prerelease versions of dependencies.",
)
def install_project(
    environment_name: str, environment_directory: Path | None, *, prerelease: bool
) -> None:  # pragma: no cover
    """Builds and installs the project into the specified mamba environment as a library."""
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    # Resolves the project's mamba environment data and generates a list of commands to interface with the environment.
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root,
        environment_name=environment_name,
        environment_directory=environment_directory,
        prerelease=prerelease,
    )

    # Checks if the project's mamba environment is accessible via subprocess activation call. If not, it raises an
    # error.
    if not environment.environment_exists():
        message = (
            f"Unable to activate the requested mamba environment '{environment.environment_name}', which likely means "
            f"that it does not exist. Use 'create-environment' ('tox -e create') command to create the environment."
        )
        raise RuntimeError(format_message(message=message))

    # Installs the project into the mamba environment.
    try:
        command: str = f"{environment.activate_command} && {environment.install_project_command}"
        subprocess.run(command, shell=True, check=True)
        message = (
            f"Project successfully installed into the requested mamba environment '{environment.environment_name}'."
        )
        click.echo(colorize_message(message=message, color="green"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to build and install the project into the requested mamba environment "
            f"'{environment.environment_name}'. See uv-generated error messages for specific details about the "
            f"errors that prevented the installation."
        )
        raise RuntimeError(format_message(message=message)) from None


@cli.command()
@click.option(
    "-e",
    "--environment-name",
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
        click.echo(colorize_message(message=message, color="yellow"))
        return

    try:
        command: str = f"{environment.activate_command} && {environment.uninstall_project_command}"
        subprocess.run(command, shell=True, check=True)
        message = (
            f"Project successfully uninstalled from the requested mamba environment '{environment.environment_name}'."
        )
        click.echo(colorize_message(message=message, color="green"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to uninstall the project from the requested mamba environment '{environment.environment_name}'. "
            f"See uv-generated error messages for specific details about the errors that prevented the uninstallation."
        )
        raise RuntimeError(format_message(message=message)) from None


@cli.command()
@click.option(
    "-e",
    "--environment-name",
    required=True,
    type=str,
    help="The name of the project's mamba environment without the os-suffix, e.g: 'project_dev'.",
)
@click.option(
    "-p",
    "--python-version",
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
@click.option(
    "--prerelease",
    is_flag=True,
    default=False,
    help="Determines whether uv is allowed to install prerelease versions of dependencies.",
)
def create_environment(
    environment_name: str, python_version: str, environment_directory: Path | None, *, prerelease: bool
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
        prerelease=prerelease,
    )

    # Checks if the project's mamba environment is accessible via subprocess activation call. If it is accessible
    # (exists), notifies the user that the environment already exists and concludes the runtime.
    if environment.environment_exists():
        message = (
            f"Requested mamba environment '{environment.environment_name}' already exists. Creation process aborted "
            f"without further actions. To recreate the environment, run 'provision-environment' ('tox -e provision') "
            f"command instead."
        )
        click.echo(colorize_message(message=message, color="yellow"))
        return

    # Creates the new environment.
    try:
        subprocess.run(environment.create_command, shell=True, check=True)
        message = f"Created '{environment.environment_name}' mamba environment."
        click.echo(colorize_message(message=message, color="white"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to create the project's mamba environment '{environment.environment_name}'. See the mamba-issued "
            f"error-messages above for more information."
        )
        raise RuntimeError(format_message(message=message)) from None

    # If the environment was successfully created, installs project dependencies.
    try:
        command = f"{environment.activate_command} && {environment.install_dependencies_command}"
        subprocess.run(command, shell=True, check=True)
        message = f"Installed project dependencies into created '{environment.environment_name}' mamba environment."
        click.echo(colorize_message(message=message, color="white"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to install project dependencies into created '{environment.environment_name}' mamba environment. "
            f"See uv-generated error messages above for more information."
        )
        raise RuntimeError(format_message(message=message)) from None

    # Displays the final success message.
    message = (
        f"Created '{environment.environment_name}' mamba environment and installed all project dependencies into the "
        f"environment."
    )
    click.echo(colorize_message(message=message, color="green"))


@cli.command()
@click.option(
    "-e",
    "--environment-name",
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
    """Removes (deletes) the project's mamba environment and its environment directory, if either exists."""
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
        click.echo(colorize_message(message=message, color="yellow"))
        return

    # Handles a rare case where the environment does not exist, but its directory exists. In this case, removes the
    # directory and ends the runtime.
    if not environment_exists and directory_exists:
        robust_rmtree(path=environment.environment_directory)
        message = f"Removed mamba environment '{environment.environment_name}'."
        click.echo(colorize_message(message=message, color="green"))
        return

    # Otherwise, ensures the environment is not active and carries out the full removal procedure.
    try:
        command: str = f"{environment.deactivate_command} && {environment.remove_command}"
        subprocess.run(command, shell=True, check=True)
        # Ensures the environment directory is deleted.
        if environment.environment_directory.exists():
            robust_rmtree(path=environment.environment_directory)
        message = f"Removed mamba environment '{environment.environment_name}'."
        click.echo(colorize_message(message=message, color="green"))

    except subprocess.CalledProcessError:
        message = (
            f"Unable to remove the requested mamba environment '{environment.environment_name}'. See the mamba-issued "
            f"error-messages above for more information."
        )
        raise RuntimeError(format_message(message=message)) from None


@cli.command()
@click.option(
    "-e",
    "--environment-name",
    required=True,
    type=str,
    help="The name of the project's mamba environment without the os-suffix, e.g: 'project_dev'.",
)
@click.option(
    "-p",
    "--python-version",
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
@click.option(
    "--prerelease",
    is_flag=True,
    default=False,
    help="Determines whether uv is allowed to install prerelease versions of dependencies.",
)
def provision_environment(
    environment_name: str, python_version: str, environment_directory: Path | None, *, prerelease: bool
) -> None:  # pragma: no cover
    """Recreates the project's mamba environment and installs the project dependencies into the recreated
    environment.
    """
    # Verifies that the working directory is pointing to a project with the necessary key directories and files
    # (src, envs, pyproject.toml, tox.ini) and resolves the absolute path to the project's root directory.
    project_root: Path = resolve_project_directory()

    # Resolves the project's mamba environment data and generates a list of commands to interface with the environment.
    environment = ProjectEnvironment.resolve_project_environment(
        project_root=project_root,
        environment_name=environment_name,
        python_version=python_version,
        environment_directory=environment_directory,
        prerelease=prerelease,
    )

    # Checks if the project's mamba environment is accessible via subprocess activation call. If it is not accessible
    # (does not exist), skips the environment removal step.
    if not environment.environment_exists():
        # Ensures the environment directory also does not exist.
        if environment.environment_directory.exists():
            robust_rmtree(path=environment.environment_directory)
    else:
        # Otherwise, removes the existing environment.
        try:
            command: str = f"{environment.deactivate_command} && {environment.remove_command}"
            subprocess.run(command, shell=True, check=True)
            # Ensures the environment directory is deleted.
            if environment.environment_directory.exists():
                robust_rmtree(path=environment.environment_directory)
            message = f"Removed mamba environment '{environment.environment_name}'."
            click.echo(colorize_message(message=message, color="green"))

        except subprocess.CalledProcessError:
            message = (
                f"Unable to provision the requested mamba environment '{environment.environment_name}'. The process "
                f"failed at the environment removal step. See the mamba-issued error-messages above for more "
                f"information."
            )
            raise RuntimeError(format_message(message=message)) from None

    # Recreates the environment.
    try:
        subprocess.run(environment.create_command, shell=True, check=True)
        message = f"Created fresh '{environment.environment_name}' mamba environment."
        click.echo(colorize_message(message=message, color="white"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to provision the requested mamba environment '{environment.environment_name}'. See the "
            f"mamba-issued error-messages above for more information."
        )
        raise RuntimeError(format_message(message=message)) from None

    # Installs all project dependencies using uv into the newly created environment.
    try:
        command = f"{environment.activate_command} && {environment.install_dependencies_command}"
        subprocess.run(command, shell=True, check=True)
        message = (
            f"Installed all project dependencies into the provisioned '{environment.environment_name}' mamba "
            f"environment."
        )
        click.echo(colorize_message(message=message, color="white"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to install project dependencies into the provisioned '{environment.environment_name}' mamba "
            f"environment. See uv-generated error messages above for more information."
        )
        raise RuntimeError(format_message(message=message)) from None

    # Displays the final success message.
    message = f"Successfully provisioned '{environment.environment_name}' mamba environment."
    click.echo(colorize_message(message=message, color="green"))


@cli.command()
@click.option(
    "-e",
    "--environment-name",
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
    if not environment.environment_exists() and environment.create_from_yaml_command is not None:
        try:
            subprocess.run(environment.create_from_yaml_command, shell=True, check=True)
            message: str = (
                f"'{environment.environment_name}' mamba environment imported (created) from existing .yml file."
            )
            click.echo(colorize_message(message=message, color="green"))
        except subprocess.CalledProcessError:
            message = (
                f"Unable to import (create) the mamba environment '{environment.environment_name}' from existing .yml "
                f"file. See mamba-issued error-message above for more information."
            )
            raise RuntimeError(format_message(message=message)) from None

    # If the mamba environment already exists and the .yml file exists, updates the environment using the .yml file.
    elif environment.update_command is not None:
        try:
            subprocess.run(environment.update_command, shell=True, check=True)
            message = f"Existing '{environment.environment_name}' mamba environment updated from .yml file."
            click.echo(colorize_message(message=message, color="green"))
        except subprocess.CalledProcessError:
            message = (
                f"Unable to update the existing mamba environment '{environment.environment_name}' from .yml file. "
                f"See mamba-issued error-message above for more information."
            )
            raise RuntimeError(format_message(message=message)) from None
    # If the .yml file does not exist, aborts with error.
    else:
        message = (
            f"Unable to import or update the '{environment.environment_name}' mamba environment as there is no valid "
            f".yml file inside the /envs directory for the given project and operating system combination. Use the "
            f"'create-environment' ('tox -e create') command to create the environment from the pyproject.toml file."
        )
        raise RuntimeError(format_message(message=message))


@cli.command()
@click.option(
    "-e",
    "--environment-name",
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
    """Exports the requested mamba environment as a .yml file to the /envs directory."""
    # Resolves the project directory. Verifies that the working directory is pointing to a project with the necessary
    # key directories and files (src, envs, pyproject.toml, tox.ini).
    project_root: Path = resolve_project_directory()

    # Resolves the project's mamba environment data and generates a list of commands to interface with the environment.
    # Since python_version is not provided, this uses the default value, which this command does not depend on.
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
        raise RuntimeError(format_message(message=message))

    # Exports environment as a .yml file.
    try:
        subprocess.run(environment.export_yaml_command, shell=True, check=True)
        message = f"'{environment.environment_name}' mamba environment exported to /envs as a .yml file."
        click.echo(colorize_message(message=message, color="green"))
    except subprocess.CalledProcessError:
        message = (
            f"Unable to export the '{environment.environment_name}' mamba environment to .yml file. See mamba-issued "
            f"error-message above for more information."
        )
        raise RuntimeError(format_message(message=message)) from None
