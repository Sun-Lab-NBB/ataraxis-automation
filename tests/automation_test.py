"""This module stores the tests for all non-cli functions available from the automation.py module."""

import os
import re
import sys
from pathlib import Path
import textwrap
import subprocess
from configparser import ConfigParser
from unittest.mock import Mock

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
        Formatted and escaped message that can be used as the 'match' argument of the pytest.raises() method.
    """
    return re.escape(textwrap.fill(message, width=120, break_long_words=False, break_on_hyphens=False))


def test_resolve_project_directory(project_dir) -> None:
    """Verifies the functionality of the resolve_project_directory() function."""
    os.chdir(project_dir)
    result = aa.resolve_project_directory()
    assert result == project_dir


def test_resolve_project_directory_error(tmp_path) -> None:
    """Verifies the error handling behavior of the resolve_project_directory() function."""

    os.chdir(tmp_path)
    message: str = (
        f"Unable to confirm that ataraxis automation CLI has been called from the root directory of a valid Python "
        f"project. This CLI expects that the current working directory is set to the root directory of the "
        f"project, judged by the presence of '/src', '/envs', 'pyproject.toml' and 'tox.ini'. Current working "
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
    """Verifies the functionality of the resolve_library_root() function.

    Tests the following scenarios:
        0 - library root being the /src directory (used by our c-extension projects).
        1 - library root being a subfolder under the /src directory.
    """

    init_dir = project_dir.joinpath(init_location)
    init_dir.mkdir(parents=True, exist_ok=True)
    init_dir.joinpath("__init__.py").touch()
    result = aa.resolve_library_root(project_root=project_dir)
    assert result == project_dir / expected


def test_resolve_library_root_error(project_dir) -> None:
    """Verifies error-handling behavior of the resolve_library_root() function."""

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
    """Verifies the functionality of the resolve_environment_files() function."""

    os.chdir(project_dir)  # Ensures working directory is set to the project directory
    environment_base_name: str = "test_env"

    project_dir: Path = aa.resolve_project_directory()

    # Verifies environment resolution works as expected for the linux platform
    monkeypatch.setattr(sys, "platform", "linux")
    env_name, yml_path, spec_path = aa._resolve_environment_files(
        project_root=project_dir, environment_base_name=environment_base_name
    )
    assert env_name == f"{environment_base_name}_lin"
    assert yml_path == project_dir / "envs" / f"{environment_base_name}_lin.yml"
    assert spec_path == project_dir / "envs" / f"{environment_base_name}_lin_spec.txt"

    # Verifies environment resolution works as expected for the Windows platform
    monkeypatch.setattr(sys, "platform", "win32")
    env_name, yml_path, spec_path = aa._resolve_environment_files(
        project_root=project_dir, environment_base_name=environment_base_name
    )
    assert env_name == f"{environment_base_name}_win"
    assert yml_path == project_dir / "envs" / f"{environment_base_name}_win.yml"
    assert spec_path == project_dir / "envs" / f"{environment_base_name}_win_spec.txt"

    # Verifies environment resolution works as expected for the darwin (OSx ARM64) platform
    monkeypatch.setattr(sys, "platform", "darwin")
    env_name, yml_path, spec_path = aa._resolve_environment_files(
        project_root=project_dir, environment_base_name=environment_base_name
    )
    assert env_name == f"{environment_base_name}_osx"
    assert yml_path == project_dir / "envs" / f"{environment_base_name}_osx.yml"
    assert spec_path == project_dir / "envs" / f"{environment_base_name}_osx_spec.txt"


def test_resolve_environment_files_error(project_dir, monkeypatch) -> None:
    """Verifies the functionality of the resolve_environment_files() function."""

    supported_platforms: dict[str, str] = {"win32": "_win", "linux": "_lin", "darwin": "_osx"}
    monkeypatch.setattr(sys, "platform", "unsupported")
    environment_base_name: str = "text_env"
    os.chdir(project_dir)
    message: str = (
        f"Unable to resolve the operating-system-specific suffix to use for conda environment file names. The "
        f"local machine is using an unsupported operating system {'unsupported'}. Currently, only the following "
        f"operating systems are supported: {', '.join(supported_platforms.keys())}."
    )
    with pytest.raises(RuntimeError, match=error_format(message)):
        aa._resolve_environment_files(project_root=project_dir, environment_base_name=environment_base_name)


def test_resolve_conda_engine(monkeypatch) -> None:
    """Verifies the functionality of the resolve_conda_engine() function when both mamba and conda are available."""

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
    """Verifies the functionality of the resolve_conda_engine() function when only conda is available."""

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
    """Verifies the error-handling behavior of the resolve_conda_engine() function when neither mamba not conda are
    available."""

    # noinspection PyUnusedLocal
    def mock_run(*args, **kwargs):
        """Ensures subprocess always returns error code 1, regardless of the command.

        This makes it fail for both mamba and conda.
        """
        raise subprocess.CalledProcessError(1, "cmd")

    # When neither conda nor mamba is available, expects a RuntimeError
    monkeypatch.setattr(subprocess, "run", mock_run)
    message: str = (
        f"Unable to determine the engine to use for 'conda' commands. Specifically, unable to interface with either "
        f"conda or mamba. Is conda or (preferred) mamba installed, initialized, and added to Path?"
    )
    with pytest.raises(RuntimeError, match=error_format(message)):
        aa.resolve_conda_engine()


def test_resolve_pip_engine(monkeypatch) -> None:
    """Verifies the functionality of the resolve_pip_engine() function when both uv and pip engines are available."""

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
    """Verifies the functionality of the resolve_pip_engine() function when only pip engine is available."""

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
    """Verifies the error-handling behavior of the resolve_pip_engine() function when neither pip nor uv are
    available."""

    # noinspection PyUnusedLocal
    def mock_run(*args, **kwargs):
        """Ensures subprocess always returns error code 1, regardless of the command.

        This makes it fail for both uv and pip.
        """
        raise subprocess.CalledProcessError(1, "cmd")

    # When neither pip nor uv is available, expects a RuntimeError
    monkeypatch.setattr(subprocess, "run", mock_run)
    message: str = (
        f"Unable to determine the engine to use for 'pip' commands. Specifically, unable to interface with either "
        f"pip or uv. Is pip or (preferred) uv installed in the active python environment?"
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
    """Verifies the functionality of the get_base_name() function.

    Tests all supported input scenarios.
    """

    assert aa._get_base_name(dependency) == expected


def test_add_dependency() -> None:
    """Verifies the functionality and duplicate input handling of the add_dependency() function."""

    # Setup
    processed_dependencies = set()
    dependencies_list = []

    # Ensures that if the base name of the dependency (stripped of "version") is correctly added to dependencies_list,
    # unless it is already contained in processed_dependencies
    dependencies_list, processed_dependencies = aa._add_dependency(
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
        aa._add_dependency(
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
        aa._add_dependency(
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
    """Verifies the functionality of the resolve_dependencies() function."""

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

    conda_deps, pip_deps = aa._resolve_dependencies(project_dir)

    assert set(conda_deps) == {f'"conda_dep1[test]"', f'"conda_dep2"', f'"condarun_dep==3"'}
    assert set(pip_deps) == {f'"dep1==1.0"', f'"dep2>=2.0"', f'"noconda_dep<2.0.1"'}


def test_resolve_dependencies_missing_tox_dep(project_dir: Path) -> None:
    """Verifies that the resolve_dependencies() function correctly detects tox dependencies missing from
    pyproject.toml."""

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
        aa._resolve_dependencies(project_dir)


def test_resolve_dependencies_duplicate_dep(project_dir: Path) -> None:
    """Verifies that resolve_dependencies() function correctly catches duplicate dependencies in supported .toml
    lists."""

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
        f"Unable to resolve project dependencies. Found a duplicate dependency for 'dep1<3.0', listed in "
        f"pyproject.toml. A dependency should only be found once across the dependencies and optional-dependencies "
        f"lists."
    )
    with pytest.raises(ValueError, match=error_format(message)):
        aa._resolve_dependencies(project_dir)


@pytest.mark.parametrize("section", ["condarun", "conda"])
def test_resolve_dependencies_priority(project_dir, section: Path) -> None:
    """Verifies that resolve_dependencies() correctly prioritizes resolving run-dependencies as conda dependencies over
    pip where possible."""

    pyproject_content = f"""
    [project]
    dependencies = ["dep1==1.0", "dep2>=2.0"]

    [project.optional-dependencies]
    conda = ["conda_dep1", "conda_dep2"{', "priority_dep"' if section == "conda" else ""}]
    noconda = ["noconda_dep"]
    condarun = ["condarun_dep"{', "priority_dep"' if section == "condarun" else ""}]
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

    conda_deps, pip_deps = aa._resolve_dependencies(project_dir)

    assert f'"priority_dep"' in conda_deps
    assert f'"priority_dep"' not in pip_deps


def test_resolve_project_name(project_dir) -> None:
    """Verifies the functionality of the resolve_project_name() function."""

    pyproject_content = """
    [project]
    name = "test-project"
    """
    pyproject_path = project_dir.joinpath("pyproject.toml")
    pyproject_path.write_text(pyproject_content)

    result = aa._resolve_project_name(project_dir)
    assert result == "test-project"


def test_resolve_project_name_errors(project_dir) -> None:
    """Verifies the error-handling behavior of the resolve_project_name() function."""

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
        aa._resolve_project_name(project_dir)

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
        aa._resolve_project_name(project_dir)

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
        aa._resolve_project_name(project_dir)


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
    """Verifies the functionality of resolve_environment_commands().

    Tests all supported platforms and conda / mamba engine combinations.
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
    result = aa.resolve_project_environment(project_dir, "test_env", python_version=python_version)

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
    assert f"test_env{os_suffix}" in result.activate_command
    assert f"conda deactivate" in result.deactivate_command
    assert f"python={python_version} pip tox uv --yes" in result.create_command
    assert f"test_env{os_suffix} --all --yes" in result.remove_command
    assert result.environment_name == f"test_env{os_suffix}"

    # When there are no conda or pip dependencies, the corresponding command is actually set to None
    if len(dependencies[0]) != 0:
        assert f"test_env{os_suffix} {' '.join(dependencies[0])} --yes" in result.conda_dependencies_command
    else:
        assert result.conda_dependencies_command is None
    if len(dependencies[1]) != 0:
        assert f"{pip_engine} install {' '.join(dependencies[1])}" in result.install_dependencies_command
    else:
        assert result.install_dependencies_command is None

    assert f"{conda_engine} env update -n test_env{os_suffix}" in result.update_command
    assert f"{conda_engine} env export --name test_env{os_suffix}" in result.export_yml_command
    assert f"{conda_engine} list -n test_env{os_suffix} --explicit" in result.export_spec_command
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
        assert f"test_env{os_suffix}" in result.uninstall_project_command
        command_string = f"--resolution highest --refresh --reinstall-package test-project --compile-bytecode"
        assert command_string in result.install_project_command
        if len(dependencies[1]) != 0:
            assert f"--compile-bytecode --python=" in result.install_dependencies_command
    else:
        assert "--yes" in result.uninstall_project_command
        assert "--compile" in result.install_project_command
        if len(dependencies[1]) != 0:
            assert "--compile" in result.install_dependencies_command
        else:
            assert result.install_dependencies_command is None

    # Checks for new yml-related commands
    assert result.create_from_yml_command == f"{conda_engine} env create -f {yml_path} --yes"
    assert result.update_command == f"{conda_engine} env update -n test_env{os_suffix} -f {yml_path} --prune"

    # Also tests the case where .yaml files are not present in the /envs folder.
    os.remove(yml_path)
    result = aa.resolve_project_environment(project_dir, "test_env", python_version=python_version)
    assert result.create_from_yml_command is None
    assert result.update_command is None


def test_generate_typed_marker(tmp_path) -> None:
    """Verifies the functionality of the generate_typed_marker() function."""
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
    """Verifies the functionality of the test_move_stubs() function."""

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

    # Verifies a unique case where there is a single file, but it uses the duplicate name notation. The file should be
    # renamed to exclude the number suffix.
    os.remove(library_root / "osx_file.pyi")
    stub_lib_dir.joinpath("__init__.pyi").touch()
    (library_root / "osx_file 1.pyi").touch()
    aa.move_stubs(stubs_dir, library_root)
    assert (library_root / "osx_file.pyi").exists()


def test_move_stubs_error(project_dir) -> None:
    """Verifies the error-handling behavior of the move_stubs() function."""

    # Sets up mock directories
    stubs_dir = project_dir.joinpath("stubs")
    library_root = project_dir / "src" / "library"
    stubs_dir.mkdir()
    library_root.mkdir(parents=True)

    # Creates invalid stub directory structure (multiple subdirectories with __init__.pyi)
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
    """Verifies the functionality of the verify_pypirc() function.

    Tests all supported pypirc layouts.
    """

    # Creates a mock .pypirc file with the given configuration
    pypirc_path = tmp_path / ".pypirc"
    config_parser = ConfigParser()
    config_parser.read_dict(config)
    with pypirc_path.open("w") as f:
        # noinspection PyTypeChecker
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
    """Verifies teh error-handling behavior of the verify_pypirc() function."""

    # Creates a path to a nonexistent file
    nonexistent_path = tmp_path / "nonexistent.pypirc"

    # Runs the verify_pypirc function
    result = aa.verify_pypirc(nonexistent_path)

    # Asserts that the function returns False for a nonexistent file
    assert result is False


def test_delete_stubs(tmp_path) -> None:
    """Verifies the functionality of the delete_stubs() function."""

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


@pytest.fixture
def mock_commands():
    """Creates a mock instance of EnvironmentCommands for testing."""
    return EnvironmentCommands(
        activate_command="conda init && conda activate test_env",
        deactivate_command="conda init && conda deactivate",
        create_command="conda create -n test_env python=3.8 tox pip uv",
        create_from_yml_command="conda env create -f env.yml -n test_env",
        remove_command="conda env remove -n test_env",
        conda_dependencies_command="conda install -n test_env package1 package2",
        pip_dependencies_command="pip install package3 package4",
        update_command="conda env update -f env.yml -n test_env",
        export_yml_command="conda env export -n test_env > env.yml",
        export_spec_command="conda list -n test_env --explicit > spec.txt",
        environment_name="test_env",
        install_project_command="uv pip install --no-cache-dir .",
        uninstall_project_command="pip uninstall -y project_name",
        provision_command="conda install --revision 0 -n test_env",
        environment_directory="mock_dir",
    )


def test_environment_exists(monkeypatch, mock_commands):
    """Verifies the functionality of environment_exists() function when environment activation command runs as
    expected.
    """

    # noinspection PyUnusedLocal
    def mock_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, 0)

    # Runs the command mocking the subprocess call output to be a success code
    monkeypatch.setattr(subprocess, "run", mock_run)
    assert aa.environment_exists(mock_commands) is True


def test_environment_exists_error(monkeypatch, mock_commands):
    """Verifies the functionality of environment_exists() function when environment activation command fails."""

    # noinspection PyUnusedLocal
    def mock_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "cmd")

    # Runs the command mocking the subprocess call output to be a failure code
    monkeypatch.setattr(subprocess, "run", mock_run)
    assert aa.environment_exists(mock_commands) is False
