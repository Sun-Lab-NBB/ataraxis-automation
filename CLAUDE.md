# Claude Code Instructions

## Session start behavior

At the beginning of each coding session, before making any code changes, you should build a comprehensive
understanding of the codebase by invoking the `/explore-codebase` skill.

## Style guide compliance

You MUST invoke the appropriate skill before performing ANY of the following tasks:

| Task                                    | Skill to invoke      |
|-----------------------------------------|----------------------|
| Writing or modifying Python code        | `/python-style`      |
| Writing or modifying C++ code           | `/cpp-style`         |
| Writing or modifying C# code            | `/csharp-style`      |
| Writing or modifying README files       | `/readme-style`      |
| Writing or modifying pyproject.toml     | `/pyproject-style`   |
| Writing or modifying PlatformIO configs | `/platformio-config` |
| Committing local changes                | `/commit`            |
| Writing or modifying Sphinx docs files  | `/api-docs`          |
| Creating or verifying project structure | `/project-layout`    |
| Writing or modifying tox.ini files      | `/tox-config`        |
| Writing or modifying skill files        | `/skill-design`      |

This is non-negotiable. Each skill contains verification checklists that you MUST complete before submitting any work.
Failure to invoke the appropriate skill results in style violations.

## Cross-referenced library verification

Unlike most Ataraxis framework and Sollertia platform projects, **ataraxis-automation has no `ataraxis-*` or
`sollertia-*` library dependencies**. Its runtime dependencies are exclusively third-party development tools (Click,
pytest, Sphinx, mypy, ruff, build, twine, and similar), so there is no cross-referenced ataraxis or sollertia library
to locate or version-check before writing code here.

The dependency relationship is inverted: every other Ataraxis framework and Sollertia platform project depends on
ataraxis-automation as a **development-time** automation dependency. Each project's `tox` tasks install it (often as
the sole dependency) to drive linting, typing, testing, documentation, and build pipelines. It is never a runtime
dependency of those projects.

Dependency direction across the two platforms is one-way: Sollertia platform libraries may depend on Ataraxis
framework libraries, but Ataraxis framework libraries never depend on Sollertia platform libraries.

## Available skills

| Skill                   | Description                                                                   |
|-------------------------|-------------------------------------------------------------------------------|
| `/explore-codebase`     | Perform in-depth codebase exploration at session start                        |
| `/explore-dependencies` | Build a live API snapshot of installed ataraxis dependencies                  |
| `/python-style`         | Apply Ataraxis framework Python coding conventions (REQUIRED for Python code) |
| `/cpp-style`            | Apply Ataraxis framework C++ coding conventions (REQUIRED for C++ code)       |
| `/csharp-style`         | Apply Ataraxis framework C# coding conventions (REQUIRED for C# code)         |
| `/readme-style`         | Apply Ataraxis framework README conventions (REQUIRED for README files)       |
| `/pyproject-style`      | Apply Ataraxis framework pyproject.toml conventions (REQUIRED for pyproject)  |
| `/platformio-config`    | Apply PlatformIO platformio.ini and library.json conventions                  |
| `/commit`               | Stage all local changes and create a style-compliant commit (no push)         |
| `/pr`                   | Draft a style-compliant pull request summary                                  |
| `/release`              | Draft style-compliant release notes for a new release                         |
| `/api-docs`             | Apply Ataraxis framework API documentation conventions (REQUIRED for docs)    |
| `/project-layout`       | Apply Ataraxis framework project directory structure conventions              |
| `/tox-config`           | Apply Ataraxis framework tox.ini conventions (REQUIRED for tox configuration) |
| `/skill-design`         | Generate, update, and verify skill files and CLAUDE.md                        |
| `/audit-facts`          | Fact-check documentation against source code (findings only)                  |
| `/audit-correctness`    | Hunt for active and latent bugs in source code (findings only)                |
| `/audit-performance`    | Hunt for numeric, algorithmic, and memory costs in source code (findings only)|
| `/audit-style`          | Audit files for style and convention compliance (findings only)               |
| `/audit-project`        | Orchestrate the four audits and merge their findings (findings only)          |

## Project context

This is **ataraxis-automation**, a Python library that supports tox-based development automation pipelines used by all
Ataraxis framework and Sollertia platform projects at Cornell University. It provides a CLI (`automation-cli`) that
abstracts project environment manipulation and facilitates development tasks such as linting, typing, testing,
documentation, and building.

**Note:** The `/cpp-style` skill applies to both C++ embedded projects (e.g., `ataraxis-transport-layer-mc`,
`ataraxis-micro-controller`, `sollertia-micro-controllers`) and C++ Python extension projects (e.g.,
`ataraxis-time`). The `/csharp-style` skill applies to C# Unity projects (e.g., `sollertia-virtual-reality`).
Both enforce conventions consistent with the Python style guide used across all Ataraxis framework projects.

### Key areas

| Directory                  | Purpose                                           |
|----------------------------|---------------------------------------------------|
| `src/ataraxis_automation/` | Main library source code                          |
| `tests/`                   | Test suite                                        |
| `envs/`                    | Pre-configured development environment .yml files |
| `docs/`                    | Sphinx documentation source                       |

### Architecture

- **CLI Module** (`cli.py`): Click-based CLI with commands for stub management, PyPI and Netlify token handling, PyPI
  upload, Netlify documentation deployment, project installation, and environment lifecycle management. Entry point is
  `automation-cli`.
- **Automation Module** (`automation.py`): Core logic including the `ProjectEnvironment` dataclass, project directory
  resolution, dependency parsing, stub file management, shared PyPI and Netlify credential storage and validation,
  Netlify documentation deployment, and OS-specific mamba/uv command generation.
- **No MCP server**: This library does not provide an MCP server. It is consumed through the `automation-cli` entry
  point.

### Key patterns

- **Multi-OS Support**: Detects Windows, Linux, and macOS via `sys.platform` and generates platform-specific commands
  for mamba and uv operations.
- **Mamba/Conda Integration**: Multi-method environment directory detection supporting CONDA_PREFIX, Miniforge paths,
  and standard installation locations.
- **uv for Package Installation**: Uses uv instead of pip for faster package installation.
- **Stub File Management**: Automated distribution and purging of `stubgen`-generated `.pyi` files with OS-specific
  duplicate handling.
- **ProjectEnvironment Dataclass**: Encapsulates the mamba and uv commands that manage the project environment as
  fields of a single frozen dataclass, and performs the environment export through the `export_environment()` method,
  which invokes mamba directly and writes the .yml file atomically.

### Core components

| Component                            | File            | Purpose                                               |
|--------------------------------------|-----------------|-------------------------------------------------------|
| CLI commands                         | `cli.py`        | Click-based command-line interface                    |
| ProjectEnvironment                   | `automation.py` | Dataclass encapsulating environment commands          |
| resolve_project_directory            | `automation.py` | Validates Python project directory structure          |
| resolve_documented_project_directory | `automation.py` | Validates docs-building project directory structure   |
| resolve_library_root                 | `automation.py` | Finds library __init__.py for stub placement          |
| move_stubs                           | `automation.py` | Distributes .pyi files to src directories             |
| resolve_application_directory        | `automation.py` | Resolves the host-wide shared credential directory    |
| verify_pypirc                        | `automation.py` | Validates PyPI token configuration                    |
| verify_netlifyrc                     | `automation.py` | Validates Netlify token configuration                 |
| deploy_documentation                 | `automation.py` | Uploads built HTML docs to the project's Netlify site |
| format_message                       | `automation.py` | Wraps text at 120 characters for CLI output           |

### Code standards

- mypy strict mode with full type annotations
- Google-style docstrings
- 120 character line limit
- See `/python-style` for complete conventions

### Workflow guidance

**Modifying CLI commands:**

1. Review `src/ataraxis_automation/cli.py` for existing command patterns
2. Follow Click decorator conventions used by other commands
3. Use `format_message()` and `colorize_message()` for consistent output formatting
4. Add corresponding helper functions in `automation.py` for non-trivial logic

**Modifying environment management:**

1. Review the `ProjectEnvironment` dataclass in `automation.py` for current command generation
2. Understand the OS-specific branching (`sys.platform` checks)
3. Test changes across supported platforms (Linux, macOS, Windows)
4. Maintain compatibility with mamba/conda and uv tooling

**Modifying API documentation:**

1. Invoke `/api-docs` for conventions on conf.py, RST structure, and Doxygen integration
2. Determine the project archetype (Python-only, C++-only, or hybrid)
3. Follow the templates in the skill's reference files for new documentation
4. Changes to documentation reach the hosted Netlify site after `tox -e docs` rebuilds it and `tox -e deploy` uploads
   it

**Note:** Claude Code skills live in the main
[ataraxis](https://github.com/Sun-Lab-NBB/ataraxis) repository. Make skill modifications there.
