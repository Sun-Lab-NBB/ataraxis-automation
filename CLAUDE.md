# Claude Code Instructions

## Session Start Behavior

At the beginning of each coding session, before making any code changes, you should build a comprehensive
understanding of the codebase by invoking the `/explore-codebase` skill.

This ensures you:
- Understand the project architecture before modifying code
- Follow existing patterns and conventions
- Don't introduce inconsistencies or break integrations

## Style Guide Requirements

You MUST invoke the appropriate skill before performing ANY of the following tasks:

| Task                                    | Skill to invoke    |
|-----------------------------------------|--------------------|
| Writing or modifying Python code        | `/python-style`    |
| Writing or modifying C# code            | `/csharp-style`    |
| Writing or modifying README files       | `/readme-style`    |
| Writing or modifying pyproject.toml     | `/pyproject-style` |
| Writing git commit messages             | `/commit`          |
| Writing or modifying Sphinx docs files  | `/api-docs`        |
| Writing or modifying skill files        | `/skill-design`    |

This is non-negotiable. Each skill contains verification checklists that you MUST complete before submitting any work.
Failure to invoke the appropriate skill results in style violations.

## Cross-Referenced Library Verification

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

## Available Skills

| Skill               | Description                                                          |
|---------------------|----------------------------------------------------------------------|
| `/explore-codebase` | Perform in-depth codebase exploration at session start               |
| `/python-style`     | Apply Sun Lab Python coding conventions (REQUIRED for Python code)   |
| `/csharp-style`     | Apply Sun Lab C# coding conventions (REQUIRED for C# code)           |
| `/readme-style`     | Apply Sun Lab README conventions (REQUIRED for README files)         |
| `/pyproject-style`  | Apply Sun Lab pyproject.toml conventions (REQUIRED for pyproject)    |
| `/commit`           | Generate style-compliant commit messages for local changes           |
| `/api-docs`         | Apply Sun Lab API documentation conventions (REQUIRED for docs)      |
| `/skill-design`     | Generate, update, and verify skill files and CLAUDE.md               |

## Project Context

This is **ataraxis-automation**, a Python library that supports tox-based development automation pipelines used by all
Sun Lab (NeuroAI) projects at Cornell University. It provides a CLI (`automation-cli`) that abstracts project
environment manipulation and facilitates development tasks such as linting, typing, testing, documentation, and
building. This library also serves as the shared Claude Code plugin, distributing the `/explore-codebase`,
`/python-style`, `/csharp-style`, `/readme-style`, `/pyproject-style`, `/api-docs`, `/commit`, and `/skill-design`
skills to all
downstream Sun Lab repositories.

**Note:** The `/csharp-style` skill applies to C# Unity projects (e.g., `sl-unity-tasks`). It enforces conventions
consistent with the C++ and Python style guides used across all Sun Lab projects.

### Key Areas

| Directory                          | Purpose                                                 |
|------------------------------------|---------------------------------------------------------|
| `src/ataraxis_automation/`         | Main library source code                                |
| `.claude/skills/explore-codebase/` | Codebase exploration skill (shared via plugin)          |
| `.claude/skills/python-style/`     | Python code style skill (shared via plugin)             |
| `.claude/skills/readme-style/`     | README style skill (shared via plugin)                  |
| `.claude/skills/commit/`           | Commit message generation skill (shared via plugin)     |
| `.claude/skills/pyproject-style/`  | pyproject.toml style skill (shared via plugin)          |
| `.claude/skills/api-docs/`         | API documentation style skill (shared via plugin)       |
| `.claude/skills/csharp-style/`     | C# code style skill (shared via plugin)                 |
| `.claude/skills/skill-design/`     | Skill and CLAUDE.md authoring skill (shared via plugin) |
| `.claude-plugin/`                  | Claude Code plugin configuration                        |
| `tests/`                           | Test suite                                              |
| `envs/`                            | Pre-configured development environment .yml files       |
| `docs/`                            | Sphinx documentation source                             |

### Architecture

- **CLI Module** (`cli.py`): Click-based CLI with commands for stub management, PyPI token handling, project
  installation, and environment lifecycle management. Entry point is `automation-cli`.
- **Automation Module** (`automation.py`): Core logic including the `ProjectEnvironment` dataclass, project directory
  resolution, dependency parsing, stub file management, and OS-specific mamba/uv command generation.
- **Plugin Architecture** (`.claude-plugin/`): Registers this library as a Claude Code plugin, making the
  `.claude/skills/` directory available to all downstream projects that install the plugin.
- **No MCP Server**: This library does not provide an MCP server.

### Key Patterns

- **Multi-OS Support**: Detects Windows, Linux, and macOS via `sys.platform` and generates platform-specific commands
  for mamba and uv operations.
- **Mamba/Conda Integration**: Multi-method environment directory detection supporting CONDA_PREFIX, Miniforge paths,
  and standard installation locations.
- **uv for Package Installation**: Uses uv instead of pip for faster package installation.
- **Stub File Management**: Automated `.pyi` stub generation and distribution with OS-specific duplicate handling.
- **ProjectEnvironment Dataclass**: Encapsulates all environment commands (create, remove, install, export, etc.) into
  a single frozen dataclass.

### Core Components

| Component            | File             | Purpose                                            |
|----------------------|------------------|----------------------------------------------------|
| CLI commands         | `cli.py`         | Click-based command-line interface                 |
| ProjectEnvironment   | `automation.py`  | Dataclass encapsulating environment commands       |
| resolve_project_dir  | `automation.py`  | Validates project directory structure              |
| resolve_library_root | `automation.py`  | Finds library __init__.py for stub placement       |
| move_stubs           | `automation.py`  | Distributes .pyi files to src directories          |
| verify_pypirc        | `automation.py`  | Validates PyPI token configuration                 |
| format_message       | `automation.py`  | Wraps text at 120 characters for CLI output        |

### Code Standards

- MyPy strict mode with full type annotations
- Google-style docstrings
- 120 character line limit
- See `/python-style` for complete conventions

### Workflow Guidance

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

**Modifying shared skills:**

1. Review the skill files in `.claude/skills/` and the plugin configuration in `.claude-plugin/plugin.json`
2. Invoke `/skill-design` for conventions on frontmatter, structure, and formatting
3. Changes to shared skills affect ALL downstream Sun Lab repositories that use the plugin
4. Test skill changes by invoking them in this repository before committing
