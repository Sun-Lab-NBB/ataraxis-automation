---
name: designing-skills
description: >-
  Generates, updates, and verifies Claude Code skill files and CLAUDE.md project instructions. Covers SKILL.md
  structure, YAML frontmatter, formatting conventions, inter-skill relationships, scope declarations, and
  verification checklists. Use when creating new skills, modifying existing skills, updating CLAUDE.md files,
  or when the user asks about skill conventions.
---

# Skill design

Generates, updates, and verifies Claude Code skill and project instruction files.

**You MUST read this entire skill before creating or modifying any skill file or CLAUDE.md.** The verification
checklists at the end are mandatory before submitting any work.

---

## File types

This skill covers two types of Claude instruction files:

| File Type  | Location          | Purpose                                        |
|------------|-------------------|------------------------------------------------|
| SKILL.md   | `skills/*/`       | Skill-specific instructions loaded on demand   |
| CLAUDE.md  | Project root      | Project-wide instructions loaded every session |

---

## Design principles

Effective skills are focused, composable, and verifiable. Apply these principles when designing any skill.

### Single responsibility

Each skill addresses one well-defined concern. A skill that tries to do too much becomes difficult to maintain and
triggers inconsistently. If a skill covers multiple unrelated tasks, split it.

**Scope declaration**: Every skill should make clear what it DOES and DOES NOT cover. This prevents scope creep and
helps the agent select the right skill for the task.

### Composability

Skills should work independently and combine freely without conflicts. No skill should assume or require another
skill's internal state. If skill A needs information from skill B, it should reference skill B explicitly rather
than duplicating its content.

**Test**: Can this skill be invoked in isolation and still produce correct results? If not, it has a hidden
dependency that should be made explicit.

### Terminology consistency

Every concept in a skill should have ONE canonical name used consistently:

- Do not use synonyms interchangeably ("skill" vs "agent" vs "role" for the same concept)
- Do not overload terms (using "template" to mean both a file structure and a code pattern)
- Define terms at their canonical home and reference from elsewhere, never duplicate definitions

### Verifiability

A skill is verifiable when its output can be checked against concrete criteria. Every skill should include a
verification checklist that the agent completes before submitting work. Checklists prevent subjective quality
assessments and ensure consistent compliance.

### Progressive disclosure

Keep SKILL.md under 500 lines. Split detailed reference material into separate files:

```
skill-name/
├── SKILL.md              # Main instructions (loaded when triggered)
├── REFERENCE.md          # Detailed reference (loaded as needed)
└── EXAMPLES.md           # Usage examples (loaded as needed)
```

Reference supplementary files using standard Markdown links: `[REFERENCE.md](REFERENCE.md)`. References should be
one level deep from SKILL.md (no chains of references to references).

---

## SKILL.md conventions

### YAML frontmatter

Every SKILL.md requires YAML frontmatter with `name` and `description`. Add `user_invocable: true` for skills that
the user can invoke directly via `/skill-name`.

```yaml
---
name: exploring-codebase
description: >-
  Performs in-depth codebase exploration at the start of a coding session. Builds comprehensive
  understanding of project structure, architecture, key components, and patterns. Use at session
  start or when the user asks to understand the codebase.
user_invocable: true
---
```

**Name**: Use gerund form (verb + -ing), lowercase with hyphens. Examples: `exploring-codebase`,
`applying-sun-lab-style`, `committing-changes`, `designing-skills`.

**Description**: Write in third person. Include both what the skill does and when to use it. End with explicit
trigger conditions ("Use when...").

### Structure template

A well-structured skill follows this layout:

```markdown
# Skill title

Brief description of the skill's purpose (one sentence).

---

## Scope

What this skill covers and what it does NOT cover. Explicit boundaries prevent scope creep.

---

## Workflow

Step-by-step instructions the agent follows when the skill is invoked.

---

## Rules / conventions

Detailed rules, formatting requirements, and examples.

---

## Related skills

Table of skills this skill interacts with and how.

---

## Verification checklist

Mandatory checklist the agent completes before submitting work.
```

Not every skill requires all sections. Omit sections that do not apply, but always include the workflow (or
equivalent main content) and verification checklist.

### Scope declarations

Every skill should declare its boundaries. This prevents the agent from drifting outside the skill's purpose.

**Example:**

```markdown
## Scope

**Covers:**
- Generating commit messages from local git changes
- Staging and committing files

**Does not cover:**
- Pushing to remote repositories
- Creating pull requests
- Branch management
```

### Inter-skill references

When a skill relates to other skills, declare the relationship explicitly using a table:

```markdown
## Related skills

| Skill               | Relationship                                                |
|---------------------|-------------------------------------------------------------|
| `/sun-lab-style`    | Provides coding conventions that inform code review skills  |
| `/commit`           | Should be invoked after completing code changes             |
| `/explore-codebase` | Provides project context that informs implementation skills |
```

This helps the agent understand the skill ecosystem and suggest appropriate next steps.

### Proactive behavior

Skills may declare when the agent should proactively offer to invoke them. Place this guidance in a dedicated
section at the end of the skill, before the verification checklist.

**Example:**

```markdown
## Proactive behavior

After completing substantial code changes, proactively offer to generate a commit message.
Do NOT invoke automatically. Always present the suggestion and wait for user approval.
```

### Workflow chaining

When a skill's workflow naturally leads to another skill, document this as a final workflow step.

**Example:**

```markdown
### Step 4: Suggest next steps

After completing the implementation, suggest:
- `/commit` to commit the changes
- Running tests if applicable
```

---

## Formatting conventions

### Line length

All skill and asset Markdown files must adhere to the **120 character line limit**. This matches the Python code
formatting standard.

- Wrap prose text at 120 characters
- Break long sentences at natural boundaries (after punctuation, between clauses)
- Code blocks may exceed 120 characters only when necessary for readability
- Tables may exceed 120 characters when proper column alignment aids clarity

### Table formatting

Use **pretty table formatting** with proper column alignment:

**Good:**

```markdown
| Field  | Type  | Required | Description                              |
|--------|-------|----------|------------------------------------------|
| `name` | str   | Yes      | Visual identifier (e.g., 'A', 'Gray')    |
| `code` | int   | Yes      | Unique uint8 code for MQTT communication |
```

**Avoid:**

```markdown
| Field | Type | Required | Description |
|---|---|---|---|
| `name` | str | Yes | Visual identifier |
```

**Rules:**

1. Align all `|` characters vertically
2. Size each column to fit its widest cell, but no wider
3. Use dashes (`-`) that span the full column width
4. Pad narrower cells to match the column width
5. Use backticks for field names, types, and values

### Code blocks

Use fenced code blocks with language identifiers:

````markdown
```yaml
cues:
  - name: "A"
    code: 1
```

```python
def process_data() -> None:
    pass
```
````

### Section organization

Separate major sections with horizontal rules (`---`). Use `##` for major sections and `###` for subsections.

### Voice

Skill files use two voice styles:

- **Descriptive content**: Third person imperative. Example: "Extracts zone positions from configuration files."
- **Agent directives**: Second person with "You MUST", "You should". Example: "You MUST use the Task tool."

### Sentence case

Use sentence case for all section headers ("Verification checklist", not "Verification Checklist").

---

## CLAUDE.md conventions

The `CLAUDE.md` file at the project root provides project-wide instructions loaded at the start of every session.

### Structure

CLAUDE.md files use the following section order:

1. **Title**: `# Claude Code Instructions`
2. **Session Start Behavior**: What Claude should do at session start
3. **Style Guide Compliance**: Required style conventions
4. **Cross-Referenced Library Verification**: Dependencies and version checking (if applicable)
5. **Available Skills**: List of project skills with descriptions
6. **MCP Server**: MCP server documentation (if applicable)
7. **Downstream Library Integration**: Related libraries and coordination (if applicable)
8. **Project Context**: Architecture, key areas, patterns, and standards

### Formatting rules

CLAUDE.md follows the same formatting conventions as skill files:

- **Line length**: 120 characters maximum
- **Tables**: Pretty formatting with aligned columns
- **Code blocks**: Include language identifiers
- **Section separators**: Use `##` headings (no horizontal rules between sections)

### Voice

- **Descriptive content**: Third person. Example: "This library provides shared assets..."
- **Agent directives**: Second person with emphasis. Example: "You MUST invoke the `/sun-lab-style` skill..."

### Content guidelines

- Keep CLAUDE.md focused on project-specific instructions
- Reference skills rather than duplicating their content
- Include workflow guidance for common tasks (e.g., adding new components)
- Document integration points with other libraries

---

## Related skills

| Skill               | Relationship                                                          |
|---------------------|-----------------------------------------------------------------------|
| `/sun-lab-style`    | Provides formatting conventions that skill files must also follow     |
| `/commit`           | Should be invoked after completing skill file changes                 |
| `/explore-codebase` | Provides project context needed when writing project-specific skills  |

---

## Verification checklist

**You MUST verify your work against the appropriate checklist before submitting.**

### Skill files (SKILL.md)

```
Skill File Compliance:
- [ ] YAML frontmatter with `name` and `description`
- [ ] `user_invocable: true` set if skill is directly invocable via slash command
- [ ] Name uses gerund form (verb + -ing), lowercase with hyphens
- [ ] Description in third person, includes what AND when to use
- [ ] Scope declaration present (what skill covers and does not cover)
- [ ] All lines ≤ 120 characters (tables/code blocks may exceed for clarity)
- [ ] Tables use pretty formatting with aligned columns
- [ ] Major sections separated with horizontal rules (`---`)
- [ ] Code blocks include language identifiers
- [ ] Third person imperative for descriptions
- [ ] Second person for agent directives ("You MUST...")
- [ ] Sentence case for section headers
- [ ] SKILL.md under 500 lines (split to reference files if needed)
- [ ] References one level deep from SKILL.md
- [ ] Inter-skill references documented if applicable
- [ ] Verification checklist included
- [ ] Terminology consistent (no synonyms or overloaded terms)
```

### Project instructions (CLAUDE.md)

```
CLAUDE.md Compliance:
- [ ] Title is `# Claude Code Instructions`
- [ ] All lines ≤ 120 characters (tables/code blocks may exceed for clarity)
- [ ] Tables use pretty formatting with aligned columns
- [ ] Code blocks include language identifiers
- [ ] Third person for descriptive content
- [ ] Second person with emphasis for directives ("You MUST...")
- [ ] Sections follow recommended order (Session Start, Style Guide, Skills, etc.)
- [ ] Workflow guidance included for common extension tasks
- [ ] Technical claims cross-referenced against codebase
- [ ] New skills listed in Available Skills table
```
