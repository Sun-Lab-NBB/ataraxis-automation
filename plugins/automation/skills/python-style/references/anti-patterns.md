# Anti-patterns and examples

Common anti-patterns to avoid and input/output transformation examples for Sun Lab Python code.

---

## Input/output examples

Transform code to match Sun Lab style:

| Input (What you wrote)                 | Output (Correct style)                                         |
|----------------------------------------|----------------------------------------------------------------|
| `def calc(x):`                         | `def calculate_value(x: float) -> float:`                      |
| `pos = get_pos()`                      | `position = get_position()`                                    |
| `np.zeros((4,), np.float32)`           | `np.zeros((4,), dtype=np.float32)`                             |
| `# set x to 5`                         | Remove comment (self-explanatory code)                         |
| `data: NDArray`                        | `data: NDArray[np.float32]`                                    |
| `"""A class that processes data."""`   | `"""Processes experimental data."""`                           |
| `"""Whether to enable filtering."""`   | `"""Determines whether to enable filtering."""`                |
| `raise ValueError("Bad input")`        | `console.error(message="...", error=ValueError)`               |
| `print("Starting...")`                 | `console.echo(...)` (exception: tabulate/formatted tables)     |
| `time.sleep(0.005)`                    | `timer.delay(delay=5000)`  (microseconds)                      |
| `elapsed = time.time() - start`        | `elapsed = timer.elapsed` (use PrecisionTimer)                 |
| `datetime.now().strftime("%Y-%m-%d")`  | `get_timestamp(output_format=TimestampFormats.STRING)`         |
| `duration_s = duration_us / 1_000_000` | `convert_time(time=duration_us, from_units=..., to_units=...)` |
| `yaml.dump(config.__dict__, file)`     | `config.to_yaml(file_path=path)` (subclass YamlConfig)         |
| `if flag == True:`                     | `if flag:` (use truthiness)                                    |
| `if data != None:`                     | `if data is not None:` (use identity)                          |
| `'single quotes'`                      | `"double quotes"` (enforced by ruff)                           |
| `"value: %d" % count`                  | `f"value: {count}"` (f-strings only)                           |
| `raise ValueError(msg)`                | `console.error(message=msg, error=ValueError)`                 |

---

## Documentation anti-patterns

| Anti-Pattern                         | Problem                     | Solution                             |
|--------------------------------------|-----------------------------|--------------------------------------|
| `"""A class that processes data."""` | Noun phrase, not imperative | `"""Processes experimental data."""` |
| Bullet lists in docstrings           | Breaks prose flow           | Use complete sentences instead       |
| `# Set x to 5` before `x = 5`        | States the obvious          | Remove or explain *why*              |
| Missing dtype in `NDArray`           | Type checking fails         | Always specify `NDArray[np.float32]` |
| `Whether to...` for booleans         | Incomplete phrasing         | Use `Determines whether to...`       |
| `# ======` section separators        | Visual clutter              | Use blank lines to separate sections |

---

## Naming anti-patterns

| Anti-Pattern        | Problem              | Solution                           |
|---------------------|----------------------|------------------------------------|
| `pos`, `idx`, `val` | Abbreviations        | `position`, `index`, `value`       |
| `curIdx`            | Missing underscore   | `_current_index`                   |
| `process()`         | Too generic          | `process_frame_data()`             |
| `data1`, `data2`    | Non-descriptive      | `input_data`, `output_data`        |

---

## Code anti-patterns

| Anti-Pattern                       | Problem                  | Solution                                       |
|------------------------------------|--------------------------|------------------------------------------------|
| `np.zeros((4,), np.float32)`       | Positional dtype arg     | `np.zeros((4,), dtype=np.float32)`             |
| `raise ValueError(...)`            | Wrong error handling     | `console.error(message=..., error=ValueError)` |
| `from typing import Optional`      | Old-style optional       | Use `Type | None` instead                      |
| `@numba.njit` without `cache=True` | Recompiles every run     | `@numba.njit(cache=True)`                      |
| Inconsistent f-string prefixes     | Confusing multi-line     | Use `f` prefix on all lines                    |
| `'single quotes'`                  | Violates ruff formatting | Use `"double quotes"`                          |
| `"val: %d" % x` or `.format()`     | Old-style formatting     | Use f-strings exclusively                      |
| `if flag is True:` / `== True`     | Redundant comparison     | Use truthiness: `if flag:`                     |
| `if len(items) == 0:`              | Verbose emptiness check  | Use truthiness: `if not items:`                |
| Deep nesting for validation        | Hard to read             | Use guard clauses with early returns           |
| Missing `__all__` in `__init__.py` | Unclear public API       | Add alphabetically sorted `__all__`            |

---

## Ataraxis library anti-patterns

| Anti-Pattern                         | Problem                         | Solution                                                             |
|--------------------------------------|---------------------------------|----------------------------------------------------------------------|
| `print("message")` for plain text    | No logging, inconsistent        | `console.echo(message="...")` (exception: tabulate/formatted tables) |
| `time.sleep(0.001)`                  | Low precision, blocks GIL       | `PrecisionTimer.delay(delay=1000)`                                   |
| `time.time()` for intervals          | Insufficient precision          | `PrecisionTimer.elapsed`                                             |
| `datetime.now().strftime(...)`       | Inconsistent format             | `get_timestamp()`                                                    |
| `elapsed_us / 1_000_000`             | Magic number conversion         | `convert_time(time=..., from_units=..., to_units=...)`               |
| Manual YAML dump/load                | No type safety                  | Subclass `YamlConfig`                                                |
| `multiprocessing.Array`              | Limited dtype support           | `SharedMemoryArray`                                                  |
| Direct file writes in loops          | Blocks acquisition              | `DataLogger` with `LogPackage`                                       |
| Manual `isinstance()` for list check | Verbose, error-prone            | `ensure_list()`                                                      |
| Manual slice batching                | Verbose, doesn't preserve dtype | `chunk_iterable()`                                                   |
