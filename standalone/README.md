# Standalone SVG Pattern Tools

Standalone versions of the Inkscape extensions. Uses **svgpathtools** for
proper path geometry — clean output suitable for CAD post-processing
(build123d, FreeCAD, etc.).

## Requirements

- Python 3.7+
- [svgpathtools](https://github.com/mathandy/svgpathtools)

```bash
pip install svgpathtools
```

## Folder Structure

```
standalone/
├── input/              ← Source SVG files (you provide these)
├── output/             ← Generated results (auto-created)
├── svg_utils.py        ← Shared utilities: transforms, join logic (wraps svgpathtools)
├── truchet_pattern.py  ← Truchet tiling generator
├── join_paths.py       ← Path joining tool
└── README.md
```

---

## Truchet Pattern

Reads `<symbol>` definitions from an input SVG, tiles them randomly into a
grid, and optionally processes the result through a pipeline of steps.

### Pipeline Steps

1. **Generate grid** — places `<use>` references with random 90° rotation + translation
2. **Convert to paths** — replaces `<use>` with inlined copies of symbol children, baking transforms into coordinates
3. **Join paths** — merges paths whose endpoints overlap within a tolerance (requires step 2)
4. **Replace stroke width** — sets a uniform `stroke-width` on all shape elements
5. **Stroke to path** — expands strokes into filled outlines (requires step 2)

### CLI Usage

```bash
# Basic — just the grid of <use> refs
python3 truchet_pattern.py input/symbols.svg

# Full pipeline
python3 truchet_pattern.py input/symbols.svg \
    -c 10 -r 8 -s 50 \
    --convert-to-paths \
    --join-paths --join-tolerance 0.5 \
    --stroke-width 2

# Convert strokes to filled outlines (for CAD)
python3 truchet_pattern.py input/symbols.svg \
    --convert-to-paths --stroke-to-path 2

# Reproducible output
python3 truchet_pattern.py input/symbols.svg --seed 42 -o output/my_pattern.svg
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `-c`, `--columns` | 10 | Number of tile columns |
| `-r`, `--rows` | 10 | Number of tile rows |
| `-s`, `--tile-size` | 40 | Size of each tile (SVG user units) |
| `--seed` | random | Random seed for reproducibility |
| `--convert-to-paths` | off | Inline symbol children as paths |
| `--join-paths` | off | Merge overlapping path endpoints |
| `--join-tolerance` | 0.1 | Max endpoint gap for joining |
| `--stroke-width` | — | Override stroke-width on all shapes |
| `--stroke-to-path` | — | Expand strokes into filled outlines at WIDTH |
| `-o`, `--output` | auto | Output file path (`output/<name>_truchet.svg`) |

### Python API

```python
from truchet_pattern import generate_truchet

# Returns the output file path
output = generate_truchet(
    input_svg="input/symbols.svg",
    columns=10,
    rows=8,
    tile_size=50,
    seed=42,
    convert_to_paths=True,
    join=True,
    join_tolerance=0.5,
    stroke_width=2.0,
    stroke_to_path_width=2.0,  # expand strokes into fills
    output="output/my_pattern.svg",  # optional
)
```

#### `generate_truchet()` Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_svg` | `str` | *required* | Path to SVG with `<symbol>` definitions |
| `output` | `str` | `None` | Output path (auto-generated if `None`) |
| `columns` | `int` | `10` | Tile columns |
| `rows` | `int` | `10` | Tile rows |
| `tile_size` | `float` | `40.0` | Tile size in SVG units |
| `seed` | `int` | `None` | Random seed |
| `convert_to_paths` | `bool` | `False` | Inline symbol children |
| `join` | `bool` | `False` | Join overlapping endpoints |
| `join_tolerance` | `float` | `0.1` | Max gap for joining |
| `stroke_width` | `float` | `None` | Override stroke-width |
| `stroke_to_path_width` | `float` | `None` | Expand strokes into filled outlines |

**Returns:** `str` — path to the saved SVG file.

---

## Join Paths

Joins open paths in any SVG file whose endpoints overlap within a tolerance.
Paths are chained end-to-end; if the merged path forms a loop it is
auto-closed.

### CLI Usage

```bash
# Basic
python3 join_paths.py input/drawing.svg

# Custom tolerance + explicit output
python3 join_paths.py input/drawing.svg -t 1.0 -o output/result.svg

# Skip auto-closing
python3 join_paths.py input/drawing.svg --no-auto-close
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `-t`, `--tolerance` | 0.1 | Max endpoint distance for overlap |
| `--no-auto-close` | off | Don't auto-close loops |
| `--stroke-to-path` | — | Expand strokes into filled outlines at WIDTH |
| `-o`, `--output` | auto | Output file path (`output/<name>_joined.svg`) |

### Python API

```python
from join_paths import join_svg_paths

output = join_svg_paths(
    input_svg="input/drawing.svg",
    tolerance=0.5,
    auto_close=True,
    stroke_to_path_width=2.0,  # optional: expand strokes
    output="output/joined.svg",  # optional
)
```

#### `join_svg_paths()` Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_svg` | `str` | *required* | Path to input SVG |
| `output` | `str` | `None` | Output path (auto-generated if `None`) |
| `tolerance` | `float` | `0.1` | Max endpoint distance |
| `auto_close` | `bool` | `True` | Close paths whose ends meet |
| `stroke_to_path_width` | `float` | `None` | Expand strokes into filled outlines |

**Returns:** `str` — path to the saved SVG file.

---

## Shared Utilities (`svg_utils.py`)

Low-level helpers importable for custom scripts:

```python
from svg_utils import (
    load_svg, save_svg, find_symbols,           # SVG I/O
    parse_transform, compose,                    # affine matrices
    make_translate, make_rotate,                 # transform builders
    apply_transform_to_point,                    # point transform
    apply_transform_to_path,                     # svgpathtools.Path transform
    join_paths, distance,                        # path join logic
)
```

### Key Functions

| Function | Description |
|----------|-------------|
| `load_svg(path)` | Returns `(ElementTree, root)` |
| `save_svg(tree, path)` | Writes SVG with proper namespaces |
| `find_symbols(root)` | Returns list of `<symbol>` elements |
| `parse_transform(attr)` | SVG `transform` attr → `[a,b,c,d,e,f]` matrix |
| `compose(m1, m2)` | Multiply two affine matrices |
| `make_translate(tx, ty)` | Translation matrix |
| `make_rotate(deg, cx, cy)` | Rotation matrix (around optional center) |
| `apply_transform_to_path(path, matrix)` | Transform an `svgpathtools.Path` |
| `join_paths(paths, tol)` | Join list of `svgpathtools.Path` → `(merged, stats)` |
| `stroke_to_path(path, width)` | Expand stroked `Path` into a filled outline `Path` |

---

## Preparing Input SVGs

The truchet tool requires `<symbol>` elements in the input SVG's `<defs>`.

**In Inkscape:**
1. Draw your tile artwork
2. Select it → **Object → Symbols → Convert to Symbol**
3. Repeat for each tile variation
4. Save the SVG → copy into `input/`

**Manually:** Any SVG with `<defs><symbol id="tile1">...</symbol></defs>` works.
