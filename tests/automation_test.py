"""This module stores the tests for all non-cli functions available from the automation.py module."""

import os
import re
import sys
from pathlib import Path
import tempfile
import textwrap
import subprocess
from configparser import ConfigParser
from unittest.mock import Mock

import yaml
import click
import pytest

import ataraxis_automation.automation as aa
from ataraxis_automation.automation import EnvironmentCommands


@pytest.fixture
def project_dir(tmp_path) -> Path:
    """Generates the test project root directory with the required files expected by the automation functions.

    Args:
        tmp_path: Internal pytest fixture that generates temporary folders to isolate test-generated files.

    Returns:
        The absolute path to the test project root directory.
    """
    project_dir = tmp_path.joinpath("project")
    project_dir.mkdir()
    project_dir.joinpath("src").mkdir()
    project_dir.joinpath("envs").mkdir()
    project_dir.joinpath("pyproject.toml").touch()
    project_dir.joinpath("tox.ini").touch()
    return project_dir


def error_format(message: str) -> str:
    """Formats the input message to match the default Console format and escapes it using re, so that it can be used to
    verify raised exceptions.

    This method is used to set up pytest 'match' clauses to verify raised exceptions.

    Args:
        message: The message to format and escape, according to standard Ataraxis testing parameters.

    Returns:
        Formatted and escape message that can be used as the 'match' argument of pytest.raises() method.
    """
    return re.escape(textwrap.fill(message, width=120, break_long_words=False, break_on_hyphens=False))


def test_configure_console(tmp_path) -> None:
    """Verifies that aa.configure_console method functions as expected under different input configurations.

    Args:
        tmp_path: Internal pytest fixture that generates temporary folders to isolate test-generated files.
    """
    # Setup
    log_dir = tmp_path.joinpath("logs")
    log_dir.mkdir()
    message_log = log_dir.joinpath("message_log.txt")
    error_log = log_dir.joinpath("error_log.txt")

    # Verifies initialization with logging enabled generates log files
    aa.configure_console(log_dir, verbose=True, enable_logging=True)
    assert message_log.exists()
    assert error_log.exists()

    # Replaces the log directory. Uses replacement instead of reset due to a permission clash on Windows platforms
    # where 'pytest' prevents the log directory from being cleared.
    log_dir = tmp_path.joinpath("logs2")
    log_dir.mkdir()
    message_log = log_dir.joinpath("message_log.txt")
    error_log = log_dir.joinpath("error_log.txt")

    # Verifies that disabling logging does not create log files
    aa.configure_console(log_dir, verbose=True, enable_logging=False)
    assert not message_log.exists()
    assert not error_log.exists()

    # Changes the working directory to the general temporary directory to fail the tests below
    new_project_directory = tempfile.gettempdir()
    os.chdir(new_project_directory)

    # This should do two things: print a formatted message with traceback to the console and (evaluated here) call a
    # SystemExit (through default callback). This is the expected 'verbose' console behavior.
    # noinspection PyTypeChecker
    with pytest.raises((SystemExit, RuntimeError), match="Runtime aborted."):
        aa.resolve_project_directory()

    # Reconfigures console to not print or log anything. This also disables() the shared console variable.
    aa.configure_console(log_dir, verbose=False, enable_logging=False)
    assert not message_log.exists()
    assert not error_log.exists()

    # When console is disabled, errors are raised using the standard python 'raise' system, which should be caught by
    # pytest.
    with pytest.raises(RuntimeError):
        aa.resolve_project_directory()


def test_resolve_project_directory(project_dir) -> None:
    """Verifies that aa.resolve_project_directory() method works as expected for a well-configured project.

    Args:
        project_dir: Local fixture that generates the project structure expected by many tests and returns the path
            to the root directory of the generated project.
    """
    os.chdir(project_dir)
    result = aa.resolve_project_directory()
    assert result == project_dir


def test_resolve_project_directory_error(tmp_path) -> None:
    """Verifies that aa.resolve_project_directory() fails for non-project directories.

    Args:
        tmp_path: Internal pytest fixture that generates temporary folders to isolate test-generated files.
    """

    os.chdir(tmp_path)
    message: str = (
        f"Unable to confirm that ataraxis automation module has been called from the root directory of a valid "
        f"Python project. This function expects that the current working directory is set to the root directory of "
        f"the project, judged by the presence of '/src', '/envs', 'pyproject.toml' and 'tox.ini'. Current working "
        f"directory is set to {os.getcwd()}, which does not contain at least one of the required files."
    )
    # noinspection PyTypeChecker
    with pytest.raises((SystemExit, RuntimeError), match=error_format(message)):
        aa.resolve_project_directory()


@pytest.mark.parametrize(
    "init_location, expected",
    [
        ("src", "src"),
        ("src/library", "src/library"),
    ],
)
def test_resolve_library_root(project_dir, init_location, expected) -> None:
    """Verifies that aa.resolve_library_root() function works as expected for src-root and library_name-root projects.

    Args:
        project_dir: Local fixture that generates the project structure expected by many tests and returns the path
            to the root directory of the generated project.
        init_location: The path to the directory, to which the __init__.py should be added. Simulates the library root
            folder.
        expected: The expected result of processing the project root structure given the __init__.py location.
    """

    init_dir = project_dir.joinpath(init_location)
    init_dir.mkdir(parents=True, exist_ok=True)
    init_dir.joinpath("__init__.py").touch()
    result = aa.resolve_library_root(project_root=project_dir)
    assert result == project_dir / expected


def test_resolve_library_root_error(project_dir) -> None:
    """Verifies error-handling behavior of aa.resolve_library_root() method.

    Args:
        project_dir: Local fixture that generates the project structure expected by many tests and returns the path
            to the root directory of the generated project.
    """

    # Verifies the method correctly fails when __init__.py is not found under /src or any subdirectory directly under
    # src

    message: str = (
        f"Unable to resolve the path to the library root directory from the project root path {project_dir}. "
        f"Specifically, did not find an __init__.py inside the /src directory and found {0} "
        f"sub-directories with __init__.py inside the /src directory. Make sure there is an __init__.py "
        f"inside /src or ONE of the sub-directories under /src."
    )
    with pytest.raises(RuntimeError, match=error_format(message)):
        aa.resolve_library_root(project_dir)

    # Verifies that the method fails for cases where multiple subdirectories under src have __init__.py
    library1 = project_dir.joinpath("src/library1")
    library2 = project_dir.joinpath("src/library2")
    library1.mkdir(parents=True, exist_ok=True)
    library2.mkdir(parents=True, exist_ok=True)
    library1.joinpath("__init__.py").touch()
    library2.joinpath("__init__.py").touch()
    message: str = (
        f"Unable to resolve the path to the library root directory from the project root path {project_dir}. "
        f"Specifically, did not find an __init__.py inside the /src directory and found {2} "
        f"sub-directories with __init__.py inside the /src directory. Make sure there is an __init__.py "
        f"inside /src or ONE of the sub-directories under /src."
    )
    with pytest.raises(RuntimeError, match=error_format(message)):
        aa.resolve_library_root(project_dir)


def test_resolve_environment_files(project_dir, monkeypatch) -> None:
    """Verifies that aa.resolve_environment_files() function works as expected for supported platforms.

    Args:
        project_dir: Local fixture that generates the project structure expected by many tests and returns the path
            to the root directory of the generated project.
        monkeypatch: Internal pytest fixture that allows mocking the output of other system package calls.
    """

    os.chdir(project_dir)  # Ensures working directory is set to the project directory
    environment_base_name: str = "test_env"

    project_dir: Path = aa.resolve_project_directory()

    # Verifies environment resolution works as expected for the linux platform
    monkeypatch.setattr(sys, "platform", "linux")
    env_name, yml_path, spec_path = aa.resolve_environment_files(
        project_root=project_dir, environment_base_name=environment_base_name
    )
    assert env_name == f"{environment_base_name}_lin"
    assert yml_path == project_dir / "envs" / f"{environment_base_name}_lin.yml"
    assert spec_path == project_dir / "envs" / f"{environment_base_name}_lin_spec.txt"

    # Verifies environment resolution works as expected for the windows platform
    monkeypatch.setattr(sys, "platform", "win32")
    env_name, yml_path, spec_path = aa.resolve_environment_files(
        project_root=project_dir, environment_base_name=environment_base_name
    )
    assert env_name == f"{environment_base_name}_win"
    assert yml_path == project_dir / "envs" / f"{environment_base_name}_win.yml"
    assert spec_path == project_dir / "envs" / f"{environment_base_name}_win_spec.txt"

    # Verifies environment resolution works as expected for the darwin (OSx ARM64) platform
    monkeypatch.setattr(sys, "platform", "darwin")
    env_name, yml_path, spec_path = aa.resolve_environment_files(
        project_root=project_dir, environment_base_name=environment_base_name
    )
    assert env_name == f"{environment_base_name}_osx"
    assert yml_path == project_dir / "envs" / f"{environment_base_name}_osx.yml"
    assert spec_path == project_dir / "envs" / f"{environment_base_name}_osx_spec.txt"


def test_resolve_environment_files_error(project_dir, monkeypatch) -> None:
    """Verifies aa.resolve_environment_files() function fails for unsupported platforms.

    Args:
        project_dir: Local fixture that generates the project structure expected by many tests and returns the path
            to the root directory of the generated project.
        monkeypatch: Internal pytest fixture that allows mocking the output of other system package calls.
    """

    supported_platforms: dict[str, str] = {"win32": "_win", "linux": "_lin", "darwin": "_osx"}
    monkeypatch.setattr(sys, "platform", "unsupported")
    environment_base_name: str = "text_env"
    os.chdir(project_dir)
    message: str = (
        f"Unable to resolve the os-specific suffix to use for conda environment file(s). Unsupported host OS "
        f"detected: {'unsupported'}. Currently, supported OS options are are: {', '.join(supported_platforms.keys())}."
    )
    with pytest.raises(RuntimeError, match=error_format(message)):
        aa.resolve_environment_files(project_root=project_dir, environment_base_name=environment_base_name)


def test_resolve_conda_engine(monkeypatch) -> None:
    """Verifies the functioning of the aa.resolve_conda_engine() function when both mamba and conda engines are
    available.

    Args:
        monkeypatch: Internal pytest fixture that allows mocking the output of other system package calls.
    """

    # noinspection PyUnusedLocal
    def mock_subprocess_run(*args, **kwargs):
        """Returns success code for either mamba or conda command."""
        if "mamba --version" == args[0] or "conda --version" in args[0]:
            return Mock(returncode=0)
        raise subprocess.CalledProcessError(1, "cmd")

    # Expects that when both mamba and conda commands return success codes, mamba is chosen over conda.
    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
    result = aa.resolve_conda_engine()
    assert result == "mamba"


def test_resolve_conda_engine_fallback(monkeypatch) -> None:
    """Verifies the functioning of the aa.resolve_conda_engine() function when only conda engine is available.

    Args:
        monkeypatch: Internal pytest fixture that allows mocking the output of other system package calls.
    """

    # noinspection PyUnusedLocal
    def mock_subprocess_run(*args, **kwargs):
        """Ensures 'conda --version' returns success code 0."""
        if "conda --version" == args[0]:
            return Mock(returncode=0)
        raise subprocess.CalledProcessError(1, "cmd")

    # When mamba is not available, expects that conda is selected as the conda engine.
    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
    result = aa.resolve_conda_engine()
    assert result == "conda"


def test_resolve_conda_engine_error(monkeypatch) -> None:
    """Verifies that aa.resolve_conda_engine() function fails when neither conda nor mamba is available.

    Args:
        monkeypatch: Internal pytest fixture that allows mocking the output of other system package calls.
    """

    # noinspection PyUnusedLocal
    def mock_run(*args, **kwargs):
        """Ensures subprocess always returns error code 1, regardless of the command.

        This makes it fail for both mamba and conda.
        """
        raise subprocess.CalledProcessError(1, "cmd")

    # When neither conda nor mamba is available, expects a RuntimeError
    monkeypatch.setattr(subprocess, "run", mock_run)
    message: str = (
        f"Unable to determine the conda / mamba engine to use for 'conda' commands. Specifically, unable"
        f"to interface with either conda or mamba. Is conda or supported equivalent installed, initialized "
        f"and added to Path?"
    )
    with pytest.raises(RuntimeError, match=error_format(message)):
        aa.resolve_conda_engine()


def test_resolve_pip_engine(monkeypatch) -> None:
    """Verifies the functioning of the aa.resolve_pip_engine() function when both uv and pip engines are available.

    Args:
        monkeypatch: Internal pytest fixture that allows mocking the output of other system package calls.
    """

    # noinspection PyUnusedLocal
    def mock_subprocess_run(*args, **kwargs):
        """Returns success code for either uv pip or pip command."""
        if "uv pip --version" == args[0] or "pip --version" == args[0]:
            return Mock(returncode=0)
        raise subprocess.CalledProcessError(1, "cmd")

    # When both pip and uv are available, expects that uv is selected over pip.
    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
    result = aa.resolve_pip_engine()
    assert result == "uv pip"


def test_resolve_pip_engine_fallback(monkeypatch) -> None:
    """Verifies the functioning of the aa.resolve_pip_engine() function when only pip engine is available.

    Args:
        monkeypatch: Internal pytest fixture that allows mocking the output of other system package calls.
    """

    # noinspection PyUnusedLocal
    def mock_subprocess_run(*args, **kwargs):
        """Ensures 'pip --version' returns success code 0."""
        if "pip --version" == args[0]:
            return Mock(returncode=0)
        raise subprocess.CalledProcessError(1, "cmd")

    # When uv is not available, expects that pip is selected as the pip engine.
    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
    result = aa.resolve_pip_engine()
    assert result == "pip"


def test_resolve_pip_engine_error(monkeypatch) -> None:
    """Verifies that aa.resolve_pip_engine() function fails when neither pip nor uv are available.

    Args:
        monkeypatch: Internal pytest fixture that allows mocking the output of other system package calls.
    """

    # noinspection PyUnusedLocal
    def mock_run(*args, **kwargs):
        """Ensures subprocess always returns error code 1, regardless of the command.

        This makes it fail for both uv and pip.
        """
        raise subprocess.CalledProcessError(1, "cmd")

    # When neither pip nor uv is available, expects a RuntimeError
    monkeypatch.setattr(subprocess, "run", mock_run)
    message: str = (
        f"Unable to determine the engine to use for pip commands. Specifically, was not able to interface with any of "
        f"the supported pip-engines. Is pip, uv or supported equivalent installed in the currently active "
        f"virtual / conda environment?"
    )
    with pytest.raises(RuntimeError, match=error_format(message)):
        aa.resolve_pip_engine()


@pytest.mark.parametrize(
    "dependency, expected",
    [
        ("package==1.0", "package"),
        ("package>=1.0", "package"),
        ("package<=1.0", "package"),
        ("package<1.0", "package"),
        ("package>1.0", "package"),
        ("package[extra]", "package"),
        ("package[extra]==1.0", "package"),
        ("package", "package"),
    ],
)
def test_get_base_name(dependency, expected) -> None:
    """Verifies that get_base_name() function correctly strips versions and extras from dependency names.

    Args:
        dependency: Tested dependency name.
        expected: Expected processing outcome.
    """

    assert aa.get_base_name(dependency) == expected


def test_add_dependency() -> None:
    """Verifies the functioning and duplicate handling of the add_dependency() minor method."""

    # Setup
    processed_dependencies = set()
    dependencies_list = []

    # Ensures that if the base name of the dependency (stripped of "version") is correctly added to dependencies_list,
    # unless it is already contained in processed_dependencies
    dependencies_list, processed_dependencies = aa.add_dependency(
        dependency="package==1.0", dependencies_list=dependencies_list, processed_dependencies=processed_dependencies
    )
    assert dependencies_list == [f'"package==1.0"']
    assert processed_dependencies == {"package"}

    # Verifies that packages with same base name but different 'extras' are correctly recognized as duplicates.
    dependency: str = "package[test]"
    message: str = (
        f"Unable to resolve conda-installable and pip-installable project dependencies. Found a duplicate "
        f"dependency for '{dependency}', listed in pyproject.toml. A dependency should only "
        f"be found in one of the supported  pyproject.toml lists: conda, noconda or condarun."
    )
    with pytest.raises(ValueError, match=error_format(message)):
        aa.add_dependency(
            dependency=dependency, dependencies_list=dependencies_list, processed_dependencies=processed_dependencies
        )

    # Verifies that packages with the same base name but different versions are correctly recognized as duplicates.
    dependency = "package>=2.0"
    message = (
        f"Unable to resolve conda-installable and pip-installable project dependencies. Found a duplicate "
        f"dependency for '{dependency}', listed in pyproject.toml. A dependency should only "
        f"be found in one of the supported  pyproject.toml lists: conda, noconda or condarun."
    )
    with pytest.raises(ValueError, match=error_format(message)):
        aa.add_dependency(
            dependency=dependency, dependencies_list=dependencies_list, processed_dependencies=processed_dependencies
        )


def write_pyproject_toml(project_dir: Path, content: str) -> None:
    """Writes the given content to the pyproject.toml file in the project directory.

    Assumes that the project_dir is configured according to the testing standards (obtained from the project_dir
    fixture).

    Args:
        project_dir: The path to the processed project root directory.
        content: The string-content to write to the pyproject.toml file of the processed project.
    """
    pyproject_path: Path = project_dir.joinpath("pyproject.toml")
    pyproject_path.write_text(content)


def write_tox_ini(project_dir: Path, content: str) -> None:
    """Writes the given content to the tox.ini file in the project directory.

    Assumes that the project_dir is configured according to the testing standards (obtained from the project_dir
    fixture).

    Args:
        project_dir: The path to the processed project root directory.
        content: The string-content to write to the tox.ini file of the processed project.
    """
    tox_path: Path = project_dir.joinpath("tox.ini")
    tox_path.write_text(content)


def test_resolve_dependencies(project_dir: Path) -> None:
    """Verifies the functioning of the resolve_dependencies() function.

    Args:
        project_dir: The path to the processed project root directory.
    """

    pyproject_content = """
[project]
dependencies = ["dep1==1.0", "dep2>=2.0"]

[project.optional-dependencies]
conda = ["conda_dep1[test]", "conda_dep2"]
noconda = ["noconda_dep<2.0.1"]
condarun = ["condarun_dep==3"]
"""
    write_pyproject_toml(project_dir, pyproject_content)

    tox_content = """
[testenv]
deps =
    dep1
    conda_dep1
    noconda_dep
    condarun_dep
requires =
    dep2
"""
    write_tox_ini(project_dir, tox_content)

    conda_deps, pip_deps = aa.resolve_dependencies(project_dir)

    assert set(conda_deps) == {f'"conda_dep1[test]"', f'"conda_dep2"', f'"condarun_dep==3"'}
    assert set(pip_deps) == {f'"dep1==1.0"', f'"dep2>=2.0"', f'"noconda_dep<2.0.1"'}


def test_resolve_dependencies_missing_tox_dep(project_dir: Path) -> None:
    """Verifies that resolve_dependencies() correctly catches when tox dependencies are missing from .toml lists.

    Args:
        project_dir: The path to the processed project root directory.
    """

    pyproject_content = """
[project]
dependencies = ["dep1==1.0", "dep2>=2.0"]

[project.optional-dependencies]
conda = ["conda_dep1", "conda_dep2"]
noconda = ["noconda_dep"]
condarun = ["condarun_dep"]
"""
    write_pyproject_toml(project_dir, pyproject_content)

    tox_content = """
[testenv]
deps =
    dep1
    conda_dep1
    noconda_dep
    condarun_dep
    missing_dep
requires =
    dep2
"""
    write_tox_ini(project_dir, tox_content)
    message: str = (
        f"Unable to resolve conda-installable and pip-installable project dependencies. The following "
        f"dependencies in tox.ini are not found in pyproject.toml: {', '.join(['missing_dep'])}. Add them to "
        f"one of the pyproject.toml dependency lists: condarun, conda or noconda."
    )
    with pytest.raises(ValueError, match=error_format(message)):
        aa.resolve_dependencies(project_dir)


def test_resolve_dependencies_duplicate_dep(project_dir: Path) -> None:
    """Verifies that resolve_dependencies() function correctly catches duplicate dependencies in supported .toml
    lists.

    Args:
        project_dir: The path to the processed project root directory.
    """

    pyproject_content = """
[project]
dependencies = ["dep1==1.0", "dep2>=2.0"]

[project.optional-dependencies]
conda = ["conda_dep1", "conda_dep2", "dep1"]
noconda = ["noconda_dep", "dep1<3.0"]
condarun = ["condarun_dep"]
"""
    write_pyproject_toml(project_dir, pyproject_content)

    tox_content = """
[testenv]
deps =
    dep1
    conda_dep1
    noconda_dep
    condarun_dep
requires =
    dep2
"""
    write_tox_ini(project_dir, tox_content)
    message: str = (
        f"Unable to resolve conda-installable and pip-installable project dependencies. Found a duplicate "
        f"dependency for 'dep1<3.0', listed in pyproject.toml. A dependency should only "
        f"be found in one of the supported  pyproject.toml lists: conda, noconda or condarun."
    )
    with pytest.raises(ValueError, match=error_format(message)):
        aa.resolve_dependencies(project_dir)


@pytest.mark.parametrize("section", ["condarun", "conda"])
def test_resolve_dependencies_priority(project_dir, section: Path) -> None:
    """Verifies that resolve_dependencies() correctly prioritizes resolving run-dependencies as conda dependencies over
    pip where possible.

    Args:
        project_dir: The path to the processed project root directory.
    """

    pyproject_content = f"""
    [project]
    dependencies = ["dep1==1.0", "dep2>=2.0"]

    [project.optional-dependencies]
    conda = ["conda_dep1", "conda_dep2"{', "priority_dep"' if section == 'conda' else ''}]
    noconda = ["noconda_dep"]
    condarun = ["condarun_dep"{', "priority_dep"' if section == 'condarun' else ''}]
    """
    write_pyproject_toml(project_dir, pyproject_content)

    tox_content = """
    [testenv]
    deps =
        dep1
        conda_dep1
        noconda_dep
        condarun_dep
        priority_dep
    requires =
        dep2
    """
    write_tox_ini(project_dir, tox_content)

    conda_deps, pip_deps = aa.resolve_dependencies(project_dir)

    assert f'"priority_dep"' in conda_deps
    assert f'"priority_dep"' not in pip_deps


def test_resolve_project_name(project_dir) -> None:
    """Verifies the functioning of the resolve_project_name() function.

    Args:
        project_dir: The path to the processed project root directory.
    """

    pyproject_content = """
    [project]
    name = "test-project"
    """
    pyproject_path = project_dir.joinpath("pyproject.toml")
    pyproject_path.write_text(pyproject_content)

    result = aa.resolve_project_name(project_dir)
    assert result == "test-project"


def test_resolve_project_name_errors(project_dir) -> None:
    """Test resolve_project_name() function error handling.

    Args:
        project_dir: The path to the processed project root directory.
    """

    # Verifies that malformed pyproject.toml files are not processed.

    pyproject_content = """
        [project
        name = "test-project"
        """
    pyproject_path = project_dir.joinpath("pyproject.toml")
    pyproject_path.write_text(pyproject_content)

    message: str = (
        f"Unable to parse the pyproject.toml file. The file may be corrupted or contain invalid TOML syntax. "
    )
    with pytest.raises(ValueError, match=error_format(message)):
        aa.resolve_project_name(project_dir)

    # Verifies that processing fails when 'name' section does not exist.
    pyproject_content = """
        [project]
        version = "1.0.0"
        """
    pyproject_path.write_text(pyproject_content)
    message = (
        f"Unable to resolve the project name from the pyproject.toml file. The 'name' field is missing or empty in "
        f"the [project] section of the file. Ensure that the project name is correctly defined."
    )

    with pytest.raises(ValueError, match=error_format(message)):
        aa.resolve_project_name(project_dir)

    # Also verifies that processing fails when 'name' section exists, but is not set to a valid name-value
    pyproject_content = """
        [project]
        name = ""
        """
    pyproject_path.write_text(pyproject_content)
    message = (
        f"Unable to resolve the project name from the pyproject.toml file. The 'name' field is missing or empty in "
        f"the [project] section of the file. Ensure that the project name is correctly defined."
    )

    with pytest.raises(ValueError, match=error_format(message)):
        aa.resolve_project_name(project_dir)


@pytest.mark.parametrize(
    "scenario, os_suffix, platform, conda_engine, pip_engine, python_version, dependencies",
    [
        ("standard", "_win", "win32", "conda", "pip", "3.12", (["conda_dep"], ["pip_dep"])),
        ("linux", "_lin", "linux", "conda", "pip", "3.12", (["conda_dep"], ["pip_dep"])),
        ("macos", "_osx", "darwin", "conda", "pip", "3.12", (["conda_dep"], ["pip_dep"])),
        ("uv_pip", "_win", "win32", "conda", "uv pip", "3.12", (["conda_dep"], ["pip_dep"])),
        ("mamba", "_win", "win32", "mamba", "pip", "3.12", (["conda_dep"], ["pip_dep"])),
        ("python_311", "_win", "win32", "conda", "pip", "3.11", (["conda_dep"], ["pip_dep"])),
        ("no_dependencies", "_win", "win32", "conda", "pip", "3.12", ([], [])),
    ],
)
def test_resolve_environment_commands(
    project_dir, monkeypatch, scenario, os_suffix, platform, conda_engine, pip_engine, python_version, dependencies
) -> None:
    """Verifies that resolve_environment_commands() function works as expected for all supported system
    configurations.

    Args:
        project_dir: The path to the processed project root directory.
        monkeypatch: Internal pytest fixture that allows mocking the output of other system package calls.
        scenario: The descriptive name of the tested configuration scenario. This is exclusively used to make reading
            test configurations more human-friendly.
        os_suffix: The os-suffix expected to be used by the test scenario (based on the simulated platform).
        platform: The platform (OS) to simulate for the test scenario.
        conda_engine: The 'conda' command to simulate for the test scenario.
        pip_engine: The 'pip' command to simulate for the test scenario.
        python_version: The python-version input to the tested function.
        dependencies: A tuple of conda and pip (in this order) dependency-lists to simulate for the test scenario.

    Notes:
        There are no error tests for this function as all errors are raised by minor sub-functions. There is no point in
        testing these in-addition to testing them for the specific sub-functions.
    """

    # Setup

    pyproject_content = """
    [project]
    name = "test-project"
    """
    pyproject_path = project_dir.joinpath("pyproject.toml")
    pyproject_path.write_text(pyproject_content)

    # Mocks the outcome of resolve_environment_files function used by the resolve_environment_commands. This command
    # is tested separately.
    # noinspection PyUnusedLocal
    def mock_resolve_environment_files(*args, **kwargs):
        return (
            f"test_env{os_suffix}",
            project_dir / f"envs/test_env{os_suffix}.yml",
            project_dir / f"envs/test_env{os_suffix}_spec.txt",
        )

    # Mocks all previously tested sub-functions to return test-required information, instead of doing a proper runtime.
    monkeypatch.setattr(aa, "resolve_environment_files", mock_resolve_environment_files)
    monkeypatch.setattr(aa, "resolve_dependencies", lambda x: dependencies)
    monkeypatch.setattr(aa, "resolve_conda_engine", lambda: conda_engine)
    monkeypatch.setattr(aa, "resolve_pip_engine", lambda: pip_engine)
    monkeypatch.setattr(sys, "platform", platform)

    # Create a mock .yml file
    yml_path = project_dir / f"envs/test_env{os_suffix}.yml"
    yml_path.parent.mkdir(parents=True, exist_ok=True)
    yml_path.touch()

    # Runs the tested command
    result = aa.resolve_environment_commands(project_dir, "test_env", python_version=python_version)

    # Verifies the returned EnvironmentCommands class instance contains the fields expected given the mocked parameters
    # and function returned data.
    assert isinstance(result, EnvironmentCommands)

    # Check conda initialization and activation
    if platform.startswith("win"):
        assert "call conda.bat" in result.activate_command
        assert "call conda.bat" in result.deactivate_command
    else:
        assert ". $(conda info --base)/etc/profile.d/conda.sh" in result.activate_command
        assert ". $(conda info --base)/etc/profile.d/conda.sh" in result.deactivate_command
    assert f"conda activate test_env{os_suffix}" in result.activate_command
    assert f"conda deactivate" in result.deactivate_command
    assert (
        f"{conda_engine} create -n test_env{os_suffix} python={python_version} tox uv pip --yes"
        in result.create_command
    )
    assert f"{conda_engine} remove -n test_env{os_suffix} --all --yes" in result.remove_command
    assert result.environment_name == f"test_env{os_suffix}"

    # When there are no conda or pip dependencies, the corresponding command is actually set to None
    if len(dependencies[0]) != 0:
        assert (
            f"{conda_engine} install -n test_env{os_suffix} {' '.join(dependencies[0])} --yes"
            in result.conda_dependencies_command
        )
    else:
        assert result.conda_dependencies_command is None
    if len(dependencies[1]) != 0:
        assert f"{pip_engine} install {' '.join(dependencies[1])}" in result.pip_dependencies_command
    else:
        assert result.pip_dependencies_command is None

    assert f"{conda_engine} env update -n test_env{os_suffix}" in result.update_command
    assert f"{conda_engine} env export --name test_env{os_suffix}" in result.export_yml_command
    assert f"{conda_engine} list -n test_env{os_suffix} --explicit -r" in result.export_spec_command
    assert "pip install ." in result.install_project_command
    assert "pip uninstall test-project" in result.uninstall_project_command

    # Verifies that OS-specific returned parameters match expectation.
    if platform == "win32":
        assert "findstr -v" in result.export_yml_command
    elif platform == "linux":
        assert "head -n -1" in result.export_yml_command
    elif platform == "darwin":
        assert "tail -r | tail -n +2 | tail -r" in result.export_yml_command

    # Verifies that pip-engine-dependent additional parameters match expectation.
    if pip_engine == "uv pip":
        assert f"--python={python_version}" in result.uninstall_project_command
        command_string = f"--reinstall-package test-project --compile-bytecode --python={python_version}"
        assert command_string in result.install_project_command
        if len(dependencies[1]) != 0:
            assert f"--compile-bytecode --python={python_version}" in result.pip_dependencies_command
    else:
        assert "--yes" in result.uninstall_project_command
        assert "--compile" in result.install_project_command
        if len(dependencies[1]) != 0:
            assert "--compile" in result.pip_dependencies_command
        else:
            assert result.pip_dependencies_command is None

    # Check for new yml-related commands
    assert result.create_from_yml_command == f"{conda_engine} env create -f {yml_path} --yes"
    assert result.update_command == f"{conda_engine} env update -n test_env{os_suffix} -f {yml_path} --prune"


def test_generate_typed_marker(tmp_path) -> None:
    """Verifies the functioning of the generate_typed_marker() function.

    Args:
        tmp_path: Internal pytest fixture that generates temporary folders to isolate test-generated files.

    Notes:
        Similar to some other tested functions, this function only tests 'success' functionality as it is not expected
        to fail.
    """
    # Sets up a mock library directory structure
    library_root = tmp_path / "library"
    library_root.mkdir()
    subdir1 = library_root / "subdir1"
    subdir1.mkdir()
    subdir2 = library_root / "subdir2"
    subdir2.mkdir()

    # Creates py.typed files in subdirectories
    (subdir1 / "py.typed").touch()
    (subdir2 / "py.typed").touch()

    aa.generate_typed_marker(library_root)

    # Verifies that py.typed exists in the root directory
    assert (library_root / "py.typed").exists()

    # Verifies that py.typed has been removed from subdirectories
    assert not (subdir1 / "py.typed").exists()
    assert not (subdir2 / "py.typed").exists()

    # Runs the function again to ensure it doesn't cause issues when py.typed already exists in root
    aa.generate_typed_marker(library_root)

    # Verifies that py.typed still exists in the root directory
    assert (library_root / "py.typed").exists()

    # Verifies that no new py.typed files have been created in subdirectories
    assert not (subdir1 / "py.typed").exists()
    assert not (subdir2 / "py.typed").exists()


def test_move_stubs(project_dir) -> None:
    """Verifies the functioning of the generate_typed_marker() function.

    Args:
        project_dir: The path to the processed project root directory.
    """

    # Sets up mock directories
    stubs_dir = project_dir / "stubs"
    library_root = project_dir / "src" / "library"
    stubs_dir.mkdir()
    library_root.mkdir(parents=True)

    # Creates mock stub files
    stub_lib_dir = stubs_dir.joinpath("library")
    stub_lib_dir.mkdir()
    stub_lib_dir.joinpath("__init__.pyi").touch()
    stub_lib_dir.joinpath("module1.pyi").touch()
    stub_lib_dir.joinpath("submodule").mkdir()
    (stub_lib_dir / "submodule" / "module2.pyi").touch()

    aa.move_stubs(stubs_dir, library_root)

    # Verifies that stubs have been moved correctly
    assert (library_root / "__init__.pyi").exists()
    assert (library_root / "module1.pyi").exists()
    assert (library_root / "submodule" / "module2.pyi").exists()

    # Verifies that original stub files have been removed
    assert not (stub_lib_dir / "__init__.pyi").exists()
    assert not (stub_lib_dir / "module1.pyi").exists()
    assert not (stub_lib_dir / "submodule" / "module2.pyi").exists()

    # Tests OSX-specific duplicate file handling
    # Ensures that the library root in stubs has an __init__.pyi. This is used by the function to discover library stub
    # root directory.
    stub_lib_dir.joinpath("__init__.pyi").touch()
    (library_root / "osx_file 1.pyi").touch()
    (library_root / "osx_file 2.pyi").touch()

    aa.move_stubs(stubs_dir, library_root)  # Runs again to trigger duplicate file resolution

    # Verifies that duplicates have been successfully replaced with a proper file name
    assert (library_root / "osx_file.pyi").exists()
    assert not (library_root / "osx_file 1.pyi").exists()
    assert not (library_root / "osx_file 2.pyi").exists()


def test_move_stubs_error(project_dir) -> None:
    """Verifies the error-handling behavior of the generate_typed_marker() function.

    Args:
        project_dir: The path to the processed project root directory.
    """

    # Set up mock directories
    stubs_dir = project_dir.joinpath("stubs")
    library_root = project_dir / "src" / "library"
    stubs_dir.mkdir()
    library_root.mkdir(parents=True)

    # Create invalid stub directory structure (multiple subdirectories with __init__.pyi)
    stubs_dir.joinpath("lib1").mkdir()
    init_1_path = Path(stubs_dir / "lib1" / "__init__.pyi")
    init_1_path.touch()
    stubs_dir.joinpath("lib2").mkdir()
    init_2_path = Path(stubs_dir / "lib2" / "__init__.pyi")
    init_2_path.touch()

    # Verifies that attempting to move files from /stubs hierarchy that contains multiple __init__.pyi files fails
    # as expected.
    message: str = (
        f"Unable to move the generated stub files to appropriate levels of the library directory. Expected exactly "
        f"one subdirectory with __init__.pyi in '{stubs_dir}', but found {2}."
    )
    with pytest.raises(RuntimeError, match=error_format(message)):
        aa.move_stubs(stubs_dir, library_root)

    # Verify that no files were moved
    assert not list(library_root.rglob("*.pyi"))

    # Verifies that attempting to move files from /stubs hierarchy that does not contain an __init__.pyi file fails
    # as expected.
    os.remove(init_1_path)
    os.remove(init_2_path)
    message: str = (
        f"Unable to move the generated stub files to appropriate levels of the library directory. Expected exactly "
        f"one subdirectory with __init__.pyi in '{stubs_dir}', but found {0}."
    )
    with pytest.raises(RuntimeError, match=error_format(message)):
        aa.move_stubs(stubs_dir, library_root)

    # Verify that no files were moved
    assert not list(library_root.rglob("*.pyi"))


@pytest.mark.parametrize(
    "config, expected_result",
    [
        # Valid configuration
        ({"pypi": {"username": "__token__", "password": "pypi-faketoken1234567890abcdef"}}, True),
        # Missing pypi section
        ({"distutils": {"index-servers": "pypi"}}, False),
        # Missing username
        ({"pypi": {"password": "pypi-faketoken1234567890abcdef"}}, False),
        # Missing password
        ({"pypi": {"username": "__token__"}}, False),
        # Incorrect username
        ({"pypi": {"username": "not_token", "password": "pypi-faketoken1234567890abcdef"}}, False),
        # Incorrect password format
        ({"pypi": {"username": "__token__", "password": "not-pypi-faketoken1234567890abcdef"}}, False),
        # Empty file
        ({}, False),
    ],
)
def test_verify_pypirc(tmp_path, config, expected_result):
    """Verifies the functioning of the verify_pypirc() function across all supported pypirc file layouts.

    Args:
        tmp_path: Internal pytest fixture that generates temporary folders to isolate test-generated files.
        config: The pypirc file (contents) configuration to be used for the test.
        expected_result: The expected boolean return for the tested configuration.

    Note:
        This tests both valid success and valid failure runtimes.
    """

    # Creates a mock .pypirc file with the given configuration
    pypirc_path = tmp_path / ".pypirc"
    config_parser = ConfigParser()
    config_parser.read_dict(config)
    with pypirc_path.open("w") as f:
        config_parser.write(f)

    # Runs the verify_pypirc function
    result = aa.verify_pypirc(pypirc_path)

    # Asserts that the function returns the expected result
    assert result == expected_result

    # For successful cases, verifies that the file was indeed configured according to expectation
    if expected_result:
        config_validator = ConfigParser()
        config_validator.read(pypirc_path)
        assert config_validator.has_section("pypi")
        assert config_validator.has_option("pypi", "username")
        assert config_validator.has_option("pypi", "password")
        assert config_validator.get("pypi", "username") == "__token__"
        assert config_validator.get("pypi", "password").startswith("pypi-")


def test_verify_pypirc_nonexistent_file(tmp_path) -> None:
    """Verifies that verify_pypirc() function correctly handles nonexistent pypirc files.

    Args:
        tmp_path: Internal pytest fixture that generates temporary folders to isolate test-generated files.
    """

    # Creates a path to a nonexistent file
    nonexistent_path = tmp_path / "nonexistent.pypirc"

    # Runs the verify_pypirc function
    result = aa.verify_pypirc(nonexistent_path)

    # Asserts that the function returns False for a nonexistent file
    assert result is False


def test_delete_stubs(tmp_path) -> None:
    """Verifies the functioning of the delete_stubs() function.

    Args:
        tmp_path: Internal pytest fixture that generates temporary folders to isolate test-generated files.
    """

    # Creates a mock library directory structure with .pyi files
    library_root = tmp_path.joinpath("library")
    library_root.mkdir()
    library_root.joinpath("module1.pyi").touch()
    library_root.joinpath("module2.pyi").touch()
    subdir = library_root.joinpath("subdir")
    subdir.mkdir()
    subdir.joinpath("module3.pyi").touch()
    library_root.joinpath("not_a_stub.py").touch()  # This file should not be deleted

    # Counts initial .pyi files
    initial_pyi_count = len(list(library_root.rglob("*.pyi")))
    assert initial_pyi_count == 3

    aa.delete_stubs(library_root)

    # Verifies that all .pyi files have been deleted
    remaining_pyi_files = list(library_root.rglob("*.pyi"))
    assert len(remaining_pyi_files) == 0

    # Verifies that non-.pyi files were not deleted
    assert (library_root / "not_a_stub.py").exists()

    # Verifies directory structure is maintained
    assert subdir.exists()

    # Runs the function again to ensure it handles the case when no .pyi files are present
    aa.delete_stubs(library_root)  # This should not raise any errors


def test_rename_all_envs(tmp_path) -> None:
    """Verifies the functioning of the rename_all_envs() function.

    Args:
        tmp_path: Internal pytest fixture that generates temporary folders to isolate test-generated files.
    """

    # Configure console to suppress output

    # Creates a mock project directory structure
    project_root = tmp_path.joinpath("project")
    envs_dir = project_root.joinpath("envs")
    envs_dir.mkdir(parents=True)

    # Creates mock environment files
    yml_content = {"name": "old_env_win", "dependencies": ["python=3.8"]}
    envs_dir.joinpath("old_env_win.yml").write_text(yaml.dump(yml_content))
    envs_dir.joinpath("old_env_lin.yml").write_text(yaml.dump(yml_content))
    envs_dir.joinpath("old_env_osx.yml").write_text(yaml.dump(yml_content))
    envs_dir.joinpath("old_env_win_spec.txt").touch()
    envs_dir.joinpath("old_env_lin_spec.txt").touch()
    envs_dir.joinpath("old_env_osx_spec.txt").touch()
    envs_dir.joinpath("unrelated_file.txt").touch()  # This file should not be renamed

    new_name = "new_env"
    aa.rename_all_envs(project_root, new_name)

    # Verifies that .yml files are renamed and their content is updated
    for os_suffix in ["win", "lin", "osx"]:
        new_yml_path = envs_dir.joinpath(f"{new_name}_{os_suffix}.yml")
        assert new_yml_path.exists(), f"Expected {new_yml_path} to exist"

        yml_content = yaml.safe_load(new_yml_path.read_text())
        assert yml_content["name"] == f"{new_name}_{os_suffix}", f"Expected name in {new_yml_path} to be updated"

        old_yml_path = envs_dir.joinpath(f"old_env_{os_suffix}.yml")
        assert not old_yml_path.exists(), f"Expected {old_yml_path} to be deleted"

    # Verifies that _spec.txt files are renamed
    for os_suffix in ["win", "lin", "osx"]:
        new_spec_path = envs_dir.joinpath(f"{new_name}_{os_suffix}_spec.txt")
        assert new_spec_path.exists(), f"Expected {new_spec_path} to exist"

        old_spec_path = envs_dir.joinpath(f"old_env_{os_suffix}_spec.txt")
        assert not old_spec_path.exists(), f"Expected {old_spec_path} to be deleted"

    # Verifies that unrelated files are not renamed
    assert envs_dir.joinpath("unrelated_file.txt").exists(), "Expected unrelated file to remain unchanged"

    # Verifies the total number of files in the directory
    all_files = list(envs_dir.iterdir())
    assert len(all_files) == 7, f"Expected 7 files in total, found {len(all_files)}"


def test_replace_markers_in_file(tmp_path) -> None:
    """Verifies the functioning of the replace_markers_in_file() function.

    Args:
        tmp_path: Internal pytest fixture that generates temporary folders to isolate test-generated files.
    """

    # Creates a temporary file with markers
    file_path = tmp_path.joinpath("test_file.txt")
    initial_content = "Hello, {{NAME}}! Welcome to {{PLACE}}. Your ID is {{ID}}."
    file_path.write_text(initial_content, encoding="utf-8")

    # Defines markers to replace
    markers = {
        "{{NAME}}": "John Doe",
        "{{PLACE}}": "Pythonville",
        "{{ID}}": "12345",
        "{{UNUSED}}": "This marker is not in the file",
    }

    # Runs the replace_markers_in_file function
    modification_count = aa.replace_markers_in_file(file_path, markers)

    # Reads the modified file content
    modified_content = file_path.read_text(encoding="utf-8")

    # Verifies the modified file matches expectations
    assert modification_count == 3
    assert modified_content == "Hello, John Doe! Welcome to Pythonville. Your ID is 12345."
    assert "{{NAME}}" not in modified_content
    assert "{{PLACE}}" not in modified_content
    assert "{{ID}}" not in modified_content
    assert "{{UNUSED}}" not in modified_content

    # Verifies modifications are not performed for files without markers.
    no_change_markers = {"{{NOTFOUND}}": "This won't be replaced"}
    no_change_count = aa.replace_markers_in_file(file_path, no_change_markers)
    assert no_change_count == 0

    # Verifies file content hasn't changed after any modifications
    unchanged_content = file_path.read_text(encoding="utf-8")
    assert unchanged_content == modified_content


@pytest.mark.parametrize(
    "library_name, is_valid",
    [
        ("valid_name", True),
        ("ValidName123", True),
        ("VALID_NAME", True),
        ("_valid_name_", True),
        ("123valid", True),
        ("invalid-name", False),
        ("invalid name", False),
        ("invalid.name", False),
        ("invalid@name", False),
        ("", True),  # Assuming empty string is valid, adjust if not
    ],
)
def test_validate_library_name(library_name, is_valid):
    """Verifies the functioning of the validate_library_name() function for all supported inputs.

    Args:
        library_name: The library name input to be validated.
        is_valid: The expected outcome of the validation process.

    Notes:
        All click validators use click, rather than console, as the messaging backend to specifically integrate
        with the broader cli interface. Only the validator functions use this backend.
    """

    if is_valid:
        # noinspection PyTypeChecker
        result = aa.validate_library_name(None, None, library_name)
        assert result == library_name
    else:
        with pytest.raises(click.BadParameter) as excinfo:
            # noinspection PyTypeChecker
            aa.validate_library_name(None, None, library_name)
        assert "Library name should contain only letters, numbers, and underscores." in str(excinfo.value)


@pytest.mark.parametrize(
    "project_name, is_valid",
    [
        ("valid-project", True),
        ("ValidProject123", True),
        ("VALID-PROJECT", True),
        ("123valid", True),
        ("invalid_project", False),
        ("invalid project", False),
        ("invalid.project", False),
        ("invalid@project", False),
        ("", False),  # Assuming empty string is invalid
    ],
)
def test_validate_project_name(project_name, is_valid):
    """Verifies the functioning of the validate_project_name() function for all supported inputs.

    Args:
        project_name: The project name input to be validated.
        is_valid: The expected outcome of the validation process.

    Notes:
        All click validators use click, rather than console, as the messaging backend to specifically integrate
        with the broader cli interface. Only the validator functions use this backend.
    """

    if is_valid:
        # noinspection PyTypeChecker
        result = aa.validate_project_name(None, None, project_name)
        assert result == project_name
    else:
        with pytest.raises(click.BadParameter) as excinfo:
            # noinspection PyTypeChecker
            aa.validate_project_name(None, None, project_name)
        assert "Project name should contain only letters, numbers, or dashes." in str(excinfo.value)


@pytest.mark.parametrize(
    "author_name, is_valid",
    [
        ("John Doe", True),
        ("John Doe (johndoe)", True),
        ("Mary-Jane O'Connor", True),
        ("Alice Bob (alice-bob)", True),
        ("Invalid Name (invalid@username)", False),
        ("Invalid.Name", False),
        ("(InvalidFormat)", False),
        ("", False),  # Assuming empty string is invalid
    ],
)
def test_validate_author_name(author_name, is_valid):
    """Verifies the functioning of the validate_author_name() function for all supported inputs.

    Args:
        author_name: The author name input to be validated.
        is_valid: The expected outcome of the validation process.

    Notes:
        All click validators use click, rather than console, as the messaging backend to specifically integrate
        with the broader cli interface. Only the validator functions use this backend.
    """

    if is_valid:
        # noinspection PyTypeChecker
        result = aa.validate_author_name(None, None, author_name)
        assert result == author_name
    else:
        with pytest.raises(click.BadParameter) as excinfo:
            # noinspection PyTypeChecker
            aa.validate_author_name(None, None, author_name)
        assert "Author name should be in the format" in str(excinfo.value)


@pytest.mark.parametrize(
    "email, is_valid",
    [
        ("valid@example.com", True),
        ("valid.email@sub.domain.com", True),
        ("valid_email123@domain.co.uk", True),
        ("invalid email@example.com", False),
        ("invalid@domain", False),
        ("@invalid.com", False),
        ("invalid.com", False),
        ("", False),  # Assuming empty string is invalid
    ],
)
def test_validate_email(email, is_valid):
    """Verifies the functioning of the validate_email() function for all supported inputs.

    Args:
        email: The email address input to be validated.
        is_valid: The expected outcome of the validation process.

    Notes:
        All click validators use click, rather than console, as the messaging backend to specifically integrate
        with the broader cli interface. Only the validator functions use this backend.
    """

    if is_valid:
        # noinspection PyTypeChecker
        result = aa.validate_email(None, None, email)
        assert result == email
    else:
        with pytest.raises(click.BadParameter) as excinfo:
            # noinspection PyTypeChecker
            aa.validate_email(None, None, email)
        assert "Invalid email address." in str(excinfo.value)


@pytest.mark.parametrize(
    "env_name, is_valid",
    [
        ("valid_env", True),
        ("ValidEnv123", True),
        ("VALID_ENV", True),
        ("_valid_env_", True),
        ("123valid", True),
        ("invalid-env", False),
        ("invalid env", False),
        ("invalid.env", False),
        ("invalid@env", False),
        ("", True),  # Assuming empty string is valid, adjust if not
    ],
)
def test_validate_env_name(env_name, is_valid):
    """Verifies the functioning of the validate_env_name() function for all supported inputs.

    Args:
        env_name: The environment name input to be validated.
        is_valid: The expected outcome of the validation process.

    Notes:
        All click validators use click, rather than console, as the messaging backend to specifically integrate
        with the broader cli interface. Only the validator functions use this backend.
    """

    if is_valid:
        # noinspection PyTypeChecker
        result = aa.validate_env_name(None, None, env_name)
        assert result == env_name
    else:
        with pytest.raises(click.BadParameter) as excinfo:
            # noinspection PyTypeChecker
            aa.validate_env_name(None, None, env_name)
        assert "Environment name should contain only letters, numbers, and underscores." in str(excinfo.value)
