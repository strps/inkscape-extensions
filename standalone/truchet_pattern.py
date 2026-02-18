#!/usr/bin/env python3
"""
Truchet Pattern — Standalone (svgpathtools).

Reads <symbol> defs from an SVG, tiles them into a grid, and optionally:
  1. Converts to inline paths  2. Joins adjacent paths  3. Sets stroke width

Usage:
    python3 truchet_pattern.py input/symbols.svg -c 10 -r 10 -s 40 \
        --convert-to-paths --join-paths --stroke-width 2
"""

import argparse
import random
import copy
import math
import os
import sys
import re
import xml.etree.ElementTree as ET
from svgpathtools import Path, parse_path

from svg_utils import (
    SVG_NS, XLINK_NS,
    register_namespaces, load_svg, save_svg, find_symbols,
    parse_transform, compose, identity,
    make_translate, make_rotate,
    apply_transform_to_point, apply_transform_to_path,
    transform_to_str, join_paths, distance,
    stroke_to_path,
)


# ── Grid generation ───────────────────────────────────────────────────

def build_grid(symbols, columns, rows, tile_size):
    """Return list of (symbol_elem, affine_matrix) for every tile."""
    tiles = []
    for i in range(columns):
        for j in range(rows):
            sym = random.choice(symbols)
            angle = 90 * random.randrange(4)
            px, py = i * tile_size + tile_size / 2, j * tile_size + tile_size / 2
            t = compose(make_rotate(angle, px, py), make_translate(px, py))
            tiles.append((sym, t))
    return tiles


def generate_svg(symbols, tiles, tile_size, columns, rows):
    """Build an SVG tree with <use> refs.  Returns (tree, root, group)."""
    register_namespaces()
    w, h = columns * tile_size, rows * tile_size

    root = ET.Element(f"{{{SVG_NS}}}svg")
    # root.set("xmlns", SVG_NS)
    # root.set("xmlns:xlink", XLINK_NS)
    root.set("width", str(w))
    root.set("height", str(h))
    root.set("viewBox", f"0 0 {w} {h}")

    defs = ET.SubElement(root, f"{{{SVG_NS}}}defs")
    sym_ids = {}
    for sym in symbols:
        clone = copy.deepcopy(sym)
        defs.append(clone)
        sym_ids[id(sym)] = clone.get("id", "")

    group = ET.SubElement(root, f"{{{SVG_NS}}}g")
    group.set("id", "truchet-pattern")

    # Map use elements → symbol elements (ET.Element forbids arbitrary attrs)
    use_sym_map = {}
    for sym, matrix in tiles:
        use = ET.SubElement(group, f"{{{SVG_NS}}}use")
        use.set(f"{{{XLINK_NS}}}href", f"#{sym_ids[id(sym)]}")
        use.set("href", f"#{sym_ids[id(sym)]}")
        use.set("x", "0")
        use.set("y", "0")
        use.set("transform", transform_to_str(matrix))
        use_sym_map[use] = sym

    return ET.ElementTree(root), root, group, use_sym_map


# ── Pipeline steps ────────────────────────────────────────────────────

def _tag_local(elem):
    """Return local tag name without namespace."""
    t = elem.tag
    return t.split("}")[-1] if "}" in t else t


def convert_uses_to_paths(group, use_sym_map):
    """Replace <use> refs with copies of the symbol children (paths inlined)."""
    for use in list(group):
        if _tag_local(use) != "use":
            continue
        sym = use_sym_map.get(use)
        if sym is None:
            continue

        matrix = parse_transform(use.get("transform", ""))
        idx = list(group).index(use)
        group.remove(use)

        for child in sym:
            clone = copy.deepcopy(child)
            tag = _tag_local(clone)
            child_matrix = parse_transform(clone.get("transform", ""))
            combined = compose(matrix, child_matrix)

            if tag == "path":
                d = clone.get("d", "")
                if d:
                    p = parse_path(d)
                    p = apply_transform_to_path(p, combined)
                    clone.set("d", p.d())
                    if "transform" in clone.attrib:
                        del clone.attrib["transform"]
                else:
                    clone.set("transform", transform_to_str(combined))

            elif tag in ("circle", "ellipse"):
                cx = float(clone.get("cx", "0"))
                cy = float(clone.get("cy", "0"))
                nx, ny = apply_transform_to_point(combined, (cx, cy))
                clone.set("cx", f"{nx:g}")
                clone.set("cy", f"{ny:g}")
                scale = math.hypot(combined[0], combined[1])
                if tag == "circle":
                    r = float(clone.get("r", "0"))
                    clone.set("r", f"{r * scale:g}")
                else:
                    rx = float(clone.get("rx", "0"))
                    ry = float(clone.get("ry", "0"))
                    sy = math.hypot(combined[2], combined[3])
                    clone.set("rx", f"{rx * scale:g}")
                    clone.set("ry", f"{ry * sy:g}")
                if "transform" in clone.attrib:
                    del clone.attrib["transform"]
            else:
                clone.set("transform", transform_to_str(combined))

            group.insert(idx, clone)
            idx += 1


def join_paths_in_group(group, tolerance):
    """Join overlapping <path> elements inside group using svgpathtools."""
    ns_path = f"{{{SVG_NS}}}path"
    elems = [c for c in group if c.tag == ns_path or _tag_local(c) == "path"]
    if len(elems) < 2:
        print(f"  Only {len(elems)} path(s) — nothing to join.")
        return

    # Parse paths, bake any remaining transforms
    parsed = []
    for elem in elems:
        d = elem.get("d", "")
        if not d:
            continue
        p = parse_path(d)
        t_str = elem.get("transform", "")
        if t_str:
            p = apply_transform_to_path(p, parse_transform(t_str))
        parsed.append((elem, p))

    path_objects = [p for _, p in parsed]
    merged, stats = join_paths(path_objects, tolerance)

    print(f"  Join stats: {stats['joins']} joins, "
          f"{stats['paths_before']} → {stats['paths_after']} paths, "
          f"{stats['closed']} auto-closed")

    # Remove old path elements
    for elem, _ in parsed:
        try:
            group.remove(elem)
        except ValueError:
            pass

    # Add merged paths back
    for p in merged:
        path_elem = ET.SubElement(group, f"{{{SVG_NS}}}path")
        path_elem.set("d", p.d())
        # Carry over style from first original path if available
        if parsed:
            style = parsed[0][0].get("style", "")
            if style:
                path_elem.set("style", style)


def replace_stroke_width(group, width):
    """Set stroke-width on every shape in the group."""
    shape_tags = {"path", "circle", "ellipse", "rect", "line", "polyline", "polygon"}
    for elem in group.iter():
        if _tag_local(elem) not in shape_tags:
            continue
        style = elem.get("style", "")
        if "stroke-width" in style:
            style = re.sub(r"stroke-width\s*:\s*[^;]+", f"stroke-width:{width:g}", style)
        elif style:
            style += f";stroke-width:{width:g}"
        else:
            style = f"stroke-width:{width:g}"
        elem.set("style", style)


def stroke_to_path_in_group(group, width):
    """Convert every <path> stroke into a filled outline at the given width."""
    ns_path = f"{{{SVG_NS}}}path"
    count = 0
    for elem in list(group.iter()):
        if elem.tag != ns_path and _tag_local(elem) != "path":
            continue
        d = elem.get("d", "")
        if not d:
            continue
        p = parse_path(d)
        t_str = elem.get("transform", "")
        if t_str:
            p = apply_transform_to_path(p, parse_transform(t_str))
            if "transform" in elem.attrib:
                del elem.attrib["transform"]
        outlined = stroke_to_path(p, width)
        elem.set("d", outlined.d())
        # Switch from stroke to fill
        style = elem.get("style", "")
        # Remove stroke-width
        style = re.sub(r"stroke-width\s*:\s*[^;]*;?", "", style)
        # Set fill to current stroke color (or black), remove stroke
        stroke_color = "black"
        m = re.search(r"stroke\s*:\s*([^;]+)", style)
        if m:
            stroke_color = m.group(1).strip()
        style = re.sub(r"stroke\s*:\s*[^;]*;?", "", style)
        style = re.sub(r"fill\s*:\s*[^;]*;?", "", style)
        style = f"fill:{stroke_color};stroke:none;{style}".rstrip(";")
        elem.set("style", style)
        count += 1
    print(f"  Converted {count} path(s) to outlined shapes (width={width:g})")


def generate_truchet(
    input_svg,
    output=None,
    columns=10,
    rows=10,
    tile_size=8.0,
    seed=None,
    convert_to_paths=False,
    join=False,
    join_tolerance=0.1,
    stroke_width=None,
    stroke_to_path_width=None,
):
    """Generate a Truchet pattern programmatically.

    Args:
        input_svg: Path to SVG with <symbol> definitions.
        output: Output SVG path (default: output/<name>_truchet.svg).
        columns: Tile columns.
        rows: Tile rows.
        tile_size: Size of each tile in SVG units.
        seed: Random seed for reproducibility.
        convert_to_paths: Inline symbol children as paths.
        join: Join overlapping path endpoints.
        join_tolerance: Max distance for joining endpoints.
        stroke_width: Override stroke-width (None = keep original).
        stroke_to_path_width: Expand strokes into filled outlines at this width (None = skip).

    Returns:
        str: Path to the saved output SVG.
    """
    if seed is not None:
        random.seed(seed)

    _, svg_root = load_svg(input_svg)
    symbols = find_symbols(svg_root)
    if not symbols:
        raise ValueError(f"No <symbol> elements found in {input_svg}")

    tiles = build_grid(symbols, columns, rows, tile_size)
    tree, root, group, use_sym_map = generate_svg(symbols, tiles, tile_size, columns, rows)

    if convert_to_paths:
        convert_uses_to_paths(group, use_sym_map)

    if join:
        if not convert_to_paths:
            raise ValueError("join requires convert_to_paths=True")
        join_paths_in_group(group, join_tolerance)

    if stroke_width is not None:
        replace_stroke_width(group, stroke_width)

    if stroke_to_path_width is not None:
        if not convert_to_paths:
            raise ValueError("stroke_to_path_width requires convert_to_paths=True")
        stroke_to_path_in_group(group, stroke_to_path_width)

    if output is None:
        base = os.path.splitext(os.path.basename(input_svg))[0]
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        os.makedirs(out_dir, exist_ok=True)
        output = os.path.join(out_dir, f"{base}_truchet.svg")

    save_svg(tree, output)
    return output


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate a Truchet pattern from symbols in an SVG file."
    )
    parser.add_argument("input_svg", help="Input SVG with <symbol> definitions")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("-c", "--columns", type=int, default=10)
    parser.add_argument("-r", "--rows", type=int, default=10)
    parser.add_argument("-s", "--tile-size", type=float, default=8.0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--convert-to-paths", action="store_true",
                        help="Inline symbol children as paths")
    parser.add_argument("--join-paths", action="store_true",
                        help="Join overlapping path endpoints")
    parser.add_argument("--join-tolerance", type=float, default=0.1)
    parser.add_argument("--stroke-width", type=float, default=None,
                        help="Override stroke-width on all shapes")
    parser.add_argument("--stroke-to-path", type=float, default=None,
                        metavar="WIDTH",
                        help="Convert strokes to filled outlines at this width")
    args = parser.parse_args()

    out = generate_truchet(
        input_svg=args.input_svg,
        output=args.output,
        columns=args.columns,
        rows=args.rows,
        tile_size=args.tile_size,
        seed=args.seed,
        convert_to_paths=args.convert_to_paths,
        join=args.join_paths,
        join_tolerance=args.join_tolerance,
        stroke_width=args.stroke_width,
        stroke_to_path_width=args.stroke_to_path,
    )
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
