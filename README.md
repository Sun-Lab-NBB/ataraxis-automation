# ataraxis-automation

A Python library that provides scripts that support tox-based development automation pipelines used by other 
Sun Lab projects.

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

This library is one of the two 'base' dependency libraries used by every other Sun Lab project (the other being 
[ataraxis-base-utilities](https://github.com/Sun-Lab-NBB/ataraxis-base-utilities)). It exposes a command-line interface
(automation-cli) that can be used through the [tox-based](https://tox.wiki/en/latest/user_guide.html) project
development automation suite that comes with every Sun Lab project (we use tox as an analog to build system).

The commands from this library generally fulfill two major roles. First, they are used to set up, support, 
or clean up after third-party packages (ruff, mypy, stubgen, grayskull, etc.) used by our tox tasks. Second, they 
automate most operations with conda environments, such as creating / removing the environment and 
installing / uninstalling the project from the environment.

The library can be used as a standalone module, but it is primarily designed to integrate with other Sun Lab projects,
providing development automation functionality. Therefore, it may require either adopting and modifying a 
tox automation suite from one of the lab projects or significant refactoring to work with non-lab projects.
___

## Features

- Supports Windows, Linux, and OSx.
- Optimized for runtime speed by preferentially using mamba and uv over conda and pip.
- Compliments the extensive suite of tox-automation tasks used by all Sun Lab projects.
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

1. Download this repository to your local machine using your preferred method, such as git-cloning. Optionally, use one
   of the stable releases that include precompiled binary wheels in addition to source code.
2. ```cd``` to the root directory of the project using your command line interface of choice.
3. Run ```python -m pip install .``` to install the project. Alternatively, if using a distribution with precompiled
   binaries, use ```python -m pip install WHEEL_PATH```, replacing 'WHEEL_PATH' with the path to the wheel file.

### PIP

Use the following command to install the library using PIP: ```pip install ataraxis-automation```

### Conda / Mamba

**_Note. Due to conda-forge contributing process being more nuanced than pip uploads, conda versions may lag behind
pip and source code distributions._**

Use the following command to install the library using Conda or Mamba: ```conda install ataraxis-automation```
___

## Usage

### Quickstart
The easiest way to get Sun Lab automation to work for your project is to initialize the project using one of our 
templates for 
[pure-python](https://github.com/Sun-Lab-NBB/pure-python-template) or 
[c-extension](https://github.com/Sun-Lab-NBB/c-python-template) projects. To initialize and customize one of our 
templates, follow these steps:
1. Navigate to the desired template via one of the links above and click ```Use this template``` button in the 
   top right corner of the page.
2. Initialize your project as necessary and download and unpack it on your local machine. To do this, you can use tools
   such as git-cloning.
3. ```cd``` into the root directory of the project.
4. Use the ```tox -e adopt``` command to 'adopt' the project. The adoption process replaces placeholder markers in the
   template 'meta' files with information appropriate for your project.
5. Add your source code and support files as needed.

### Automation Command-Line Interface
All library functions designed to be called by end-users are exposed through the 'automation-cli' script.
This cli script is automatically exposed after installing the library into a conda or virtual environment.

#### Automation-CLI
While the preferred use case for this library is via 'tox' tasks, you can access all functions supplied by the library
by calling ```automation-cli``` from the shell that has access to the python environment with the library. Here are 
some examples of how you can use the automation-cli directly:
- Use ```automation-cli --help``` to verify that the cli is available and to see the list of supported commands.
- Use ```automation-cli COMMAND-NAME --help``` to display additional information about a specific command. For example:
  ```automation-cli import-env --help```.

#### Tox automation
This library is intended to be used to augment 'tox' runtimes, and this is always the preferred use case.
To use any of the commands as part of a tox 'task,' add it to the 'commands' section of the tox.ini:
```
[testenv:create]
basepython = py310
deps =
    ataraxis-automation>=3,<4
description =
    Creates a minimally-configured conda environment using the requested python version and installs conda- and pip-
    dependencies extracted from pyproject.toml file into the environment. Does not install the project!
commands =
    automation-cli --verbose create-env --environment-name axa_dev --python-version 3.12
```
#### Logging and Printing
All cli commands come with two parameters exposed through the main cli group:
1. ```--verbose```: Determines whether to display Information, Warning and Success messages to inform the user about
   the ongoing runtime.
2. ```--log```: Determines whether to save messages and errors to log files (located in automatically generated folder
   inside user log directory).

#### Command-specific flags
*__Note!__* Many sub-commands of the cli have additional flags and arguments that can be used to further customize
their runtime. Consult the API documentation to see these options with detailed descriptions.

*__Warning!__* When using any cli command that uses ```--python-version``` flag from tox, you __have__ to include 
```basepython=``` line in the environment configuration __and__ set it to a python version __different__ from the 
one provided after ```--python-version``` argument. See the 'testenv:create' example above.

### Intended cli use pattern
All cli commands are intended to be used through tox pipelines. The most recent version of Sun Lab tox configuration
is always available from this libraries' [tox.ini file](tox.ini). Since this library plays a large role in our tox 
automation pipelines, its tox configuration is always the most up to date and feature-packed compared to all other 
Sun Lab projects.

Any well-maintained Sun Lab project comes with an up-to-date tox configuration that automates most 'meta' 
development steps, such as code formatting, project testing, and project distribution. By automating most of these 
steps, we seek to provide clear standards to be shared by internal and external collaborators. Additionally, this 
allows developers to focus on the important task of planning and writing the code of their projects over 'meta' tasks
like code formatting.

### Available 'tox' commands
This library is tightly linked to our 'tox' configuration. Most of our 'tox' tasks either use some functions from this 
library in addition to external packages or entirely consist of calling functions from this library. Therefore, this
documentation would not have been complete without having a section about our 'tox' tasks, in addition to the basic
information about our 'automation-cli' script.

Note that commands listed here may and frequently are modified based on the specific needs of each project that 
uses them. Therefore, this section is *__not__* a replacement for studying the tox.ini file for the specific project you
seek to develop. Additionally, using tasks listed here 'as is' may not work for your project without customizations.

Most of the commands in this section are designed to be executed together (some sequentially, some in-parallel) when
a general ```tox``` command is used. These are considered 'checkout' tasks, and they generally cover the things that 
need to be present for a commit to be pushed to the main branch of any Sun Lab project.

#### Lint
Shell command: ```tox -e lint```

Uses [ruff](https://github.com/astral-sh/ruff) and [mypy](https://github.com/python/mypy) to statically analyze and, 
where possible, fix code formatting, typing, and problematic use patterns. This helps to ensure the code is 
formatted according to our standards and does not contain easily identifiable problematic use patterns, such as 
type violations. As part of its runtime, this task uses automation cli to remove existing stub (.pyi) files from 
the source folders, as they interfere with type-checking.

Example tox.ini section:
```
[testenv: lint]
description =
    Runs static code formatting, style and typing checkers. Mypy may not work properly until py.typed marker is
    added by 'stubs' task.
deps =
    mypy>=1,<2
    ruff>=0,<1
    types-pyyaml>=6,<7
    ataraxis-automation>=3,<4
depends = uninstall
# Note! Basepython has to be set to the 'lowest' version supported by your project
basepython = py310
commands =
    automation-cli --verbose purge-stubs
    ruff check --select I --fix
    ruff format
    mypy . --strict --extra-checks --warn-redundant-cast
```

#### Stubs
Shell command: ```tox -e stubs```

Uses [stubgen](https://mypy.readthedocs.io/en/stable/stubgen.html) to generate stub (.pyi) files and, 
via automation-cli, distribute them to the appropriate levels of the library source folder. This is necessary to 
support static type-checking for projects that use your project. As part of that process, automation-cli also ensures 
that there is a 'py.typed' marker file in the highest library directory. This is required for type-checkers like mypy 
to recognize the project as 'typed' and process it during type-checking tasks.

Example tox.ini section:
```
[testenv: stubs]
description =
    Generates the py.typed marker and the stub files using the built library wheel. Formats the stubs with ruff before
    moving them to appropriate source sub-directories.
deps =
    mypy>=1,<2
    ruff>=0,<1
    ataraxis-automation>=3,<4
depends = lint
commands =
    automation-cli --verbose process-typed-markers
    stubgen -o stubs --include-private --include-docstrings -p ataraxis_automation -v
    ruff check --select I --fix
    ruff format
    automation-cli --verbose process-stubs
```

#### Test
Shell command: ```tox -e pyXXX-test``` 

This task is available for all python versions supported by each project. For example, automation supports versions 
3.10, 3.11, and 3.12. Therefore, it will have ```tox -e py310-test```, ```tox -e py311-test``` and 
```tox -e py312-test``` as valid 'test' tasks. These tasks are used to build the project in an isolated environment and 
run the tests expected to be located inside the project_root/tests directory to verify the project works as expected 
for each python version. This is especially relevant for c-extension projects that compile code for specific python 
versions and platforms.

Example tox.ini section:
```
[testenv: {py310, py311, py312}-test]
package = wheel
description =
    Runs unit and integration tests for each of the python versions listed in the task name. Uses 'loadgroup' balancing
    and all logical cores to optimize runtime speed while allowing manual control over which cores execute tasks (see
    pytest-xdist documentation).
deps =
    pytest>=8,<9
    pytest-cov>=5,<6
    pytest-xdist>=3,<4
    coverage[toml]>=7,<8
depends = uninstall
setenv =
    # Sets environment parameters, which includes intermediate coverage aggregation file used by coverage.
    COVERAGE_FILE = reports{/}.coverage.{envname}
commands =
    # Make sure the --cov is always set to the intended library name, so that coverage runs on the whole library
    # exactly once.
    pytest --import-mode=append --cov=ataraxis_automation --cov-config=pyproject.toml --cov-report=xml \
    --junitxml=reports/pytest.xml.{envname} -n logical --dist loadgroup
```

#### Coverage
Shell command: ```tox -e coverage``` 

This task is designed to be used in-conjunction with the 'test' task. It aggregates code coverage data for different 
python versions and compiles it into a html-report accessible by opening project_root/reports/coverage_html/index.html 
in a browser. For all lab projects, we try to provide as close to 100% code coverage as possible for each project.

Example tox.ini section:
```
[testenv:coverage]
skip_install = true
description =
    Combines test-coverage data from multiple test runs (for different python versions) into a single html file. The
    file can be viewed by loading the 'reports/coverage_html/index.html'.
setenv = COVERAGE_FILE = reports/.coverage
depends = {py310, py311, py312}-test
deps =
    junitparser>=3,<4
    coverage[toml]>=7,<8
commands =
    junitparser merge --glob reports/pytest.xml.* reports/pytest.xml
    coverage combine --keep
    coverage xml
    coverage html
```
#### Doxygen
Shell command: ```tox -e doxygen```

*__Note!__* This task is only used in c-extension projects.

This task is unique to our c-extension projects (projects that contain compiled c / c++ code). It uses 
[Doxygen](https://www.doxygen.nl/) to parse doxygen-styled docstrings used in our c-code to make them accessible to 
[Sphinx](https://www.sphinx-doc.org/en/master/) (used as part of our 'docs' task). This allows automatically building
C/C++ API documentation and organically bundling it with Python API documentation via sphinx.

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

Uses [sphinx](https://www.sphinx-doc.org/en/master/) to automatically parse docstrings from source code and use them 
to build API documentation for the project. C-extension projects use a slightly modified version of this task that uses
[breathe](https://breathe.readthedocs.io/en/latest/) to convert doxygen-generated xml files for c-code into a format 
that sphinx can parse. This way, c-extension projects can include both Python and C/C++ API documentation as part of 
the same file. This task relies on the configuration files stored inside /project_root/docs/source folder to define 
the generated documentation format. Built documentation can be viewed by opening 
project_root/docs/build/html/index.html in a browser.

Example tox.ini section for a pure-python project:
```
[testenv:docs]
description =
    Builds the API documentation from source code docstrings using Sphinx. The result can be viewed by loading
    'docs/build/html/index.html'.
depends = uninstall
deps =
    sphinx>=7,<8
    importlib_metadata>=8,<9
    sphinx-rtd-theme>=2,<3
    sphinx-click>=6,<7
    sphinx-autodoc-typehints>=2,<3
commands =
    sphinx-build -b html -d docs/build/doctrees docs/source docs/build/html -j auto -v
```

Example tox.ini section for a c-extension project:
```
[testenv:docs]
description =
    Builds the API documentation from source code docstrings using Sphinx. Integrates with C / C++ documentation via
    Breathe, provided that Doxygen was used to generate the initial .xml file for C-extension sources. The result can
    be viewed by loading 'docs/build/html/index.html'.
depends = doxygen
deps =
    sphinx>=7,<8
    importlib_metadata>=8,<9
    sphinx-rtd-theme>=2,<3
    sphinx-click>=6,<7
    sphinx-autodoc-typehints>=2,<3
    breathe>=4,<5
commands =
    sphinx-build -b html -d docs/build/doctrees docs/source docs/build/html -j auto -v
```

#### Build
Shell command: ```tox -e build```

This task differs for c-extension and pure-python projects. In both cases, it builds a source-code distribution (sdist)
and a binary distribution (wheel) for the project. These distributions can then be uploaded to GitHub, PyPI, and Conda 
for further distribution or shared with other people manually. Pure Python projects use 
[hatchling](https://hatch.pypa.io/latest/) and [build](https://build.pypa.io/en/stable/) to generate
one source-code and one binary distribution. C-extension projects use 
[cibuildwheel](https://cibuildwheel.pypa.io/en/stable/) to compile c-code for all supported platforms and 
architectures, building many binary distribution files alongside source-code distribution generated via build.

Example tox.ini section for a pure-python project:
```
[testenv:build]
skip-install = true
description =
    Builds the source code distribution (sdist) and the binary distribution package (wheel). Use 'upload' task to
    subsequently upload built wheels to PIP.
deps =
    build>=1,<2
    hatchling>=1,<2
allowlist_externals =
    docker
commands =
    python -m build . --sdist
    python -m build . --wheel
```

Example tox.ini section for a c-extension project:
```
[testenv:build]
skip-install = true
description =
    Builds the source code distribution (sdist) and compiles and assembles binary wheels for all architectures of the
    host-platform supported by the library. Use 'upload' task to subsequently upload built wheels to PIP.
deps =
    cibuildwheel[uv]>=2,<3
    build>=1,<2
allowlist_externals =
    docker
commands =
    python -m build . --sdist
    cibuildwheel --output-dir dist --platform auto
```

#### Upload
Shell command: ```tox -e upload```

Uploads the sdist and wheel files created by 'build' task to [PyPI](https://pypi.org/). When this task runs for the 
first time, it uses automation-cli to generate a .pypirc file and store user-provided PyPI upload token into that file.
This allows reusing the token for later uploads, streamlining the process. The task is configured to skip uploading
already uploaded files to avoid errors. This is all it takes to make your project available for downloads using 
'pip install.'

Example tox.ini section:
```
[testenv:upload]
description =
    Uses twine to upload all files inside the '/dist' folder to pip, ignoring any files that are already uploaded.
    Uses API token stored in '.pypirc' file or provided by user to authenticate the upload.
deps =
    twine>=5,<6
    ataraxis-automation>=3,<4
allowlist_externals =
    distutils
commands =
    automation-cli --verbose acquire-pypi-token {posargs:}
    twine upload dist/* --skip-existing --config-file .pypirc
```

#### Recipe
Shell command: ```tox -e recipe```

This task is the *first* out of *multiple* steps to upload a project to [conda-forge](https://conda-forge.org/) channel.
Overall, this process leads to your project becoming installable with 'conda install.' The task uses automation-cli 
to generate a 'recipe' folder inside the root project directory and then uses grayskull to generate the project recipe
using *the most recent pip version* of the project. This task assumes that pip contains the source-code distribution
(sdist) for the project. Since all our projects are distributed under GPL3 license, they always contain source-code 
distributions. See [conda-forge documentation](https://conda-forge.org/docs/maintainer/adding_pkgs/) for more 
information on uploading packages to conda-forge.

Example tox.ini section:
```
[testenv:recipe]
skip_install = true
description =
    Uses grayskull to parse the source code tarball stored on pip and generate the recipe used to submit the
    package to conda-forge. The submission process has to be carried out manually, see
    https://conda-forge.org/docs/maintainer/adding_pkgs/ for more details.
deps =
    grayskull>=2,<3
    ataraxis-automation>=3,<4
commands =
    automation-cli --verbose generate-recipe-folder
    grayskull pypi ataraxis_automation -o recipe --strict-conda-forge --list-missing-deps -m Inkaros
```

### Conda-environment manipulation tox commands
*__Note!__* These commands were written to automate repetitive tasks associated with project-specific conda 
environments. They assume that there is a validly configured conda or mamba version installed and accessible from the
shell of the machine these commands are called on. All of these tasks can be replaced with sequences of manual conda
or pip commands if necessary.


#### Install
Shell command: ```tox -e install```

Installs the project into the requested environment. This task is used to build and install the project into the 
project development environment. This is a prerequisite for manually running and testing projects that are being 
actively developed. During general 'tox' runtime, this task is used to (re)install the project into the
project environment as necessary to avoid collisions with 'tox.'

*__Note!__* The 'basepython' argument should always be set to a version different from '--python-version.'

Example tox.ini section:
```
[testenv:install]
basepython = py310
deps =
    ataraxis-automation>=3,<4
depends =
    uninstall
    lint
    stubs
    {py310, py311, py312}-test
    coverage
    docs
description =
    Builds and installs the project into the specified conda environment. If the environment does not exist, creates
    it before installing the project.
commands =
    automation-cli --verbose install-project --environment-name axa_dev --python-version 3.12
```

#### Uninstall
Shell command: ```tox -e uninstall```

Removes the project from the requested environment. This task is used in-conjunction with the 'install' task to 
avoid version collisions when running general 'tox' tasks.

*__Note!__* The 'basepython' argument should always be set to a version different from '--python-version.'

Example tox.ini section:
```
[testenv:uninstall]
basepython = py310
deps =
    ataraxis-automation>=3,<4
description =
    Uninstalls the project from the specified conda environment. If the environment does not exist
    this task silently succeeds.
commands =
    automation-cli --verbose uninstall-project --environment-name axa_dev --python-version 3.12
```

#### Create
Shell command: ```tox -e create```

Creates the requested conda environment and installs project dependencies listed in pyproject.toml into the environment.
This task is intended to be used when setting up project development environments for new platforms and architectures. 
To work as intended, it uses automation-cli to parse the contents of tox.ini and pyproject.toml files to generate a 
list of project dependencies. It assumes that dependencies are stored using Sun Lab format: inside 'conda,' 'noconda,'
'condarun,' and general 'dependencies' section.

*__Note!__* The 'basepython' argument should always be set to a version different from '--python-version.'

Example tox.ini section:
```
[testenv:create]
basepython = py310
deps =
    ataraxis-automation>=3,<4
description =
    Creates a minimally-configured conda environment using the requested python version and installs conda- and pip-
    dependencies extracted from pyproject.toml file into the environment. Does not install the project!
commands =
    automation-cli --verbose create-env --environment-name axa_dev --python-version 3.12
```

#### Remove
Shell command: ```tox -e remove```

Removes the project-specific conda environment. Primarily, this task is intended to be used to clean the local system 
after finishing development and to hard-reset the environment (this use is discouraged!).

Example tox.ini section:
```
[testenv:remove]
basepython = py310
deps =
    ataraxis-automation>=3,<4
description =
    Removes the requested conda environment, if it is installed locally.
commands =
    automation-cli --verbose remove-env --environment-name axa_dev
```

#### Provision
Shell command: ```tox -e provsion```

This task is a 'soft' combination of the 'remove' and 'create' tasks that allows resetting environments without deleting
them. It first uninstalls all packages in the environment and then re-installs project dependencies using pyproject.toml
file. This is the same procedure as used by the 'create' task. Since this task does not remove the environment, it 
preserves all references used by tools such as IDEs, but completely resets all packages in the environment. This can
be used to both reset and actualize project development environments to match the latest version of the 
.toml specification.

*__Note!__* The 'basepython' argument should always be set to a version different from '--python-version.'

Example tox.ini section:
```
[testenv:provision]
basepython = py310
deps =
    ataraxis-automation>=3,<4
description =
    Provisions an already existing environment by uninstalling all packages from the environment and then installing the
    project dependencies using pyproject.toml specifications.
commands =
    automation-cli --verbose provision-env --environment-name axa_dev --python-version 3.12
```

#### Export
Shell command: ```tox -e export```

Exports the target development environment as a .yml and spec.txt files. This task is used before distributing new 
versions of the project. This allows end-users to generate an identical copy of the development environment, which is 
a highly encouraged feature for most projects. While our 'create' and 'provision' tasks make this largely obsolete, we 
still include exported environments in all our project distributions.

Example tox.ini section:
```
[testenv:export]
deps =
    ataraxis-automation>=3,<4
description =
    Exports the requested conda environment to the 'envs' folder as a .yml file and as a spec.txt with revision history.
commands =
    automation-cli --verbose export-env --environment-name axa_dev
```

#### Import
Shell command: ```tox -e import```

Imports the project development environment from an available '.yml' file. If the environment does not exist, this 
creates an identical copy of the environment stored in the .yml file. If the environment already exists, it is instead
updated using the '.yml' file. The update process is configured to prune any 'unused' packages not found inside the 
'.yml' file. This can be used to clone or actualize the project development environment from a file distributed via
'export' task.

Example tox.ini section:
```
[testenv:import]
deps =
    ataraxis-automation>=3,<4
description =
    Discovers and imports (installs) a new or updates an already existing environment using the .yml file
    stored in the 'envs' directory.
commands =
    automation-cli --verbose import-env --environment-name axa_dev
```

#### Rename
Shell command: ```tox -e rename```

Renames all environment files inside the project_root/envs directory to use the provided base_name (obtained from 
user via dialog). This is used to quickly rename all environment files, which is helpful when renaming the project. 
Primarily, this task is used during 'adoption' task, but it also has uses during general development. The renaming 
procedure also changes the value of the 'name' field inside the '.yml' files. Environments created from renamed files
will use the 'altered' environment name.

Example tox.ini section:
```
[testenv:rename]
deps =
    ataraxis-automation>=3,<4
description =
    Replaces the base environment name used by all files inside the 'envs' directory with the user-input name.
commands =
    automation-cli --verbose rename-environments
```

#### Adopt
Shell command: ```tox -e adopt```

This task is designed to be used on new projects initialized from one of Sun Lab templates. Templates come with 
'placeholders' in most meta-files (pyproject.toml, tox.ini, etc.). This task finds and replaces the placeholders with
user-defined values (obtained via dialog). This simplifies customizing the template projects to suite the specific needs
of your particular project, while still benefiting from the Sun Lab structure and support files.

Example tox.ini section:
```
[testenv:adopt]
deps =
    ataraxis-automation>=3,<4
description =
    Adopts a Sun Lab template-generated project by replacing default placeholders with user-provided information.
commands =
    automation-cli --verbose adopt-project
```
___

## API Documentation

See the [API documentation](https://ataraxis-automation-api-docs.netlify.app/) for the
detailed description of the methods and classes exposed by components of this library. __*Note*__ the documentation
also includes a list of all command-line interface functions provided by automation-cli script.
___

## Developers

This section provides installation, dependency, and build-system instructions for the developers that want to
modify the source code of this library. Additionally, it contains instructions for recreating the conda environments
that were used during development from the included .yml files.

### Installing the library

1. Download this repository to your local machine using your preferred method, such as git-cloning.
2. ```cd``` to the root directory of the project using your command line interface of choice.
3. Install development dependencies. You have multiple options of satisfying this requirement:
    1. **_Preferred Method:_** Use conda or pip to install
       [tox](https://tox.wiki/en/latest/user_guide.html) or use an environment that has it installed and
       call ```tox -e import``` to automatically import the os-specific development environment included with the
       source code in your local conda distribution. Alternatively, you can use ```tox -e create``` to create the 
       environment from scratch and automatically install the necessary dependencies using pyproject.toml file. See
       [environments](#environments) section for other environment installation methods.
    2. Run ```python -m pip install .'[dev]'``` command to install development dependencies and the library using 
       pip. On some systems, you may need to use a slightly modified version of this command: 
       ```python -m pip install .[dev]```.
    3. As long as you have an environment with [tox](https://tox.wiki/en/latest/user_guide.html) installed
       and do not intend to run any code outside the predefined project automation pipelines, tox will automatically
       install all required dependencies for each task.

**Note:** When using tox automation, having a local version of the library may interfere with tox tasks that attempt
to build the library using an isolated environment. While the problem is rare, our 'tox' pipelines automatically 
install and uninstall the project from its' conda environment. This relies on a static tox configuration and will only 
target the project-specific environment, so it is advised to always ```tox -e import``` or ```tox -e create``` the 
project environment using 'tox' before running other tox commands.

### Additional Dependencies

In addition to installing the required python packages, separately install the following dependencies:

1. [Python](https://www.python.org/downloads/) distributions, one for each version that you intend to support. 
   Currently, this library supports version 3.10 and above. The easiest way to get tox to work as intended is to have 
   separate python distributions, but using [pyenv](https://github.com/pyenv/pyenv) is a good alternative too. 
   This is needed for the 'test' task to work as intended.


### Development Automation

This project comes with a fully configured set of automation pipelines implemented using 
[tox](https://tox.wiki/en/latest/user_guide.html). Check [tox.ini file](tox.ini) for details about 
available pipelines and their implementation. Alternatively, call ```tox list``` from the root directory of the project
to see the list of available tasks. __*Note*__, automation pipelines for this library list itself as a circular
dependency in some use cases. Generally, this is not an issue when patching or adding new functionality, but requires
extra care when working on major library versions.

**Note!** All commits to this library have to successfully complete the ```tox``` task before being pushed to GitHub. 
To minimize the runtime task for this task, use ```tox --parallel```.

### Environments

All environments used during development are exported as .yml files and as spec.txt files to the [envs](envs) folder.
The environment snapshots were taken on each of the three explicitly supported OS families: Windows 11, OSx (M1) 14.5
and Linux Ubuntu 22.04 LTS.

**Note!** Since the OSx environment was built on an M1 (Apple Silicon) platform, it may not work on Intel-based 
Apple devices.

To install the development environment for your OS:

1. Download this repository to your local machine using your preferred method, such as git-cloning.
2. ```cd``` into the [envs](envs) folder.
3. Use one of the installation methods below:
    1. **_Preferred Method_**: Install [tox](https://tox.wiki/en/latest/user_guide.html) or use another
       environment with already installed tox and call ```tox -e import-env```.
    2. **_Alternative Method_**: Run ```conda env create -f ENVNAME.yml``` or ```mamba env create -f ENVNAME.yml```.
       Replace 'ENVNAME.yml' with the name of the environment you want to install (axa_dev_osx for OSx,
       axa_dev_win for Windows, and axa_dev_lin for Linux).

**Hint:** while only the platforms mentioned above were explicitly evaluated, this project is likely to work on any 
common OS, but may require additional configurations steps.

Since the release of ataraxis-automation 2.0.0, you can also create the development environment from scratch 
via pyproject.toml dependencies. To do this, use ```tox -e create``` from project root directory.

### Automation Troubleshooting

Many packages used in 'tox' automation pipelines (uv, mypy, ruff) and 'tox' itself are prone to various failures. In 
most cases, this is related to their caching behavior. Despite a considerable effort to disable caching behavior known 
to be problematic, in some cases it cannot or should not be eliminated. If you run into an unintelligible error with 
any of the automation components, deleting the corresponding .cache (.tox, .ruff_cache, .mypy_cache, etc.) manually 
or via a cli command is very likely to fix the issue.
___

## Versioning

We use [semantic versioning](https://semver.org/) for this project. For the versions available, see the 
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
- [pyyaml](https://github.com/yaml/pyyaml.org), [appdirs](https://github.com/ActiveState/appdirs), 
  and [tomli](https://github.com/hukkin/tomli) for providing low-level functionality for some of the automation 
  functions.
- The teams behind [pip](https://github.com/pypa/pip), [uv](https://github.com/astral-sh/uv), 
  [conda](https://conda.org/), [mamba](https://github.com/mamba-org/mamba) and [tox](https://github.com/tox-dev/tox), 
  which form the backbone of our code distribution and management pipeline.
- The creators of all other projects listed in out [pyproject.toml](pyproject.toml) file and used in automation 
  pipelines across all Sun Lab projects.
