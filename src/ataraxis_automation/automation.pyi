from pathlib import Path
from dataclasses import dataclass

from _typeshed import Incomplete

_SUPPORTED_PLATFORMS: dict[str, str]
_BASE_NAME_PATTERN: Incomplete

def format_message(message: str) -> str:
    """Formats input message strings to follow the general Sun lab and project Ataraxis style.

    This function uses the same parameters as the default Console class implementation available through
    the ataraxis-base-utilities library. This function is used to decouple the ataraxis-automation library from
    the ataraxis-base-utilities library, removing the circular dependency introduced for these libraries in versions 2
    and 3 and allows mimicking the output of the console.error() method.

    Args:
        message: The input message string to format.

    Returns:
        Formatted message string with appropriate line breaks.
    """

def colorize_message(message: str, color: str, wrap: bool = True) -> str:
    """Modifies the input string to include an ANSI color code and, if necessary, formats the message by wrapping it
    at 120 lines.

    This function uses the same parameters as the default Console class implementation available through
    the ataraxis-base-utilities library. This function is used to decouple the ataraxis-automation library from
    ataraxis-base-utilities and, together with click.echo, allows mimicking the output of the console.echo() method.

    Args:
        message: The input message string to format and colorize.
        color: The ANSI color code to use for coloring the message.
        wrap: Determines whether to format the message by wrapping it at 120 lines.

    Returns:
        Colorized and wrapped (if requested) message string.
    """

def resolve_project_directory() -> Path:
    """Resolves the current working directory and verifies that it points to a valid Python project.

    This function is used to retrieve, verify, and return the absolute path to the root directory of the project to be
    processed with ataraxis-automation toolset.

    Raises:
        RuntimeError: If the current working directory does not point to a valid Sun lab project.
    """

def resolve_library_root(project_root: Path) -> Path:
    """Determines the absolute path to the library root directory.

    Library root differs from project root. Library root is the root folder that will be included in the binary
    distribution of the project and is typically either the 'src' directory or the folder directly under 'src'.

    Notes:
        Since C-extension and pure-Python projects in the Sun lab use a slightly different layout, this function is
        used to resolve whether /src or /src/library is used as a library root. To do so, it uses a simple heuristic:
        library root is a directory at most one level below /src with __init__.py. There can only be one library root.

    Args:
        project_root: The absolute path to the root directory of the processed project.

    Returns:
        The absolute path to the root directory of the library.

    Raises:
        RuntimeError: If the valid root directory candidate cannot be found based on the determination heuristics.
    """

def _get_base_name(dependency: str) -> str:
    """Extracts the base name of a dependency, removing versions, extras, and platform markers.

    This helper function is used by the main resolve_dependencies() function to match tox.ini dependencies with
    pyproject.toml dependencies.

    Args:
        dependency: The name of the dependency that can include [extras], version data, and platform markers that
            need to be stripped from the base name.

    Returns:
        The base name of the dependency.
    """

def _should_include_dependency(dependency: str, platform_name: str) -> bool:
    """Evaluates whether a dependency should be included in the dependency installation list based on its platform
    marker.

    This function parses the dependency string to extract any platform marker and evaluates it against the current
    platform. Platform markers are expected to follow PEP 508 specification and appear after a semicolon in dependency
    strings.

    Notes:
        If this parsing function does not recognize the platform marker or the inclusion logic operator, it defaults to
        installing the dependency.

    Args:
        dependency: The full dependency string that may include platform markers after a semicolon.
        platform_name: The standardized platform name ('windows', 'linux', or 'darwin').

    Returns:
        True if the dependency should be included for the current platform, False otherwise.
    """

def _add_dependency(dependency: str, dependencies: list[str], processed_dependencies: set[str]) -> None:
    """Verifies that dependency base-name is not already added to the input list and, if not, adds it to the list.

    This method ensures that each dependency only appears in a single pyproject.toml dependency list. As part of its
    runtime, it modifies the input dependencies list and processed_dependencies set to include resolved dependency
    names by reference.

    Args:
        dependency: The name of the evaluated dependency. Can contain extras, version, and platform markers, but only
            the base dependency name is extracted for duplicate checking.
        dependencies: The list to which the processed dependency should be added if it passes verification.
        processed_dependencies: The set used to store already processed dependencies. This is used to filter out
            duplicate (double-listed) dependencies.

    Raises:
        ValueError: If the extracted dependency is found in multiple pyproject.toml dependency lists.
    """

def _resolve_dependencies(project_root: Path, platform_name: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Extracts project dependencies from all pyproject.toml lists as a platform-specific tuple of all dependencies
    (runtime and development).

    This function is used as a standard checkout step to ensure dependency metadata integrity and to automate
    environment manipulations. Specifically, it builds a tuple of all dependencies that need to be installed into a
    project environment to run and develop the project. This data is used by the resolve_environment_commands()
    function to generate the dependency installation command.

    Notes:
        As part of its runtime, this function also ensures that all dependencies listed inside the tox.ini file are
        also listed in one of the pyproject.toml dependency lists.

    Args:
        project_root: The absolute path to the root directory of the processed project.

    Returns:
        A tuple containing two elements. The first element is a tuple of runtime dependencies. The second element is
        a tuple of development dependencies. The two tuples do not include overlapping dependencies.

    Raises:
        ValueError: If duplicate dependencies (based on versionless dependency names) are found in different pyproject
            dependency lists.
        RuntimeError: If the host platform (operating system) is not supported.
    """

def _resolve_project_name(project_root: Path) -> str:
    """Extracts the project name from the pyproject.toml file.

    This function reads the pyproject.toml file and extracts the project name from the [project] section. The project
    name is useful for some operations, such as uninstalling or reinstalling the project into a mamba environment.

    Args:
        project_root: The absolute path to the root directory of the processed project.

    Returns:
        The name of the project.

    Raises:
        ValueError: If the project name is not defined in the pyproject.toml file. Also, if the pyproject.toml file is
            corrupted or otherwise malformed.
    """

def generate_typed_marker(library_root: Path) -> None:
    """Crawls the library directory tree and ensures that the py.typed marker exists only at the root level of the
    directory.

    Specifically, if the 'py.typed' is not found in the root directory, adds the marker file. If it is found in any
    subdirectory, removes the marker file.

    Notes:
        The marker file has to be present in addition to the '.pyi' typing files to notify type-checkers, like mypy,
        that the library contains type-annotations. This is necessary to allow other projects using type-checkers to
        verify this library API is accessed correctly.

    Args:
        library_root: The path to the root level of the library directory.
    """

def move_stubs(stubs_dir: Path, library_root: Path) -> None:
    """Moves typing stub (.pyi) files from the \'stubs\' directory to the appropriate level(s) of the library directory
    tree.

    This function should be called after running stubgen on the built library package (wheel). It distributes the stubs
    generated by stubgen to their final destinations in the library source code.

    Notes:
        This function expects that the \'stubs\' directory has exactly one subdirectory, which contains an __init__.pyi
        file. This subdirectory is considered to be the library root in the \'stubs\' directory structure. The \'stubs\'
        directory structure otherwise should mirror the library source code directory structure.

        The function contains the logic to work around a problem unique to OSx devices, where the stubgen process may
        generate multiple identical .pyi files. In this case, the function uses the files with the highest
        \'copy counter\' suffix.

    Args:
        stubs_dir: The absolute path to the "stubs" directory, expected to be found under the project root directory.
        library_root: The absolute path to the library root directory.
    """

def delete_stubs(library_root: Path) -> None:
    """Removes all .pyi stub files from the library root directory and its subdirectories.

    This function is used before running the linting task, as mypy tends to be biased to analyze the .pyi files,
    ignoring the source code. When .pyi files are not present, mypy reverts to properly analyzing the source code.

    Args:
        library_root: The absolute path to the library root directory.
    """

def verify_pypirc(file_path: Path) -> bool:
    """Verifies that the .pypirc file located at the input path contains valid options to support automatic
    authentication for pip uploads.

    Assumes that the file is used only to store the API token to upload compiled packages to pip. Does not verify any
    other information.

    Args:
        file_path: The absolute path to the .pypirc file to verify.

    Returns:
        True if the .pypirc is well-configured and False otherwise.
    """

def _resolve_mamba_environments_directory() -> Path:
    """Returns the absolute path to the local mamba environments directory.

    This worker function is used as part of the broader process of detecting the physical location of the mamba
    environment for the processed project. This is primarily used to ensure that environment removal command
    physically removes the environment folder from the host-machine.

    Raises:
        RuntimeError: If mamba (via miniforge) is not installed and/or initialized.
    """

def _resolve_environment_files(project_root: Path, environment_base_name: str) -> tuple[str, Path, Path]:
    """Determines the OS of the host platform and uses it to generate the absolute paths to os-specific mamba
    environment '.yml' and 'spec.txt' files.

    Since different operating systems typically use different feedstocks and compiled package versions, it is essential
    to properly separate environment files constructed on different development platforms via the use of os-specific
    suffixes. This function is used to ensure that all environment-related operations are performed using the
    os-specific environment files.

    Notes:
        Currently, this command explicitly supports only 3 OSes: OSx (ARM64: Darwin), Linux (AMD64), and Windows
        (AMD64).

    Args:
        project_root: The absolute path to the root directory of the processed project.
        environment_base_name: The name of the environment excluding the os_suffix, e.g.: 'axa_dev'.

    Returns:
        A tuple of three elements. The first element is the name of the environment with os-suffix, suitable
        for local mamba commands. The second element is the absolute path to the os-specific mamba environment '.yml'
        file. The third element is the absolute path to the os-specific environment mamba 'spec.txt' file.

    Raises:
        RuntimeError: If the host OS does not match any of the supported operating systems.
    """

def _check_package_engines() -> None:
    """Determines whether mamba and uv can be accessed from this script by silently calling 'COMMAND --version'.

    This function verifies that both mamba (for environment management) and uv (for package installation) are
    available. These tools provide significantly faster operations compared to their predecessors (conda and pip)
    and are now required for this automation module.

    Raises:
        RuntimeError: If either mamba or uv is not accessible via subprocess call through the shell.
    """
@dataclass
class ProjectEnvironment:
    """Encapsulates the data used to interface with the project's mamba environment.

    Primarily, this class resolves and stores executable commands used to manage the project environment as
    subprocess-passable strings. Additionally, it stores certain metadata information, such as the path to the physical
    location of the mamba environment.

    Notes:
        This class should not be instantiated directly. Instead, use the `resolve_environment_commands()` class method
        to get an instance of this class.
    """

    activate_command: str
    deactivate_command: str
    create_command: str
    create_from_yml_command: str | None
    remove_command: str
    install_dependencies_command: str
    update_command: str | None
    export_yml_command: str
    export_spec_command: str
    install_project_command: str
    uninstall_project_command: str
    environment_name: str
    environment_directory: Path
    @classmethod
    def resolve_project_environment(
        cls, project_root: Path, environment_name: str, python_version: str = "3.13"
    ) -> ProjectEnvironment:
        """Generates the list of mamba and uv commands used to manipulate the project- and os-specific mamba environment
        and packages it into ProjectEnvironment class.

        This initialization method is used by all environment-manipulating cli commands as an entry-point for
        interfacing with the project's mamba environment on the host-machine.

        Args:
            project_root: The absolute path to the root directory of the processed project.
            environment_name: The base-name of the project's mamba environment.
            python_version: The Python version to use as part of the new environment creation or provisioning process.

        Returns:
            The resolved ProjectEnvironment instance.
        """
    def environment_exists(self) -> bool:
        """Returns True if the environment can be activated (and, implicitly, exists) and False otherwise."""
