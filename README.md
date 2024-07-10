# ataraxis-automation

A Python library that provides scripts that support tox-based development automation pipelines used by other 
Sun Lab projects.

![PyPI - Version](https://img.shields.io/pypi/v/ataraxis-automation)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ataraxis-automation)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
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

### Automation Command-Line Interface

All library functions designed to be called by end-users are exposed through the automation-cli command-line interface.
This cli is automatically exposed after installing the library into a conda or virtual environment.

Here are some examples on how you can access the cli from your shell:
- Use ```automation-cli --help``` to verify that the cli is available and to see the list of supported commands.
- Use ```automation-cli COMMAND-NAME --help``` to display additional information about a specific command. For example:
  ```automation-cli import-env --help```.
- To use any of the commands as part of tox pipeline, add it to the 'commands' section of the tox.ini:
```
[testenv:create]
basepython = py310
deps =
    ataraxis-automation>=2
description =
    Creates a minimally-configured conda environment using the requested python version and installs conda- and pip-
    dependencies extracted from pyproject.toml file into the environment. Does not install the project!
commands =
    automation-cli --verbose create-env --environment-name axa_dev --python-version 3.12
```

All cli commands come with two parameters exposed through the main cli group:
1. ```--verbose```: Determines whether to display Information and Success messages to inform the user about the 
   ongoing runtime.
2. ```--log```: Determines whether to save messages and errors to log files (located in automatically generated folder
   inside user log directory.

*__Note!__* Many sub-commands of the cli have additional flags and arguments that can be sued to further customize
their runtime. Consult the API documentation to see these options with detailed descriptions.

*__Warning!__* When using any cli command that uses ```--python-version``` flag from tox, you __have__ to include 
```basepython=``` line in the environment configuration __and__ set it to a python version __different__ from the 
one provided after ```--python-version``` argument. See the 'testenv:create' example above.

### Intended cli use pattern
All cli commands are intended to be used through tox pipelines. The most recent version of Sun Lab tox configuration
is always available from this libraries' [tox.ini file](tox.ini). Since this library plays a large role in our tox 
automation pipelines, its tox configuration is always the most up to date and feature packed compared to all other 
Sun Lab projects.

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

**Note!** Since the OSx environment was built against an M1 (Apple Silicon) platform and may not work on Intel-based 
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
