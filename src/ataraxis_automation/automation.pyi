import click
from .utilities import format_message as format_message
from os import PathLike
from typing import AnyStr

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
def delete_stubs(directory: str) -> None:
    """Removes all .pyi stub files from the given directory and its subdirectories.

    This function is intended to be used before linting as mypy tends to be biased to analyze the .pyi files, ignoring
    the source code. When .pyi files are not present, mypy reverts to properly analyzing the source code.

    Args:
        directory: The path to the root directory from which to start removing .pyi files.
    """
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
def cli() -> None:
    """This CLI exposes helper commands used to automate various project management steps. See below for details
    about the available commands.
    """
def process_typed_markers() -> None:
    """Crawls the '/src' directory and ensures that the 'py.typed' marker is found only at the highest level of the
    library hierarchy (the highest directory with __init__.py in it).

    This command should be called as part of the stub-generation tox command.

    Raises:
        RuntimeError: If root (highest) directory cannot be resolved. If the function runs into an error
            processing 'py.typed' markers. If 'src' directory does not exist.
    """
def process_stubs() -> None:
    """Distributes the stub files from the '/stubs' directory to the appropriate level of the '/src' or
     'src/library' directory (depending on the type of the processed project).

    Notes:
        This command should only be called after the /stubs directory has been generated using stubgen command from tox.

    Raises:
        RuntimeError: If root (highest) directory cannot be resolved. If the function runs into an error
            processing stubs. If 'src' or 'stubs directories do not exist.
    """
def purge_stubs() -> None:
    """Removes all existing stub (.pyi) files from the 'src' directory.

    This is a necessary step before running the linting task, as it forces mypy to type-check the source code instead
    of the stubs.

    Raises:
        RuntimeError: If root (highest) directory cannot be resolved. If the function runs into an error
            removing stubs. If 'src' directory does not exist.
    """
def generate_recipe_folder() -> None:
    """Generates the recipe folder used by Grayskull.

    Since Grayskull does not generate output folders by itself, this task is 'outsourced' to this command instead.

    Raises:
        RuntimeError: If the recipe folder cannot be generated for any reason.
    """
def is_valid_pypirc(file_path: str) -> bool:
    """Verifies that the .pypirc file pointed to by the input path contains valid options to support automatic
    authentication for pip uploads.

    Assumes that the file is used only to store the API token to upload compiled packages to pip. Does not verify any
    other information.

    Returns:
        True if the .pypirc is well-configured configured and False otherwise.
    """
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
def get_env_extension() -> str:
    """Determines the OS version used by the host platform and uses it to set the OS-postfix used in conda
    environment files.

    Currently, this command explicitly supports only 3 OS versions: OSx (Apple Silicon, Darwin), Linux and Windows.

    Returns: The postfix used to identify the Conda development environment for the host OS.

    Raises:
        BadParameter: If the host OS does not match any of the supported operating systems.
    """
def get_conda_cmdlet() -> str:
    """Determines whether mamba or conda can be accessed from this script by silently calling 'command --version'.

    If mamba is available, it is used over conda. This process optimizes conda-related operations
    (especially de novo environment creation) to use the fastest available engine.

    Returns:
        The string-name of the cmdlet to use for all conda (or mamba) related commands.

    Raises:
        RuntimeError: If neither conda nor mamba is accessible via subprocess call through the shell.
    """
def import_env() -> None:
    """Creates or updates an existing Conda environment based on the operating system-specific .yml file stored in
    'envs' folder.

    Uses the fastest available engine to resolve environment data (prefers mamba over conda, if mamba is available).

    Raises:
        RuntimeError: If there is no .yml file for the desired base-name and OS-extension combination in the 'envs'
            folder. If creation and update commands both fail for any reason. If 'envs' folder does not exist
    """
def get_export_command(cmdlet_name: str, env_name: str, yml_path: str, spec_path: str) -> tuple[str, str]:
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
def export_env(base_env: str) -> None:
    """Exports the OS-specific Conda environment as a .yml and as a spec.txt files.

    Args:
        base_env: The base name (e.g.: axt_dev) of the environment. The OS-specific postfix for the environment is
            resolved and appended automatically.

    Raises:
        RuntimeError: If 'envs' directory does not exist. If any environment export command fails for any reason.
    """
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
def validate_library_name(_ctx: click.Context, _param: click.Parameter, value: str) -> str:
    """Verifies that the input library name contains only letters, numbers, and underscores.

    Args:
        _ctx: Not used. Provided by click automatically.
        _param: Not used. Provided by click automatically.
        value: The string-value to check

    Raises:
        BadParameter: If the input value contains invalid characters.
    """
def validate_project_name(_ctx: click.Context, _param: click.Parameter, value: str) -> str:
    """Verifies that the input project name contains only letters, numbers, and dashes.

    Args:
        _ctx: Not used. Provided by click automatically.
        _param: Not used. Provided by click automatically.
        value: The string-value to check

    Raises:
        BadParameter: If the input value contains invalid characters.
    """
def validate_author_name(_ctx: click.Context, _param: click.Parameter, value: str) -> str:
    """Verifies that the input author name contains a valid human name and an optional GitHub username in parentheses.

    Args:
        _ctx: Not used. Provided by click automatically.
        _param: Not used. Provided by click automatically.
        value: The string-value to check

    Raises:
        BadParameter: If the input value does not match the expected format.
    """
def validate_email(_ctx: click.Context, _param: click.Parameter, value: str) -> str:
    """Verifies that the input email address contains only valid characters.

    Args:
        _ctx: Not used. Provided by click automatically.
        _param: Not used. Provided by click automatically.
        value: The string-value to check

    Raises:
        BadParameter: If the input value contains invalid characters.
    """
def validate_env_name(_ctx: click.Context, _param: click.Parameter, value: str) -> str:
    """Verifies that the input environment name contains only letters, numbers, and underscores.

    Args:
        _ctx: Not used. Provided by click automatically.
        _param: Not used. Provided by click automatically.
        value: The string-value to check

    Raises:
        BadParameter: If the input value contains invalid characters.
    """
def rename_environments(new_name: str) -> None:
    """Iteratively renames environment files inside the 'envs' directory to use the input new_name as the base-name."""
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
