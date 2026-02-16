"""Contains tests for non-CLI functions provided by the automation module."""

import os
import re
import sys
import stat
import shutil
from pathlib import Path
import subprocess
from configparser import ConfigParser
from unittest.mock import Mock, patch, call

import pytest

import ataraxis_automation.automation as aa
from ataraxis_automation.automation import ProjectEnvironment


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Generates the test project root directory with the required files expected by the automation functions."""
    project_dir = tmp_path.joinpath("project")
    project_dir.mkdir()
    project_dir.joinpath("src").mkdir()
    project_dir.joinpath("envs").mkdir()
    project_dir.joinpath("pyproject.toml").touch()
    project_dir.joinpath("tox.ini").touch()
    return project_dir


@pytest.fixture
def clean_mamba_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Clears all env vars that _resolve_mamba_environments_directory() checks."""
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.delenv("CONDA_DEFAULT_ENV", raising=False)
    monkeypatch.delenv("CONDA_EXE", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    return monkeypatch


def _error_format(message: str) -> str:
    """Formats the input message to match the default Console format and escapes it using re, so that it can be used to
    verify raised exceptions.

    This method is used to set up pytest 'match' clauses to verify raised exceptions.

    Args:
        message: The message to format and escape, according to standard Ataraxis testing parameters.

    Returns:
        Formatted and escaped message that can be used as the 'match' argument of the pytest.raises() method.
    """
    return re.escape(aa.format_message(message=message))


def test_resolve_project_directory(project_dir: Path) -> None:
    """Verifies the functionality of the resolve_project_directory() function."""
    os.chdir(project_dir)
    result = aa.resolve_project_directory()
    assert result == project_dir


def test_resolve_project_directory_error(tmp_path: Path) -> None:
    """Verifies the error handling behavior of the resolve_project_directory() function."""
    os.chdir(tmp_path)
    message: str = (
        f"Unable to confirm that ataraxis automation CLI has been called from the root directory of a valid Python "
        f"project. This CLI expects that the current working directory is set to the root directory of the "
        f"project, judged by the presence of '/src', '/envs', 'pyproject.toml' and 'tox.ini'. Current working "
        f"directory is set to {Path.cwd()}, which does not contain at least one of the required files."
    )
    # noinspection PyTypeChecker
    with pytest.raises((SystemExit, RuntimeError), match=_error_format(message)):
        aa.resolve_project_directory()


@pytest.mark.parametrize(
    "init_location, expected",
    [
        ("src", "src"),
        ("src/library", "src/library"),
    ],
)
def test_resolve_library_root(project_dir: Path, init_location: str, expected: str) -> None:
    """Verifies the functionality of the resolve_library_root() function.

    Tests the following scenarios:
        0 - library root being the /src directory (used by Sun lab c-extension projects).
        1 - library root being a subfolder under the /src directory (Used by Sun lab pure-python projects).
    """
    init_dir = project_dir.joinpath(init_location)
    init_dir.mkdir(parents=True, exist_ok=True)
    init_dir.joinpath("__init__.py").touch()
    result = aa.resolve_library_root(project_root=project_dir)
    assert result == project_dir / expected


def test_resolve_library_root_error(project_dir: Path) -> None:
    """Verifies the error-handling behavior of the resolve_library_root() function."""
    # Verifies the method correctly fails when __init__.py is not found under /src or any subdirectory directly under
    # src
    message: str = (
        f"Unable to resolve the path to the library root directory from the project root path {project_dir}. "
        f"Specifically, did not find an __init__.py inside the /src directory and found {0} "
        f"sub-directories with __init__.py inside the /src directory. Make sure there is an __init__.py "
        f"inside /src or ONE of the sub-directories under /src."
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa.resolve_library_root(project_root=project_dir)

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
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa.resolve_library_root(project_root=project_dir)


def test_resolve_environment_files(project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the functionality of the _resolve_environment_files() function."""
    os.chdir(project_dir)  # Ensures working directory is set to the project directory
    environment_base_name: str = "test_env"

    resolved_project_directory: Path = aa.resolve_project_directory()

    # Verifies environment resolution works as expected for the linux platform
    monkeypatch.setattr(sys, "platform", "linux")
    environment_name, yaml_path, spec_path = aa._resolve_environment_files(
        project_root=resolved_project_directory,
        environment_base_name=environment_base_name,
    )
    assert environment_name == f"{environment_base_name}_lin"
    assert yaml_path == resolved_project_directory / "envs" / f"{environment_base_name}_lin.yml"
    assert spec_path == resolved_project_directory / "envs" / f"{environment_base_name}_lin_spec.txt"

    # Verifies environment resolution works as expected for the Windows platform
    monkeypatch.setattr(sys, "platform", "win32")
    environment_name, yaml_path, spec_path = aa._resolve_environment_files(
        project_root=resolved_project_directory,
        environment_base_name=environment_base_name,
    )
    assert environment_name == f"{environment_base_name}_win"
    assert yaml_path == resolved_project_directory / "envs" / f"{environment_base_name}_win.yml"
    assert spec_path == resolved_project_directory / "envs" / f"{environment_base_name}_win_spec.txt"

    # Verifies environment resolution works as expected for the darwin (macOS ARM64) platform
    monkeypatch.setattr(sys, "platform", "darwin")
    environment_name, yaml_path, spec_path = aa._resolve_environment_files(
        project_root=resolved_project_directory,
        environment_base_name=environment_base_name,
    )
    assert environment_name == f"{environment_base_name}_osx"
    assert yaml_path == resolved_project_directory / "envs" / f"{environment_base_name}_osx.yml"
    assert spec_path == resolved_project_directory / "envs" / f"{environment_base_name}_osx_spec.txt"


def test_resolve_environment_files_error(project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the error handling behavior of the _resolve_environment_files() function."""
    supported_platforms: dict[str, str] = {"win32": "_win", "linux": "_lin", "darwin": "_osx"}
    monkeypatch.setattr(sys, "platform", "unsupported")
    environment_base_name: str = "test_env"
    os.chdir(project_dir)
    message: str = (
        f"Unable to resolve the operating-system-specific suffix to use for mamba environment file names. The "
        f"local machine is using an unsupported operating system 'unsupported'. Currently, only the following "
        f"operating systems are supported: {', '.join(supported_platforms.keys())}."
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa._resolve_environment_files(project_root=project_dir, environment_base_name=environment_base_name)


def test_check_package_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the functionality of the _check_package_engines() function when both mamba and uv are available."""

    def mock_subprocess_run(cmd, *args, **kwargs):
        """Returns success code for mamba and uv commands."""
        if "mamba --version" in cmd or "uv --version" in cmd:
            return Mock(returncode=0)
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
    # Should not raise any exception when both tools are available
    aa._check_package_engines()


def test_check_package_engines_missing_mamba(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies error handling behavior of the _check_package_engines() function when mamba is not available."""

    def mock_subprocess_run(cmd, *args, **kwargs):
        """Fails for mamba but succeeds for uv."""
        if "uv --version" in cmd:
            return Mock(returncode=0)
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
    message: str = (
        "Unable to interface with mamba for environment management. Mamba is required for this automation "
        "module and provides significantly faster conda operations. Install mamba (e.g., via miniforge3) and ensure "
        "it is initialized and added to PATH."
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa._check_package_engines()


def test_check_package_engines_missing_uv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies error handling behavior of the _check_package_engines() function when uv is not available."""

    def mock_subprocess_run(cmd, *args, **kwargs):
        """Succeeds for mamba but fails for uv."""
        if "mamba --version" in cmd:
            return Mock(returncode=0)
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
    message = (
        "Unable to interface with uv for package installation. uv is required for this automation module and "
        "provides significantly faster pip operations. Install uv (e.g., 'pip install uv' or 'mamba install uv') "
        "in the active Python environment."
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa._check_package_engines()


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
        ('"package==1.0"', "package"),
        ("'package>=1.0'", "package"),
        # Platform-specific dependencies
        ("package==1.0; platform_system=='Windows'", "package"),
        ("package>=2.0; sys_platform=='darwin'", "package"),
        ("package[extra]==1.0; platform_system!='Linux'", "package"),
        ("package; platform_system=='Linux' and python_version>='3.8'", "package"),
        ("'package==1.0; platform_system==\"Windows\"'", "package"),
        ("package[test,dev]>=1.0; platform_system=='Darwin'", "package"),
    ],
)
def test_get_base_name(dependency: str, expected: str) -> None:
    """Verifies the functionality of the _get_base_name() function.

    Tests all supported input scenarios, including platform-specific dependencies.
    """
    assert aa._get_base_name(dependency=dependency) == expected


def test_add_dependency() -> None:
    """Verifies the functionality and duplicate input handling of the _add_dependency() function."""
    # Setup
    processed_dependencies = set()
    dependencies = []

    # Ensures that if the base name of the dependency (stripped of "version") is correctly added to dependencies,
    # unless it is already contained in processed_dependencies
    aa._add_dependency(
        dependency="package==1.0",
        dependencies=dependencies,
        processed_dependencies=processed_dependencies,
    )
    assert dependencies == ['"package==1.0"']
    assert processed_dependencies == {"package"}

    # Verifies that packages with the same base name but different 'extras' are correctly recognized as duplicates.
    dependency: str = "package[test]"
    message: str = (
        f"Unable to resolve project dependencies. Found a duplicate dependency for '{dependency}', listed in the "
        f"pyproject.toml file. A dependency should only be found once across the 'dependencies' and "
        f"'dependency-groups' lists."
    )
    with pytest.raises(ValueError, match=_error_format(message)):
        aa._add_dependency(
            dependency=dependency,
            dependencies=dependencies,
            processed_dependencies=processed_dependencies,
        )

    # Verifies that packages with the same base name but different versions are correctly recognized as duplicates.
    dependency = "package>=2.0"
    message = (
        f"Unable to resolve project dependencies. Found a duplicate dependency for '{dependency}', listed in the "
        f"pyproject.toml file. A dependency should only be found once across the 'dependencies' and "
        f"'dependency-groups' lists."
    )
    with pytest.raises(ValueError, match=_error_format(message)):
        aa._add_dependency(
            dependency=dependency,
            dependencies=dependencies,
            processed_dependencies=processed_dependencies,
        )


def _write_pyproject_toml(project_dir: Path, content: str) -> None:
    """Writes the given content to the pyproject.toml file in the project directory.

    Assumes that the project_dir is configured according to the testing standards (obtained from the project_dir
    fixture).

    Args:
        project_dir: The path to the processed project root directory.
        content: The string-content to write to the pyproject.toml file of the processed project.
    """
    pyproject_path: Path = project_dir.joinpath("pyproject.toml")
    pyproject_path.write_text(content)


def _write_tox_ini(project_dir: Path, content: str) -> None:
    """Writes the given content to the tox.ini file in the project directory.

    Assumes that the project_dir is configured according to the testing standards (obtained from the project_dir
    fixture).

    Args:
        project_dir: The path to the processed project root directory.
        content: The string-content to write to the tox.ini file of the processed project.
    """
    tox_path: Path = project_dir.joinpath("tox.ini")
    tox_path.write_text(content)


def test_resolve_dependencies(project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the functionality of the _resolve_dependencies() function."""
    pyproject_content = """
        [project]
        dependencies = ["dep1==1.0", "dep2>=2.0"]

        [dependency-groups]
        dev = ["dev_dep1[test]", "dev_dep2<2.0.1"]
    """
    _write_pyproject_toml(project_dir=project_dir, content=pyproject_content)

    tox_content = """
        [testenv]
        deps =
            dep1
            dev_dep1
            dev_dep2
        requires =
            dep2
    """
    _write_tox_ini(project_dir=project_dir, content=tox_content)

    # Test for the Linux platform
    runtime_deps = aa._resolve_dependencies(
        project_root=project_dir,
    )

    assert set(runtime_deps) == {'"dep1==1.0"', '"dep2>=2.0"', '"dev_dep1[test]"', '"dev_dep2<2.0.1"'}


def test_resolve_dependencies_duplicate_dep(project_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that _resolve_dependencies() function correctly catches duplicate dependencies in supported .toml
    lists.
    """
    pyproject_content = """
    [project]
    dependencies = ["dep1==1.0", "dep2>=2.0"]

    [dependency-groups]
    dev = ["dev_dep1", "dev_dep2", "dep1<3.0"]
    """
    _write_pyproject_toml(project_dir=project_dir, content=pyproject_content)

    tox_content = """
[testenv]
deps =
    dep1
    dev_dep1
    dev_dep2
requires =
    dep2
"""
    _write_tox_ini(project_dir=project_dir, content=tox_content)
    message: str = (
        "Unable to resolve project dependencies. Found a duplicate dependency for 'dep1<3.0', listed in the "
        "pyproject.toml file. A dependency should only be found once across the 'dependencies' and "
        "'dependency-groups' lists."
    )
    with pytest.raises(ValueError, match=_error_format(message)):
        aa._resolve_dependencies(project_root=project_dir)


def test_resolve_project_name(project_dir: Path) -> None:
    """Verifies the functionality of the _resolve_project_name() function."""
    pyproject_content = """
    [project]
    name = "test-project"
    """
    pyproject_path = project_dir.joinpath("pyproject.toml")
    pyproject_path.write_text(pyproject_content)

    result = aa._resolve_project_name(project_root=project_dir)
    assert result == "test-project"


def test_resolve_project_name_errors(project_dir: Path) -> None:
    """Verifies the error-handling behavior of the _resolve_project_name() function."""

    # Verifies that malformed pyproject.toml files are not processed.
    pyproject_content = """
        [project
        name = "test-project"
        """
    pyproject_path = project_dir.joinpath("pyproject.toml")
    pyproject_path.write_text(pyproject_content)

    message: str = "Unable to parse the pyproject.toml file. The file may be corrupted or contains invalid TOML syntax."
    with pytest.raises(ValueError, match=_error_format(message)):
        aa._resolve_project_name(project_root=project_dir)

    # Verifies that processing fails when the 'name' section does not exist.
    pyproject_content = """
        [project]
        version = "1.0.0"
        """
    pyproject_path.write_text(pyproject_content)
    message = (
        "Unable to resolve the project name from the pyproject.toml file. The 'name' field is missing or "
        "empty in the [project] section of the file."
    )

    with pytest.raises(ValueError, match=_error_format(message)):
        aa._resolve_project_name(project_root=project_dir)


def test_resolve_mamba_environments_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the functionality of _resolve_mamba_environments_directory()."""
    # Tests with CONDA_PREFIX set to base environment
    monkeypatch.setenv("CONDA_PREFIX", "/path/to/miniforge3")
    monkeypatch.setenv("CONDA_DEFAULT_ENV", "base")
    result = aa._resolve_mamba_environments_directory()
    assert result == Path("/path/to/miniforge3/envs")

    # Tests with CONDA_PREFIX set to the named environment
    monkeypatch.setenv("CONDA_PREFIX", "/path/to/miniforge3/envs/myenv")
    monkeypatch.setenv("CONDA_DEFAULT_ENV", "myenv")
    result = aa._resolve_mamba_environments_directory()
    assert result == Path("/path/to/miniforge3/envs")


@pytest.mark.parametrize(
    "os_suffix, platform, python_version",
    [
        ("_win", "win32", "3.12"),
        ("_lin", "linux", "3.12"),
        ("_osx", "darwin", "3.12"),
        ("_win", "win32", "3.11"),
    ],
)
def test_project_environment_resolve(
    project_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    os_suffix: str,
    platform: str,
    python_version: str,
) -> None:
    """Verifies the functionality of ProjectEnvironment.resolve_project_environment().

    Tests all supported platforms and Python versions.
    """
    # Setup
    pyproject_content = """
    [project]
    name = "test-project"
    dependencies = ["runtime_dep==1.0"]

    [dependency-groups]
    dev = ["dev_dep==1.0"]
    """
    pyproject_path = project_dir.joinpath("pyproject.toml")
    pyproject_path.write_text(pyproject_content)

    # Mocks tox.ini
    tox_content = """
    [testenv]
    deps =
        runtime_dep
        dev_dep
    """
    _write_tox_ini(project_dir=project_dir, content=tox_content)

    # Mocks platform and environment resolution
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setenv("CONDA_PREFIX", "/path/to/miniforge3")
    monkeypatch.setenv("CONDA_DEFAULT_ENV", "base")

    # Mocks _check_package_engines to pass
    def mock_check_engines():
        pass

    monkeypatch.setattr(aa, "_check_package_engines", mock_check_engines)

    # Creates a mock .yml file
    yaml_path = project_dir / f"envs/test_env{os_suffix}.yml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.touch()

    # Runs the tested command
    result = ProjectEnvironment.resolve_project_environment(
        project_root=project_dir, environment_name="test_env", python_version=python_version
    )

    # Verifies the returned ProjectEnvironment class instance contains the expected fields
    assert isinstance(result, ProjectEnvironment)

    # Checks conda initialization and activation
    if platform.startswith("win"):
        assert "call conda.bat" in result.activate_command
        assert "call conda.bat" in result.deactivate_command
    else:
        assert ". $(conda info --base)/etc/profile.d/conda.sh" in result.activate_command
        assert ". $(conda info --base)/etc/profile.d/conda.sh" in result.deactivate_command

    assert f"test_env{os_suffix}" in result.activate_command
    assert "conda deactivate" in result.deactivate_command
    assert f"python={python_version} uv tox tox-uv --yes" in result.create_command
    assert f"test_env{os_suffix} --all --yes" in result.remove_command
    assert result.environment_name == f"test_env{os_suffix}"

    # Checks dependency installation command (prerelease disabled by default).
    assert "uv pip install" in result.install_dependencies_command
    assert '"runtime_dep==1.0"' in result.install_dependencies_command
    assert '"dev_dep==1.0"' in result.install_dependencies_command
    assert "--prerelease=allow" not in result.install_dependencies_command
    assert "--prerelease=allow" not in result.install_project_command

    # Checks other commands
    assert f"mamba env update -n test_env{os_suffix}" in result.update_command
    assert f"mamba env export --name test_env{os_suffix}" in result.export_yaml_command
    assert f"mamba list -n test_env{os_suffix} --use-uv --explicit" in result.export_spec_command
    assert "uv pip install ." in result.install_project_command
    assert "uv pip uninstall test-project" in result.uninstall_project_command

    # Verifies that OS-specific returned parameters match expectation.
    if platform == "win32":
        assert "findstr -v" in result.export_yaml_command
    elif platform == "linux":
        assert "head -n -1" in result.export_yaml_command
    elif platform == "darwin":
        assert "tail -r | tail -n +2 | tail -r" in result.export_yaml_command

    # Checks for yml-related commands
    assert (
        result.create_from_yaml_command == f"mamba env create -f {yaml_path} --yes --retry-clean-cache --pyc --use-uv"
    )
    assert result.update_command == f"mamba env update -n test_env{os_suffix} -f {yaml_path} --yes --prune --use-uv"

    # Also tests the case where .yml files are not present in the /envs folder.
    yaml_path.unlink()
    result = ProjectEnvironment.resolve_project_environment(
        project_root=project_dir, environment_name="test_env", python_version=python_version
    )
    assert result.create_from_yaml_command is None
    assert result.update_command is None

    # Verifies that prerelease=True includes the --prerelease=allow flag in uv commands.
    yaml_path.touch()
    result = ProjectEnvironment.resolve_project_environment(
        project_root=project_dir, environment_name="test_env", python_version=python_version, prerelease=True
    )
    assert "--prerelease=allow" in result.install_dependencies_command
    assert "--prerelease=allow" in result.install_project_command


def test_generate_typed_marker(tmp_path: Path) -> None:
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

    aa.generate_typed_marker(library_root=library_root)

    # Verifies that py.typed exists in the root directory
    assert (library_root / "py.typed").exists()

    # Verifies that py.typed has been removed from subdirectories
    assert not (subdir1 / "py.typed").exists()
    assert not (subdir2 / "py.typed").exists()

    # Runs the function again to ensure it doesn't cause issues when py.typed already exists in the root
    aa.generate_typed_marker(library_root=library_root)

    # Verifies that py.typed still exists in the root directory
    assert (library_root / "py.typed").exists()

    # Verifies that no new py.typed files have been created in subdirectories
    assert not (subdir1 / "py.typed").exists()
    assert not (subdir2 / "py.typed").exists()


def test_move_stubs(project_dir: Path) -> None:
    """Verifies the functionality of the move_stubs() function."""
    # Sets up mock directories
    stubs_directory = project_dir / "stubs"
    library_root = project_dir / "src" / "library"
    stubs_directory.mkdir()
    library_root.mkdir(parents=True)

    # Creates mock stub files
    stub_lib_dir = stubs_directory.joinpath("library")
    stub_lib_dir.mkdir()
    stub_lib_dir.joinpath("__init__.pyi").touch()
    stub_lib_dir.joinpath("module1.pyi").touch()
    stub_lib_dir.joinpath("submodule").mkdir()
    (stub_lib_dir / "submodule" / "module2.pyi").touch()

    aa.move_stubs(stubs_directory=stubs_directory, library_root=library_root)

    # Verifies that stubs have been moved correctly
    assert (library_root / "__init__.pyi").exists()
    assert (library_root / "module1.pyi").exists()
    assert (library_root / "submodule" / "module2.pyi").exists()

    # Verifies that original stub files have been removed
    assert not (stub_lib_dir / "__init__.pyi").exists()
    assert not (stub_lib_dir / "module1.pyi").exists()
    assert not (stub_lib_dir / "submodule" / "module2.pyi").exists()


def test_move_stubs_osx_duplicates(project_dir: Path) -> None:
    """Tests OSX-specific duplicate file handling in move_stubs()."""
    # Sets up mock directories
    stubs_directory = project_dir / "stubs"
    library_root = project_dir / "src" / "library"
    stubs_directory.mkdir()
    library_root.mkdir(parents=True)

    # Creates stub files with OSX duplicate pattern (space + number)
    stub_lib_dir = stubs_directory.joinpath("library")
    stub_lib_dir.mkdir()
    stub_lib_dir.joinpath("__init__.pyi").touch()
    stub_lib_dir.joinpath("test 1.pyi").touch()
    stub_lib_dir.joinpath("test 2.pyi").touch()
    stub_lib_dir.joinpath("test 3.pyi").touch()

    aa.move_stubs(stubs_directory=stubs_directory, library_root=library_root)

    # Verifies that the duplicate handling worked - should keep highest numbered and rename
    assert (library_root / "test.pyi").exists()
    assert not (library_root / "test 1.pyi").exists()
    assert not (library_root / "test 2.pyi").exists()
    assert not (library_root / "test 3.pyi").exists()


def test_move_stubs_error(project_dir: Path) -> None:
    """Verifies the error-handling behavior of the move_stubs() function."""
    # Sets up mock directories
    stubs_directory = project_dir.joinpath("stubs")
    library_root = project_dir / "src" / "library"
    stubs_directory.mkdir()
    library_root.mkdir(parents=True)

    # Creates invalid stub directory structure (multiple subdirectories with __init__.pyi)
    stubs_directory.joinpath("lib1").mkdir()
    init_1_path = Path(stubs_directory / "lib1" / "__init__.pyi")
    init_1_path.touch()
    stubs_directory.joinpath("lib2").mkdir()
    init_2_path = Path(stubs_directory / "lib2" / "__init__.pyi")
    init_2_path.touch()

    # Verifies that attempting to move files from /stubs hierarchy that contains multiple __init__.pyi files fails
    # as expected.
    message: str = (
        f"Unable to move the generated stub files to appropriate levels of the library source code directory. "
        f"Expected exactly one subdirectory with __init__.pyi in '{stubs_directory}', but found {2}."
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa.move_stubs(stubs_directory=stubs_directory, library_root=library_root)

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
def test_verify_pypirc(tmp_path: Path, config: dict[str, dict[str, str]], expected_result: bool) -> None:
    """Verifies the functionality of the verify_pypirc() function.

    Tests all supported pypirc layouts.
    """
    # Creates a mock .pypirc file with the given configuration
    pypirc_path = tmp_path / ".pypirc"
    config_parser = ConfigParser()
    config_parser.read_dict(config)
    with pypirc_path.open("w") as pypirc_file:
        # noinspection PyTypeChecker
        config_parser.write(pypirc_file)

    # Runs the verify_pypirc function
    result = aa.verify_pypirc(file_path=pypirc_path)

    # Asserts that the function returns the expected result
    assert result == expected_result


def test_verify_pypirc_nonexistent_file(tmp_path: Path) -> None:
    """Verifies the error-handling behavior of the verify_pypirc() function."""
    # Creates a path to a nonexistent file
    nonexistent_path = tmp_path / "nonexistent.pypirc"

    # Runs the verify_pypirc function
    result = aa.verify_pypirc(file_path=nonexistent_path)

    # Asserts that the function returns False for a nonexistent file
    assert result is False


def test_delete_stubs(tmp_path: Path) -> None:
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

    aa.delete_stubs(library_root=library_root)

    # Verifies that all .pyi files have been deleted
    remaining_pyi_files = list(library_root.rglob("*.pyi"))
    assert not remaining_pyi_files

    # Verifies that non-.pyi files were not deleted
    assert (library_root / "not_a_stub.py").exists()

    # Verifies directory structure is maintained
    assert subdir.exists()

    # Runs the function again to ensure it handles the case when no .pyi files are present
    aa.delete_stubs(library_root=library_root)  # This should not raise any errors


def test_project_environment_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the functionality of the ProjectEnvironment.environment_exists() method."""
    # Create a mock ProjectEnvironment instance
    env = ProjectEnvironment(
        activate_command="conda init && conda activate test_env",
        deactivate_command="conda init && conda deactivate",
        create_command="mamba create -n test_env",
        create_from_yaml_command=None,
        remove_command="mamba remove -n test_env",
        install_dependencies_command="uv pip install deps",
        update_command=None,
        export_yaml_command="mamba env export",
        export_spec_command="mamba list --explicit",
        install_project_command="uv pip install .",
        uninstall_project_command="uv pip uninstall project",
        environment_name="test_env",
        environment_directory=Path("/path/to/env"),
    )

    # Test when the environment exists
    def mock_run_success(*args, **kwargs):
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(subprocess, "run", mock_run_success)
    assert env.environment_exists() is True

    # Test when the environment doesn't exist
    def mock_run_failure(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "cmd")

    monkeypatch.setattr(subprocess, "run", mock_run_failure)
    assert env.environment_exists() is False


# ---- Group 1: resolve_project_environment() fallback (lines 113-118) ----


def test_resolve_project_environment_with_manual_override(
    project_dir: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verifies that resolve_project_environment() uses the manual override when automatic resolution fails."""
    pyproject_content = """
[project]
name = "test-project"
dependencies = ["dep1==1.0"]

[dependency-groups]
dev = ["dev_dep==1.0"]
"""
    project_dir.joinpath("pyproject.toml").write_text(pyproject_content)

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(aa, "_check_package_engines", lambda: None)

    def mock_resolve_mamba() -> Path:
        raise RuntimeError("Mamba not found")

    monkeypatch.setattr(aa, "_resolve_mamba_environments_directory", mock_resolve_mamba)

    override_dir = tmp_path / "custom_envs"
    override_dir.mkdir()

    result = ProjectEnvironment.resolve_project_environment(
        project_root=project_dir,
        environment_name="test_env",
        environment_directory=override_dir,
    )

    assert result.environment_directory == override_dir / "test_env_lin"


def test_resolve_project_environment_reraise_without_override(
    project_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies that resolve_project_environment() re-raises RuntimeError when no override is provided."""
    pyproject_content = """
[project]
name = "test-project"
dependencies = ["dep1==1.0"]

[dependency-groups]
dev = ["dev_dep==1.0"]
"""
    project_dir.joinpath("pyproject.toml").write_text(pyproject_content)

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(aa, "_check_package_engines", lambda: None)

    def mock_resolve_mamba() -> Path:
        raise RuntimeError("Mamba not found")

    monkeypatch.setattr(aa, "_resolve_mamba_environments_directory", mock_resolve_mamba)

    with pytest.raises(RuntimeError, match="Mamba not found"):
        ProjectEnvironment.resolve_project_environment(
            project_root=project_dir,
            environment_name="test_env",
        )


# ---- Group 2: _resolve_dependencies() legacy path (lines 634-641) ----


def test_resolve_dependencies_optional_dependencies_fallback(project_dir: Path) -> None:
    """Verifies that _resolve_dependencies() falls back to [project.optional-dependencies] when [dependency-groups]
    is not present.
    """
    pyproject_content = """
[project]
dependencies = ["dep1==1.0"]

[project.optional-dependencies]
dev = ["dev_dep1>=2.0", "dev_dep2<3.0"]
"""
    _write_pyproject_toml(project_dir=project_dir, content=pyproject_content)

    result = aa._resolve_dependencies(project_root=project_dir)
    assert set(result) == {'"dep1==1.0"', '"dev_dep1>=2.0"', '"dev_dep2<3.0"'}


def test_resolve_dependencies_no_dev_dependencies(project_dir: Path) -> None:
    """Verifies that _resolve_dependencies() works correctly when only runtime dependencies are defined."""
    pyproject_content = """
[project]
dependencies = ["dep1==1.0", "dep2>=2.0"]
"""
    _write_pyproject_toml(project_dir=project_dir, content=pyproject_content)

    result = aa._resolve_dependencies(project_root=project_dir)
    assert set(result) == {'"dep1==1.0"', '"dep2>=2.0"'}


# ---- Group 3: _resolve_mamba_environments_directory() methods (lines 716-776) ----


def test_resolve_mamba_envs_via_executable_envs_dir(tmp_path: Path, clean_mamba_env: pytest.MonkeyPatch) -> None:
    """Verifies _resolve_mamba_environments_directory() finds envs/ by ascending from a miniforge executable."""
    # Create: tmp_path/miniforge3/envs/myenv/bin/python
    envs_dir = tmp_path / "miniforge3" / "envs"
    python_dir = envs_dir / "myenv" / "bin"
    python_dir.mkdir(parents=True)
    python_exe = python_dir / "python"
    python_exe.touch()

    clean_mamba_env.setattr(sys, "executable", str(python_exe))

    result = aa._resolve_mamba_environments_directory()
    assert result == envs_dir


def test_resolve_mamba_envs_via_executable_conda_meta(tmp_path: Path, clean_mamba_env: pytest.MonkeyPatch) -> None:
    """Verifies _resolve_mamba_environments_directory() finds envs/ via conda-meta in a miniforge root."""
    # Create: tmp_path/miniforge3/{conda-meta/, envs/, bin/python}
    miniforge_root = tmp_path / "miniforge3"
    miniforge_root.joinpath("conda-meta").mkdir(parents=True)
    miniforge_root.joinpath("envs").mkdir()
    python_dir = miniforge_root / "bin"
    python_dir.mkdir()
    python_exe = python_dir / "python"
    python_exe.touch()

    clean_mamba_env.setattr(sys, "executable", str(python_exe))

    result = aa._resolve_mamba_environments_directory()
    assert result == miniforge_root / "envs"


def test_resolve_mamba_envs_via_executable_conda_meta_parent_envs(
    tmp_path: Path, clean_mamba_env: pytest.MonkeyPatch
) -> None:
    """Verifies _resolve_mamba_environments_directory() uses the parent envs/ directory when conda-meta is found in a
    named environment that lacks its own envs/ subdirectory.
    """
    # Create: tmp_path/miniforge3/envs/myenv/{conda-meta/, bin/python}
    envs_dir = tmp_path / "miniforge3" / "envs"
    myenv_dir = envs_dir / "myenv"
    myenv_dir.joinpath("conda-meta").mkdir(parents=True)
    python_dir = myenv_dir / "bin"
    python_dir.mkdir()
    python_exe = python_dir / "python"
    python_exe.touch()

    clean_mamba_env.setattr(sys, "executable", str(python_exe))

    result = aa._resolve_mamba_environments_directory()
    assert result == envs_dir


def test_resolve_mamba_envs_via_conda_exe(tmp_path: Path, clean_mamba_env: pytest.MonkeyPatch) -> None:
    """Verifies _resolve_mamba_environments_directory() resolves envs/ via the CONDA_EXE environment variable."""
    # Create: tmp_path/miniforge3/{bin/mamba, envs/}
    miniforge_root = tmp_path / "miniforge3"
    miniforge_root.joinpath("bin").mkdir(parents=True)
    mamba_exe = miniforge_root / "bin" / "mamba"
    mamba_exe.touch()
    miniforge_root.joinpath("envs").mkdir()

    clean_mamba_env.setenv("CONDA_EXE", str(mamba_exe))

    result = aa._resolve_mamba_environments_directory()
    assert result == miniforge_root / "envs"


def test_resolve_mamba_envs_via_standard_location(tmp_path: Path, clean_mamba_env: pytest.MonkeyPatch) -> None:
    """Verifies _resolve_mamba_environments_directory() finds envs/ at the standard ~/miniforge3/envs location."""
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    fake_home.joinpath("miniforge3", "envs").mkdir(parents=True)

    clean_mamba_env.setattr(Path, "home", staticmethod(lambda: fake_home))
    clean_mamba_env.setattr(sys, "platform", "linux")

    result = aa._resolve_mamba_environments_directory()
    assert result == fake_home / "miniforge3" / "envs"


def test_resolve_mamba_envs_via_windows_appdata(tmp_path: Path, clean_mamba_env: pytest.MonkeyPatch) -> None:
    """Verifies _resolve_mamba_environments_directory() finds envs/ at the Windows AppData/Local location."""
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    # Only create at AppData/Local level (not at home/miniforge3 which would be caught by method 3)
    fake_home.joinpath("AppData", "Local", "miniforge3", "envs").mkdir(parents=True)

    clean_mamba_env.setattr(Path, "home", staticmethod(lambda: fake_home))
    clean_mamba_env.setattr(sys, "platform", "win32")

    result = aa._resolve_mamba_environments_directory()
    assert result == fake_home / "AppData" / "Local" / "miniforge3" / "envs"


def test_resolve_mamba_envs_via_windows_localappdata(tmp_path: Path, clean_mamba_env: pytest.MonkeyPatch) -> None:
    """Verifies _resolve_mamba_environments_directory() finds envs/ via the LOCALAPPDATA environment variable."""
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    # No miniforge3/envs at home or AppData/Local level
    local_appdata_dir = tmp_path / "localappdata"
    local_appdata_dir.joinpath("miniforge3", "envs").mkdir(parents=True)

    clean_mamba_env.setattr(Path, "home", staticmethod(lambda: fake_home))
    clean_mamba_env.setattr(sys, "platform", "win32")
    clean_mamba_env.setenv("LOCALAPPDATA", str(local_appdata_dir))

    result = aa._resolve_mamba_environments_directory()
    assert result == local_appdata_dir / "miniforge3" / "envs"


def test_resolve_mamba_envs_failure_linux(tmp_path: Path, clean_mamba_env: pytest.MonkeyPatch) -> None:
    """Verifies _resolve_mamba_environments_directory() raises RuntimeError when no resolution method works on
    Linux.
    """
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()

    clean_mamba_env.setattr(Path, "home", staticmethod(lambda: fake_home))
    clean_mamba_env.setattr(sys, "platform", "linux")

    message = (
        "Unable to resolve the path to the mamba environments directory. This version of ataraxis-automation expects "
        "that mamba is installed via miniforge3, following the deprecation of mambaforge. Make sure miniforge3 is "
        "installed and initialized before using ataraxis-automation cli. Install from: "
        "https://github.com/conda-forge/miniforge"
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa._resolve_mamba_environments_directory()


def test_resolve_mamba_envs_failure_windows(tmp_path: Path, clean_mamba_env: pytest.MonkeyPatch) -> None:
    """Verifies _resolve_mamba_environments_directory() raises RuntimeError after exhausting all Windows resolution
    paths.
    """
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()

    clean_mamba_env.setattr(Path, "home", staticmethod(lambda: fake_home))
    clean_mamba_env.setattr(sys, "platform", "win32")

    message = (
        "Unable to resolve the path to the mamba environments directory. This version of ataraxis-automation expects "
        "that mamba is installed via miniforge3, following the deprecation of mambaforge. Make sure miniforge3 is "
        "installed and initialized before using ataraxis-automation cli. Install from: "
        "https://github.com/conda-forge/miniforge"
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa._resolve_mamba_environments_directory()


# ---- Group 4: move_stubs() single-file rename (lines 446-452) ----


def test_move_stubs_single_file_with_copy_number(project_dir: Path) -> None:
    """Verifies that move_stubs() correctly renames a single stub file that has an OSX copy number suffix."""
    stubs_directory = project_dir / "stubs"
    library_root = project_dir / "src" / "library"
    stubs_directory.mkdir()
    library_root.mkdir(parents=True)

    stub_lib_dir = stubs_directory / "library"
    stub_lib_dir.mkdir()
    stub_lib_dir.joinpath("__init__.pyi").touch()
    stub_lib_dir.joinpath("module 1.pyi").touch()

    aa.move_stubs(stubs_directory=stubs_directory, library_root=library_root)

    # The "module 1.pyi" file should be renamed to "module.pyi"
    assert (library_root / "module.pyi").exists()
    assert not (library_root / "module 1.pyi").exists()
    assert (library_root / "__init__.pyi").exists()


# ---- Group 5: Windows file lock retry helpers ----


def test_unlink_with_retry_passthrough_non_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that _unlink_with_retry() calls Path.unlink() directly on non-Windows platforms."""
    monkeypatch.setattr(sys, "platform", "linux")
    target_file = tmp_path / "test.txt"
    target_file.touch()

    aa._unlink_with_retry(target_file)
    assert not target_file.exists()


def test_unlink_with_retry_missing_ok_non_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that _unlink_with_retry() respects missing_ok on non-Windows platforms."""
    monkeypatch.setattr(sys, "platform", "linux")
    nonexistent = tmp_path / "nonexistent.txt"

    # Should not raise when missing_ok=True
    aa._unlink_with_retry(nonexistent, missing_ok=True)

    # Should raise FileNotFoundError when missing_ok=False
    with pytest.raises(FileNotFoundError):
        aa._unlink_with_retry(nonexistent, missing_ok=False)


def test_unlink_with_retry_retries_on_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that _unlink_with_retry() retries on PermissionError when platform is win32."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(aa, "_FILE_RETRY_INITIAL_DELAY", 0.01)

    target_file = tmp_path / "test.txt"
    target_file.touch()

    # Simulates PermissionError on first two calls, then succeeds on third
    call_count = 0
    original_unlink = Path.unlink

    def mock_unlink(self: Path, missing_ok: bool = False) -> None:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise PermissionError("File is locked")
        original_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    aa._unlink_with_retry(target_file)
    assert call_count == 3


def test_unlink_with_retry_exhausts_retries_on_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that _unlink_with_retry() raises PermissionError after exhausting all retries on Windows."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(aa, "_FILE_RETRY_INITIAL_DELAY", 0.01)

    target_file = tmp_path / "test.txt"
    target_file.touch()

    def mock_unlink(self: Path, missing_ok: bool = False) -> None:
        raise PermissionError("File is locked")

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    with pytest.raises(PermissionError, match="File is locked"):
        aa._unlink_with_retry(target_file)


def test_rename_with_retry_passthrough_non_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that _rename_with_retry() calls Path.rename() directly on non-Windows platforms."""
    monkeypatch.setattr(sys, "platform", "linux")
    source = tmp_path / "source.txt"
    source.touch()
    destination = tmp_path / "destination.txt"

    aa._rename_with_retry(source, destination)
    assert not source.exists()
    assert destination.exists()


def test_rename_with_retry_retries_on_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that _rename_with_retry() retries on PermissionError when platform is win32."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(aa, "_FILE_RETRY_INITIAL_DELAY", 0.01)

    source = tmp_path / "source.txt"
    source.touch()
    destination = tmp_path / "destination.txt"

    call_count = 0
    original_rename = Path.rename

    def mock_rename(self: Path, target: Path) -> Path:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise PermissionError("File is locked")
        return original_rename(self, target)

    monkeypatch.setattr(Path, "rename", mock_rename)

    aa._rename_with_retry(source, destination)
    assert call_count == 3
    assert destination.exists()


def test_rename_with_retry_exhausts_retries_on_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that _rename_with_retry() raises PermissionError after exhausting all retries on Windows."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(aa, "_FILE_RETRY_INITIAL_DELAY", 0.01)

    source = tmp_path / "source.txt"
    source.touch()
    destination = tmp_path / "destination.txt"

    def mock_rename(self: Path, target: Path) -> Path:
        raise PermissionError("File is locked")

    monkeypatch.setattr(Path, "rename", mock_rename)

    with pytest.raises(PermissionError, match="File is locked"):
        aa._rename_with_retry(source, destination)


def test_robust_rmtree_passthrough_non_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that robust_rmtree() calls shutil.rmtree() directly on non-Windows platforms."""
    monkeypatch.setattr(sys, "platform", "linux")
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    (target_dir / "file.txt").touch()

    aa.robust_rmtree(target_dir)
    assert not target_dir.exists()


def test_robust_rmtree_retries_on_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that robust_rmtree() retries on PermissionError when platform is win32."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(aa, "_FILE_RETRY_INITIAL_DELAY", 0.01)

    target_dir = tmp_path / "target"
    target_dir.mkdir()
    (target_dir / "file.txt").touch()

    call_count = 0
    original_rmtree = shutil.rmtree

    def mock_rmtree(path: Path, onerror: object = None) -> None:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise PermissionError("Directory is locked")
        original_rmtree(path)

    monkeypatch.setattr(shutil, "rmtree", mock_rmtree)

    aa.robust_rmtree(target_dir)
    assert call_count == 3


def test_robust_rmtree_exhausts_retries_on_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that robust_rmtree() raises PermissionError after exhausting all retries on Windows."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(aa, "_FILE_RETRY_INITIAL_DELAY", 0.01)

    target_dir = tmp_path / "target"
    target_dir.mkdir()
    (target_dir / "file.txt").touch()

    def mock_rmtree(path: Path, onerror: object = None) -> None:
        raise PermissionError("Directory is locked")

    monkeypatch.setattr(shutil, "rmtree", mock_rmtree)

    with pytest.raises(PermissionError, match="Directory is locked"):
        aa.robust_rmtree(target_dir)


def test_rmtree_onerror_clears_readonly(tmp_path: Path) -> None:
    """Verifies that _rmtree_onerror() clears the read-only attribute and retries the deletion."""
    target_file = tmp_path / "readonly.txt"
    target_file.touch()

    # Makes the file read-only
    target_file.chmod(stat.S_IREAD)

    # Simulates the onerror callback with os.remove as the function
    try:
        aa._rmtree_onerror(
            func=os.remove,
            path=str(target_file),
            exc_info=(PermissionError, PermissionError("Permission denied"), None),
        )
    except Exception:
        # Restores write permission for cleanup if the test fails
        target_file.chmod(stat.S_IWRITE)
        raise

    assert not target_file.exists()


def test_rmtree_onerror_reraises_non_permission_error() -> None:
    """Verifies that _rmtree_onerror() re-raises exceptions that are not PermissionError."""
    error = OSError("Disk error")
    with pytest.raises(OSError, match="Disk error"):
        aa._rmtree_onerror(
            func=os.remove,
            path="/nonexistent",
            exc_info=(OSError, error, None),
        )
