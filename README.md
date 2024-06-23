# ataraxis-automation

A Python library that provides CLI scripts and utility functions used by Sun Lab automation pipelines.

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

This library decouples automation-assisting scripts used by most Sun Lab projects from the 'tox' tasks that use them.
This allows updating custom automation functions without the need to manually update each module that uses these
scripts. Since most functions exposed through this module are 'meta-functions' providing build-system
functionality, they currently do not contain an automated test suite, but they have been extensively tested on multiple
Ataraxis libraries.

In addition to automation functions, this library provides meta-utility functions, such as message-formatting. Since
all other Sun Lab projects use automation functions, bundling them with widely used utilities unifies these
critical dependencies in one pacakge.

The library can be used as a standalone module, but it is primarily designed to integrate with other Sun Lab libraries,
providing development automation functionality. Additionally, it comes pre-bundled with all Sun Lab templates,
private or public.
___

## Features

- Supports Windows, Linux, and OSx.
- Optimized for runtime speed.
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
2. ```cd``` to the root directory of the project using your CLI of choice.
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

This library is primarily designed for two purposes: providing a CLI suite of tox-assisting scripts and a set of widely
used utility functions.

This is a minimal example of how to use the automation CLI functions:

- Use ```automation-cli --help``` from your shell to display the list of available cli command.
- Use ```automation-cli COMMAND-NAME --help``` to display additional information about each command. For example:
  ```automation-cli import-env --help```.
- To use any of the CLI commands as part of tox pipeline, add it to the 'commands' section of the tox.ini:

```
[testenv:rename-envs]
skip_install = true
deps =
    ataraxis-automation
description =
    Replaces the base environment name used by all files inside the 'envs' directory with the user-input name.
commands =
    automation-cli rename-environments
```

This is a minimal example of how to use the utility functions from this library:

```
# Import the desired function(s) from the utilities module.
from ataraxis_automation.utilities import format_message

# Message formatting example. The function is used across all Sun Lab projects to format any emitted messages:
long_message = (
        "This is a very long message that needs to be formatted properly. It should be wrapped at 120 characters "
        "without breaking long words or splitting on hyphens. The formatting should be applied correctly to ensure "
        "readability and consistency across the library."
    )
print(long_message) # Showcases unformatted message
print()
print(format_message(long_message)) # Showcases formatted message
```

___

## API Documentation

See the [API documentation](https://ataraxis-automation-api-docs.netlify.app/) for the
detailed description of the methods and classes exposed by components of this library. __*Note*__ the documentation
also includes a list of all CLI functions provided by automation-cli command.
___

## Developers

This section provides installation, dependency, and build-system instructions for the developers that want to
modify the source code of this library. Additionally, it contains instructions for recreating the conda environments
that were used during development from the included .yml files.

### Installing the library

1. Download this repository to your local machine using your preferred method, such as git-cloning.
2. ```cd``` to the root directory of the project using your CLI of choice.
3. Install development dependencies. You have multiple options of satisfying this requirement:
    1. **_Preferred Method:_** Use conda or pip to install
       [tox](https://tox.wiki/en/latest/config.html#provision_tox_env) or use an environment that has it installed and
       call ```tox -e import-env``` to automatically import the os-specific development environment included with the
       source code in your local conda distribution. Alternatively, see [environments](#environments) section for other
       environment installation methods.
    2. Run ```python -m pip install .'[dev]'``` command to install development dependencies and the library using 
       pip. On some systems, you may need to use a slightly modified version of this command: 
       ```python -m pip install .[dev]```.
    3. As long as you have an environment with [tox](https://tox.wiki/en/latest/config.html#provision_tox_env) installed
       and do not intend to run any code outside the predefined project automation pipelines, tox will automatically
       install all required dependencies for each task.

**Note:** When using tox automation, having a local version of the library may interfere with tox methods that attempt
to build the library using an isolated environment. It is advised to remove the library from your test environment, or
disconnect from the environment, prior to running any tox tasks. This problem is rarely observed with the latest version
of the automation pipeline, but is worth mentioning.

### Additional Dependencies

In addition to installing the required python packages, separately install the following dependencies:

1. [Python](https://www.python.org/downloads/) distributions, one for each version that you intend to support. 
  Currently, this library supports version 3.10 and above. The easiest way to get tox to work as intended is to have 
  separate python distributions, but using [pyenv](https://github.com/pyenv/pyenv) is a good alternative too. 
  This is needed for the 'test' task to work as intended.


### Development Automation

This project comes with a fully configured set of automation pipelines implemented using 
[tox](https://tox.wiki/en/latest/config.html#provision_tox_env). 
Check [tox.ini file](tox.ini) for details about available pipelines and their implementation. __*Note*__, automation 
pipelines for this specific project list it as a circular dependency in some use cases, which is not ideal, but works.

**Note!** All commits to this library have to successfully complete the ```tox``` task before being pushed to GitHub. 
To minimize the runtime task for this task, use ```tox --parallel```.

### Environments

All environments used during development are exported as .yml files and as spec.txt files to the [envs](envs) folder.
The environment snapshots were taken on each of the three supported OS families: Windows 11, OSx 14.5 and
Ubuntu 22.04 LTS.

To install the development environment for your OS:

1. Download this repository to your local machine using your preferred method, such as git-cloning.
2. ```cd``` into the [envs](envs) folder.
3. Use one of the installation methods below:
    1. **_Preferred Method_**: Install [tox](https://tox.wiki/en/latest/config.html#provision_tox_env) or use another
       environment with already installed tox and call ```tox -e import-env```.
    2. **_Alternative Method_**: Run ```conda env create -f ENVNAME.yml``` or ```mamba env create -f ENVNAME.yml```.
       Replace 'ENVNAME.yml' with the name of the environment you want to install (axa_dev_osx for OSx,
       axa_dev_win for Windows and axa_dev_lin for Linux).

**Note:** the OSx environment was built against M1 (Apple Silicon) platform and may not work on Intel-based Apple
devices.

___

## Authors

- Ivan Kondratyev ([Inkaros](https://github.com/Inkaros))

___

## License

This project is licensed under the GPL3 License: see the [LICENSE](LICENSE) file for details.
___

## Acknowledgments

- All Sun Lab [members](https://neuroai.github.io/sunlab/people) for providing the inspiration and comments during the
  development of this library.
