# Claude Code Instructions

## Session start behavior

At the beginning of each coding session, before making any code changes, you should build a comprehensive
understanding of the codebase by invoking the `/explore-codebase` skill.

This ensures you:
- Understand the project architecture before modifying code
- Follow existing patterns and conventions
- Don't introduce inconsistencies or break integrations

## Style guide requirements

You MUST invoke the appropriate skill before performing ANY of the following tasks:

| Task                                    | Skill to invoke     |
|-----------------------------------------|---------------------|
| Writing or modifying Python code        | `/python-style`     |
| Writing or modifying C++ code           | `/cpp-style`        |
| Writing or modifying C# code            | `/csharp-style`     |
| Writing or modifying README files       | `/readme-style`     |
| Writing or modifying pyproject.toml     | `/pyproject-style`  |
| Writing git commit messages             | `/commit`           |
| Writing or modifying Sphinx docs files  | `/api-docs`         |
| Creating or verifying project structure | `/project-layout`   |
| Writing or modifying tox.ini files      | `/tox-config`       |
| Writing or modifying skill files        | `/skill-design`     |

This is non-negotiable. Each skill contains verification checklists that you MUST complete before submitting any work.
Failure to invoke the appropriate skill results in style violations.

## Cross-referenced library verification

Sun Lab projects often depend on other `ataraxis-*` or `sl-*` libraries. These libraries may be stored locally in the
same parent directory as this project (`/home/cyberaxolotl/Desktop/GitHubRepos/`).

**Before writing code that interacts with a cross-referenced library, you MUST:**

1. **Check for local version**: Look for the library in the parent directory (e.g., `../ataraxis-base-utilities/`,
   `../ataraxis-time/`).

2. **Compare versions**: If a local copy exists, compare its version against the latest release or main branch on
   GitHub:
   - Read the local `pyproject.toml` to get the current version
   - Use `gh api repos/Sun-Lab-NBB/{repo-name}/releases/latest` to check the latest release
   - Alternatively, check the main branch version on GitHub

3. **Handle version mismatches**: If the local version differs from the latest release or main branch, notify the user
   with the following options:
   - **Use online version**: Fetch documentation and API details from the GitHub repository
   - **Update local copy**: The user will pull the latest changes locally before proceeding

4. **Proceed with correct source**: Use whichever version the user selects as the authoritative reference for API
   usage, patterns, and documentation.

**Why this matters**: Skills and documentation may reference outdated APIs. Always verify against the actual library
state to prevent integration errors.

## Available skills

| Skill               | Description                                                        |
|---------------------|--------------------------------------------------------------------|
| `/explore-codebase` | Perform in-depth codebase exploration at session start             |
| `/python-style`     | Apply Sun Lab Python coding conventions (REQUIRED for Python code) |
| `/cpp-style`        | Apply Sun Lab C++ coding conventions (REQUIRED for C++ code)       |
| `/csharp-style`     | Apply Sun Lab C# coding conventions (REQUIRED for C# code)         |
| `/readme-style`     | Apply Sun Lab README conventions (REQUIRED for README files)       |
| `/pyproject-style`  | Apply Sun Lab pyproject.toml conventions (REQUIRED for pyproject)  |
| `/commit`           | Generate style-compliant commit messages for local changes         |
| `/api-docs`         | Apply Sun Lab API documentation conventions (REQUIRED for docs)    |
| `/project-layout`   | Apply Sun Lab project directory structure conventions              |
| `/tox-config`       | Apply Sun Lab tox.ini conventions (REQUIRED for tox configuration) |
| `/skill-design`     | Generate, update, and verify skill files and CLAUDE.md             |

## Project context

This is **ataraxis-automation**, a Python library that supports tox-based development automation pipelines used by all
Sun Lab (NeuroAI) projects at Cornell University. It provides a CLI (`automation-cli`) that abstracts project
environment manipulation and facilitates development tasks such as linting, typing, testing, documentation, and
building.

**Note:** The `/cpp-style` skill applies to both C++ embedded projects (e.g., `ataraxis-transport-layer-mc`,
`ataraxis-micro-controller`, `sl-micro-controllers`) and C++ Python extension projects (e.g., `ataraxis-time`). The
`/csharp-style` skill applies to C# Unity projects (e.g., `sl-unity-tasks`). Both enforce conventions consistent with
the Python style guide used across all Sun Lab projects.

### Key areas

| Directory                  | Purpose                                           |
|----------------------------|---------------------------------------------------|
| `src/ataraxis_automation/` | Main library source code                          |
| `tests/`                   | Test suite                                        |
| `envs/`                    | Pre-configured development environment .yml files |
| `docs/`                    | Sphinx documentation source                       |

### Architecture

- **CLI Module** (`cli.py`): Click-based CLI with commands for stub management, PyPI token handling, project
  installation, and environment lifecycle management. Entry point is `automation-cli`.
- **Automation Module** (`automation.py`): Core logic including the `ProjectEnvironment` dataclass, project directory
  resolution, dependency parsing, stub file management, and OS-specific mamba/uv command generation.
- **No MCP Server**: This library does not provide an MCP server.

### Key patterns

- **Multi-OS Support**: Detects Windows, Linux, and macOS via `sys.platform` and generates platform-specific commands
  for mamba and uv operations.
- **Mamba/Conda Integration**: Multi-method environment directory detection supporting CONDA_PREFIX, Miniforge paths,
  and standard installation locations.
- **uv for Package Installation**: Uses uv instead of pip for faster package installation.
- **Stub File Management**: Automated `.pyi` stub generation and distribution with OS-specific duplicate handling.
- **ProjectEnvironment Dataclass**: Encapsulates all environment commands (create, remove, install, export, etc.) into
  a single frozen dataclass.

### Core components

| Component            | File             | Purpose                                            |
|----------------------|------------------|----------------------------------------------------|
| CLI commands         | `cli.py`         | Click-based command-line interface                 |
| ProjectEnvironment   | `automation.py`  | Dataclass encapsulating environment commands       |
| resolve_project_dir  | `automation.py`  | Validates project directory structure              |
| resolve_library_root | `automation.py`  | Finds library __init__.py for stub placement       |
| move_stubs           | `automation.py`  | Distributes .pyi files to src directories          |
| verify_pypirc        | `automation.py`  | Validates PyPI token configuration                 |
| format_message       | `automation.py`  | Wraps text at 120 characters for CLI output        |

### Code standards

- MyPy strict mode with full type annotations
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
4. Changes to documentation affect the hosted Netlify site after rebuild

**Note:** Claude Code skills have been moved to the main
[ataraxis](https://github.com/Sun-Lab-NBB/ataraxis) repository. Skill modifications should be made there.
