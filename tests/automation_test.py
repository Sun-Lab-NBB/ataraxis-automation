"""This module stores the tests for all classes and functions available from the automation.py module."""

import tempfile

import pytest
import os
import sys
import subprocess
from pathlib import Path
from ataraxis_automation.automation import (
    configure_console, resolve_project_directory, resolve_library_root,
    resolve_environment_files, resolve_conda_engine, resolve_pip_engine
)
import shutil as sh
import re
import textwrap
import subprocess
from unittest.mock import Mock


@pytest.fixture
def project_dir(tmp_path) -> Path:
    """Generates the test project root directory with the required files expected by the automation functions.

    Args:
        tmp_path: internal pytest fixture that generates temporary folders to isolate test-generated files.

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

    This method is used to setup pytest 'match' clauses to verify raised exceptions.
    """
    return re.escape(textwrap.fill(message, width=120, break_long_words=False, break_on_hyphens=False))


def test_configure_console(tmp_path, capsys):
    """Verifies that configure_console method functions as expected under different input configurations."""
    # Setup
    log_dir = tmp_path.joinpath("logs")
    log_dir.mkdir()
    message_log = log_dir.joinpath("message_log.txt")
    error_log = log_dir.joinpath("error_log.txt")

    # Verifies initialization with logging enabled generates log files
    configure_console(log_dir, verbose=True, enable_logging=True)
    assert message_log.exists()
    assert error_log.exists()

    # Resets the log directory
    sh.rmtree(log_dir)
    log_dir.mkdir()

    # Verifies that disabling logging does not create log files
    configure_console(log_dir, verbose=True, enable_logging=False)
    assert not message_log.exists()
    assert not error_log.exists()

    # Changes the working directory to the general temporary directory to fail the tests below
    os.chdir(tempfile.gettempdir())

    # This should do two things: print a formatted message with traceback to the console and (evaluated here) call a
    # SystemExit. This is the expected 'verbose' console behavior.
    # noinspection PyTypeChecker
    with pytest.raises((SystemExit, RuntimeError)):
        resolve_project_directory()
    captured = capsys.readouterr()
    assert "Unable to confirm that ataraxis automation module has been called" in captured.err

    # Reconfigures console to not print or log anything
    configure_console(log_dir, verbose=False, enable_logging=False)
    assert not message_log.exists()
    assert not error_log.exists()

    # When console is disabled, errors are raised using standard python 'raise' system, which should be caught by
    # pytest.
    with pytest.raises(RuntimeError):
        resolve_project_directory()


def test_resolve_project_directory(project_dir):
    """Verifies that resolve_project_directory() method works as expected for a well-configured project."""
    configure_console(verbose=False, enable_logging=False)
    os.chdir(project_dir)
    result = resolve_project_directory()
    assert result == project_dir


def test_resolve_project_directory_error(tmp_path):
    """Verifies that resolve_project_directory() fails for non-project directories."""
    configure_console(verbose=False, enable_logging=False)
    os.chdir(tmp_path)
    message: str = (
        f"Unable to confirm that ataraxis automation module has been called from the root directory of a valid "
        f"Python project. This function expects that the current working directory is set to the root directory of "
        f"the project, judged by the presence of '/src', '/envs', 'pyproject.toml' and 'tox.ini'. Current working "
        f"directory is set to {os.getcwd()}, which does not contain at least one of the required files."
    )
    with pytest.raises(RuntimeError, match=error_format(message)):
        resolve_project_directory()


@pytest.mark.parametrize("init_location, expected", [
    ("src", "src"),
    ("src/library", "src/library"),
])
def test_resolve_library_root(project_dir, init_location, expected):
    """Verifies that resolve_library_root() function works as expected for src-root and library_name-root projects."""
    configure_console(verbose=False, enable_logging=False)
    init_dir = project_dir.joinpath(init_location)
    init_dir.mkdir(parents=True, exist_ok=True)
    init_dir.joinpath('__init__.py').touch()
    result = resolve_library_root(project_root=project_dir)
    assert result == project_dir / expected


def test_resolve_library_root_error(project_dir):
    """Verifies error-handling behavior of resolve_library_root() method."""

    # Verifies the method correctly fails when __init__.py is not found under /src or any subdirectory directly under
    # src
    configure_console(verbose=False, enable_logging=False)
    message: str = (
        f"Unable to resolve the path to the library root directory from the project root path {project_dir}. "
        f"Specifically, did not find an __init__.py inside the /src directory and found {0} "
        f"sub-directories with __init__.py inside the /src directory. Make sure there is an __init__.py "
        f"inside /src or ONE of the sub-directories under /src."
    )
    with pytest.raises(RuntimeError, match=error_format(message)):
        resolve_library_root(project_dir)

    # Verifies that the method fails for cases where multiple subdirectories under src have __init__.py
    library1 = project_dir.joinpath("src/library1")
    library2 = project_dir.joinpath("src/library2")
    library1.mkdir(parents=True, exist_ok=True)
    library2.mkdir(parents=True, exist_ok=True)
    library1.joinpath('__init__.py').touch()
    library2.joinpath('__init__.py').touch()
    message: str = (
        f"Unable to resolve the path to the library root directory from the project root path {project_dir}. "
        f"Specifically, did not find an __init__.py inside the /src directory and found {2} "
        f"sub-directories with __init__.py inside the /src directory. Make sure there is an __init__.py "
        f"inside /src or ONE of the sub-directories under /src."
    )
    with pytest.raises(RuntimeError, match=error_format(message)):
        resolve_library_root(project_dir)


def test_resolve_environment_files(project_dir, monkeypatch):
    """Verifies that resolve_environment_files() function works as expected for supported platforms."""
    configure_console(verbose=False, enable_logging=False)
    os.chdir(project_dir)  # Ensures working directory is set to the project directory
    environment_base_name: str = "test_env"

    # Verifies environment resolution works as expected for linux platform
    monkeypatch.setattr(sys, 'platform', 'linux')
    yml_path, spec_path = resolve_environment_files(environment_base_name=environment_base_name)
    assert yml_path == project_dir / "envs" / f"{environment_base_name}_lin.yml"
    assert spec_path == project_dir / "envs" / f"{environment_base_name}_lin_spec.txt"

    # Verifies environment resolution works as expected for windows platform
    monkeypatch.setattr(sys, 'platform', 'win32')
    yml_path, spec_path = resolve_environment_files(environment_base_name=environment_base_name)
    assert yml_path == project_dir / "envs" / f"{environment_base_name}_win.yml"
    assert spec_path == project_dir / "envs" / f"{environment_base_name}_win_spec.txt"

    # Verifies environment resolution works as expected for darwin (OSx ARM64) platform
    monkeypatch.setattr(sys, 'platform', 'darwin')
    yml_path, spec_path = resolve_environment_files(environment_base_name=environment_base_name)
    assert yml_path == project_dir / "envs" / f"{environment_base_name}_osx.yml"
    assert spec_path == project_dir / "envs" / f"{environment_base_name}_osx_spec.txt"


def test_resolve_environment_files_error(project_dir, monkeypatch):
    """Verifies resolve_environment_files() function fails for unsupported platforms."""
    configure_console(verbose=False, enable_logging=False)
    supported_platforms: dict[str, str] = {"win32": "_win",
                                           "linux": "_lin",
                                           "darwin": "_osx"
                                           }
    monkeypatch.setattr(sys, 'platform', 'unsupported')
    environment_base_name: str = 'text_env'
    os.chdir(project_dir)
    message: str = (
        f"Unable to resolve the os-specific suffix to use for conda environment file(s). Unsupported host OS "
        f"detected: {'unsupported'}. Currently, supported OS options are are: {', '.join(supported_platforms.keys())}."
    )
    with pytest.raises(RuntimeError, match=error_format(message)):
        resolve_environment_files(environment_base_name=environment_base_name)


def test_resolve_conda_engine_success(monkeypatch):
    """Verifies the functioning of the resolve_conda_engine() function when both mamba and conda engines are available.
    """
    configure_console(verbose=False, enable_logging=False)

    def mock_subprocess_run(*args, **kwargs):
        """Returns success code for either mamba or conda command. """
        if 'mamba --version' == args[0] or 'conda --version' in args[0]:
            return Mock(returncode=0)
        raise subprocess.CalledProcessError(1, 'cmd')

    # Expects that when both mamba and conda commands return success codes, mamba is chosen over conda.
    monkeypatch.setattr(subprocess, 'run', mock_subprocess_run)
    result = resolve_conda_engine()
    assert result == "mamba"


def test_resolve_conda_engine_fallback(monkeypatch):
    """Verifies the functioning of the resolve_conda_engine() function when only conda engine is available. """
    configure_console(verbose=False, enable_logging=False)

    def mock_subprocess_run(*args, **kwargs):
        """Ensures 'conda --version' returns success code 0."""
        if 'conda --version' == args[0]:
            return Mock(returncode=0)
        raise subprocess.CalledProcessError(1, 'cmd')

    # When mamba is not available, expects that conda is selected as the conda engine.
    monkeypatch.setattr(subprocess, 'run', mock_subprocess_run)
    result = resolve_conda_engine()
    assert result == "conda"


def test_resolve_conda_engine_error(monkeypatch):
    """Verifies that resolve_conda_engine() function fails when neither conda nor mamba are available."""
    configure_console(verbose=False, enable_logging=False)

    def mock_run(*args, **kwargs):
        """Ensures subprocess always returns error code 1, regardless of the command.

        This makes it fail for both mamba and conda.
        """
        raise subprocess.CalledProcessError(1, 'cmd')

    # When neither conda nor mamba is available, expects a RuntimeError
    monkeypatch.setattr(subprocess, 'run', mock_run)
    message: str = (f"Unable to determine the conda / mamba engine to use for 'conda' commands. Specifically, unable"
                    f"to interface with either conda or mamba. Is conda or supported equivalent installed, initialized "
                    f"and added to Path?")
    with pytest.raises(RuntimeError, match=error_format(message)):
        resolve_conda_engine()


def test_resolve_pip_engine_success(monkeypatch):
    """Verifies the functioning of the resolve_pip_engine() function when both uv and pip engines are available.
    """
    configure_console(verbose=False, enable_logging=False)

    def mock_subprocess_run(*args, **kwargs):
        """Returns success code for either uv pip or pip command."""
        if 'uv pip --version' == args[0] or 'pip --version' == args[0]:
            return Mock(returncode=0)
        raise subprocess.CalledProcessError(1, 'cmd')

    # When both pip and uv are available, expects that uv is selected over pip.
    monkeypatch.setattr(subprocess, 'run', mock_subprocess_run)
    result = resolve_pip_engine()
    assert result == "uv pip"


def test_resolve_pip_engine_fallback(monkeypatch):
    """Verifies the functioning of the resolve_pip_engine() function when only pip engine is available."""
    configure_console(verbose=False, enable_logging=False)

    def mock_subprocess_run(*args, **kwargs):
        """Ensures 'pip --version' returns success code 0."""
        if 'pip --version' == args[0]:
            return Mock(returncode=0)
        raise subprocess.CalledProcessError(1, 'cmd')

    # When uv is not available, expects that pip is selected as the pip engine.
    monkeypatch.setattr(subprocess, 'run', mock_subprocess_run)
    result = resolve_pip_engine()
    assert result == "pip"


def test_resolve_pip_engine_error(monkeypatch):
    """Verifies that resolve_pip_engine() function fails when neither pip nor uv are available."""
    configure_console(verbose=False, enable_logging=False)

    def mock_run(*args, **kwargs):
        """Ensures subprocess always returns error code 1, regardless of the command.

        This makes it fail for both uv and pip.
        """
        raise subprocess.CalledProcessError(1, 'cmd')

    # When neither pip nor uv is available, expects a RuntimeError
    monkeypatch.setattr(subprocess, 'run', mock_run)
    message: str = (
        f"Unable to determine the engine to use for pip commands. Specifically, was not able to interface with any of "
        f"the supported pip-engines. Is pip, uv or supported equivalent installed in the currently active "
        f"virtual / conda environment?"
    )
    with pytest.raises(RuntimeError, match=error_format(message)):
        resolve_pip_engine()
