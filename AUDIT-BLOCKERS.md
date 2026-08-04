# Audit blockers

Findings from the documentation fact-check and the style-compliance sweep that were NOT applied, because each either
changes a public contract, requires a dependency the project does not declare, contradicts a finding from the sibling
audit, or is a restructuring large enough to warrant a separate review. Every other finding from both audits was
applied on this branch.

---

## 1. `CONTEXT_SETTINGS` visibility tier contradicts the Click reference example

**Audit:** style. **Category:** CONFLICT. **Location:** `src/ataraxis_automation/cli.py:43`.

`/python-style` states that a symbol referenced only inside its defining module MUST carry a leading underscore, and
`CONTEXT_SETTINGS` has exactly one consumer, `cli.py:47`, inside its own module. The four sibling constants at
`cli.py:34-41` already follow that tier. The same skill's Click reference, however, shows the bare public spelling
verbatim in its own example, so the two halves of one skill disagree.

**Why it needs approval:** renaming to `_CONTEXT_SETTINGS` demotes a public name and requires regenerating `cli.pyi`,
which currently declares `CONTEXT_SETTINGS: dict[str, int]`.

**Change if approved:** rename at `cli.py:43` and `cli.py:47`, then run `tox -e stubs`. If the Click example is
authoritative instead, the divergence should be raised with the skill owner so one of the two statements is corrected.

---

## 2. `conf.py` version extraction cannot use `importlib_metadata`

**Audit:** style. **Category:** BLOCKING. **Location:** `docs/source/conf.py:2` and `:9`.

`/api-docs` requires the version to be extracted through the module-qualified `importlib_metadata` backport, while the
file imports the stdlib `importlib.metadata`.

**Why it was not applied:** the backport is neither installed nor declared. `import importlib_metadata` raises
`ModuleNotFoundError`, and `grep importlib pyproject.toml` returns nothing. Applying the change as written would break
`tox -e docs` on this machine. The skill's companion checklist item assumes the package "reaches conf.py through
ataraxis-automation", and that premise does not hold here, so the fix is a dependency decision rather than an edit.

**Change if approved:** add `importlib_metadata` to `[project].dependencies`, then set `conf.py:2` to
`import importlib_metadata` and `conf.py:9` to `release = importlib_metadata.version("ataraxis-automation")`.
Alternatively, raise with the skill owner whether the stdlib module is acceptable for projects on Python 3.12 and
above, where `importlib.metadata` is always present.

---

## 3. Coverage and build task descriptions: fact-check and style audits disagree

**Audits:** facts and style. **Category:** CONFLICT. **Locations:** `tox.ini:65-69` and `tox.ini:88-90`.

The fact-check found both descriptions factually incomplete: the coverage description omitted the `junitparser merge`
and `coverage xml` commands, and the build description omitted the `dist` cleanup. Those omissions were fixed on this
branch. The style sweep then flagged the very sentences that fix added, because `/tox-config` states a description is
one sentence, two at most, and must not narrate the commands declared below it.

**Resolution taken:** the factual version was kept, because `/audit-facts` fixes are applied before `/audit-style` and
a description that is short but wrong is the worse failure. The style finding is recorded here rather than discarded.

**Decision needed:** either accept the longer descriptions as the local exception, or shorten them and accept that the
task's full output surface is documented only by the commands block.

---

## 4. `welcome.rst` scope sentence: fact-check and style audits disagree

**Audits:** facts and style. **Category:** CONFLICT. **Location:** `docs/source/welcome.rst:9-10`.

The fact-check found the original sentence, "This website only contains the API documentation for the classes and
methods offered by this library", factually wrong: `api.rst:12-17` renders a second top-level section documenting every
`automation-cli` command through the `click` directive. The sentence was corrected on this branch. The style sweep then
flagged the correction for deviating from the `/api-docs` template, which carries the original wording verbatim.

**Resolution taken:** the corrected, factually accurate sentence was kept.

**Decision needed:** the `/api-docs` template sentence appears to be wrong for every project whose `api.rst` includes a
`click` directive, so the template itself may need updating rather than this file.

---

## 5. README structural reduction

**Audit:** style. **Category:** STANDARD. **Location:** `README.md:129-561`.

The two tox task sections span 433 of the README's 679 lines and reproduce a full `[testenv:...]` block for all 15
environments, which `/readme-style` judges disproportionate.

**Why it was not applied:** removing roughly 400 lines of the project's primary documentation is an editorial decision
about how much of the tox suite the README should carry, not a mechanical style fix, and it is far larger than every
other finding in this run.

**Change if approved:** keep one representative `[testenv:...]` block to show the invocation shape, replace the
remaining fourteen with per-task prose plus a link to `tox.ini`, and drop the sentences the Developers environments
table already states.

---

## 6. README CLI command overview table

**Audit:** style. **Category:** STANDARD. **Location:** `README.md:93-105`.

`/readme-style` requires a CLI section to carry a command overview table with one row per registered command, and to
title the subsection `### CLI Commands`.

**Why it was not applied:** the rename changes a Table of Contents anchor that the README links to internally, and the
table duplicates content that would go stale against `cli.py` unless it is generated. Both are worth a deliberate
decision.

**Change if approved:** add the overview table under the CLI subsection, rename the heading to `### CLI Commands`, and
update the matching Table of Contents entry.

---

## 7. Acknowledgments bullet naming the lab

**Audit:** style. **Category:** STANDARD. **Location:** `README.md:671-672`.

`/readme-style` prescribes the standard opening bullet, "All individuals who contributed to the development of this
library, directly or indirectly", where the file names lab members instead.

**Why it was not applied:** the acknowledgments section is an attribution context, which the project's own terminology
rule exempts, and rewriting attribution text is the maintainer's call rather than an audit's.

---

## 8. Smaller style items left for a deliberate pass

Applied nothing for these, each recorded with its location so it can be picked up:

- `tests/automation_test.py` private helpers are interleaved among the public tests rather than collected below them.
  Moving `_error_format`, `_write_pyproject_toml`, `_write_tox_ini`, `_capture_exc_info`, and `_build_environment` into
  one trailing block is a large reordering of a 2000-line file and was judged too broad to fold into this commit.
- `tests/automation_test.py:1498` and the surrounding block call project helpers positionally where the checklist
  requires keyword arguments.
- `tests/automation_test.py:962` places the `documentation_directory` fixture away from the fixture block at the top.
- `CLAUDE.md:29` heading `## Dependency position` does not match the canonical `## Cross-referenced library
  verification` spelling. The section's content is the inverse of that heading, since this project has no ataraxis
  dependencies, so the rename needs a judgment call.
- `CLAUDE.md:54` and `:160` carry a trailing distribution note that `/skill-design` would promote into its own
  `## Distribution model` section.
- `pyproject.toml:170` declares an 18-entry `tests/**/*.py` ignore corpus. The lint task now covers `./tests`, so the
  pairing this finding asked for exists, but the corpus itself has not been re-verified entry by entry.
