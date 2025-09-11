# ataraxis-automation

A Python library that provides tools that support tox-based development automation pipelines used by other 
Sun (NeuroAI) lab projects.

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

This library is one of the two 'base' dependency libraries used by every other Sun lab project (the other being 
[ataraxis-base-utilities](https://github.com/Sun-Lab-NBB/ataraxis-base-utilities)). It exposes a command-line interface
(automation-cli) that can be used through the [tox-based](https://tox.wiki/en/latest/user_guide.html) project
development automation suite that comes with every Sun Lab project to streamline project development.

The commands from this library generally fulfill two major roles. First, they are used to set up, support the runtime 
of, or clean up after third-party packages (ruff, mypy, etc.) used in tox project-management tasks. Second, they 
automate most operations with mamba (conda) environments, such as creating the environment and installing the project 
and its dependencies.

The library can be used as a standalone module, but it is primarily designed to integrate with other Sun lab projects,
providing development automation functionality. Therefore, it may require either adopting and modifying a 
tox automation suite from one of the lab projects or significant refactoring to work with non-lab projects.

___

## Features

- Supports Windows, Linux, and OSx.
- Optimized for runtime speed by using mamba and uv over conda and pip.
- Compliments the extensive suite of tox-automation tasks used by all Sun lab projects.
- Pure-python API.
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

For users, all library dependencies are installed automatically for all supported installation methods
(see [Installation](#installation) section). For developers, see the [Developers](#developers) section for
information on installing additional development dependencies.

___

## Installation

### Source

1. Download this repository to the local machine using the preferred method, such as git-cloning. Use one of the stable 
   releases that include precompiled binary and source code distribution (sdist) wheels.
2. ```cd``` to the root directory of the project.
3. Run ```python -m pip install .``` to install the project. Alternatively, if using a distribution with precompiled
   binaries, use ```python -m pip install WHEEL_PATH```, replacing 'WHEEL_PATH' with the path to the wheel file.

### PIP

Use the following command to install the library using PIP: ```pip install ataraxis-automation```.

___

## Usage
*__Note!__* The library expects the managed project to follow a specific configuration and layout. If any CLI script 
terminates with an error, read all information printed in the terminal to determine whether the error is due to an 
invalid project configuration or filesystem layout.

### Automation Command-Line Interface
All library functions designed to be called by end-users are exposed through the 'automation-cli' Command Line 
Interface (CLI). This CLI is automatically exposed by installing the library into a Python environment.

#### Automation-CLI
While the preferred use case for this library is via 'tox' tasks, all functions supplied by the library are accessible 
by calling ```automation-cli``` from the Python environment that has the library installed. For example:
- Use ```automation-cli --help``` to verify that the CLI is available and to see the list of supported commands.
- Use ```automation-cli COMMAND-NAME --help``` to display additional information about a specific command. For example:
  ```automation-cli import-environment --help```.

#### Tox automation
This library is intended to be used via 'tox' tasks (environments). To use any of the library CLI commands as part of a 
tox 'task,' add it to the 'commands' section of the tox.ini:
```
[testenv:create]
deps =
    ataraxis-automation==6.0.0
description =
    Creates the mamba environment using the requested python version and installs runtime and development project
    dependencies extracted from the pyproject.toml file into the environment. Does not install the project library.
commands =
    automation-cli create-environment --environment_name axa_dev --python_version 3.13
```

#### Command-specific flags
*__Note!__* Many sub-commands of the CLI have additional flags and arguments that can be used to further customize
their runtime. Consult the API documentation for the list of additional runtime flags for all supported CLI commands.

### Intended CLI use pattern
All CLI commands are intended to be used through tox pipelines. The most recent version of Sun Lab tox configuration
is always available from this libraries’ [tox.ini file](tox.ini). Since version 6.0.0, this library is designed to be 
the sole dependency for most tox tasks, its tox.ini file is always the most up to date and feature-complete compared 
to all other Sun Lab projects. The only exception to this rule is the C-extension projects. For the most up-to-date 
tox.ini configuration for Sun lab C-extension projects, see the 
[ataraxis-time](https://github.com/Sun-Lab-NBB/ataraxis-time) library.

Any well-maintained Sun Lab project comes with an up-to-date tox configuration that automates most 'meta' development 
steps, such as code formatting, project testing, and project distribution. Primarily, this allows all contributors 
working on any Sun lab projects to abide by the same standards and practices, in addition to streamlining many of the 
routine project maintenance tasks.

### Available 'tox' commands
This library is tightly linked to the 'tox' configuration. Most 'tox' tasks used in the Sun lab either use some 
functions from this library in addition to external packages or entirely consist of calling functions from this library.

Note that commands listed here may and frequently are modified based on the specific needs of each project that 
uses them. Therefore, this section is *__not__* a replacement for studying the tox.ini file for each Sun lab project.

Most of the commands in this section are designed to be executed together (some sequentially, some in-parallel) when
a general ```tox``` command is used. These are considered 'checkout' tasks, and they generally cover the things that 
need to be present for a commit to be pushed to the main branch of any Sun Lab project.

#### Lint
Shell command: ```tox -e lint```

Uses [ruff](https://github.com/astral-sh/ruff) and [mypy](https://github.com/python/mypy) to statically analyze and, 
where possible, fix code formatting, typing, and problematic use patterns. This ensures the code is formatted according 
to Sun lab standards and does not contain easily identifiable problematic use patterns, such as type violations. As part
of its runtime, this task uses automation-cli to remove existing stub (.pyi) files from the source folders, as they 
interfere with type-checking.

Example tox.ini section:
```
[testenv: lint]
description =
    Runs static code formatting, style, and typing checkers. Mypy may not always work properly until py.typed marker is
    added the first time the 'stubs' task is executed.
extras = dev
deps = ataraxis-automation==6.0.0
basepython = py311
commands =
    automation-cli purge-stubs
    ruff format
    ruff check --fix ./src
    mypy ./src
```

#### Stubs
Shell command: ```tox -e stubs```

Uses [stubgen](https://mypy.readthedocs.io/en/stable/stubgen.html) to generate stub (.pyi) files and distribute them
via automation-cli to the appropriate levels of the library source code hierarchy. This is necessary to support static 
type-checking for projects that use the library. As part of that process, automation-cli also ensures that there is a 
'py.typed' marker file in the highest library directory. This is required for type-checkers like mypy to recognize the 
library as 'typed' and process it during type-checking tasks.

Example tox.ini section:
```
[testenv: stubs]
description =
    Generates the py.typed marker and the stub files using the built library wheel. Formats the stubs with ruff before
    moving them to appropriate source sub-directories.
depends = lint
deps = ataraxis-automation==6.0.0
commands =
    automation-cli process-typed-markers
    stubgen -o stubs --include-private -p ataraxis_automation -v
    automation-cli process-stubs
    ruff format
    ruff check --select I --fix ./src
```

#### Test
Shell command: ```tox -e pyXXX-test``` 

This task is available for all python versions supported by each project. For example, ataraxis-automation supports 
versions 3.11, 3.12, and 3.13. Therefore, it has ```tox -e py311-test```, ```tox -e py312-test``` and 
```tox -e py313-test``` as valid 'test' tasks. These tasks are used to build the project in an isolated environment and 
run the tests expected to be located inside the project_root/tests directory to verify the project works as expected 
for each python version. This is especially relevant for C-extension projects that compile code for each supported 
python version and platforms combination.

Example tox.ini section:
```
[testenv: {py311, py312, py313}-test]
package = wheel
description =
    Runs unit and integration tests for each of the python versions listed in the task name. Uses 'loadgroup' balancing
    and all logical cores to optimize runtime speed while allowing manual control over which cores execute tasks (see
    pytest-xdist documentation).
deps = ataraxis-automation==6.0.0
setenv =
    COVERAGE_FILE = reports{/}.coverage.{envname}
commands =
    pytest --import-mode=append --cov=ataraxis_automation --cov-config=pyproject.toml --cov-report=xml \
    --junitxml=reports/pytest.xml.{envname} -n logical --dist loadgroup
```

#### Coverage
Shell command: ```tox -e coverage``` 

This task is used in conjunction with the 'test' task. It aggregates code coverage data for different python versions 
and compiles it into an HTML report accessible by opening project_root/reports/coverage_html/index.html in a browser.

Example tox.ini section:
```
[testenv:coverage]
skip_install = true
description =
    Combines test-coverage data from multiple test runs (for different python versions) into a single html file. The
    file can be viewed by loading the 'reports/coverage_html/index.html'.
deps = ataraxis-automation==6.0.0
setenv = COVERAGE_FILE = reports/.coverage
depends = {py311, py312, py313}-test
commands =
    junitparser merge --glob reports/pytest.xml.* reports/pytest.xml
    coverage combine --keep
    coverage xml
    coverage html
```

#### Doxygen
Shell command: ```tox -e doxygen```

*__Note!__* This task is only used in C-extension projects.

This task is unique to Sun lab C-extension projects (projects that contain compiled c / c++ code). It uses 
[Doxygen](https://www.doxygen.nl/) to parse doxygen-styled docstrings used in the C-code to make them accessible to 
[Sphinx](https://www.sphinx-doc.org/en/master/) (used as part of the 'docs' task). This automatically generates the 
C/C++ API documentation and bundles it with Python API documentation via Sphinx.

Example tox.ini section:
```
[testenv:doxygen]
skip_install = true
description =
    Generates C++ / C source code documentation using Doxygen. This assumes the source code uses doxygen-compatible
    docstrings and that the root directory contains a Doxyfile that minimally configures Doxygen runtime.
allowlist_externals = doxygen
depends = uninstall
commands =
    doxygen Doxyfile
```

#### Docs
Shell command: ```tox -e docs```

Uses [Sphinx](https://www.sphinx-doc.org/en/master/) to automatically parse docstrings from source code and use them 
to build API documentation for the project. C-extension projects use a slightly modified version of this task that uses
[breathe](https://breathe.readthedocs.io/en/latest/) to convert doxygen-generated XML files for C-code into a format 
that Sphinx can parse. This way, C-extension projects can include both Python and C/C++ API documentation in the same 
.html file. This task relies on the configuration files stored inside /project_root/docs/source folder to define 
the generated documentation format. Built documentation can be viewed by opening project_root/docs/build/html/index.html
in a browser.

Example tox.ini section:
```
description =
    Builds the API documentation from source code docstrings using Sphinx. The result can be viewed by loading
    'docs/build/html/index.html'.
depends = 
    uninstall
    doxygen
deps = ataraxis-automation==6.0.0
commands =
    sphinx-build -b html -d docs/build/doctrees docs/source docs/build/html -j auto -v
```

#### Build
Shell command: ```tox -e build```

This task differs for C-extension and pure-python projects. In both cases, it builds a source-code distribution (sdist)
and a binary distribution (wheel) for the project. These distributions can then be uploaded to GitHub or PyPI 
for further distribution or shared with other people manually. Pure-python projects use 
[hatchling](https://hatch.pypa.io/latest/) and [build](https://build.pypa.io/en/stable/) to generate
one source-code and one binary distribution. C-extension projects use 
[cibuildwheel](https://cibuildwheel.pypa.io/en/stable/) to compile C-code for all supported platforms and 
architectures, building many binary distribution files alongside source-code distribution generated via build.

Example tox.ini section for a pure-python project:
```
[testenv:build]
skip-install = true
description =
    Builds the source code distribution (sdist) and the binary distribution package (wheel). Use 'upload' task to
    subsequently upload built wheels to PIP.
deps = ataraxis-automation==6.0.0
allowlist_externals =
    docker
commands =
    python -m build . --sdist
    python -m build . --wheel
```

Example tox.ini section for a C-extension project:
```
[testenv:build]
skip-install = true
description =
    Builds the source code distribution (sdist) and compiles and assembles binary wheels for all host-platform 
    architectures supported by the library. Use 'upload' task to subsequently upload built wheels to PIP.
deps = ataraxis-automation==6.0.0
allowlist_externals =
    docker
commands =
    python -m build . --sdist
    cibuildwheel --output-dir dist --platform auto
```

#### Upload
Shell command: ```tox -e upload```

Uploads the sdist and wheel files created by the 'build' task to [PyPI](https://pypi.org/). When this task runs for the 
first time, it uses automation-cli to generate a .pypirc file and store a user-provided PyPI API token in that file.
This allows reusing the token for later uploads, streamlining the process. The task is configured to skip uploading
already uploaded files to avoid errors. Once uploaded, the project (library) becomes a valid target for 'pip install' as
a means of distribution.

Example tox.ini section:
```
[testenv:upload]
skip_install = true
description =
    Uses twine to upload all files inside the '/dist' folder to pip, ignoring any files that are already uploaded.
    Uses API token stored in '.pypirc' file or provided by user to authenticate the upload.
deps = ataraxis-automation==6.0.0
allowlist_externals =
    distutils
commands =
    automation-cli acquire-pypi-token {posargs:}
    twine upload dist/* --skip-existing --config-file .pypirc
```

### Conda-environment manipulation tox commands
*__Note!__* These commands were added to automate repetitive tasks associated with managing development mamba 
environments. They assume that there is a validly configured mamba distribution installed and accessible from the
shell of the machine that calls these commands.


#### Install
Shell command: ```tox -e install```

Installs the project into the requested mamba environment. This task is used to build and install the project into the 
project development environment. This is a prerequisite for manually running and testing projects that are being 
actively developed. During general 'tox' runtime, this task is used to (re)install the project into the
project environment as necessary to avoid collisions with certain 'checkout' tasks, such as exporting the snapshot of 
the development environment as a .yml file.

Example tox.ini section:
```
[testenv:install]
skip_install = true
deps = ataraxis-automation==6.0.0
depends =
    lint
    stubs
    {py311, py312, py313}-test
    coverage
    docs
    export
description =
    Builds and installs the project into the specified mamba environment. The environment must already exist for this
    task to run as expected.
commands =
    automation-cli install-project --environment_name axa_dev
```

#### Uninstall
Shell command: ```tox -e uninstall```

Removes the project from the requested environment. This task is used to remove the project from the environment before 
exporting it as a .yml file to prevent the development environment depending on the unreleased project version.

Example tox.ini section:
```
[testenv:uninstall]
skip_install = true
deps = ataraxis-automation==6.0.0
description =
    Uninstalls the project from the specified mamba environment. If the environment does not exist this task silently
    succeeds.
commands =
    automation-cli uninstall-project --environment_name axa_dev
```

#### Create
Shell command: ```tox -e create```

Creates the requested mamba environment and installs project dependencies listed in pyproject.toml into the environment.
This task is intended to be used when setting up project development environments for new platforms and architectures. 
To work as intended, it uses automation-cli to parse the contents of tox.ini and pyproject.toml files to generate a 
list of project dependencies. It assumes that dependencies are stored using Sun Lab format: inside the general 
'dependencies' section and the optional 'dev' dependency section.

Example tox.ini section:
```
[testenv:create]
skip_install = true
deps = ataraxis-automation==6.0.0
description =
    Creates the mamba environment using the requested python version and installs runtime and development project
    dependencies extracted from the pyproject.toml file into the environment. Does not install the project library.
commands =
    automation-cli create-environment --environment_name axa_dev --python_version 3.13
```

#### Remove
Shell command: ```tox -e remove```

Removes the project’s mamba environment. Primarily, this task is intended to be used to clean the local system 
after the development is finished. Note; to reset the environment, it is advised to use the 'provision' task instead
(see below)

Example tox.ini section:
```
[testenv:remove]
skip_install = true
deps = ataraxis-automation==6.0.0
description =
    Removes the requested mamba environment.
commands =
    automation-cli remove-environment --environment_name axa_dev
```

#### Provision
Shell command: ```tox -e provsion```

This task is a combination of the 'remove' and 'create' tasks that reset environments by recreating them from
scratch. This can be used to both reset and actualize project development environments to match the latest version of 
the .toml file dependency specification.

Example tox.ini section:
```
[testenv:provision]
skip_install = true
deps = ataraxis-automation==6.0.0
description =
    Provisions the requested mamba environment by removing and (re)creating the environment.
commands =
    automation-cli provision-environment --environment_name axa_dev --python_version 3.13
```

#### Export
Shell command: ```tox -e export```

Exports the target development environment as a .yml and spec.txt file. This task is used before distributing new 
versions of the project. This allows contributors and end-users to generate an identical copy of the development 
environment and install the project into that environment. While 'create' and 'provision' tasks make this largely 
obsolete, this functionality is maintained for all Sun lab projects.

Example tox.ini section:
```
[testenv:export]
skip_install = true
deps = ataraxis-automation==6.0.0
description =
    Exports the requested mamba environment to the 'envs' folder as a .yml file and as a spec.txt with revision history.
commands =
    automation-cli export-environment --environment_name axa_dev
```

#### Import
Shell command: ```tox -e import```

Imports the project development environment from an available '.yml' file. If the environment does not exist, this 
creates an identical copy of the environment stored in the .yml file. If the environment already exists, it is instead
updated using the '.yml' file. The update process is configured to prune any unused packages not found inside the 
'.yml' file. This can be used to clone or actualize the project development environment from a file distributed via the
'export' task.

Example tox.ini section:
```
[testenv:import]
skip_install = true
deps = ataraxis-automation==6.0.0
description =
    Discovers and imports (installs) a new or updates an already existing mamba environment using the .yml file
    stored in the 'envs' directory.
commands =
    automation-cli import-environment --environment_name axa_dev
```

___

## API Documentation

See the [API documentation](https://ataraxis-automation-api-docs.netlify.app/) for the
detailed description of the methods and classes exposed by components of this library. __*Note*__ the documentation
also includes a list of all command-line interface functions and their arguments exposed during library installation.

___

## Developers

This section provides installation, dependency, and build-system instructions for the developers that want to
modify the source code of this library. Additionally, it contains instructions for recreating the conda environments
that were used during development from the included .yml files.

### Installing the library

1. Download this repository to the local machine using the preferred method, such as git-cloning.
2. ```cd``` to the root directory of the project.
3. Install development dependencies. There are multiple ways of satisfying this requirement:
    1. **_Preferred Method:_** Use mamba, uv, or pip to install
       [tox](https://tox.wiki/en/latest/user_guide.html) or use an environment that has it installed and
       call ```tox -e import``` to automatically import the os-specific development environment included with the
       project source code. Alternatively, use ```tox -e create``` to create the environment from scratch and 
       automatically install the necessary dependencies using the pyproject.toml file. See the 
       [environments](#environments) section for other environment installation methods.
    2. Run ```python -m pip install .'[dev]'``` command to install development dependencies and the library using 
       pip. Some platforms may require a slightly modified version of this command: 
       ```python -m pip install .[dev]```.

### Additional Dependencies

In addition to installing the required python packages, separately install the following dependencies:

1. [Python](https://www.python.org/downloads/) distributions, one for each version supported by the developed project. 
   Currently, this library supports the three latest stable versions. The easiest way to get tox to work as intended is 
   to have separate python distributions. Alternatively, use [pyenv](https://github.com/pyenv/pyenv) to install multiple
   Python versions. This is needed for the 'test' task to work as intended.
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
To expedite the task runtime, use ```tox --parallel``` command to run some tasks in-parallel.

### Environments

All environments used during development are exported as .yml files and as spec.txt files to the [envs](envs) folder.
The environment snapshots were taken on each of the three explicitly supported OS families: Windows, OSx (M1),
and Linux Ubuntu LTS.

**Note!** Since the OSx environment was built on an M1 (Apple Silicon) platform, it may not work on Intel-based 
Apple devices.

To install any development environment on the local platform:

1. Download this repository to the local machine using the preferred method, such as git-cloning.
2. ```cd``` into the [envs](envs) folder.
3. Use one of the installation methods below:
    1. **_Preferred Method_**: Install [tox](https://tox.wiki/en/latest/user_guide.html) or use another
       environment with an already installed tox distribution and call ```tox -e import-env```.
    2. **_Alternative Method_**: Run ```conda env create -f ENVNAME.yml``` or ```mamba env create -f ENVNAME.yml```.
       Replace 'ENVNAME.yml' with the name of the environment to install (axa_dev_osx for OSx, axa_dev_win for Windows, 
       and axa_dev_lin for Linux).

**Hint:** while only the platforms mentioned above were explicitly evaluated, this project is likely to work on any 
common OS but may require additional configuration steps.

Since the release of ataraxis-automation 2.0.0, the development environment can also be created from scratch 
via pyproject.toml dependencies. To do this, use ```tox -e create``` from the project root directory.

### Automation Troubleshooting

Many packages used in 'tox' automation pipelines (uv, mypy, ruff) and 'tox' itself may experience runtime failures. In 
most cases, this is related to their caching behavior. Despite a considerable effort to disable caching behavior known 
to be problematic, in some cases it cannot or should not be eliminated. If an unintelligible error is encountered with 
any of the automation components, deleting the corresponding .cache (.tox, .ruff_cache, .mypy_cache, etc.) manually  
or via a CLI command is very likely to fix the issue.

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
