from .automation import (
    ProjectEnvironment as ProjectEnvironment,
    move_stubs as move_stubs,
    delete_stubs as delete_stubs,
    verify_pypirc as verify_pypirc,
    format_message as format_message,
    colorize_message as colorize_message,
    resolve_library_root as resolve_library_root,
    generate_typed_marker as generate_typed_marker,
    resolve_project_directory as resolve_project_directory,
)

def cli() -> None:
    """This command-line interface exposes the helper environment used to automate various project development and
    building steps.
    """

def process_typed_markers() -> None:
    """Crawls the library root directory and ensures that the 'py.typed' marker is found only at the highest level of
    the library hierarchy (the highest directory with __init__.py in it).

    This command should be called as part of the stub-generation tox command ('tox -e stubs') to mark the library as
    typed for static linters.
    """

def process_stubs() -> None:
    """Distributes the stub files from the /stubs directory to the appropriate level of the /src or src/library_name
    directory (depending on the type of the processed project).

    This command is intended to be called after the /stubs directory has been generated and filled by 'stubgen' as part
    of the tox stub-generation command ('tox -e stubs').
    """

def purge_stubs() -> None:
    """Removes all existing stub (.pyi) files from the library source code directories.

    This command is intended to be called as part of the tox linting task ('tox -e lint'). If stub files are present
    during linting, mypy (type-checker) preferentially processes stub files and ignores source code files. Removing the
    stubs before running mypy ensures it runs on the source code.
    """

def acquire_pypi_token(replace_token: bool) -> None:
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

def install_project(environment_name: str) -> None:
    """Builds and installs the project into the specified mamba environment as a library.

    This command is primarily used to support project development by compiling and installing the developed project into
    the target environment to support testing. Since tests have to be written to use the compiled package, rather
    than the source code, to support tox testing, the project has to be rebuilt each time source code is changed, which
    is conveniently performed by this command.
    """

def uninstall_project(environment_name: str) -> None:
    """Uninstalls the project library from the specified mamba environment.

    This command is not used in most modern automation pipelines but is kept for backward compatibility with legacy
    projects. Previously, it was used to remove the project from its mamba environment before running tests, as
    installed projects used to interfere with tox re-building the testing wheels in some cases.
    """

def create_environment(environment_name: str, python_version: str) -> None:
    """Creates the project's mamba environment and installs the project dependencies into the created environment.

    This command is intended to be called as part of the initial project setup on new machines and / or operating
    systems. For most runtimes, it is advised to import ('tox -e import') an existing .yml file if it is available. To
    reset an already existing environment, use the provision ('tox -e provision') command instead, which inlines
    removing and (re)creating the environment.
    """

def remove_environment(environment_name: str) -> None:
    """Removes (deletes) the project's mamba environment if it exists.

    This command can be used to clean up the project's mamba environment that is no longer needed. To reset the
    environment, it is recommended to use the 'provision-environment' ('tox -e provision') command instead, which
    removes and (re)creates the environment as a single operation.
    """

def provision_environment(environment_name: str, python_version: str) -> None:
    """Recreates the project's mamba environment.

    This command inlines removing and (re)creating the project's mamba environment, which effectively resets the
    requested environment.
    """

def import_environment(environment_name: str) -> None:
    """Creates or updates the existing project's mamba environment based on the operating-system-specific .yml file
    stored in the project /envs directory.

    If the .yml file does not exist, it aborts processing with an error. This command used to be preferred over the
    'de-novo' environment creation, but modern Sun lab dependency resolution strategies ensure that using the .yml file
    and pyproject.toml creation procedures yields identical results in most cases.
    """

def export_environment(environment_name: str) -> None:
    """Exports the requested mamba environment as .yml and spec.txt files to the /envs directory.

    This command is intended to be called as part of the pre-release checkout before building the source distribution
    for the project (and releasing the new project version).
    """
