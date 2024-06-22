# YOUR-PROJECT-NAME

A short (1–2 line max) description of your library (what does it do?)

![PyPI - Version](https://img.shields.io/pypi/v/YOUR-PROJECT-NAME)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/YOUR-PROJECT-NAME)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![type-checked: mypy](https://img.shields.io/badge/type--checked-mypy-blue?style=flat-square&logo=python)
![PyPI - License](https://img.shields.io/pypi/l/YOUR-PROJECT-NAME)
![PyPI - Status](https://img.shields.io/pypi/status/YOUR-PROJECT-NAME)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/YOUR-PROJECT-NAME)
___

## Adopt Me
**_Note. Remember to completely delete this section before releasing v1.0.0 to the public! This section contains 
a set of steps you need to carry out to 'adopt' a project instantiated using this template._**

To adopt this project, you can loosely follow these steps:
1. Install [tox](https://tox.wiki/en/4.14.2/user_guide.html) into (**_recommended_**) an independent conda 
environment or, if you mostly work with lab projects, into the base environment (**_this is not recommended_**).
2. Open your shell environment of choice (terminal, zsh, powershell, etc.), run ```tox -e adopt``` task and work 
through the prompts. This task mostly renames the placeholders left through template project files, which effectively 
converts a generic template into your desired project.
3. Run ```tox -e import-env```. This will automatically discover the '.yml' file for your os among the files stored in 
'envs' and install it into your local conda distribution. Generally, this step is not required, but is 
**_highly recommended_** for running source code outside our automation pipelines.
4. Verify the information in pyproject.toml file. Specifically, modify the project metadata and add any project-wide 
dependencies where necessary.
5. Look through the files inside the 'docs/source/' hierarchy, especially the 'api.rst' and configure it to work for 
your source code.
6. Use conda to add the necessary dependencies to the environment you have imported. Once the environment is 
configured, use ```tox -e export-env``` to export the environment to the 'envs' folder. The lab requires that each 
project contains a copy of the fully configured library for each of the operational systems used in development.
7. Remove this section and adjust the rest of the ReadMe to cover the basics of your project. You will tweak it later
as you develop your source code to better depict your project.
8. Add some source code and some tests to verify it works as intended... This is where development truly starts. 
Run ```tox``` before pushing the code back to GitHub to make sure it complies with our standards. 
9. Congratulations! You have successfully adopted a SunLab project. Welcome to the family!

## Detailed Description

A long description (1–2 paragraphs max). Should highlight the specific advantages of the library and may mention how it
integrates with the broader Ataraxis project (for Ataraxis-related modules)
___

## Features

- Supports Windows, Linux, and OSx.
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

Use the following command to install the library using PIP:
```pip install YOUR-PROJECT-NAME```

### Conda / Mamba

**_Note. Due to conda-forge contributing process being more nuanced than pip uploads, conda versions may lag behind
pip and source code distributions._**

Use the following command to install the library using Conda or Mamba:
```conda install YOUR-PROJECT-NAME```
___

## Usage

Add some minimal examples on how the end-user can use your library.

___

## API Documentation

See the [API documentation](https://YOUR-PROJECT-NAME-api-docs.netlify.app/) for the
detailed description of the methods and classes exposed by components of this library. The documentation also 
covers any cli-interfaces (such as benchmarks).
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
   source code in your local conda distribution.
   2. Run ```python -m pip install .'[dev]'``` command to install development dependencies and the library. For some
   systems, you may need to use a slightly modified version of this command: ```python -m pip install .[dev]```.
   3. As long as you have an environment with [tox](https://tox.wiki/en/latest/config.html#provision_tox_env) installed
   and do not intend to run any code outside the predefined project automation pipelines, tox will automatically 
   install all required dependencies for each task. Generally, this option is **_not_** recommended.

**Note:** When using tox automation, having a local version of the library may interfere with tox methods that attempt
to build the library using an isolated environment. It is advised to remove the library from your test environment, or
disconnect from the environment, prior to running any tox tasks. This problem is rarely observed with the latest version
of the automation pipeline, but is worth mentioning.

### Additional Dependencies

In addition to installing the required python packages, separately install the following dependencies:

- [Python](https://www.python.org/downloads/) distributions, one for each version that you intend to support. Currently,
  this library supports version 3.10 and above. The easiest way to get tox to work as intended is to have separate
  python distributions, but using [pyenv](https://github.com/pyenv/pyenv) is a good alternative too. This is needed for 
  the 'test' task to work as intended

### Development Automation

To help developers, this project comes with a set of fully configured 'tox'-based pipelines for verifying and building
the project. Each of the tox commands builds the project in an isolated environment before carrying out its task. Some 
commands rely on the 'automation.py' module that provides the helper-scripts implemented in python. This module 
is stored in the source code root directory for each Sun Lab project.

- ```tox -e stubs``` Builds the library and uses mypy-stubgen to generate the stubs for the library wheel and move them 
to the appropriate position in the '/src' directory. This enables mypy and other type-checkers to work with this 
library.
- ```tox -e lint``` Checks and, where safe, fixes code formatting, style, and type-hinting.
- ```tox -e {py310, py311, py312}-test``` Builds the library and executes the tests stored in the /tests directory 
using pytest-coverage module.
- ```tox -e combine-test-reports``` Combines coverage reports from all test commands (for each python version) and 
compiles them into an interactive .html file stored inside '/reports' directory.
- ```tox -e docs``` Uses Sphinx to generate API documentation from Python Google-style docstrings.
- ```tox``` Sequentially carries out the commands above (in the same order). Use ```tox --parallel``` to parallelize 
command execution (may not work on all platforms).

The commands above are considered 'checkout' commands and generally required to pass before every code push. The 
commands below are not intended to be used as-frequently and, therefore, are not part of the 'generic' tox-flow.

- ```tox -e build``` Builds the sdist and the binary wheel for all python version supported by the library.
- ```tox -e upload``` Uploads the sdist and wheels to PIP using twine, if they have not yet been uploaded. Optionally 
use ```tox -e upload -- --replace-token true``` to replace the token stored in .pypirc file.
- ```tox -e recipe``` Uses Grayskull to generate the conda-forge recipe from the latest available PIP-distribution. 
Assumes sdist is included with binary wheels when they are uploaded to PIP.
- ```tox -e export-env``` Exports the os-specific local conda development environment as a .yml and spec.txt file to the
'/envs' directory. This automatically uses the project-specific base-environment-name.
- ```tox -e import-env``` Imports and os-specific conda development environment from the .yml file stored in the '/envs'
directory.
- ```tox -e rename-envs``` Replaces the base-name for all environment files inside the '/envs' directory. Remember to 
also change the base-name argument of the export-env command.

### Environments

All environments used during development are exported as .yml files and as spec.txt files to the [envs](envs) folder. 
The environment snapshots were taken on each of the three supported OS families: Windows 11, OSx 14.5 and 
Ubuntu Cinnamon 24.04 LTS.

To install the development environment for your OS:

1. Download this repository to your local machine using your preferred method, such as git-cloning.
2. ```cd``` into the [envs](envs) folder.
3. Use one of the installation methods below:
   1. **_Preferred Method_**: Install [tox](https://tox.wiki/en/latest/config.html#provision_tox_env) or use another 
   environment with already installed tox and call ```tox -e import-env```.
   2. Alternative Method: Run ```conda env create -f ENVNAME.yml``` or ```mamba env create -f ENVNAME.yml```. 
   Replace 'ENVNAME.yml' with the name of the environment you want to install (YOUR_ENV_NAME_osx for OSx, 
   YOUR_ENV_NAME_win64 for Windows and YOUR_ENV_NAME_lin64 for Linux).

**Note:** the OSx environment was built against M1 (Apple Silicon) platform and may not work on Intel-based Apple 
devices.

___

## Authors

- YOUR_AUTHOR_NAME.
___

## License

This project is licensed under the GPL3 License: see the [LICENSE](LICENSE) file for details.
___

## Acknowledgments

- All Sun Lab [members](https://neuroai.github.io/sunlab/people) for providing the inspiration and comments during the
  development of this library.
