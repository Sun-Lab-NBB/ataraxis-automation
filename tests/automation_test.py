"""Contains tests for non-CLI functions provided by the automation module."""

import io
import os
import re
import sys
import stat
from types import TracebackType
import shutil
from typing import Any
from pathlib import Path
import zipfile
import subprocess
from configparser import ConfigParser
from unittest.mock import Mock

import pytest
import platformdirs

import ataraxis_automation.automation as aa
from ataraxis_automation.automation import ProjectEnvironment


@pytest.fixture
def project_directory(tmp_path: Path) -> Path:
    """Generates the test project root directory with the required files expected by the automation functions."""
    project_directory = tmp_path.joinpath("project")
    project_directory.mkdir()
    project_directory.joinpath("src").mkdir()
    project_directory.joinpath("envs").mkdir()
    project_directory.joinpath("pyproject.toml").touch()
    project_directory.joinpath("tox.ini").touch()
    return project_directory


@pytest.fixture
def documented_project_directory(tmp_path: Path) -> Path:
    """Generates the test project root directory with the file layout shared by every project archetype that builds
    API documentation.
    """
    project_directory = tmp_path.joinpath("project")
    project_directory.mkdir()
    project_directory.joinpath("src").mkdir()
    project_directory.joinpath("docs").mkdir()
    project_directory.joinpath("tox.ini").touch()
    return project_directory


@pytest.fixture
def application_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolates the shared application directory from the host machine to avoid polluting real user state."""
    application_directory = tmp_path.joinpath("application")
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(application_directory))
    return application_directory


@pytest.fixture
def clean_mamba_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Clears all env vars that _resolve_mamba_environments_directory() checks and repoints sys.executable away from
    any miniforge installation, so that only the resolution method under test can succeed.
    """
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.delenv("CONDA_DEFAULT_ENV", raising=False)
    monkeypatch.delenv("CONDA_EXE", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    return monkeypatch


@pytest.fixture
def documentation_directory(tmp_path: Path) -> Path:
    """Generates a mock built documentation directory with the file layout produced by the 'docs' tox task."""
    documentation_directory = tmp_path.joinpath("html")
    documentation_directory.mkdir()
    documentation_directory.joinpath("index.html").write_text("<html></html>")
    static_directory = documentation_directory.joinpath("_static")
    static_directory.mkdir()
    static_directory.joinpath("styles.css").write_text("body {}")
    return documentation_directory


def test_resolve_project_directory(project_directory: Path) -> None:
    """Verifies the functionality of the resolve_project_directory() function."""
    os.chdir(project_directory)
    result = aa.resolve_project_directory()
    assert result == project_directory


def test_resolve_project_directory_error(tmp_path: Path) -> None:
    """Verifies the error handling behavior of the resolve_project_directory() function."""
    os.chdir(tmp_path)
    message: str = (
        f"Unable to confirm that ataraxis automation CLI has been called from the root directory of a valid Python "
        f"project. This CLI expects that the current working directory is set to the root directory of the "
        f"project, judged by the presence of '/src', '/envs', 'pyproject.toml' and 'tox.ini'. Current working "
        f"directory is set to {Path.cwd()}, which does not contain at least one of the required files."
    )
    with pytest.raises((SystemExit, RuntimeError), match=_error_format(message)):
        aa.resolve_project_directory()


@pytest.mark.parametrize(
    "init_location, expected",
    [
        ("src", "src"),
        ("src/library", "src/library"),
    ],
)
def test_resolve_library_root(project_directory: Path, init_location: str, expected: str) -> None:
    """Verifies the functionality of the resolve_library_root() function, for the library root resolving to the /src
    directory as in c-extension projects, and to a subfolder under /src as in pure-python projects.
    """
    init_directory = project_directory.joinpath(init_location)
    init_directory.mkdir(parents=True, exist_ok=True)
    init_directory.joinpath("__init__.py").touch()
    result = aa.resolve_library_root(project_root=project_directory)
    assert result == project_directory / expected


def test_resolve_library_root_error(project_directory: Path) -> None:
    """Verifies the error-handling behavior of the resolve_library_root() function."""
    # Verifies the method correctly fails when __init__.py is not found under /src or any subdirectory directly under
    # src
    message: str = (
        f"Unable to resolve the path to the library root directory from the project root path {project_directory}. "
        f"Specifically, did not find an __init__.py inside the /src directory and found {0} "
        f"sub-directories with __init__.py inside the /src directory. Make sure there is an __init__.py "
        f"inside /src or ONE of the sub-directories under /src."
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa.resolve_library_root(project_root=project_directory)

    # Verifies that the method fails for cases where multiple subdirectories under src have __init__.py.
    library1 = project_directory.joinpath("src/library1")
    library2 = project_directory.joinpath("src/library2")
    library1.mkdir(parents=True, exist_ok=True)
    library2.mkdir(parents=True, exist_ok=True)
    library1.joinpath("__init__.py").touch()
    library2.joinpath("__init__.py").touch()
    message = (
        f"Unable to resolve the path to the library root directory from the project root path {project_directory}. "
        f"Specifically, did not find an __init__.py inside the /src directory and found {2} "
        f"sub-directories with __init__.py inside the /src directory. Make sure there is an __init__.py "
        f"inside /src or ONE of the sub-directories under /src."
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa.resolve_library_root(project_root=project_directory)


def test_resolve_environment_files(project_directory: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the functionality of the _resolve_environment_files() function."""
    os.chdir(project_directory)
    environment_base_name: str = "test_env"

    resolved_project_directory: Path = aa.resolve_project_directory()

    # Verifies environment resolution works as expected for the Linux platform.
    monkeypatch.setattr(sys, "platform", "linux")
    environment_name, yaml_path = aa._resolve_environment_files(
        project_root=resolved_project_directory,
        environment_base_name=environment_base_name,
    )
    assert environment_name == f"{environment_base_name}_lin"
    assert yaml_path == resolved_project_directory / "envs" / f"{environment_base_name}_lin.yml"

    # Verifies environment resolution works as expected for the Windows platform.
    monkeypatch.setattr(sys, "platform", "win32")
    environment_name, yaml_path = aa._resolve_environment_files(
        project_root=resolved_project_directory,
        environment_base_name=environment_base_name,
    )
    assert environment_name == f"{environment_base_name}_win"
    assert yaml_path == resolved_project_directory / "envs" / f"{environment_base_name}_win.yml"

    # Verifies environment resolution works as expected for the Darwin (macOS) platform.
    monkeypatch.setattr(sys, "platform", "darwin")
    environment_name, yaml_path = aa._resolve_environment_files(
        project_root=resolved_project_directory,
        environment_base_name=environment_base_name,
    )
    assert environment_name == f"{environment_base_name}_osx"
    assert yaml_path == resolved_project_directory / "envs" / f"{environment_base_name}_osx.yml"


def test_resolve_environment_files_error(project_directory: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the error handling behavior of the _resolve_environment_files() function."""
    supported_platforms: dict[str, str] = {"win32": "_win", "linux": "_lin", "darwin": "_osx"}
    monkeypatch.setattr(sys, "platform", "unsupported")
    environment_base_name: str = "test_env"
    os.chdir(project_directory)
    message: str = (
        f"Unable to resolve the operating-system-specific suffix to use for mamba environment file names. The "
        f"local machine is using an unsupported operating system 'unsupported'. Currently, only the following "
        f"operating systems are supported: {', '.join(supported_platforms.keys())}."
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa._resolve_environment_files(project_root=project_directory, environment_base_name=environment_base_name)


def test_check_package_engines(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the functionality of the _check_package_engines() function when both mamba and uv are available."""

    def mock_subprocess_run(command: str, *_args: Any, **_kwargs: Any) -> Mock:
        """Returns success code for mamba and uv commands."""
        if "mamba --version" in command or "uv --version" in command:
            return Mock(returncode=0)
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
    # Completes without raising when both tools are available.
    aa._check_package_engines()


def test_check_package_engines_missing_mamba(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies error handling behavior of the _check_package_engines() function when mamba is not available."""

    def mock_subprocess_run(command: str, *_args: Any, **_kwargs: Any) -> Mock:
        """Fails for mamba but succeeds for uv."""
        if "uv --version" in command:
            return Mock(returncode=0)
        raise subprocess.CalledProcessError(1, command)

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

    def mock_subprocess_run(command: str, *_args: Any, **_kwargs: Any) -> Mock:
        """Succeeds for mamba but fails for uv."""
        if "mamba --version" in command:
            return Mock(returncode=0)
        raise subprocess.CalledProcessError(1, command)

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
        # Hyphenated and dotted distribution names, which the shared dependency corpus is built from. Dropping either
        # character from the base-name pattern would collapse sibling packages onto one name.
        ("ataraxis-automation>=9,<10", "ataraxis-automation"),
        ("pytest-cov>=7,<8", "pytest-cov"),
        ("sphinx-autodoc-typehints>=3,<4", "sphinx-autodoc-typehints"),
        ("ruamel.yaml>=0.17", "ruamel.yaml"),
        ("backports.tarfile", "backports.tarfile"),
        ("cibuildwheel[uv]>=4,<5", "cibuildwheel"),
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

    # Ensures that the full dependency string is quoted and added to 'dependencies', while its base name (stripped
    # of the version) is recorded in 'processed_dependencies', unless that base name was already recorded.
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


def test_resolve_dependencies(project_directory: Path) -> None:
    """Verifies the functionality of the _resolve_dependencies() function."""
    pyproject_content = """
        [project]
        dependencies = ["dep1==1.0", "dep2>=2.0"]

        [dependency-groups]
        dev = ["dev_dep1[test]", "dev_dep2<2.0.1"]
    """
    _write_pyproject_toml(project_directory=project_directory, content=pyproject_content)

    tox_content = """
        [testenv]
        deps =
            dep1
            dev_dep1
            dev_dep2
        requires =
            dep2
    """
    _write_tox_ini(project_directory=project_directory, content=tox_content)

    # Resolves the dependencies declared by the mock pyproject.toml file.
    runtime_deps = aa._resolve_dependencies(
        project_root=project_directory,
    )

    assert set(runtime_deps) == {'"dep1==1.0"', '"dep2>=2.0"', '"dev_dep1[test]"', '"dev_dep2<2.0.1"'}


def test_resolve_dependencies_duplicate_dep(project_directory: Path) -> None:
    """Verifies that _resolve_dependencies() function correctly catches duplicate dependencies in supported .toml
    lists.
    """
    pyproject_content = """
    [project]
    dependencies = ["dep1==1.0", "dep2>=2.0"]

    [dependency-groups]
    dev = ["dev_dep1", "dev_dep2", "dep1<3.0"]
    """
    _write_pyproject_toml(project_directory=project_directory, content=pyproject_content)

    tox_content = """
[testenv]
deps =
    dep1
    dev_dep1
    dev_dep2
requires =
    dep2
"""
    _write_tox_ini(project_directory=project_directory, content=tox_content)
    message: str = (
        "Unable to resolve project dependencies. Found a duplicate dependency for 'dep1<3.0', listed in the "
        "pyproject.toml file. A dependency should only be found once across the 'dependencies' and "
        "'dependency-groups' lists."
    )
    with pytest.raises(ValueError, match=_error_format(message)):
        aa._resolve_dependencies(project_root=project_directory)


def test_resolve_project_name(project_directory: Path) -> None:
    """Verifies the functionality of the _resolve_project_name() function."""
    pyproject_content = """
    [project]
    name = "test-project"
    """
    pyproject_path = project_directory.joinpath("pyproject.toml")
    pyproject_path.write_text(pyproject_content)

    result = aa._resolve_project_name(project_root=project_directory)
    assert result == "test-project"


def test_resolve_project_name_errors(project_directory: Path) -> None:
    """Verifies the error-handling behavior of the _resolve_project_name() function."""
    # Verifies that malformed pyproject.toml files are not processed.
    pyproject_content = """
        [project
        name = "test-project"
        """
    pyproject_path = project_directory.joinpath("pyproject.toml")
    pyproject_path.write_text(pyproject_content)

    message: str = "Unable to parse the pyproject.toml file. The file may be corrupted or contains invalid TOML syntax."
    with pytest.raises(ValueError, match=_error_format(message)):
        aa._resolve_project_name(project_root=project_directory)

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
        aa._resolve_project_name(project_root=project_directory)


def test_resolve_mamba_environments_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the functionality of _resolve_mamba_environments_directory()."""
    # Tests with CONDA_PREFIX set to base environment.
    monkeypatch.setenv("CONDA_PREFIX", "/path/to/miniforge3")
    monkeypatch.setenv("CONDA_DEFAULT_ENV", "base")
    result = aa._resolve_mamba_environments_directory()
    assert result == Path("/path/to/miniforge3/envs")

    # Tests with CONDA_PREFIX set to the named environment.
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
    project_directory: Path,
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
    pyproject_path = project_directory.joinpath("pyproject.toml")
    pyproject_path.write_text(pyproject_content)

    # Mocks tox.ini
    tox_content = """
    [testenv]
    deps =
        runtime_dep
        dev_dep
    """
    _write_tox_ini(project_directory=project_directory, content=tox_content)

    # Mocks platform and environment resolution.
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setenv("CONDA_PREFIX", "/path/to/miniforge3")
    monkeypatch.setenv("CONDA_DEFAULT_ENV", "base")

    # Mocks _check_package_engines to pass.
    def mock_check_engines() -> None:
        pass

    monkeypatch.setattr(aa, "_check_package_engines", mock_check_engines)

    # Creates a mock .yml file.
    yaml_path = project_directory / f"envs/test_env{os_suffix}.yml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.touch()

    # Runs the tested command.
    result = ProjectEnvironment.resolve_project_environment(
        project_root=project_directory, environment_name="test_env", python_version=python_version
    )

    # Verifies the returned ProjectEnvironment class instance contains the expected fields.
    assert isinstance(result, ProjectEnvironment)

    # The commands of the default configuration are pinned by full equality rather than by substring containment, so
    # that dropping or altering any flag inside them fails the test.
    environment_directory = f"/path/to/miniforge3/envs/test_env{os_suffix}"
    if platform == "win32":
        conda_initialization = "call conda.bat >NUL 2>&1"
        quoted_directory = f'"{environment_directory}"'
        quoted_yaml_path = f'"{yaml_path}"'
    else:
        conda_initialization = '. "$(conda info --base)/etc/profile.d/conda.sh"'
        quoted_directory = environment_directory
        quoted_yaml_path = str(yaml_path)

    assert result.environment_name == f"test_env{os_suffix}"
    assert result.environment_directory == Path(environment_directory)
    assert result.environment_yaml_path == yaml_path

    assert result.activate_command == f"{conda_initialization} && conda activate {quoted_directory}"
    assert result.deactivate_command == f"{conda_initialization} && conda deactivate"
    assert result.create_command == (
        f"mamba create -n test_env{os_suffix} python={python_version} uv tox tox-uv --yes "
        f"--retry-clean-cache --pyc --use-uv"
    )
    assert result.create_dry_run_command == (
        f"mamba create -n test_env{os_suffix} python={python_version} uv tox tox-uv --yes "
        f"--retry-clean-cache --pyc --use-uv --dry-run"
    )
    assert result.remove_command == f"mamba remove -n test_env{os_suffix} --all --yes"

    # Checks dependency installation command (prerelease disabled by default). Runtime dependencies are ordered ahead
    # of development dependencies.
    assert result.install_dependencies_command == (
        f'uv pip install "runtime_dep==1.0" "dev_dep==1.0" --resolution highest --refresh --compile-bytecode '
        f"--python={quoted_directory} --strict --exact"
    )
    assert result.install_project_command == (
        f"uv pip install . --resolution highest --refresh --reinstall-package test-project --compile-bytecode "
        f"--python={quoted_directory} --strict"
    )
    assert result.uninstall_project_command == f"uv pip uninstall test-project --python={quoted_directory}"

    # Checks for yml-related commands. Both pin the target environment name, so the 'name' key inside the .yml file
    # cannot redirect them.
    assert result.create_from_yaml_command == (
        f"mamba env create -n test_env{os_suffix} -f {quoted_yaml_path} --yes --retry-clean-cache --pyc --use-uv"
    )
    assert result.update_command == (
        f"mamba env update -n test_env{os_suffix} -f {quoted_yaml_path} --yes --prune --use-uv"
    )

    # Also tests the case where .yml files are not present in the /envs folder.
    yaml_path.unlink()
    result = ProjectEnvironment.resolve_project_environment(
        project_root=project_directory, environment_name="test_env", python_version=python_version
    )
    assert result.create_from_yaml_command is None
    assert result.update_command is None

    # Verifies that prerelease=True includes the --prerelease=allow flag in uv commands.
    yaml_path.touch()
    result = ProjectEnvironment.resolve_project_environment(
        project_root=project_directory, environment_name="test_env", python_version=python_version, prerelease=True
    )
    assert "--prerelease=allow" in result.install_dependencies_command
    assert "--prerelease=allow" in result.install_project_command


def test_generate_typed_marker(tmp_path: Path) -> None:
    """Verifies the functionality of the generate_typed_marker() function."""
    # Sets up a mock library directory structure.
    library_root = tmp_path / "library"
    library_root.mkdir()
    subdirectory1 = library_root / "subdirectory1"
    subdirectory1.mkdir()
    subdirectory2 = library_root / "subdirectory2"
    subdirectory2.mkdir()

    # Creates py.typed files in subdirectories.
    (subdirectory1 / "py.typed").touch()
    (subdirectory2 / "py.typed").touch()

    aa.generate_typed_marker(library_root=library_root)

    # Verifies that py.typed exists in the root directory.
    assert (library_root / "py.typed").exists()

    # Verifies that py.typed has been removed from subdirectories.
    assert not (subdirectory1 / "py.typed").exists()
    assert not (subdirectory2 / "py.typed").exists()

    # Runs the function again to ensure it doesn't cause issues when py.typed already exists in the root.
    aa.generate_typed_marker(library_root=library_root)

    # Verifies that py.typed still exists in the root directory.
    assert (library_root / "py.typed").exists()

    # Verifies that no new py.typed files have been created in subdirectories.
    assert not (subdirectory1 / "py.typed").exists()
    assert not (subdirectory2 / "py.typed").exists()


def test_move_stubs(project_directory: Path) -> None:
    """Verifies the functionality of the move_stubs() function."""
    # Sets up mock directories.
    stubs_directory = project_directory / "stubs"
    library_root = project_directory / "src" / "library"
    stubs_directory.mkdir()
    library_root.mkdir(parents=True)

    # Creates mock stub files.
    stub_library_directory = stubs_directory.joinpath("library")
    stub_library_directory.mkdir()
    stub_library_directory.joinpath("__init__.pyi").touch()
    stub_library_directory.joinpath("module1.pyi").touch()
    stub_library_directory.joinpath("submodule").mkdir()
    (stub_library_directory / "submodule" / "module2.pyi").touch()

    aa.move_stubs(stubs_directory=stubs_directory, library_root=library_root)

    # Verifies that stubs have been moved correctly.
    assert (library_root / "__init__.pyi").exists()
    assert (library_root / "module1.pyi").exists()
    assert (library_root / "submodule" / "module2.pyi").exists()

    # Verifies that original stub files have been removed.
    assert not (stub_library_directory / "__init__.pyi").exists()
    assert not (stub_library_directory / "module1.pyi").exists()
    assert not (stub_library_directory / "submodule" / "module2.pyi").exists()


def test_move_stubs_osx_duplicates(project_directory: Path) -> None:
    """Verifies OSX-specific duplicate file handling in move_stubs()."""
    # Sets up mock directories.
    stubs_directory = project_directory / "stubs"
    library_root = project_directory / "src" / "library"
    stubs_directory.mkdir()
    library_root.mkdir(parents=True)

    # Creates stub files with OSX duplicate pattern (space + number).
    stub_library_directory = stubs_directory.joinpath("library")
    stub_library_directory.mkdir()
    stub_library_directory.joinpath("__init__.pyi").touch()
    stub_library_directory.joinpath("test 1.pyi").touch()
    stub_library_directory.joinpath("test 2.pyi").touch()
    stub_library_directory.joinpath("test 3.pyi").touch()

    aa.move_stubs(stubs_directory=stubs_directory, library_root=library_root)

    # Verifies that the duplicate handling kept the highest-numbered file and renamed it.
    assert (library_root / "test.pyi").exists()
    assert not (library_root / "test 1.pyi").exists()
    assert not (library_root / "test 2.pyi").exists()
    assert not (library_root / "test 3.pyi").exists()


def test_move_stubs_error(project_directory: Path) -> None:
    """Verifies the error-handling behavior of the move_stubs() function."""
    # Sets up mock directories.
    stubs_directory = project_directory.joinpath("stubs")
    library_root = project_directory / "src" / "library"
    stubs_directory.mkdir()
    library_root.mkdir(parents=True)

    # Creates invalid stub directory structure (multiple subdirectories with __init__.pyi).
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

    # Verifies that no files were moved.
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
    # Creates a mock .pypirc file with the given configuration.
    pypirc_path = tmp_path / ".pypirc"
    config_parser = ConfigParser()
    config_parser.read_dict(config)
    with pypirc_path.open("w") as pypirc_file:
        config_parser.write(pypirc_file)

    # Runs the verify_pypirc function.
    result = aa.verify_pypirc(file_path=pypirc_path)

    # Asserts that the function returns the expected result.
    assert result == expected_result


def test_verify_pypirc_nonexistent_file(tmp_path: Path) -> None:
    """Verifies the error-handling behavior of the verify_pypirc() function."""
    # Creates a path to a nonexistent file.
    nonexistent_path = tmp_path / "nonexistent.pypirc"

    # Runs the verify_pypirc function.
    result = aa.verify_pypirc(file_path=nonexistent_path)

    # Asserts that the function returns False for a nonexistent file.
    assert result is False


@pytest.mark.parametrize(
    "config, expected_result",
    [
        # Valid configuration
        ({"netlify": {"token": "faketoken1234567890abcdef"}}, True),
        # Missing netlify section
        ({"pypi": {"username": "__token__"}}, False),
        # Missing token
        ({"netlify": {"site": "project-api-docs.netlify.app"}}, False),
        # Empty token
        ({"netlify": {"token": ""}}, False),
        # Empty file
        ({}, False),
    ],
)
def test_verify_netlifyrc(tmp_path: Path, config: dict[str, dict[str, str]], expected_result: bool) -> None:
    """Verifies the functionality of the verify_netlifyrc() function.

    Tests all supported netlifyrc layouts.
    """
    # Creates a mock .netlifyrc file with the given configuration.
    netlifyrc_path = tmp_path / ".netlifyrc"
    config_parser = ConfigParser()
    config_parser.read_dict(config)
    with netlifyrc_path.open("w") as netlifyrc_file:
        config_parser.write(netlifyrc_file)

    # Runs the verify_netlifyrc function.
    result = aa.verify_netlifyrc(file_path=netlifyrc_path)

    # Asserts that the function returns the expected result.
    assert result == expected_result


def test_verify_netlifyrc_nonexistent_file(tmp_path: Path) -> None:
    """Verifies the error-handling behavior of the verify_netlifyrc() function."""
    # Creates a path to a nonexistent file.
    nonexistent_path = tmp_path / "nonexistent.netlifyrc"

    # Runs the verify_netlifyrc function.
    result = aa.verify_netlifyrc(file_path=nonexistent_path)

    # Asserts that the function returns False for a nonexistent file.
    assert result is False


def test_resolve_documented_project_directory(documented_project_directory: Path) -> None:
    """Verifies the functionality of the resolve_documented_project_directory() function."""
    os.chdir(documented_project_directory)
    result = aa.resolve_documented_project_directory()
    assert result == documented_project_directory


def test_resolve_documented_project_directory_python_project(project_directory: Path) -> None:
    """Verifies that the resolve_documented_project_directory() function accepts Python project layouts."""
    project_directory.joinpath("docs").mkdir()
    os.chdir(project_directory)
    result = aa.resolve_documented_project_directory()
    assert result == project_directory


def test_resolve_documented_project_directory_error(tmp_path: Path) -> None:
    """Verifies the error handling behavior of the resolve_documented_project_directory() function."""
    os.chdir(tmp_path)
    message: str = (
        f"Unable to confirm that ataraxis automation CLI has been called from the root directory of a valid "
        f"documented project. This CLI expects that the current working directory is set to the root directory of "
        f"the project, judged by the presence of '/src', '/docs' and 'tox.ini'. Current working directory is set to "
        f"{Path.cwd()}, which does not contain at least one of the required files."
    )
    with pytest.raises((SystemExit, RuntimeError), match=_error_format(message)):
        aa.resolve_documented_project_directory()


def test_resolve_application_directory(application_directory: Path) -> None:
    """Verifies the functionality of the application directory path resolution functions."""
    assert aa.resolve_application_directory() == application_directory
    assert application_directory.is_dir()
    assert aa.resolve_pypirc_path() == application_directory.joinpath(".pypirc")
    assert aa.resolve_netlifyrc_path() == application_directory.joinpath(".netlifyrc")


def test_derive_netlify_site(tmp_path: Path) -> None:
    """Verifies the functionality of the derive_netlify_site() function."""
    project_root = tmp_path.joinpath("ataraxis-automation")
    assert aa.derive_netlify_site(project_root=project_root) == "ataraxis-automation-api-docs.netlify.app"


def test_read_and_write_netlify_site(tmp_path: Path) -> None:
    """Verifies the functionality of the read_netlify_site() and write_netlify_site() functions."""
    assert aa.read_netlify_site(project_root=tmp_path) is None

    aa.write_netlify_site(project_root=tmp_path, site="project-api-docs.netlify.app")
    assert aa.read_netlify_site(project_root=tmp_path) == "project-api-docs.netlify.app"


def test_read_netlify_site_empty_file(tmp_path: Path) -> None:
    """Verifies that the read_netlify_site() function treats a blank .netlify-site file as an unconfigured file."""
    tmp_path.joinpath(".netlify-site").write_text("   \n")
    assert aa.read_netlify_site(project_root=tmp_path) is None


def test_migrate_legacy_pypirc(tmp_path: Path, application_directory: Path) -> None:
    """Verifies the functionality of the migrate_legacy_pypirc() function."""
    # A project without a legacy file has nothing to migrate.
    assert aa.migrate_legacy_pypirc(project_root=tmp_path) is False

    legacy_config = ConfigParser()
    legacy_config["pypi"] = {"username": "__token__", "password": "pypi-faketoken"}
    with tmp_path.joinpath(".pypirc").open("w") as legacy_file:
        legacy_config.write(legacy_file)

    assert aa.migrate_legacy_pypirc(project_root=tmp_path) is True
    assert aa.verify_pypirc(file_path=application_directory.joinpath(".pypirc"))

    # The shared token is already configured, so a second call does not overwrite it.
    assert aa.migrate_legacy_pypirc(project_root=tmp_path) is False


def test_migrate_legacy_netlifyrc(tmp_path: Path, application_directory: Path) -> None:
    """Verifies the functionality of the migrate_legacy_netlifyrc() function."""
    # A project without a legacy file has nothing to migrate.
    result = aa.migrate_legacy_netlifyrc(project_root=tmp_path)
    assert result == aa.NetlifyMigrationResult(token_migrated=False, site_migrated=False)
    assert not result

    legacy_config = ConfigParser()
    legacy_config["netlify"] = {"site": "project-api-docs.netlify.app", "token": "faketoken1234567890abcdef"}
    with tmp_path.joinpath(".netlifyrc").open("w") as legacy_file:
        legacy_config.write(legacy_file)

    result = aa.migrate_legacy_netlifyrc(project_root=tmp_path)
    assert result == aa.NetlifyMigrationResult(token_migrated=True, site_migrated=True)
    assert aa.verify_netlifyrc(file_path=application_directory.joinpath(".netlifyrc"))
    assert aa.read_netlify_site(project_root=tmp_path) == "project-api-docs.netlify.app"

    # Both credentials are already configured, so a second call does not overwrite them.
    result = aa.migrate_legacy_netlifyrc(project_root=tmp_path)
    assert result == aa.NetlifyMigrationResult(token_migrated=False, site_migrated=False)


def test_migrate_legacy_netlifyrc_partial_migrations(tmp_path: Path, application_directory: Path) -> None:
    """Verifies that migrate_legacy_netlifyrc() reports the token and the site migrations independently."""
    # The shared token is already configured, so only the site identifier migrates.
    shared_config = ConfigParser()
    shared_config["netlify"] = {"token": "sharedtoken1234567890abcd"}
    application_directory.mkdir(parents=True, exist_ok=True)
    with application_directory.joinpath(".netlifyrc").open("w") as shared_file:
        shared_config.write(shared_file)

    legacy_config = ConfigParser()
    legacy_config["netlify"] = {"site": "project-api-docs.netlify.app", "token": "projecttoken9876543210zyx"}
    with tmp_path.joinpath(".netlifyrc").open("w") as legacy_file:
        legacy_config.write(legacy_file)

    result = aa.migrate_legacy_netlifyrc(project_root=tmp_path)
    assert result == aa.NetlifyMigrationResult(token_migrated=False, site_migrated=True)

    # The shared file keeps the token it already stored.
    shared_credentials = ConfigParser()
    shared_credentials.read(application_directory.joinpath(".netlifyrc"))
    assert shared_credentials.get(section="netlify", option="token") == "sharedtoken1234567890abcd"

    # The project already carries a site identifier, so only the token migrates.
    other_project = tmp_path.joinpath("other")
    other_project.mkdir()
    other_project.joinpath(".netlify-site").write_text("deviating-site.netlify.app\n")
    application_directory.joinpath(".netlifyrc").unlink()
    with other_project.joinpath(".netlifyrc").open("w") as legacy_file:
        legacy_config.write(legacy_file)

    result = aa.migrate_legacy_netlifyrc(project_root=other_project)
    assert result == aa.NetlifyMigrationResult(token_migrated=True, site_migrated=False)
    assert aa.read_netlify_site(project_root=other_project) == "deviating-site.netlify.app"


def test_deploy_documentation(monkeypatch: pytest.MonkeyPatch, documentation_directory: Path) -> None:
    """Verifies the functionality of the deploy_documentation() function."""
    captured_request: dict[str, Any] = {}

    def _mock_post(**kwargs: Any) -> Mock:
        captured_request.update(kwargs)
        response = Mock()
        response.ok = True
        response.json.return_value = {"ssl_url": "https://project-api-docs.netlify.app"}
        return response

    monkeypatch.setattr(aa.requests, "post", _mock_post)

    result = aa.deploy_documentation(
        documentation_directory=documentation_directory, site="project-api-docs.netlify.app", token="faketoken"
    )

    # Asserts that the function returns the URL reported by Netlify.
    assert result == "https://project-api-docs.netlify.app"

    # Asserts that the request targets the deploys endpoint of the requested site and carries the expected headers.
    assert captured_request["url"] == "https://api.netlify.com/api/v1/sites/project-api-docs.netlify.app/deploys"
    assert captured_request["headers"]["Content-Type"] == "application/zip"
    assert captured_request["headers"]["Authorization"] == "Bearer faketoken"

    # Asserts that the uploaded archive stores every documentation file under a site-root-relative path.
    with zipfile.ZipFile(file=io.BytesIO(captured_request["data"])) as archive:
        assert sorted(archive.namelist()) == ["_static/styles.css", "index.html"]


def test_deploy_documentation_falls_back_to_insecure_url(
    monkeypatch: pytest.MonkeyPatch, documentation_directory: Path
) -> None:
    """Verifies that deploy_documentation() reports the plain URL for sites that do not serve traffic over HTTPS."""

    def _mock_post(**_kwargs: Any) -> Mock:
        response = Mock()
        response.ok = True
        response.json.return_value = {"url": "http://project-api-docs.netlify.app"}
        return response

    monkeypatch.setattr(aa.requests, "post", _mock_post)

    result = aa.deploy_documentation(
        documentation_directory=documentation_directory, site="project-api-docs.netlify.app", token="faketoken"
    )

    assert result == "http://project-api-docs.netlify.app"


def test_deploy_documentation_unbuilt_documentation(tmp_path: Path) -> None:
    """Verifies the error-handling behavior of the deploy_documentation() function for unbuilt documentation."""
    documentation_directory = tmp_path.joinpath("html")
    documentation_directory.mkdir()

    message = (
        f"Unable to deploy the API documentation stored in {documentation_directory}. The directory does not "
        f"contain the 'index.html' file, which indicates that the documentation has not been built. Build the "
        f"documentation with the 'docs' ('tox -e docs') task before deploying it."
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa.deploy_documentation(
            documentation_directory=documentation_directory, site="project-api-docs.netlify.app", token="faketoken"
        )


def test_deploy_documentation_rejected_deployment(
    monkeypatch: pytest.MonkeyPatch, documentation_directory: Path
) -> None:
    """Verifies the error-handling behavior of the deploy_documentation() function for rejected deployments."""

    def _mock_post(**_kwargs: Any) -> Mock:
        response = Mock()
        response.ok = False
        response.status_code = 401
        response.text = "Unauthorized"
        return response

    monkeypatch.setattr(aa.requests, "post", _mock_post)

    message = (
        "Unable to deploy the API documentation to the 'project-api-docs.netlify.app' Netlify site. Netlify rejected "
        "the deployment request with the status code 401 and the following response: Unauthorized."
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa.deploy_documentation(
            documentation_directory=documentation_directory, site="project-api-docs.netlify.app", token="faketoken"
        )


def test_deploy_documentation_failed_request(monkeypatch: pytest.MonkeyPatch, documentation_directory: Path) -> None:
    """Verifies the error-handling behavior of the deploy_documentation() function for unreachable Netlify servers."""

    def _mock_post(**_kwargs: Any) -> Mock:
        raise aa.requests.ConnectionError("Connection refused")

    monkeypatch.setattr(aa.requests, "post", _mock_post)

    message = (
        "Unable to deploy the API documentation to the 'project-api-docs.netlify.app' Netlify site. The deployment "
        "request failed with the following error: Connection refused."
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa.deploy_documentation(
            documentation_directory=documentation_directory, site="project-api-docs.netlify.app", token="faketoken"
        )


def test_delete_stubs(tmp_path: Path) -> None:
    """Verifies the functionality of the delete_stubs() function."""
    # Creates a mock library directory structure with .pyi files.
    library_root = tmp_path.joinpath("library")
    library_root.mkdir()
    library_root.joinpath("module1.pyi").touch()
    library_root.joinpath("module2.pyi").touch()
    subdirectory = library_root.joinpath("subdirectory")
    subdirectory.mkdir()
    subdirectory.joinpath("module3.pyi").touch()
    library_root.joinpath("not_a_stub.py").touch()  # Survives the purge.

    # Counts initial .pyi files.
    initial_pyi_count = len(list(library_root.rglob("*.pyi")))
    assert initial_pyi_count == 3

    aa.delete_stubs(library_root=library_root)

    # Verifies that all .pyi files have been deleted.
    remaining_pyi_files = list(library_root.rglob("*.pyi"))
    assert not remaining_pyi_files

    # Verifies that non-.pyi files were not deleted.
    assert (library_root / "not_a_stub.py").exists()

    # Verifies directory structure is maintained.
    assert subdirectory.exists()

    # Runs the function again to ensure it handles the case when no .pyi files are present.
    aa.delete_stubs(library_root=library_root)  # Completes without raising.


def test_project_environment_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the functionality of the ProjectEnvironment.environment_exists() method."""
    # Creates a mock ProjectEnvironment instance.
    environment = ProjectEnvironment(
        activate_command="conda init && conda activate test_env",
        deactivate_command="conda init && conda deactivate",
        create_command="mamba create -n test_env",
        create_from_yaml_command=None,
        remove_command="mamba remove -n test_env",
        install_dependencies_command="uv pip install deps",
        update_command=None,
        install_project_command="uv pip install .",
        uninstall_project_command="uv pip uninstall project",
        environment_name="test_env",
        environment_directory=Path("/path/to/env"),
        environment_yaml_path=Path("/path/to/envs/test_env.yml"),
        create_dry_run_command="mamba create -n test_env --dry-run",
    )

    # Tests the case where the environment exists.
    def mock_run_success(*args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(subprocess, "run", mock_run_success)
    assert environment.environment_exists() is True

    # Tests the case where the environment does not exist.
    def mock_run_failure(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.CalledProcessError(1, "cmd")

    monkeypatch.setattr(subprocess, "run", mock_run_failure)
    assert environment.environment_exists() is False


# resolve_project_environment() fallback.


def test_resolve_project_environment_with_manual_override(
    project_directory: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verifies that resolve_project_environment() uses the manual override when automatic resolution fails."""
    pyproject_content = """
[project]
name = "test-project"
dependencies = ["dep1==1.0"]

[dependency-groups]
dev = ["dev_dep==1.0"]
"""
    project_directory.joinpath("pyproject.toml").write_text(pyproject_content)

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(aa, "_check_package_engines", lambda: None)

    def mock_resolve_mamba() -> Path:
        raise RuntimeError("Mamba not found")

    monkeypatch.setattr(aa, "_resolve_mamba_environments_directory", mock_resolve_mamba)

    override_directory = tmp_path / "custom_envs"
    override_directory.mkdir()

    result = ProjectEnvironment.resolve_project_environment(
        project_root=project_directory,
        environment_name="test_env",
        environment_directory=override_directory,
    )

    assert result.environment_directory == override_directory / "test_env_lin"


def test_resolve_project_environment_reraise_without_override(
    project_directory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies that resolve_project_environment() re-raises RuntimeError when no override is provided."""
    pyproject_content = """
[project]
name = "test-project"
dependencies = ["dep1==1.0"]

[dependency-groups]
dev = ["dev_dep==1.0"]
"""
    project_directory.joinpath("pyproject.toml").write_text(pyproject_content)

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(aa, "_check_package_engines", lambda: None)

    def mock_resolve_mamba() -> Path:
        raise RuntimeError("Mamba not found")

    monkeypatch.setattr(aa, "_resolve_mamba_environments_directory", mock_resolve_mamba)

    with pytest.raises(RuntimeError, match="Mamba not found"):
        ProjectEnvironment.resolve_project_environment(
            project_root=project_directory,
            environment_name="test_env",
        )


# _resolve_dependencies() legacy path.


def test_resolve_dependencies_optional_dependencies_fallback(project_directory: Path) -> None:
    """Verifies that _resolve_dependencies() falls back to [project.optional-dependencies] when [dependency-groups]
    is not present.
    """
    pyproject_content = """
[project]
dependencies = ["dep1==1.0"]

[project.optional-dependencies]
dev = ["dev_dep1>=2.0", "dev_dep2<3.0"]
"""
    _write_pyproject_toml(project_directory=project_directory, content=pyproject_content)

    result = aa._resolve_dependencies(project_root=project_directory)
    assert set(result) == {'"dep1==1.0"', '"dev_dep1>=2.0"', '"dev_dep2<3.0"'}


def test_resolve_dependencies_no_dev_dependencies(project_directory: Path) -> None:
    """Verifies that _resolve_dependencies() works correctly when only runtime dependencies are defined."""
    pyproject_content = """
[project]
dependencies = ["dep1==1.0", "dep2>=2.0"]
"""
    _write_pyproject_toml(project_directory=project_directory, content=pyproject_content)

    result = aa._resolve_dependencies(project_root=project_directory)
    assert set(result) == {'"dep1==1.0"', '"dep2>=2.0"'}


# _resolve_mamba_environments_directory() resolution methods.


def test_resolve_mamba_envs_via_executable_envs_dir(tmp_path: Path, clean_mamba_env: pytest.MonkeyPatch) -> None:
    """Verifies _resolve_mamba_environments_directory() finds envs/ by ascending from a miniforge executable."""
    # Creates tmp_path/miniforge3/envs/myenv/bin/python.
    envs_directory = tmp_path / "miniforge3" / "envs"
    python_directory = envs_directory / "myenv" / "bin"
    python_directory.mkdir(parents=True)
    python_exe = python_directory / "python"
    python_exe.touch()

    clean_mamba_env.setattr(sys, "executable", str(python_exe))

    result = aa._resolve_mamba_environments_directory()
    assert result == envs_directory


def test_resolve_mamba_envs_via_executable_conda_meta(tmp_path: Path, clean_mamba_env: pytest.MonkeyPatch) -> None:
    """Verifies _resolve_mamba_environments_directory() finds envs/ via conda-meta in a miniforge root."""
    # Creates tmp_path/miniforge3 with conda-meta, envs, and bin/python.
    miniforge_root = tmp_path / "miniforge3"
    miniforge_root.joinpath("conda-meta").mkdir(parents=True)
    miniforge_root.joinpath("envs").mkdir()
    python_directory = miniforge_root / "bin"
    python_directory.mkdir()
    python_exe = python_directory / "python"
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
    # Creates tmp_path/miniforge3/envs/myenv with conda-meta and bin/python.
    envs_directory = tmp_path / "miniforge3" / "envs"
    myenv_directory = envs_directory / "myenv"
    myenv_directory.joinpath("conda-meta").mkdir(parents=True)
    python_directory = myenv_directory / "bin"
    python_directory.mkdir()
    python_exe = python_directory / "python"
    python_exe.touch()

    clean_mamba_env.setattr(sys, "executable", str(python_exe))

    result = aa._resolve_mamba_environments_directory()
    assert result == envs_directory


def test_resolve_mamba_envs_via_conda_exe(tmp_path: Path, clean_mamba_env: pytest.MonkeyPatch) -> None:
    """Verifies _resolve_mamba_environments_directory() resolves envs/ via the CONDA_EXE environment variable."""
    # Creates tmp_path/miniforge3 with bin/mamba and envs.
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
    # Creates the directory only at the AppData/Local level, so that method 3 does not resolve it first.
    fake_home.joinpath("AppData", "Local", "miniforge3", "envs").mkdir(parents=True)

    clean_mamba_env.setattr(Path, "home", staticmethod(lambda: fake_home))
    clean_mamba_env.setattr(sys, "platform", "win32")

    result = aa._resolve_mamba_environments_directory()
    assert result == fake_home / "AppData" / "Local" / "miniforge3" / "envs"


def test_resolve_mamba_envs_via_windows_localappdata(tmp_path: Path, clean_mamba_env: pytest.MonkeyPatch) -> None:
    """Verifies _resolve_mamba_environments_directory() finds envs/ via the LOCALAPPDATA environment variable."""
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    # Omits miniforge3/envs at the home and AppData/Local levels, so that only LOCALAPPDATA resolves.
    local_appdata_directory = tmp_path / "localappdata"
    local_appdata_directory.joinpath("miniforge3", "envs").mkdir(parents=True)

    clean_mamba_env.setattr(Path, "home", staticmethod(lambda: fake_home))
    clean_mamba_env.setattr(sys, "platform", "win32")
    clean_mamba_env.setenv("LOCALAPPDATA", str(local_appdata_directory))

    result = aa._resolve_mamba_environments_directory()
    assert result == local_appdata_directory / "miniforge3" / "envs"


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


# move_stubs() single-file rename.


def test_move_stubs_single_file_with_copy_number(project_directory: Path) -> None:
    """Verifies that move_stubs() correctly renames a single stub file that has an OSX copy number suffix."""
    stubs_directory = project_directory / "stubs"
    library_root = project_directory / "src" / "library"
    stubs_directory.mkdir()
    library_root.mkdir(parents=True)

    stub_library_directory = stubs_directory / "library"
    stub_library_directory.mkdir()
    stub_library_directory.joinpath("__init__.pyi").touch()
    stub_library_directory.joinpath("module 1.pyi").touch()

    aa.move_stubs(stubs_directory=stubs_directory, library_root=library_root)

    # Verifies that the "module 1.pyi" file was renamed to "module.pyi".
    assert (library_root / "module.pyi").exists()
    assert not (library_root / "module 1.pyi").exists()
    assert (library_root / "__init__.pyi").exists()


# Windows file lock retry helpers.


def test_unlink_with_retry_passthrough_non_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that _unlink_with_retry() calls Path.unlink() directly on non-Windows platforms."""
    monkeypatch.setattr(sys, "platform", "linux")
    target_file = tmp_path / "test.txt"
    target_file.touch()

    aa._unlink_with_retry(path=target_file)
    assert not target_file.exists()


def test_unlink_with_retry_missing_ok_non_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that _unlink_with_retry() respects missing_ok on non-Windows platforms."""
    monkeypatch.setattr(sys, "platform", "linux")
    nonexistent = tmp_path / "nonexistent.txt"

    # Completes without raising when missing_ok is True.
    aa._unlink_with_retry(nonexistent, missing_ok=True)

    # Raises FileNotFoundError when missing_ok is False.
    with pytest.raises(FileNotFoundError):
        aa._unlink_with_retry(nonexistent, missing_ok=False)


def test_unlink_with_retry_retries_on_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that _unlink_with_retry() retries on PermissionError when platform is win32."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(aa, "_FILE_RETRY_INITIAL_DELAY", 0.01)

    target_file = tmp_path / "test.txt"
    target_file.touch()

    # Simulates PermissionError on first two calls, then succeeds on third.
    call_count = 0
    original_unlink = Path.unlink

    def mock_unlink(self: Path, missing_ok: bool = False) -> None:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise PermissionError("File is locked")
        original_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    aa._unlink_with_retry(path=target_file)
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
        aa._unlink_with_retry(path=target_file)


def test_rename_with_retry_passthrough_non_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that _rename_with_retry() calls Path.rename() directly on non-Windows platforms."""
    monkeypatch.setattr(sys, "platform", "linux")
    source = tmp_path / "source.txt"
    source.touch()
    destination = tmp_path / "destination.txt"

    aa._rename_with_retry(source=source, destination=destination)
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

    aa._rename_with_retry(source=source, destination=destination)
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
        aa._rename_with_retry(source=source, destination=destination)


def test_robust_rmtree_passthrough_non_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that robust_rmtree() calls shutil.rmtree() directly on non-Windows platforms."""
    monkeypatch.setattr(sys, "platform", "linux")
    target_directory = tmp_path / "target"
    target_directory.mkdir()
    (target_directory / "file.txt").touch()

    aa.robust_rmtree(path=target_directory)
    assert not target_directory.exists()


def test_robust_rmtree_retries_on_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that robust_rmtree() retries on PermissionError when platform is win32."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(aa, "_FILE_RETRY_INITIAL_DELAY", 0.01)

    target_directory = tmp_path / "target"
    target_directory.mkdir()
    (target_directory / "file.txt").touch()

    call_count = 0
    original_rmtree = shutil.rmtree

    def mock_rmtree(path: Path, onerror: object | None = None) -> None:
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise PermissionError("Directory is locked")
        original_rmtree(path)

    monkeypatch.setattr(shutil, "rmtree", mock_rmtree)

    aa.robust_rmtree(path=target_directory)
    assert call_count == 3


def test_robust_rmtree_exhausts_retries_on_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that robust_rmtree() raises PermissionError after exhausting all retries on Windows."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(aa, "_FILE_RETRY_INITIAL_DELAY", 0.01)

    target_directory = tmp_path / "target"
    target_directory.mkdir()
    (target_directory / "file.txt").touch()

    def mock_rmtree(path: Path, onerror: object | None = None) -> None:
        raise PermissionError("Directory is locked")

    monkeypatch.setattr(shutil, "rmtree", mock_rmtree)

    with pytest.raises(PermissionError, match="Directory is locked"):
        aa.robust_rmtree(path=target_directory)


def test_rmtree_onerror_clears_readonly(tmp_path: Path) -> None:
    """Verifies that _rmtree_onerror() clears the read-only attribute and retries the deletion."""
    target_file = tmp_path / "readonly.txt"
    target_file.touch()

    # Makes the file read-only.
    target_file.chmod(stat.S_IREAD)

    # Simulates the onerror callback with os.remove as the function.
    exc_info = _capture_exc_info(exception=PermissionError("Permission denied"))
    try:
        aa._rmtree_onerror(failing_function=os.remove, path=str(target_file), exception_information=exc_info)
    except Exception:
        # Restores write permission for cleanup if the test fails.
        target_file.chmod(stat.S_IWRITE)
        raise

    assert not target_file.exists()


def test_rmtree_onerror_reraises_non_permission_error() -> None:
    """Verifies that _rmtree_onerror() re-raises exceptions that are not PermissionError."""
    exc_info = _capture_exc_info(exception=OSError("Disk error"))
    with pytest.raises(OSError, match="Disk error"):
        aa._rmtree_onerror(failing_function=os.remove, path="/nonexistent", exception_information=exc_info)


# Shell-command quoting, environment export, and subprocess invocation pinning.


@pytest.mark.parametrize(
    "platform, directory, expected",
    [
        ("linux", "/home/user/project/envs", "/home/user/project/envs"),
        ("linux", "/home/user/My Projects/envs", "'/home/user/My Projects/envs'"),
        ("darwin", "/Users/user/My Projects/envs", "'/Users/user/My Projects/envs'"),
        ("win32", "/Users/John Smith/miniforge3/envs", '"/Users/John Smith/miniforge3/envs"'),
        ("win32", "/Users/user/miniforge3/envs", '"/Users/user/miniforge3/envs"'),
    ],
)
def test_quote_path(monkeypatch: pytest.MonkeyPatch, platform: str, directory: str, expected: str) -> None:
    """Verifies that _quote_path() wraps paths in the syntax used by the host platform's command shell."""
    monkeypatch.setattr(sys, "platform", platform)
    assert aa._quote_path(path=Path(directory)) == expected


@pytest.mark.parametrize(
    "specification_lines, expected",
    [
        # A specification exported for an environment mamba does not track.
        (["name: missing", "channels:", "dependencies:"], False),
        # A specification with no dependencies key at all.
        (["name: missing", "channels:"], False),
        # A fully populated specification.
        (["name: env", "channels:", "  - conda-forge", "dependencies:", "  - python=3.14"], True),
        # An empty export.
        ([], False),
    ],
)
def test_declares_dependencies(specification_lines: list[str], expected: bool) -> None:
    """Verifies that _declares_dependencies() distinguishes a populated specification from a contentless one."""
    assert aa._declares_dependencies(specification_lines=specification_lines) is expected


def test_export_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that export_environment() writes the specification without the host-specific prefix line."""
    yaml_path = tmp_path.joinpath("test_env_lin.yml")
    yaml_path.write_text("name: test_env_lin\ndependencies:\n  - stale=1.0\nprefix: /old\n")
    environment = _build_environment(yaml_path=yaml_path, environment_directory=tmp_path.joinpath("env"))

    captured: dict[str, Any] = {}

    def mock_run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["kwargs"] = kwargs
        specification = "name: test_env_lin\nchannels:\n  - conda-forge\ndependencies:\n  - python=3.14\nprefix: /x\n"
        return subprocess.CompletedProcess(command, 0, stdout=specification, stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    environment.export_environment()

    # The export is issued without a shell, so the environment name cannot be re-parsed by one.
    assert captured["command"] == ["mamba", "env", "export", "--name", "test_env_lin", "--use-uv"]
    assert captured["kwargs"]["check"] is True
    assert captured["kwargs"]["capture_output"] is True

    # The host-specific prefix line is stripped and no temporary file survives the write.
    assert yaml_path.read_text() == "name: test_env_lin\nchannels:\n  - conda-forge\ndependencies:\n  - python=3.14\n"
    assert not tmp_path.joinpath("test_env_lin.yml.tmp").exists()


def test_export_environment_mamba_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that a failing mamba export leaves the previously exported file unchanged."""
    yaml_path = tmp_path.joinpath("test_env_lin.yml")
    original = "name: test_env_lin\ndependencies:\n  - python=3.14\n"
    yaml_path.write_text(original)
    environment = _build_environment(yaml_path=yaml_path, environment_directory=tmp_path.joinpath("env"))

    def mock_run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(109, command, stderr="solver failure")

    monkeypatch.setattr(subprocess, "run", mock_run)

    message: str = (
        "Unable to export the 'test_env_lin' mamba environment to a .yml file. Mamba exited with the code 109 and "
        "the following error: solver failure."
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        environment.export_environment()

    assert yaml_path.read_text() == original


def test_export_environment_contentless_specification(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that a specification declaring no dependencies does not overwrite the exported file.

    Mamba answers a request for an environment it does not track with a zero exit code and a contentless skeleton,
    which would otherwise replace the stored dependency pins.
    """
    yaml_path = tmp_path.joinpath("test_env_lin.yml")
    original = "name: test_env_lin\ndependencies:\n  - python=3.14\n"
    yaml_path.write_text(original)
    environment = _build_environment(yaml_path=yaml_path, environment_directory=tmp_path.joinpath("env"))

    def mock_run(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command, 0, stdout="name: test_env_lin\nchannels:\ndependencies:\n", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    message: str = (
        "Unable to export the 'test_env_lin' mamba environment to a .yml file. Mamba exported a specification that "
        "declares no dependencies, which indicates that it does not track an environment under that name. The "
        "previously exported file has been left unchanged."
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        environment.export_environment()

    assert yaml_path.read_text() == original


def test_environment_exists_reports_broken_activation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that a registered environment that fails to activate is reported as an error rather than as absent.

    Collapsing the two conditions into a False return lets the callers that remove environments delete a working one.
    """
    environment_directory = tmp_path.joinpath("test_env_lin")
    environment_directory.joinpath("conda-meta").mkdir(parents=True)
    environment = _build_environment(
        yaml_path=tmp_path.joinpath("test_env_lin.yml"), environment_directory=environment_directory
    )

    def mock_run(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.CalledProcessError(127, "cmd")

    monkeypatch.setattr(subprocess, "run", mock_run)

    message: str = (
        f"Unable to activate the 'test_env_lin' mamba environment stored under {environment_directory}, although the "
        f"directory contains a valid environment. This typically indicates that conda is not installed or "
        f"initialized on this machine. Make sure miniforge3 is installed and initialized before using the "
        f"ataraxis-automation cli."
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        environment.environment_exists()


def test_environment_exists_pins_subprocess_arguments(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that environment_exists() runs the activation command with check enabled."""
    environment = _build_environment(
        yaml_path=tmp_path.joinpath("test_env_lin.yml"), environment_directory=tmp_path.joinpath("env")
    )
    captured: dict[str, Any] = {}

    def mock_run(command: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", mock_run)
    assert environment.environment_exists() is True
    assert captured["command"] == environment.activate_command
    assert captured["kwargs"]["check"] is True
    assert captured["kwargs"]["shell"] is True


def test_check_package_engines_pins_subprocess_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that _check_package_engines() probes both engines with check enabled."""
    captured: list[dict[str, Any]] = []

    def mock_run(command: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        captured.append({"command": command, "kwargs": kwargs})
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", mock_run)
    aa._check_package_engines()

    assert [entry["command"] for entry in captured] == ["mamba --version", "uv --version"]
    assert all(entry["kwargs"]["check"] is True for entry in captured)


# Guards that reject malformed inputs.


def test_resolve_project_name_rejects_empty_name(project_directory: Path) -> None:
    """Verifies that an empty project name is rejected alongside a missing one."""
    project_directory.joinpath("pyproject.toml").write_text('[project]\nname = ""\n')

    message = (
        "Unable to resolve the project name from the pyproject.toml file. The 'name' field is missing or empty in "
        "the [project] section of the file."
    )
    with pytest.raises(ValueError, match=_error_format(message)):
        aa._resolve_project_name(project_root=project_directory)


def test_resolve_project_environment_rejects_empty_dependencies(
    project_directory: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies that a project declaring no dependencies is rejected before any dependency-installation or
    environment-creation command is built.
    """
    project_directory.joinpath("pyproject.toml").write_text('[project]\nname = "test-project"\n')
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(aa, "_check_package_engines", lambda: None)
    monkeypatch.setenv("CONDA_PREFIX", "/path/to/miniforge3")
    monkeypatch.setenv("CONDA_DEFAULT_ENV", "base")

    message = (
        f"Unable to resolve the mamba environment for the project stored under {project_directory}. The project's "
        f"pyproject.toml file declares no runtime or development dependencies, so there is nothing to install into "
        f"the environment."
    )
    with pytest.raises(ValueError, match=_error_format(message)):
        ProjectEnvironment.resolve_project_environment(project_root=project_directory, environment_name="test_env")


@pytest.mark.parametrize("conda_executable", ["mamba", "/mamba", "bin/mamba"])
def test_resolve_mamba_envs_rejects_unusable_conda_exe(
    tmp_path: Path, clean_mamba_env: pytest.MonkeyPatch, conda_executable: str
) -> None:
    """Verifies that a relative or single-component CONDA_EXE value falls through to the remaining methods.

    Indexing such a value raises IndexError, and resolving a relative one would silently select the 'envs' directory
    of whichever project happens to be the working directory.
    """
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    clean_mamba_env.setattr(Path, "home", staticmethod(lambda: fake_home))
    clean_mamba_env.setattr(sys, "platform", "linux")
    clean_mamba_env.setenv("CONDA_EXE", conda_executable)

    # Creates an 'envs' directory in the working directory, which every valid project root carries.
    os.chdir(tmp_path)
    tmp_path.joinpath("envs").mkdir(exist_ok=True)

    message = (
        "Unable to resolve the path to the mamba environments directory. This version of ataraxis-automation expects "
        "that mamba is installed via miniforge3, following the deprecation of mambaforge. Make sure miniforge3 is "
        "installed and initialized before using ataraxis-automation cli. Install from: "
        "https://github.com/conda-forge/miniforge"
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa._resolve_mamba_environments_directory()


@pytest.mark.parametrize(
    "required_items, present_items",
    [
        (aa._PYTHON_PROJECT_ITEMS, ("tox.ini",)),
        (aa._PYTHON_PROJECT_ITEMS, ("src", "envs", "tox.ini")),
        (aa._DOCUMENTED_PROJECT_ITEMS, ("src", "tox.ini")),
    ],
)
def test_resolve_project_directory_rejects_partial_layouts(
    tmp_path: Path, required_items: tuple[str, ...], present_items: tuple[str, ...]
) -> None:
    """Verifies that a directory holding only some of the required items is rejected."""
    for item in present_items:
        target = tmp_path.joinpath(item)
        if "." in item:
            target.touch()
        else:
            target.mkdir()

    os.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="Unable to confirm that ataraxis automation CLI"):
        aa._resolve_project_directory(
            required_items=required_items, project_description="Python", items_description="the required items"
        )


# Deserialization oracles, message formatting, and move_stubs() guards.


@pytest.mark.parametrize(
    "json_value, json_error, expected",
    [
        # Netlify prefers the HTTPS address when the site serves it.
        ({"ssl_url": "https://site.netlify.app", "url": "http://site.netlify.app"}, None, "https://site.netlify.app"),
        # A response carrying no JSON body still describes an accepted deployment.
        (None, ValueError("Expecting value"), "https://project-api-docs.netlify.app"),
        # A JSON array body carries no address keys.
        ([], None, "https://project-api-docs.netlify.app"),
    ],
)
def test_deploy_documentation_resolves_website_url(
    monkeypatch: pytest.MonkeyPatch,
    documentation_directory: Path,
    json_value: Any,
    json_error: Exception | None,
    expected: str,
) -> None:
    """Verifies the address reported for each shape of the Netlify success response."""

    def _mock_post(**_kwargs: Any) -> Mock:
        response = Mock()
        response.ok = True
        if json_error is not None:
            response.json.side_effect = json_error
        else:
            response.json.return_value = json_value
        return response

    monkeypatch.setattr(aa.requests, "post", _mock_post)

    result = aa.deploy_documentation(
        documentation_directory=documentation_directory, site="project-api-docs.netlify.app", token="faketoken"
    )
    assert result == expected


def test_format_message_wraps_at_120_characters() -> None:
    """Verifies that format_message() wraps text at the width shared by all Ataraxis framework output."""
    message = " ".join(["word"] * 60)
    formatted = aa.format_message(message=message)

    assert all(len(line) <= 120 for line in formatted.splitlines())
    assert formatted.splitlines()[0] == " ".join(["word"] * 24)

    # Long words and hyphenated words are never broken across lines.
    unbroken = aa.format_message(message="a" * 200)
    assert unbroken == "a" * 200


def test_move_stubs_rejects_missing_library_directory(project_directory: Path) -> None:
    """Verifies that a stubs directory holding no qualifying subdirectory is rejected by the structure guard."""
    stubs_directory = project_directory.joinpath("stubs")
    library_root = project_directory / "src" / "library"
    stubs_directory.mkdir()
    library_root.mkdir(parents=True)

    message: str = (
        f"Unable to move the generated stub files to appropriate levels of the library source code directory. "
        f"Expected exactly one subdirectory with __init__.pyi in '{stubs_directory}', but found {0}."
    )
    with pytest.raises(RuntimeError, match=_error_format(message)):
        aa.move_stubs(stubs_directory=stubs_directory, library_root=library_root)


def test_move_stubs_keeps_highest_numbered_duplicate_content(project_directory: Path) -> None:
    """Verifies that the duplicate collapsing keeps the content of the highest-numbered copy."""
    stubs_directory = project_directory / "stubs"
    library_root = project_directory / "src" / "library"
    stubs_directory.mkdir()
    library_root.mkdir(parents=True)

    stub_library_directory = stubs_directory / "library"
    stub_library_directory.mkdir()
    stub_library_directory.joinpath("__init__.pyi").touch()
    stub_library_directory.joinpath("module 1.pyi").write_text("superseded")
    stub_library_directory.joinpath("module 2.pyi").write_text("current")

    aa.move_stubs(stubs_directory=stubs_directory, library_root=library_root)

    assert (library_root / "module.pyi").read_text() == "current"


# Private helpers shared by the tests above.


def _error_format(message: str) -> str:
    """Formats the input message with format_message() and escapes it using re, so that it can be used to verify
    raised exceptions.

    Args:
        message: The message to format and escape, according to standard Ataraxis testing parameters.

    Returns:
        Formatted and escaped message that can be used as the 'match' argument of the pytest.raises() method.
    """
    return re.escape(aa.format_message(message=message))


def _write_pyproject_toml(project_directory: Path, content: str) -> None:
    """Writes the given content to the pyproject.toml file in the project directory.

    Args:
        project_directory: The path to the processed project root directory.
        content: The string-content to write to the pyproject.toml file of the processed project.
    """
    pyproject_path: Path = project_directory.joinpath("pyproject.toml")
    pyproject_path.write_text(content)


def _write_tox_ini(project_directory: Path, content: str) -> None:
    """Writes the given content to the tox.ini file in the project directory.

    Args:
        project_directory: The path to the processed project root directory.
        content: The string-content to write to the tox.ini file of the processed project.
    """
    tox_path: Path = project_directory.joinpath("tox.ini")
    tox_path.write_text(content)


def _capture_exc_info(exception: BaseException) -> tuple[type[BaseException], BaseException, TracebackType]:
    """Raises and catches the given exception to build a populated exception info tuple.

    The resulting tuple mirrors the value passed by shutil.rmtree() to its onerror callback, including a real
    traceback object, so it can be forwarded to _rmtree_onerror() in tests.

    Args:
        exception: The exception instance to raise and capture.

    Returns:
        The exception info tuple containing the exception type, the exception instance, and a populated traceback.
    """
    try:
        raise exception
    except BaseException as caught:
        traceback = caught.__traceback__
        assert traceback is not None
        return type(caught), caught, traceback


def _build_environment(yaml_path: Path, environment_directory: Path) -> ProjectEnvironment:
    """Builds a ProjectEnvironment instance for tests that exercise its methods directly."""
    return ProjectEnvironment(
        activate_command="conda init && conda activate test_env",
        deactivate_command="conda init && conda deactivate",
        create_command="mamba create -n test_env",
        create_dry_run_command="mamba create -n test_env --dry-run",
        create_from_yaml_command=None,
        remove_command="mamba remove -n test_env",
        install_dependencies_command="uv pip install deps",
        update_command=None,
        install_project_command="uv pip install .",
        uninstall_project_command="uv pip uninstall project",
        environment_name="test_env_lin",
        environment_directory=environment_directory,
        environment_yaml_path=yaml_path,
    )
