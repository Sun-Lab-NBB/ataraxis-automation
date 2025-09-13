# ataraxis-automation

A Python library that supports tox-based development automation pipelines used by other Sun (NeuroAI) lab projects.

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
[tox](https://tox.wiki/en/latest/user_guide.html)-based project development automation suite that comes with every Sun 
Lab project. The CLI abstracts the project’s environment manipulation and facilitates mundane development tasks, such as
linting, typing, and documenting the source code API.

___

## Features

- Supports Windows, Linux, and macOS.
- Optimized for runtime speed by using mamba and uv for all environment management tasks.
- Compliments the extensive suite of tox environments and tasks used by all Sun lab projects to streamline development.
- GPL 3 License.

___

## Table of Contents

- [Dependencies](#dependencies)
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Developers](#developers)
- [Versioning](#versioning)
- [Authors](#authors)
- [License](#license)
- [Acknowledgements](#Acknowledgments)

___

## Dependencies

- [miniforge3](https://github.com/conda-forge/miniforge). This library expects that a miniforge3 distribution is 
  used to install and export the [mamba](https://github.com/mamba-org/mamba) environment manager to the host-system’s 
  PATH variable.
- [uv](https://docs.astral.sh/uv/). This library uses uv as the main package management engine and expects that uv is
  available from the system’s base Python environment.

***Note!*** Developers should see the [Developers](#developers) section for information on installing additional 
development dependencies.

___

## Installation

### Source

Note, installation from source is ***highly discouraged*** for everyone who is not an active project developer.

1. Download this repository to the local machine using the preferred method, such as git-cloning. Use one of the stable 
   releases that include precompiled binary and source code distribution (sdist) wheels.
2. ```cd``` to the root directory of the project.
3. Run ```python -m pip install .``` to install the project. Alternatively, if using a distribution with precompiled
   binaries, use ```python -m pip install WHEEL_PATH```, replacing 'WHEEL_PATH' with the path to the wheel file.

### pip

Use the following command to install the library using pip: ```pip install ataraxis-automation```.

___

## Usage
*__Note!__* The library expects the managed project to use a specific configuration and file structure. If any CLI 
command terminates with an error, read all information printed in the terminal to determine whether the error is due to 
an invalid project configuration or file structure.

### Automation Command-Line Interface
All library functions designed to be called by end-users are exposed through the 'automation-cli' Command Line 
Interface (CLI). This CLI is automatically exposed by installing the library into a Python environment.

#### Automation-CLI
All functions supplied by the library are accessible by calling ```automation-cli``` from a Python environment where 
the library is installed. For example:
- Use ```automation-cli --help``` to verify that the CLI is available and to see the list of supported commands.
- Use ```automation-cli COMMAND-NAME --help``` to display additional information about a specific command. For example:
  ```automation-cli import-environment --help```.

#### Tox Integration
This library is intended to be used via [tox](https://tox.wiki/en/latest/user_guide.html) tasks (environments). To use 
any of the exposed CLI’s commands as part of a tox environment, add it to the 'commands' section of the tox.ini:
```
[testenv:create]
deps =
    ataraxis-automation==6.1.0
commands =
    automation-cli create-environment --environment_name axa_dev --python_version 3.13
```

See the [tox.ini file](tox.ini) configuration file for the most up-to-date project development automation 
suite used in the Sun lab. For the most up-to-date C-extension project automation suite, see the tox.ini file of the
[ataraxis-time](https://github.com/Sun-Lab-NBB/ataraxis-time) library.

#### Additional Command Arguments
*__Note!__* Many sub-commands of the CLI have additional flags and arguments that can be used to further customize
their runtime. Consult the [API documentation](#api-documentation) for the list of additional runtime flags for all 
supported CLI commands.

### Supported Checkout Tox Tasks
This library is tightly linked to the environments defined in the [tox.ini file](tox.ini) configuration file.

***Warning!*** Commands listed in this section may and frequently are modified based on the specific needs of each 
Sun lab project. This section is *__not__* a replacement for studying the tox.ini file for each Sun lab project.

Most commands in this section are designed to be executed together as part of the ```tox``` CLI command. These commands
are referred to as 'checkout' tasks and must run successfully for any pull request candidate before it is merged into 
the main branch of each Sun lab project.

#### Lint
Shell command: ```tox -e lint```

Uses [ruff](https://github.com/astral-sh/ruff) and [mypy](https://github.com/python/mypy) to statically analyze and, 
where possible, fix code formatting, typing, and problematic use patterns. As part of its runtime, this task uses 
automation-cli to remove existing stub (.pyi) files from the source directories, as they sometimes interfere with 
type-checking.

Example tox.ini section:
```
[testenv: lint]
description =
    Runs static code formatting, style, and typing checkers. Follows the configuration defined in the pyproject.toml
    file.
extras = dev
basepython = py311
commands =
    automation-cli purge-stubs
    ruff format
    ruff check --fix ./src
    mypy ./src
```

#### Stubs
Shell command: ```tox -e stubs```

Uses [stubgen](https://mypy.readthedocs.io/en/stable/stubgen.html) to generate stub (.pyi) files and distributes them
via automation-cli to the appropriate levels of the project’s source code hierarchy. As part of this process, 
automation-cli also ensures that there is a 'py.typed' marker file in the highest library directory. This is required 
for type-checkers like mypy to recognize the library as 'typed' and process it during type-checking tasks.

Example tox.ini section:
```
description = Generates the py.typed marker and the .pyi stub files using the project's wheel distribution.
depends = lint
extras = dev
commands =
    automation-cli process-typed-markers
    stubgen -o stubs --include-private -p ataraxis_automation -v
    automation-cli process-stubs
    ruff format
    ruff check --select I --fix ./src
```

#### Test
Shell command: ```tox -e pyXXX-test``` 

This task is executed for all python versions supported by each project. For example, ataraxis-automation supports 
versions 3.11, 3.12, and 3.13. Therefore, it has ```tox -e py311-test```, ```tox -e py312-test```, and 
```tox -e py313-test``` as valid 'test' tasks. These tasks build the project in an isolated environment and 
run the project’s unit and integration tests to verify that the project works as expected for each supported python 
version.

Example tox.ini section:
```
[testenv: {py311, py312, py313}-test]
package = wheel
description =
    Runs unit and integration tests for each of the python versions listed in the task name and aggregates test coverage
    data. Uses 'loadgroup' balancing and all logical cores to optimize task runtime speed.
extras = dev
setenv = COVERAGE_FILE = reports{/}.coverage.{envname}
commands =
    pytest --import-mode=append --cov=ataraxis_automation --cov-config=pyproject.toml --cov-report=xml \
    --junitxml=reports/pytest.xml.{envname} -n logical --dist loadgroup
```

#### Coverage
Shell command: ```tox -e coverage``` 

This task is used in conjunction with the 'test' task. It aggregates code coverage data for different python versions 
and compiles it into an HTML report accessible by opening PROJECT_ROOT/reports/coverage_html/index.html in a browser.

Example tox.ini section:
```
[testenv:coverage]
skip_install = true
description =
    Combines test-coverage data from multiple test runs (for different python versions) into a single html file. The
    file can be viewed by loading the 'reports/coverage_html/index.html'.
deps = ataraxis-automation==6.1.0
setenv = COVERAGE_FILE = reports/.coverage
depends = {py311, py312, py313}-test
commands =
    junitparser merge --glob reports/pytest.xml.* reports/pytest.xml
    coverage combine --keep
    coverage xml
    coverage html
```

#### Docs
Shell command: ```tox -e docs```

Uses [Sphinx](https://www.sphinx-doc.org/en/master/) to automatically parse docstrings from source code and build the 
API documentation for the project. This task relies on the configuration files stored inside the 
PROJECT_ROOT/docs/source directory to define the generated documentation format. Built documentation can be viewed by 
opening PROJECT_ROOT/docs/build/html/index.html in a browser.

Example tox.ini section for a pure-python project:
```
description =
    Builds the API documentation from source code docstrings using Sphinx. The result can be viewed by loading
    'docs/build/html/index.html'.
depends = uninstall
deps = ataraxis-automation==6.1.0
commands =
    sphinx-build -b html -d docs/build/doctrees docs/source docs/build/html -j auto -v
```

*__Note!__* C-extension projects use a slightly modified version of this task that uses
[Doxygen](https://www.doxygen.nl/) to parse doxygen-styled docstrings used in the C-code and 
[breathe](https://breathe.readthedocs.io/en/latest/) to convert doxygen-generated XML files for C-code into a 
Sphinx-compatible format. This allows C-extension projects to include both Python and C/C++ API documentation in the 
same .html file. To support this behavior, the tox.ini file must include an additional command: ```doxygen Doxyfile```.

Example tox.ini section for a C-extension project:
```
description =
    Builds the API documentation from source code docstrings using Sphinx. The result can be viewed by loading
    'docs/build/html/index.html'.
depends = uninstall
deps = ataraxis-automation==6.1.0
commands =
    doxygen Doxyfile
    sphinx-build -b html -d docs/build/doctrees docs/source docs/build/html -j auto -v
```

#### Build
Shell command: ```tox -e build```

This task builds a source-code distribution (sdist) and a binary distribution (wheel) for the project. These 
distributions can then be uploaded to GitHub or PyPI or shared with the intended audience through any other means. 
Pure-python projects use [hatchling](https://hatch.pypa.io/latest/) and [build](https://build.pypa.io/en/stable/) to 
generate one source-code and one binary distribution. C-extension projects use 
[cibuildwheel](https://cibuildwheel.pypa.io/en/stable/) to compile the C-code for all supported platforms and 
architectures, building many binary distribution files alongside source-code distribution generated via build.

Example tox.ini section for a pure-python project:
```
[testenv:build]
skip_install = true
description = Builds the project's source code distribution (sdist) and binary distribution (wheel).
deps = ataraxis-automation==6.1.0
allowlist_externals = docker
commands =
    python -m build . --sdist
    python -m build . --wheel
```

Example tox.ini section for a C-extension project:
```
[testenv:build]
skip-install = true
description =
    Builds the project's source code distribution (sdist) and compiles and assembles binary wheels for all 
    supported platform architectures.
deps = ataraxis-automation==6.1.0
allowlist_externals = docker
commands =
    python -m build . --sdist
    cibuildwheel --output-dir dist --platform auto
```

#### Upload
Shell command: ```tox -e upload```

Uploads the sdist and wheel files created by the 'build' task to [PyPI](https://pypi.org/). When this task runs for the 
first time, it uses automation-cli to generate a .pypirc file and store the user-provided PyPI API token in that file.
This allows reusing the token for later uploads, streamlining the process. Once uploaded, the project (library) becomes
a valid target for ```pio install LIBRARYNAME``` commands.

Example tox.ini section:
```
[testenv:upload]
skip_install = true
description = Uses twine to upload all files inside the project's 'dist' directory to PyPI.
deps = ataraxis-automation==6.1.0
allowlist_externals = distutils
commands =
    automation-cli acquire-pypi-token {posargs:}
    twine upload dist/* --skip-existing --config-file .pypirc
```

### Supported Mamba Environment Manipulation Tox Tasks
These tasks were added to automate repetitive tasks associated with managing project mamba environments during 
development. They assume that there is a validly configured mamba distribution installed and accessible from the
shell of the machine that calls these commands.


#### Install
Shell command: ```tox -e install```

Installs the project into its development mamba environment.

Example tox.ini section:
```
[testenv:install]
skip_install = true
deps = ataraxis-automation==6.1.0
depends =
    lint
    stubs
    {py311, py312, py313}-test
    coverage
    docs
    export
description = Builds and installs the project into the its' development mamba environment.
commands =
    automation-cli install-project --environment_name axa_dev
```

#### Uninstall
Shell command: ```tox -e uninstall```

Removes the project from its development mamba environment.

Example tox.ini section:
```
[testenv:uninstall]
skip_install = true
deps = ataraxis-automation==6.1.0
description = Uninstalls the project from its' development mamba environment.
commands =
    automation-cli uninstall-project --environment_name axa_dev
```

#### Create
Shell command: ```tox -e create```

Creates the project’s development mamba environment and installs project dependencies listed in the pyproject.toml file 
into the environment. This task is intended to be used when setting up project development environments for new 
platforms and architectures. The task assumes that all dependencies are stored using the Sun Lab format: inside the 
general 'dependencies' section and the optional 'dev' dependency section.

Example tox.ini section:
```
[testenv:create]
skip_install = true
deps = ataraxis-automation==6.1.0
description =
    Creates the project's development mamba environment using the requested python version and installs runtime and 
    development project dependencies extracted from the pyproject.toml file.
commands =
    automation-cli create-environment --environment_name axa_dev --python_version 3.13
```

#### Remove
Shell command: ```tox -e remove```

Removes the project’s development mamba environment. Primarily, this task is intended to be used to clean the local 
system after project development is finished. Note; to reset the environment, it is advised to use the 'provision' task 
instead (see below).

Example tox.ini section:
```
[testenv:remove]
skip_install = true
deps = ataraxis-automation==6.1.0
description = Removes the project's development mamba environment.
commands =
    automation-cli remove-environment --environment_name axa_dev
```

#### Provision
Shell command: ```tox -e provsion```

This task is a combination of the 'remove' and 'create' tasks. It is designed to reset the project’s development 
environment by recreating it from scratch. This is used to both reset and actualize project development environments 
to match the latest version of the pyproject.toml file dependency specification.

Example tox.ini section:
```
[testenv:provision]
skip_install = true
deps = ataraxis-automation==6.1.0
description = Provisions the project's development mamba environment by removing and (re)creating the environment.
commands =
    automation-cli provision-environment --environment_name axa_dev --python_version 3.13
```

#### Export
Shell command: ```tox -e export```

Exports the project’s development environment as a .yml and spec.txt file. This task is used before distributing new 
versions of the project to allow the target audience to generate an identical copy of the development environment using
the generated .yml and spec.txt files. While 'create' and 'provision' tasks make this largely obsolete, this 
functionality is maintained for all Sun lab projects.

Example tox.ini section:
```
[testenv:export]
skip_install = true
deps = ataraxis-automation==6.1.0
description =
    Exports the project's development mamba environment to the 'envs' project directory as a .yml file and as a
    spec.txt with revision history.
commands =
    automation-cli export-environment --environment_name axa_dev
```

#### Import
Shell command: ```tox -e import```

Imports the project’s development environment from it’s '.yml' file. If the environment does not exist, this 
creates an identical copy of the environment stored in the .yml file. If the environment already exists, it is updated 
using the '.yml' file. The update process is configured to prune any unused packages not found inside the '.yml' file.

Example tox.ini section:
```
[testenv:import]
skip_install = true
deps = ataraxis-automation==6.1.0
description =
    Creates or updates the project's development mamba environment using the .yml file stored in the 'envs' project 
    directory.
commands =
    automation-cli import-environment --environment_name axa_dev
```

___

## API Documentation

See the [API documentation](https://ataraxis-automation-api-docs.netlify.app/) for the
detailed description of the methods and classes exposed by components of this library. __*Note*__ the documentation
also includes a list of all command-line interface functions and their arguments.

___

## Developers

This section provides installation, dependency, and build-system instructions for project developers.

### Installing the Project

1. Download this repository to the local machine using the preferred method, such as git-cloning.
2. ```cd``` to the root project directory.
3. Install core Sun lab development dependencies into the 'base' mamba environment via the 
   ```mamba install tox uv tox-uv``` command.
4. Use the ```tox -e create``` command to create the project-specific development environment followed by 
   ```tox -e install``` command to isntall the project into that environment as a library.

### Additional Dependencies

In addition to installing the project and all user dependencies, install the following dependencies:

1. [Python](https://www.python.org/downloads/) distributions, one for each version supported by the developed project. 
   Currently, this library supports the three latest stable versions. It is recommended to use a tool like 
   [pyenv](https://github.com/pyenv/pyenv).
2. [Doxygen](https://doxygen.nl/), if the project uses c-extensions. This is necessary to build the API documentation
   for the C-code portion of the project.

### Development Automation

This project comes with a fully configured set of automation pipelines implemented using 
[tox](https://tox.wiki/en/latest/user_guide.html). Check [tox.ini file](tox.ini) for details about 
available pipelines and their implementation. Alternatively, call ```tox list``` from the root directory of the project
to see the list of available tasks. __*Note*__, automation pipelines for this library have been modified from the 
implementation used in all other projects, as they require this library to support their runtime. To avoid circular 
dependencies, the pipelines for this library always compile and install the library from source code before running 
each automation task.

**Note!** All pull requests for this project have to successfully complete the ```tox``` task before being merged. 
To expedite the task’s runtime, use ```tox --parallel``` command to run some tasks in-parallel.

### Automation Troubleshooting

Many packages used in 'tox' automation pipelines (uv, mypy, ruff) and 'tox' itself may experience runtime failures. In 
most cases, this is related to their caching behavior. If an unintelligible error is encountered with 
any of the automation components, deleting the corresponding .cache (.tox, .ruff_cache, .mypy_cache, etc.) manually  
or via a CLI command typically solves the issue.

___

## Versioning

This project uses [semantic versioning](https://semver.org/). For the versions available, see the 
[tags on this repository](https://github.com/Sun-Lab-NBB/ataraxis-automation/tags).

---

## Authors

- Ivan Kondratyev ([Inkaros](https://github.com/Inkaros))

___

## License

This project is licensed under the GPL3 License: see the [LICENSE](LICENSE) file for details.

___

## Acknowledgments

- All Sun Lab [members](https://neuroai.github.io/sunlab/people) for providing the inspiration and comments during the
  development of this library.
- [click](https://github.com/pallets/click/) project for providing the low-level command-line-interface functionality 
  for this project.
- The teams behind [pip](https://github.com/pypa/pip), [uv](https://github.com/astral-sh/uv), 
  [conda](https://conda.org/), [mamba](https://github.com/mamba-org/mamba) and [tox](https://github.com/tox-dev/tox), 
  which form the backbone of Sun lab automation pipelines.
- The creators of all other projects that are listed in the [pyproject.toml](pyproject.toml) file and used in automation
  pipelines across all Sun Lab projects.
