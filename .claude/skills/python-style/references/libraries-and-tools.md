# Libraries and tools

Conventions for ataraxis libraries, Numba, Click CLI, testing, and linting in Sun Lab projects.

---

## Ataraxis library preferences

Sun Lab projects use a suite of ataraxis libraries that provide standardized, high-performance utilities. **Always
prefer these libraries** over standard library alternatives or reimplementation for their designated tasks.

### Console output (ataraxis-base-utilities)

Use `console.echo()` for **all console output** instead of `print()`:

```python
from ataraxis_base_utilities import console

# Good - use console.echo() for all output
console.echo(message="Processing frame 1 of 100...")
console.echo(message="Analysis complete.", level="SUCCESS")
console.echo(message="Potential memory issue detected.", level="WARNING")

# Avoid - do not use print()
print("Processing frame 1 of 100...")  # Wrong - use console.echo()
```

**Log levels**: `DEBUG`, `INFO` (default), `SUCCESS`, `WARNING`, `ERROR`, `CRITICAL`

The global `console` instance is pre-configured and shared across all Sun Lab projects. Call `console.enable()` at
application entry points if needed.

**Exception**: Use `print()` or `click.echo()` when output requires specific formatting that would be disrupted by
console's line-width formatting, such as tables created with `tabulate` or manually aligned ASCII tables:

```python
from tabulate import tabulate

# Good - print() for pre-formatted tabulate output
table = tabulate(data, headers=["Port", "Device", "Status"], tablefmt="grid")
print("Device Information:")
print(table)

# Good - click.echo() for manually aligned CLI tables
click.echo("Precision | Duration | Mean Time")
click.echo("----------+----------+----------")
for row in results:
    click.echo(f"{row.precision:9} | {row.duration:8} | {row.mean:9.3f}")
```

When using this exception, add a comment explaining why standard console output is not used.

### List conversion (ataraxis-base-utilities)

Use `ensure_list()` to normalize inputs to list form:

```python
from ataraxis_base_utilities import ensure_list

# Good - handles scalars, numpy arrays, and iterables
items = ensure_list(input_item=user_input)

# Avoid - manual type checking
if isinstance(user_input, list):
    items = user_input
elif isinstance(user_input, np.ndarray):
    items = user_input.tolist()
else:
    items = [user_input]
```

### Iterable chunking (ataraxis-base-utilities)

Use `chunk_iterable()` for batching operations:

```python
from ataraxis_base_utilities import chunk_iterable

# Good - preserves numpy array types
for batch in chunk_iterable(iterable=large_array, chunk_size=100):
    process_batch(batch=batch)

# Avoid - manual slicing logic
for i in range(0, len(large_array), 100):
    batch = large_array[i:i + 100]
```

### Timing and delays (ataraxis-time)

Use `PrecisionTimer` for all timing operations:

```python
from ataraxis_time import PrecisionTimer, TimerPrecisions

# Good - high-precision interval timing
timer = PrecisionTimer(precision=TimerPrecisions.MICROSECOND)
timer.reset()
# ... operation ...
elapsed_us = timer.elapsed

# Good - non-blocking delay (releases GIL for other threads)
timer.delay(delay=5000, allow_sleep=True, block=False)  # 5ms delay

# Avoid - time.sleep() for precision timing
import time
time.sleep(0.005)  # Wrong for microsecond precision work
```

**Precision options**: `NANOSECOND`, `MICROSECOND` (default), `MILLISECOND`, `SECOND`

### Timestamps (ataraxis-time)

Use `get_timestamp()` for generating timestamps:

```python
from ataraxis_time import get_timestamp, TimestampFormats

# Good - string format for filenames
timestamp = get_timestamp(output_format=TimestampFormats.STRING)
output_path = data_directory / f"session_{timestamp}.npy"

# Good - integer format for calculations (microseconds since epoch)
timestamp_us = get_timestamp(output_format=TimestampFormats.INTEGER)

# Good - bytes format for binary serialization
timestamp_bytes = get_timestamp(output_format=TimestampFormats.BYTES)

# Avoid - datetime manipulation
from datetime import datetime
timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")  # Wrong
```

### Time unit conversion (ataraxis-time)

Use `convert_time()` for converting between time units:

```python
from ataraxis_time import convert_time, TimeUnits

# Good - explicit unit conversion
duration_seconds = convert_time(
    time=elapsed_microseconds,
    from_units=TimeUnits.MICROSECOND,
    to_units=TimeUnits.SECOND,
)

# Avoid - manual conversion with magic numbers
duration_seconds = elapsed_microseconds / 1_000_000  # Wrong
```

**Supported units**: `NANOSECOND`, `MICROSECOND`, `MILLISECOND`, `SECOND`, `MINUTE`, `HOUR`, `DAY`

### YAML configuration (ataraxis-data-structures)

Use `YamlConfig` as a base class for configuration dataclasses:

```python
from dataclasses import dataclass
from pathlib import Path
from ataraxis_data_structures import YamlConfig

# Good - subclass YamlConfig for YAML serialization
@dataclass
class ExperimentConfig(YamlConfig):
    """Defines experiment configuration parameters."""

    animal_id: str
    """The unique identifier for the animal."""
    session_duration: float
    """The duration in seconds."""

# Saving and loading
config = ExperimentConfig(animal_id="M001", session_duration=3600.0)
config.to_yaml(file_path=Path("config.yaml"))
loaded_config = ExperimentConfig.from_yaml(file_path=Path("config.yaml"))

# Avoid - manual YAML handling
import yaml
with open("config.yaml", "w") as file:
    yaml.dump(config.__dict__, file)  # Wrong
```

### Shared memory (ataraxis-data-structures)

Use `SharedMemoryArray` for inter-process data sharing:

```python
from ataraxis_data_structures import SharedMemoryArray
import numpy as np

# Good - create shared array in main process
prototype = np.zeros((100, 100), dtype=np.float32)
shared_array = SharedMemoryArray.create_array(name="frame_buffer", prototype=prototype)

# In child process - connect before use
shared_array.connect()
with shared_array.array() as arr:  # Thread-safe access
    arr[:] = new_data
shared_array.disconnect()

# Cleanup in main process
shared_array.destroy()

# Avoid - multiprocessing.Array or manual shared memory
from multiprocessing import Array
shared = Array('f', 10000)  # Wrong for complex array operations
```

### Data logging (ataraxis-data-structures)

Use `DataLogger` and `LogPackage` for high-throughput logging:

```python
from pathlib import Path
from ataraxis_data_structures import DataLogger, LogPackage
import numpy as np

# Good - dedicated logger process for parallel I/O
logger = DataLogger(
    output_directory=Path("/data/experiment"),
    instance_name="neural_data",
    thread_count=5,
)
logger.start()

# Package and submit data
package = LogPackage(
    source_id=np.uint8(1),
    acquisition_time=np.uint64(elapsed_us),
    serialized_data=data_array.tobytes(),
)
logger.input_queue.put(package)

# Cleanup
logger.stop()

# Avoid - direct file writes in acquisition loop
np.save(f"frame_{i}.npy", data)  # Wrong - blocks acquisition
```

### Quick reference table

| Task                    | Use This                    | Not This                                |
|-------------------------|-----------------------------|-----------------------------------------|
| Console output          | `console.echo()`            | `print()` (exception: formatted tables) |
| Error handling          | `console.error()`           | `raise Exception()`                     |
| Convert to list         | `ensure_list()`             | Manual type checking                    |
| Batch iteration         | `chunk_iterable()`          | Manual slicing                          |
| Precision timing        | `PrecisionTimer`            | `time.time()`, `time.perf_counter()`    |
| Delays                  | `PrecisionTimer.delay()`    | `time.sleep()`                          |
| Timestamps              | `get_timestamp()`           | `datetime.now().strftime()`             |
| Time unit conversion    | `convert_time()`            | Manual division/multiplication          |
| YAML serialization      | `YamlConfig` subclass       | `yaml.dump()`/`yaml.load()`             |
| Inter-process arrays    | `SharedMemoryArray`         | `multiprocessing.Array`                 |
| High-throughput logging | `DataLogger` + `LogPackage` | Direct file writes                      |

---

## Numba functions

### Decorator patterns

```python
# Standard cached function
@numba.njit(cache=True)
def _compute_values(...) -> None:
    ...

# Parallelized function
@numba.njit(cache=True, parallel=True)
def _process_batch(...) -> None:
    for i in prange(data.shape[0]):  # Parallel outer loop
        for j in range(data.shape[1]):  # Sequential inner loop
            ...

# Inlined helper (for small, frequently-called functions)
@numba.njit(cache=True, inline="always")
def compute_coefficients(...) -> None:
    ...
```

### Guidelines

- Always use `cache=True` for disk caching (avoids recompilation)
- Use `parallel=True` with `prange` only when no race conditions exist
- Use `inline="always"` for small helper functions called in hot loops
- Don't use `nogil` unless explicitly using threading
- Use Python type hints (not Numba signature strings) for readability

---

## Click CLI conventions

Sun Lab CLIs use [Click](https://click.palletsprojects.com/) with consistent patterns across all projects.

### Group and command setup

```python
CONTEXT_SETTINGS: dict[str, int] = {"max_content_width": 120}


@click.group("axvs", context_settings=CONTEXT_SETTINGS)
def axvs_cli() -> None:
    """Manages video capture sessions and camera configurations."""


@axvs_cli.command("discover")
@click.option(
    "-i",
    "--interface",
    required=False,
    default="all",
    type=click.Choice(["all", "opencv", "harvester"], case_sensitive=False),
    help="The camera interface to use for discovery.",
)
def discover_cameras(interface: str) -> None:
    """Discovers all compatible cameras connected to the system."""
    ...
```

### Option naming

- **Short flags**: Single or double lowercase letters (`-i`, `-sp`, `-id`)
- **Long flags**: Lowercase with hyphens (`--input-path`, `--camera-index`, `--output-directory`)
- **Path options**: Use `click.Path()` with explicit validation:

```python
@click.option(
    "-o",
    "--output-directory",
    required=True,
    type=click.Path(exists=False, file_okay=False, dir_okay=True, writable=True, path_type=Path),
    help="The directory to save output files.",
)
```

### Output formatting

- Use `console.echo()` for standard CLI output
- Use `print()` or `click.echo()` only for pre-formatted tables (tabulate, manually aligned ASCII)
- Use `console.error()` for error reporting with proper error types

### Entry points

Define CLI entry points in `pyproject.toml`:

```toml
[project.scripts]
axvs = "ataraxis_video_system.cli:axvs_cli"
```

---

## Test files

Test files follow simplified documentation conventions.

### Module docstrings

Test module docstrings use the "Contains tests for..." format:

```python
"""Contains tests for classes and methods provided by the saver.py module."""
```

### Test function docstrings

Test function docstrings use imperative mood with "Verifies...":

```python
def test_video_saver_init_repr(tmp_path, has_ffmpeg):
    """Verifies the functioning of the VideoSaver __init__() and __repr__() methods."""
```

**Important**: Test function docstrings do not include Args, Returns, or Raises sections.

### Fixture docstrings

Pytest fixtures use imperative mood docstrings describing what the fixture provides:

```python
@pytest.fixture(scope="session")
def has_nvidia():
    """Checks for NVIDIA GPU availability in the test environment."""
    ...
```

---

## Linting and code quality

### Running checks

Run `tox -e lint` after making changes. This runs both **ruff** (style and formatting) and **mypy** (strict type
checking) in a single command. All issues must be resolved or suppressed with specific ignore comments.

If `tox` is unavailable, the underlying tools can be run directly:
- `ruff check .` and `ruff format --check .` for style violations
- `mypy` for type violations

Prefer `tox -e lint` when possible, as it ensures consistent tool versions and configuration.

### Resolution policy

Prefer resolving issues unless the resolution would:
- Make the code unnecessarily complex
- Hurt performance by adding redundant checks
- Harm codebase readability instead of helping it

### Magic numbers (PLR2004)

For magic number warnings, prefer defining constants:

```python
def calculate_threshold(self, value: float) -> float:
    """Calculates the adjusted threshold."""
    adjustment_factor = 1.5  # Empirically determined scaling factor.
    return value * adjustment_factor
```

### Using noqa

When suppressing a warning, always include the specific error code:

```python
if mode == 3:  # noqa: PLR2004 - LICK_TRAINING mode value from VisualizerMode enum.
    ...
```
