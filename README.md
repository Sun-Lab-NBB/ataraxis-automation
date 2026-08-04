# ataraxis-automation

Supports tox-based development automation pipelines used by other Ataraxis framework projects.

![PyPI - Version](https://img.shields.io/pypi/v/ataraxis-automation)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ataraxis-automation)
[![uv](https://tinyurl.com/uvbadge)](https://github.com/astral-sh/uv)
[![Ruff](https://tinyurl.com/ruffbadge)](https://github.com/astral-sh/ruff)
![type-checked: mypy](https://img.shields.io/badge/type--checked-mypy-blue?style=flat-square&logo=python)
![PyPI - License](https://img.shields.io/pypi/l/ataraxis-automation)
![PyPI - Status](https://img.shields.io/pypi/status/ataraxis-automation)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/ataraxis-automation)

___

## Detailed Description

Upon installation into a Python environment, this library exposes a command-line interface (automation-cli) used by the
[tox](https://tox.wiki/en/latest/user_guide.html)-based project development automation suite that comes with every
Ataraxis framework project. The CLI abstracts the project's environment manipulation and facilitates mundane
development tasks, such as linting, typing, and documenting the source code API. This library is part of the
[Ataraxis](https://github.com/Sun-Lab-NBB/ataraxis) framework for AI-assisted scientific hardware control.

___

## Features

- Supports Windows, Linux, and macOS.
- Optimized for runtime speed by using mamba and uv for all environment management tasks.
- Supplies the CLI commands used by the tox environments of all Ataraxis framework projects.
- Apache 2.0 License.

___

## Table of Contents

- [Dependencies](#dependencies)
- [Installation](#installation)
- [Usage](#usage)
  - [CLI Commands](#cli-commands)
  - [Supported Checkout Tox Tasks](#supported-checkout-tox-tasks)
  - [Supported Mamba Environment Manipulation Tox Tasks](#supported-mamba-environment-manipulation-tox-tasks)
- [API Documentation](#api-documentation)
- [Developers](#developers)
- [Versioning](#versioning)
- [Authors](#authors)
- [License](#license)
- [Acknowledgments](#acknowledgments)

___

## Dependencies

- [miniforge3](https://github.com/conda-forge/miniforge). This library expects that a miniforge3 distribution is
  used to install and export the [mamba](https://github.com/mamba-org/mamba) environment manager to the host-system's
  PATH variable.
- [uv](https://docs.astral.sh/uv/). This library uses uv as the main package management engine and expects that uv is
  available from the system's base Python environment.

For users, all other library dependencies are installed automatically by all supported installation methods.
For developers, see the [Developers](#developers) section for information on installing additional development
dependencies.

___

## Installation

### Source

***Note,*** installation from source is ***highly discouraged*** for anyone who is not an active project developer.

1. Download this repository to the local machine using the preferred method, such as git-cloning. Use one of the
   [stable releases](https://github.com/Sun-Lab-NBB/ataraxis-automation/tags) that include precompiled binary and
   source code distribution (sdist) wheels.
2. If the downloaded distribution is stored as a compressed archive, unpack it using the appropriate decompression tool.
3. `cd` to the root directory of the prepared project distribution.
4. Run `pip install .` to install the project and its dependencies.

### pip

Use the following command to install the library and all of its dependencies via
[pip](https://pip.pypa.io/en/stable/): `pip install ataraxis-automation`

___

## Usage

***Note,*** the library expects the managed project to use a specific configuration and file structure. If any CLI
command terminates with an error, the terminal output describes whether the error is due to an invalid project
configuration or file structure.

### CLI Commands

All library functions designed to be called by automation pipelines are exposed through the 'automation-cli' Command
Line Interface (CLI). This CLI is automatically exposed by installing the library into a Python environment. The
commands are intended to be invoked through 'tox' tasks rather than directly by end-users.

| Command                   | Description                                                                          |
|---------------------------|--------------------------------------------------------------------------------------|
| `process-typed-markers`   | Ensures the 'py.typed' marker exists only at the root of the library directory tree. |
| `process-stubs`           | Distributes generated stub (.pyi) files to the library source directories.           |
| `purge-stubs`             | Removes all existing stub (.pyi) files from the library source directories.          |
| `acquire-pypi-token`      | Ensures the shared '.pypirc' file holds a validly formatted PyPI API token.          |
| `acquire-netlify-token`   | Ensures the project's site identifier and the shared Netlify API token are set.      |
| `deploy-docs`             | Deploys the documentation built by the 'docs' task to the project's Netlify site.    |
| `upload-project`          | Uploads the wheel and sdist distributions built by the 'build' task to PyPI.         |
| `install-project`         | Builds and installs the project into its mamba environment as a library.             |
| `uninstall-project`       | Uninstalls the project library from its mamba environment.                           |
| `create-environment`      | Creates the project's mamba environment and installs its dependencies.               |
| `remove-environment`      | Removes the project's mamba environment and its environment directory.               |
| `provision-environment`   | Recreates the project's mamba environment and reinstalls its dependencies.           |
| `import-environment`      | Creates or updates the mamba environment from the os-specific .yml file in /envs.    |
| `export-environment`      | Exports the mamba environment to the /envs directory as an os-specific .yml file.    |

#### Automation-CLI

All CLI commands supplied by the library are accessible by calling `automation-cli` from a Python environment where
the library is installed. For example:
- Use `automation-cli --help` to verify that the CLI is available and to see the list of supported commands.
- Use `automation-cli COMMAND-NAME --help` to display additional information about a specific command. For example:
  `automation-cli import-environment --help`.

#### Tox Integration

This library is intended to be used via [tox](https://tox.wiki/en/latest/user_guide.html) tasks (environments). To use
any of the exposed CLI's commands as part of a tox environment, add it to the 'commands' section of the tox.ini:
```
[testenv:create]
deps =
    ataraxis-automation==9.0.1
commands =
    automation-cli create-environment --environment-name axa_dev --python-version 3.14 {posargs:}
```

See the [tox.ini](tox.ini) configuration file for the most up-to-date project development automation
suite used in the Ataraxis framework. For the most up-to-date C-extension project automation suite, see the
tox.ini file of the [ataraxis-time](https://github.com/Sun-Lab-NBB/ataraxis-time) library.

#### Additional Command Arguments

***Note,*** many sub-commands of the CLI have additional flags and arguments that can be used to further customize
their runtime. Consult the [API documentation](#api-documentation) for the list of additional runtime flags for all
supported CLI commands.

### Supported Checkout Tox Tasks

This library is tightly linked to the environments defined in the [tox.ini](tox.ini) configuration file.

Commands listed in this section are frequently modified based on the specific needs of
each Ataraxis framework project. This section is ***not*** a replacement for studying the tox.ini file for each
Ataraxis framework project.

Most commands in this section are designed to be executed together as part of the `tox` CLI command. These commands
are referred to as 'checkout' tasks and must run successfully for any pull request candidate before it is merged into
the main branch of each Ataraxis framework project. The 'upload' and 'deploy' tasks are kept out of the envlist and
are called manually at release time.

#### Lint

Shell command: `tox -e lint`

Uses [ruff](https://github.com/astral-sh/ruff) and [mypy](https://github.com/python/mypy) to statically analyze and,
where possible, fix code formatting, typing, and problematic use patterns. As part of its runtime, this task uses
automation-cli to remove existing stub (.pyi) files from the source directories, as they sometimes interfere with
type-checking.

Example tox.ini section:
```
[testenv:lint]
description =
    Runs static code formatting, style, and typing checkers. Follows the configuration defined in the pyproject.toml
    file.
dependency_groups = dev
basepython = py312
commands =
    automation-cli purge-stubs
    ruff format
    ruff check --fix ./src ./tests
    mypy ./src
```

***Note,*** the `mypy ./src` command runs single-threaded, which is optimal for the typical
ataraxis or sollertia library: warm, incremental runs finish in well under a second. Large projects
whose source code takes several seconds to type-check (such as `cindra` or `sollertia-experiment`)
can opt into mypy 2.x's experimental parallel checking by appending `-n N` (`--num-workers N`) to
the command, where `N` is the number of available CPU cores. This mainly accelerates fresh checkout
runs and is not recommended for smaller projects, where the worker-startup overhead negates the
gain.

#### Stubs

Shell command: `tox -e stubs`

Uses [stubgen](https://mypy.readthedocs.io/en/stable/stubgen.html) to generate stub (.pyi) files and distributes them
via automation-cli to the appropriate levels of the project's source code hierarchy. As part of this process,
automation-cli also ensures that there is a 'py.typed' marker file in the highest library directory. This is required
for type-checkers like mypy to recognize the library as 'typed' and process it during type-checking tasks.

Example tox.ini section:
```
[testenv:stubs]
description = Generates the py.typed marker and the .pyi stub files using the project's sdist distribution.
depends = lint
dependency_groups = dev
commands =
    automation-cli process-typed-markers
    stubgen -o stubs --include-private -p ataraxis_automation -v
    automation-cli process-stubs
    ruff format
    ruff check --select I --fix ./src
```

#### Test

Shell command: `tox -e pyXXX-test`

This task is executed for all python versions supported by each project. For example, ataraxis-automation supports
versions 3.12, 3.13, and 3.14. Therefore, it has `tox -e py312-test`, `tox -e py313-test`, and
`tox -e py314-test` as valid 'test' tasks. These tasks build the project in an isolated environment and
run the project's unit and integration tests to verify that the project works as expected for each supported python
version.

Example tox.ini section:
```
[testenv:{py312, py313, py314}-test]
package = wheel
description =
    Runs unit and integration tests for each of the python versions listed in the task name and aggregates test coverage
    data. Uses 'loadgroup' balancing and all logical cores to optimize task runtime speed.
dependency_groups = dev
setenv = COVERAGE_FILE = reports{/}.coverage.{envname}
commands =
    pytest --import-mode=importlib --cov=ataraxis_automation --cov-config=pyproject.toml --cov-report=xml \
    --junitxml=reports/pytest.xml.{envname} -n logical --dist loadgroup
```

#### Coverage

Shell command: `tox -e coverage`

This task is used in conjunction with the 'test' task. It aggregates code coverage data for different python versions
and compiles it into an HTML report accessible by opening PROJECT_ROOT/reports/coverage_html/index.html in a browser.

The task also applies the project's coverage gate, which requires the test suite to cover 100% of the measured
statements. The gate is configured through the 'fail_under' option in the pyproject.toml file. Interface modules, such
as the CLI, stay outside the measured statements through the 'omit' list in the same file, and individual statements
that the test suite cannot reach are marked with the 'pragma: no cover' comment.

Every reporting command combines the coverage data files it finds, so all of them run with the '--keep-combined' flag
to preserve the per-version data files for the commands that follow. The 'tool.coverage.paths' section of the
pyproject.toml file lists both the POSIX and the Windows virtual environment layouts, so the data measured by each
'test' task merges into a single record per source file on every supported platform.

Example tox.ini section:
```
[testenv:coverage]
skip_install = true
description =
    Combines test-coverage data from multiple test runs (for different python versions) into a single html file and
    verifies that the combined data covers 100% of the measured statements. The file can be viewed by loading the
    'reports/coverage_html/index.html'. The task also merges the per-version JUnit test-result reports into
    'reports/pytest.xml' and writes an xml coverage report to the project root.
deps = ataraxis-automation==9.0.1
setenv = COVERAGE_FILE = reports/.coverage
depends = {py312, py313, py314}-test
commands =
    junitparser merge --glob reports/pytest.xml.* reports/pytest.xml
    coverage combine --keep
    coverage xml --fail-under=0 --keep-combined
    coverage html --fail-under=0 --keep-combined
    coverage report --keep-combined
```

#### Docs

Shell command: `tox -e docs`

Uses [Sphinx](https://www.sphinx-doc.org/en/master/) to automatically parse docstrings from source code and build the
API documentation for the project. This task relies on the configuration files stored inside the
PROJECT_ROOT/docs/source directory to define the generated documentation format. Built documentation can be viewed by
opening PROJECT_ROOT/docs/build/html/index.html in a browser.

Example tox.ini section for a pure-python project:
```
[testenv:docs]
description =
    Builds the API documentation from source code docstrings using Sphinx. The result can be viewed by loading
    'docs/build/html/index.html'.
depends = uninstall
deps = ataraxis-automation==9.0.1
commands =
    sphinx-build -b html -d docs/build/doctrees docs/source docs/build/html -j auto -v
```

***Note,*** C-extension projects use a slightly modified version of this task that uses
[Doxygen](https://www.doxygen.nl/) to parse doxygen-styled docstrings used in the C-code and
[breathe](https://breathe.readthedocs.io/en/latest/) to convert doxygen-generated XML files for C-code into a
Sphinx-compatible format. This allows C-extension projects to include both Python and C/C++ API documentation in the
same .html file. To support this behavior, the tox.ini file must include an additional command: `doxygen Doxyfile`.

Example tox.ini section for a C-extension project:
```
[testenv:docs]
description =
    Builds the API documentation from source code docstrings using Doxygen, Breathe and Sphinx. The result can be
    viewed by loading 'docs/build/html/index.html'.
depends = uninstall
deps = ataraxis-automation==9.0.1
allowlist_externals = doxygen
commands =
    doxygen Doxyfile
    sphinx-build -b html -d docs/build/doctrees docs/source docs/build/html -j auto -v
```

#### Build

Shell command: `tox -e build`

This task clears the project's 'dist' directory and then builds a source-code distribution (sdist) and a binary
distribution (wheel) for the project, so that artifacts built for an earlier version cannot be carried into the
'upload' task. These distributions can then be uploaded to GitHub or PyPI or shared with the intended audience through
any other means.
Pure-python projects use [hatchling](https://hatch.pypa.io/latest/) and [build](https://build.pypa.io/en/stable/) to
generate one source-code and one binary distribution. C-extension projects use
[cibuildwheel](https://cibuildwheel.pypa.io/en/stable/) to compile the C-code for all supported platforms and
architectures, building many binary distribution files alongside the source-code distribution generated via build.

Example tox.ini section for a pure-python project:
```
[testenv:build]
skip_install = true
description =
    Builds the project's source code distribution (sdist) and binary distribution (wheel), clearing the 'dist'
    directory beforehand so that artifacts built for an earlier version cannot be carried into the upload task.
deps = ataraxis-automation==9.0.1
allowlist_externals = docker
commands =
    python -c "import shutil; shutil.rmtree('dist', ignore_errors=True)"
    python -m build . --sdist
    python -m build . --wheel
```

Example tox.ini section for a C-extension project:
```
[testenv:build]
skip_install = true
description =
    Builds the project's source code distribution (sdist) and binary distribution (wheel), clearing the 'dist'
    directory beforehand so that artifacts built for an earlier version cannot be carried into the upload task.
deps = ataraxis-automation==9.0.1
allowlist_externals = docker
commands =
    python -c "import shutil; shutil.rmtree('dist', ignore_errors=True)"
    python -m build . --sdist
    cibuildwheel --output-dir dist --platform auto
```

#### Upload

Shell command: `tox -e upload`

Uploads the sdist and wheel files created by the 'build' task to [PyPI](https://pypi.org/). When this task runs for the
first time, it uses automation-cli to store the user-provided PyPI API token inside a .pypirc file kept in the shared
application directory. Every project developed on the same machine reuses that token, so it only has to be entered
once. Once uploaded, the project (library) becomes a valid target for `pip install LIBRARYNAME` commands.

***Warning!*** The .pypirc file stores an active API token. It is kept outside every project directory, so it stays out
of reach of the version control systems that track the projects using it.

***Note,*** projects that still keep a .pypirc file in their root directory have the token migrated to the shared file
the next time this task runs. The project-local file can be deleted once the migration is reported.

Example tox.ini section:
```
[testenv:upload]
skip_install = true
description =
    Uses twine to upload the wheel ('*.whl') and source ('*.tar.gz') distributions found inside the project's 'dist'
    directory to PyPI.
deps = ataraxis-automation==9.0.1
commands =
    automation-cli acquire-pypi-token {posargs:}
    automation-cli upload-project
```

#### Deploy

Shell command: `tox -e deploy`

Uploads the API documentation built by the 'docs' task to the project's [Netlify](https://www.netlify.com/) site. When
this task runs for the first time, it uses automation-cli to acquire two credentials. The API token is stored inside a
.netlifyrc file kept in the shared application directory, and the site identifier is stored inside the project's
.netlify-site file. Each deployment fully replaces the content served by the target site.

This task supports every project archetype that builds API documentation, including the C++ PlatformIO projects that
have no pyproject.toml or envs directory. It verifies the project root through the presence of the /src and /docs
directories and the tox.ini file.

***Note,*** this task uploads the documentation found inside the PROJECT_ROOT/docs/build/html directory. Run the 'docs'
task to build the documentation before calling this task. The task aborts with an error when the directory does not
contain an index.html file.

***Note,*** the site identifier accepts both the site's domain name, such as 'project-api-docs.netlify.app', and the
site's API (UUID) identifier. Full site URLs are also accepted and are reduced to the bare identifier before use. The
acquisition prompt offers the PROJECT_DIRECTORY_NAME-api-docs.netlify.app identifier as its default, derived from the
name of the project's root directory, which is the naming convention followed by nearly all projects. Use
`tox -e deploy -- --replace-site` to change the stored identifier.

***Note,*** Netlify API tokens are generated under 'User settings' → 'Applications' → 'Personal access tokens' in the
Netlify web interface. A single token authorizes deployments to every site owned by the account that generated it, so
one token is shared by all projects developed on the same machine.

***Note,*** projects that still keep a .netlifyrc file in their root directory have the token migrated to the shared
file and the site identifier migrated to the project's .netlify-site file the next time this task runs. The
project-local .netlifyrc file can be deleted once the migration is reported.

***Warning!*** The .netlifyrc file stores an active API token. It is kept outside every project directory, so it stays
out of reach of the version control systems that track the projects using it. The .netlify-site file stores no secret
and is committed to the repository, as the site it identifies differs for each project.

Example tox.ini section:
```
[testenv:deploy]
skip_install = true
description =
    Uploads the API documentation built by the 'docs' task to the project's Netlify site. Build the documentation with
    'tox -e docs' before calling this task.
deps = ataraxis-automation==9.0.1
commands =
    automation-cli acquire-netlify-token {posargs:}
    automation-cli deploy-docs
```

### Supported Mamba Environment Manipulation Tox Tasks

These tasks automate the repetitive work of managing project mamba environments during development. They assume that
validly configured mamba and uv distributions are installed and accessible from the shell of the machine that calls
these commands.

#### Install

Shell command: `tox -e install`

Installs the project into its development mamba environment. To allow installing prerelease packages, use
`tox -e install -- --prerelease`.

Example tox.ini section:
```
[testenv:install]
skip_install = true
deps = ataraxis-automation==9.0.1
depends =
    lint
    stubs
    {py312, py313, py314}-test
    coverage
    docs
    export
description = Builds and installs the project into its development mamba environment.
commands =
    automation-cli install-project --environment-name axa_dev {posargs:}
```

#### Uninstall

Shell command: `tox -e uninstall`

Removes the project from its development mamba environment.

Example tox.ini section:
```
[testenv:uninstall]
skip_install = true
deps = ataraxis-automation==9.0.1
description = Uninstalls the project from its development mamba environment.
commands =
    automation-cli uninstall-project --environment-name axa_dev
```

#### Create

Shell command: `tox -e create`

Creates the project's development mamba environment and installs project dependencies listed in the pyproject.toml file
into the environment. This task is intended to be used when setting up project development environments for new
platforms and architectures. The task assumes that all dependencies are stored using the Ataraxis framework format:
inside the general 'dependencies' section and the PEP 735 '[dependency-groups]' dev group. The legacy
'[project.optional-dependencies]' dev section is also supported. To allow installing prerelease packages, use
`tox -e create -- --prerelease`.

Example tox.ini section:
```
[testenv:create]
skip_install = true
deps = ataraxis-automation==9.0.1
description =
    Creates the project's development mamba environment using the requested python version and installs runtime and
    development project dependencies extracted from the pyproject.toml file.
commands =
    automation-cli create-environment --environment-name axa_dev --python-version 3.14 {posargs:}
```

#### Remove

Shell command: `tox -e remove`

Removes the project's development mamba environment. Primarily, this task is intended to be used to clean the local
system after project development is finished. ***Note,*** to reset the environment, use the 'provision' task instead
(see below).

Example tox.ini section:
```
[testenv:remove]
skip_install = true
deps = ataraxis-automation==9.0.1
description = Removes the project's development mamba environment.
commands =
    automation-cli remove-environment --environment-name axa_dev
```

#### Provision

Shell command: `tox -e provision`

This task is a combination of the 'remove' and 'create' tasks. It is designed to reset the project's development
environment by recreating it from scratch. Before removing the existing environment, the task verifies that the
replacement environment specification resolves. If it does not, the task aborts and leaves the existing environment in
place. This is used to both reset and actualize project development environments
to match the latest version of the pyproject.toml file dependency specification. To allow installing prerelease
packages, use `tox -e provision -- --prerelease`.

Example tox.ini section:
```
[testenv:provision]
skip_install = true
deps = ataraxis-automation==9.0.1
description =
    Provisions the project's development mamba environment by verifying that the new environment specification
    resolves, then removing and (re)creating the environment and installing the project dependencies into it.
commands =
    automation-cli provision-environment --environment-name axa_dev --python-version 3.14 {posargs:}
```

#### Export

Shell command: `tox -e export`

Exports the project's development environment as a .yml file. This task is used before distributing new versions of
the project to allow the target audience to generate an identical copy of the development environment using the
generated .yml file. This functionality is maintained for all Ataraxis framework projects.

Example tox.ini section:
```
[testenv:export]
skip_install = true
deps = ataraxis-automation==9.0.1
depends = uninstall
description = Exports the project's development mamba environment to the 'envs' project directory as a .yml file.
commands =
    automation-cli export-environment --environment-name axa_dev
```

#### Import

Shell command: `tox -e import`

Imports the project's development environment from its .yml file. If the environment does not exist, this
creates an identical copy of the environment stored in the .yml file. If the environment already exists, it is updated
using the .yml file. The update process is configured to prune any unused packages not found inside the .yml file.

Example tox.ini section:
```
[testenv:import]
skip_install = true
deps = ataraxis-automation==9.0.1
description =
    Creates or updates the project's development mamba environment using the .yml file stored in the 'envs' project
    directory.
commands =
    automation-cli import-environment --environment-name axa_dev
```

___

## API Documentation

See the [API documentation](https://ataraxis-automation-api-docs.netlify.app/) for the
detailed description of the methods and classes exposed by components of this library. ***Note,*** the documentation
also includes a list of all command-line interface functions and their arguments.

___

## Developers

This section provides installation, dependency, and build-system instructions for the developers that want to modify
the source code of this library.

### Installing the Project

***Note,*** this installation method requires **mamba version 2.3.2 or above**. Currently, all Ataraxis framework
automation pipelines require that mamba is installed through the [miniforge3](https://github.com/conda-forge/miniforge)
installer.

1. Download this repository to the local machine using the preferred method, such as git-cloning.
2. If the downloaded distribution is stored as a compressed archive, unpack it using the appropriate decompression tool.
3. `cd` to the root directory of the prepared project distribution.
4. Install the core Ataraxis framework development dependencies into the ***base*** mamba environment via the
   `mamba install tox uv tox-uv` command.
5. Use the `tox -e create` command to create the project-specific development environment followed by
   `tox -e install` command to install the project into that environment as a library.

### Additional Dependencies

In addition to installing the project and all user dependencies, install the following dependencies:

1. [Python](https://www.python.org/downloads/) distributions, one for each version supported by the developed project.
   Currently, this library supports the three latest stable versions. It is recommended to use a tool like
   [pyenv](https://github.com/pyenv/pyenv) to install and manage the required versions.
2. [Doxygen](https://doxygen.nl/), if the project uses C-extensions. This is necessary to build the API documentation
   for the C-code portion of the project.

### Development Automation

This project uses `tox` for development automation. The following tox environments are available:

| Environment          | Description                                                  |
|----------------------|--------------------------------------------------------------|
| `lint`               | Runs ruff formatting, ruff linting, and mypy type checking   |
| `stubs`              | Generates py.typed marker and .pyi stub files                |
| `{py312,...}-test`   | Runs the test suite via pytest for each supported Python     |
| `coverage`           | Aggregates test coverage and applies the 100% coverage gate  |
| `docs`               | Builds the API documentation via Sphinx                      |
| `build`              | Builds sdist and wheel distributions                         |
| `upload`             | Uploads distributions to PyPI via twine                      |
| `deploy`             | Uploads the built API documentation to Netlify               |
| `install`            | Builds and installs the project into its mamba environment   |
| `uninstall`          | Uninstalls the project from its mamba environment            |
| `create`             | Creates the project's mamba development environment          |
| `remove`             | Removes the project's mamba development environment          |
| `provision`          | Recreates the mamba environment from scratch                 |
| `export`             | Exports the mamba environment as a .yml file                 |
| `import`             | Creates or updates the mamba environment from a .yml file    |

Run any environment using `tox -e ENVIRONMENT`. For example, `tox -e lint`.

***Note,*** automation pipelines for this library have been modified from the implementation used in all other
projects, as they require this library to support their runtime. To avoid circular dependencies, the pipelines for
this library always compile and install the library from source code before running each automation task.

***Note,*** all pull requests for this project have to successfully complete the `tox` task before being merged.
To expedite the task's runtime, use the `tox --parallel` command to run some tasks in parallel.

### AI-Assisted Development

Claude Code skills and other AI development assets for this project are distributed through the
[ataraxis](https://github.com/Sun-Lab-NBB/ataraxis) marketplace as part of the **automation** plugin. Install the
plugin from the marketplace to make all associated skills and development tools available to compatible AI coding
agents. See the [ataraxis](https://github.com/Sun-Lab-NBB/ataraxis) README for the full list of available skills and
installation instructions.

### Automation Troubleshooting

Many packages used in `tox` automation pipelines (uv, mypy, ruff) and `tox` itself may experience runtime failures. In
most cases, this is related to their caching behavior. If an unintelligible error is encountered with any of the
automation components, deleting the corresponding cache directories (`.tox`, `.ruff_cache`, `.mypy_cache`, etc.)
manually or via a CLI command typically resolves the issue.

___

## Versioning

This project uses [semantic versioning](https://semver.org/). See the
[tags on this repository](https://github.com/Sun-Lab-NBB/ataraxis-automation/tags) for the available project releases.

___

## Authors

- Ivan Kondratyev ([Inkaros](https://github.com/Inkaros))

___

## License

This project is licensed under the Apache 2.0 License: see the [LICENSE](LICENSE) file for details.

___

## Acknowledgments

- All Sun lab [members](https://neuroai.github.io/sunlab/people) for providing the inspiration and comments during the
  development of this library.
- [click](https://github.com/pallets/click/) project for providing the low-level command-line-interface functionality
  for this project.
- The teams behind [pip](https://github.com/pypa/pip), [uv](https://github.com/astral-sh/uv),
  [conda](https://conda.org/), [mamba](https://github.com/mamba-org/mamba) and [tox](https://github.com/tox-dev/tox),
  which form the backbone of Ataraxis framework automation pipelines.
- The creators of all other dependencies and projects listed in the [pyproject.toml](pyproject.toml) file.
