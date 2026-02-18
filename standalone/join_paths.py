#!/usr/bin/env python3
"""
Join Paths — Standalone (svgpathtools).

Reads an SVG, joins open paths whose endpoints overlap, writes the result.

Usage:
    python3 join_paths.py input/drawing.svg -t 0.5
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from svgpathtools import parse_path

from svg_utils import (
    SVG_NS,
    load_svg, save_svg,
    parse_transform, apply_transform_to_path,
    join_paths, stroke_to_path,
)


def _tag_local(elem):
    t = elem.tag
    return t.split("}")[-1] if "}" in t else t


def join_all_paths(root, tolerance, auto_close=True):
    """Find all <path> elements, join overlapping ones."""
    ns_path = f"{{{SVG_NS}}}path"
    path_elems = list(root.iter(ns_path))
    if len(path_elems) < 2:
        print(f"  Only {len(path_elems)} path(s) — nothing to join.")
        return

    # Parse + bake transforms
    parsed = []
    for elem in path_elems:
        d = elem.get("d", "")
        if not d:
            continue
        p = parse_path(d)
        t_str = elem.get("transform", "")
        if t_str:
            p = apply_transform_to_path(p, parse_transform(t_str))
        parsed.append((elem, p))

    path_objects = [p for _, p in parsed]
    merged, stats = join_paths(path_objects, tolerance, auto_close)

    print(f"  Joins: {stats['joins']}")
    print(f"  Auto-closed: {stats['closed']}")
    print(f"  Paths: {stats['paths_before']} → {stats['paths_after']}")

    # Build parent map for removal
    parent_map = {c: p for p in root.iter() for c in p}

    # Remove old elements
    for elem, _ in parsed:
        parent = parent_map.get(elem)
        if parent is not None:
            try:
                parent.remove(elem)
            except ValueError:
                pass

    # Add merged paths to root (or first group found)
    target = root.find(f".//{{{SVG_NS}}}g")
    if target is None:
        target = root

    style = parsed[0][0].get("style", "") if parsed else ""
    for p in merged:
        path_elem = ET.SubElement(target, f"{{{SVG_NS}}}path")
        path_elem.set("d", p.d())
        if style:
            path_elem.set("style", style)


import re as _re


def stroke_to_path_in_svg(root, width, samples_per_segment=64):
    """Convert every <path> stroke to a filled outline."""
    ns_path = f"{{{SVG_NS}}}path"
    count = 0
    for elem in list(root.iter(ns_path)):
        d = elem.get("d", "")
        if not d:
            continue
        p = parse_path(d)
        t_str = elem.get("transform", "")
        if t_str:
            p = apply_transform_to_path(p, parse_transform(t_str))
            if "transform" in elem.attrib:
                del elem.attrib["transform"]
        outlined = stroke_to_path(p, width, samples_per_segment)
        elem.set("d", outlined.d())
        style = elem.get("style", "")
        style = _re.sub(r"stroke-width\s*:\s*[^;]*;?", "", style)
        stroke_color = "black"
        m = _re.search(r"stroke\s*:\s*([^;]+)", style)
        if m:
            stroke_color = m.group(1).strip()
        style = _re.sub(r"stroke\s*:\s*[^;]*;?", "", style)
        style = _re.sub(r"fill\s*:\s*[^;]*;?", "", style)
        style = f"fill:{stroke_color};stroke:none;{style}".rstrip(";")
        elem.set("style", style)
        count += 1
    print(f"  Converted {count} path(s) to outlined shapes (width={width:g})")


def join_svg_paths(
    input_svg,
    output=None,
    tolerance=0.1,
    auto_close=True,
    stroke_to_path_width=None,
):
    """Join overlapping paths in an SVG file programmatically.

    Args:
        input_svg: Path to input SVG file.
        output: Output SVG path (default: output/<name>_joined.svg).
        tolerance: Max endpoint distance for joining.
        auto_close: Close paths whose ends meet within tolerance.
        stroke_to_path_width: Expand strokes into filled outlines at this width (None = skip).

    Returns:
        str: Path to the saved output SVG.
    """
    tree, root = load_svg(input_svg)
    join_all_paths(root, tolerance, auto_close)

    if stroke_to_path_width is not None:
        stroke_to_path_in_svg(root, stroke_to_path_width)

    if output is None:
        base = os.path.splitext(os.path.basename(input_svg))[0]
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        os.makedirs(out_dir, exist_ok=True)
        output = os.path.join(out_dir, f"{base}_joined.svg")

    save_svg(tree, output)
    return output


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Join open paths in an SVG whose endpoints overlap."
    )
    parser.add_argument("input_svg", help="Input SVG file")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("-t", "--tolerance", type=float, default=0.1)
    parser.add_argument("--no-auto-close", action="store_true")
    parser.add_argument("--stroke-to-path", type=float, default=None,
                        metavar="WIDTH",
                        help="Convert strokes to filled outlines at this width")
    args = parser.parse_args()

    out = join_svg_paths(
        input_svg=args.input_svg,
        output=args.output,
        tolerance=args.tolerance,
        auto_close=not args.no_auto_close,
        stroke_to_path_width=args.stroke_to_path,
    )
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
