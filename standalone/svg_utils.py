"""
SVG utilities — powered by svgpathtools.

Thin wrapper providing helpers for truchet_pattern.py and join_paths.py.
Uses svgpathtools for all path/geometry work and xml.etree for the parts
of the SVG tree (symbols, groups) that svgpathtools doesn't cover.
"""

import math
import re
import xml.etree.ElementTree as ET
from svgpathtools import (
    Path, Line, CubicBezier, QuadraticBezier, Arc,
    parse_path, concatpaths,
)

__all__ = [
    "SVG_NS", "XLINK_NS",
    "register_namespaces", "load_svg", "save_svg",
    "find_symbols",
    "parse_transform", "compose", "identity",
    "make_translate", "make_rotate",
    "apply_transform_to_point", "apply_transform_to_path",
    "transform_to_str",
    "join_paths", "distance",
    "stroke_to_path",
]

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"


# ── Namespace helpers ─────────────────────────────────────────────────

def register_namespaces():
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)
    ET.register_namespace("sodipodi", "http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd")
    ET.register_namespace("inkscape", "http://www.inkscape.org/namespaces/inkscape")


# ── SVG file I/O ─────────────────────────────────────────────────────

def load_svg(filepath):
    register_namespaces()
    tree = ET.parse(filepath)
    return tree, tree.getroot()


def save_svg(tree, filepath):
    register_namespaces()
    tree.write(filepath, xml_declaration=True, encoding="unicode")


# ── Symbol helpers ────────────────────────────────────────────────────

def find_symbols(root):
    return root.findall(f".//{{{SVG_NS}}}symbol")


# ── 2D affine [a,b,c,d,e,f] ──────────────────────────────────────────
#   | a c e |
#   | b d f |
#   | 0 0 1 |

def identity():
    return [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]


def compose(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return [
        a1*a2 + c1*b2,      b1*a2 + d1*b2,
        a1*c2 + c1*d2,      b1*c2 + d1*d2,
        a1*e2 + c1*f2 + e1, b1*e2 + d1*f2 + f1,
    ]


def make_translate(tx, ty):
    return [1, 0, 0, 1, tx, ty]


def make_rotate(deg, cx=0, cy=0):
    a = math.radians(deg)
    c_, s_ = math.cos(a), math.sin(a)
    if cx == 0 and cy == 0:
        return [c_, s_, -s_, c_, 0, 0]
    return compose(make_translate(cx, cy),
                   compose([c_, s_, -s_, c_, 0, 0],
                           make_translate(-cx, -cy)))


def _parse_single(s):
    m = re.match(r"(\w+)\s*\(([^)]*)\)", s.strip())
    if not m:
        return identity()
    fn = m.group(1).lower()
    args = [float(x) for x in re.findall(r"[+-]?[\d.]+(?:[eE][+-]?\d+)?", m.group(2))]
    if fn == "translate":
        return make_translate(args[0] if args else 0, args[1] if len(args) > 1 else 0)
    if fn == "scale":
        sx = args[0] if args else 1
        return [sx, 0, 0, args[1] if len(args) > 1 else sx, 0, 0]
    if fn == "rotate":
        cx = args[1] if len(args) >= 3 else 0
        cy = args[2] if len(args) >= 3 else 0
        return make_rotate(args[0] if args else 0, cx, cy)
    if fn == "matrix" and len(args) >= 6:
        return list(args[:6])
    return identity()


def parse_transform(attr):
    if not attr:
        return identity()
    result = identity()
    for fn in re.findall(r"\w+\s*\([^)]*\)", attr):
        result = compose(result, _parse_single(fn))
    return result


def apply_transform_to_point(matrix, point):
    a, b, c, d, e, f = matrix
    x, y = point
    return (a*x + c*y + e, b*x + d*y + f)


def transform_to_str(m):
    a, b, c, d, e, f = m
    return f"matrix({a:g},{b:g},{c:g},{d:g},{e:g},{f:g})"


def apply_transform_to_path(svg_path, matrix):
    """Apply 2D affine to an svgpathtools.Path via complex-number transform.

    Works for rotation + uniform scale + translation (Truchet tiles).
    """
    a, b, c, d, e, f = matrix
    # svgpathtools uses complex coords: point = x + yj
    # Affine as complex: new_z = z_scale * z + z_translate
    z_scale = complex(a, b)
    z_translate = complex(e, f)
    return svg_path.scaled(z_scale).translated(z_translate)


# ── Distance ─────────────────────────────────────────────────────────

def distance(p1, p2):
    """Distance between two complex points."""
    return abs(p1 - p2)


# ── Join paths ────────────────────────────────────────────────────────

def _try_merge(a, b, tol):
    """Try to merge two Paths.  Returns merged Path or None."""
    if distance(a.end, b.start) <= tol:
        return concatpaths([a, b])
    if distance(a.end, b.end) <= tol:
        return concatpaths([a, b.reversed()])
    if distance(a.start, b.end) <= tol:
        return concatpaths([b, a])
    if distance(a.start, b.start) <= tol:
        return concatpaths([b.reversed(), a])
    return None


def join_paths(path_list, tolerance, auto_close=True):
    """Join svgpathtools.Path objects whose endpoints overlap.

    Returns (merged_paths: list[Path], stats: dict).
    """
    chains = list(path_list)
    joins = 0
    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(chains):
            j = i + 1
            while j < len(chains):
                merged = _try_merge(chains[i], chains[j], tolerance)
                if merged is not None:
                    chains[i] = merged
                    chains.pop(j)
                    changed = True
                    joins += 1
                    j = i + 1
                else:
                    j += 1
            i += 1

    closed = 0
    if auto_close:
        for idx, p in enumerate(chains):
            d = distance(p.start, p.end)
            if len(p) > 0 and 0 < d <= tolerance:
                chains[idx].append(Line(p.end, p.start))
                closed += 1

    return chains, {
        "joins": joins,
        "closed": closed,
        "paths_before": len(path_list),
        "paths_after": len(chains),
    }


# ── Stroke to path ────────────────────────────────────────────────────

def _offset_segment(segment, offset, samples=64):
    """Sample a segment and return offset points on one side."""
    pts = []
    for i in range(samples + 1):
        t = i / samples
        pt = segment.point(t)
        try:
            n = segment.normal(t)
        except (ValueError, ZeroDivisionError):
            n = 1j  # fallback: up
        pts.append(pt + offset * n)
    return pts


def _pts_to_closed_loop(pts):
    """Convert a list of points into a closed Path of Line segments."""
    if len(pts) < 2:
        return Path()
    segs = [Line(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    segs.append(Line(pts[-1], pts[0]))
    return Path(*segs)


def stroke_to_path(svg_path, width, samples_per_segment=64, close_tolerance=1e-3):
    """Convert a stroked path into a filled outline Path.

    For **open** paths: creates two offset curves at ±width/2 and connects
    them into a single closed polygon (strip).

    For **closed** paths (start ≈ end within *close_tolerance*): creates two
    concentric loops (outer + inner) so the result is an annulus/ring shape.
    The two sub-paths are returned inside a single Path using an SVG
    "even-odd" style cut-out (two closed loops).

    Args:
        svg_path: An svgpathtools.Path.
        width: Stroke width to expand.
        samples_per_segment: Sampling density per segment (higher = smoother).
        close_tolerance: Max gap to consider a path closed.

    Returns:
        svgpathtools.Path: Closed filled outline (one or two loops).
    """
    half = width / 2.0

    # Build offset points for left (+half) and right (-half)
    left_pts = []
    right_pts = []
    for seg in svg_path:
        left_pts.extend(_offset_segment(seg, half, samples_per_segment))
        right_pts.extend(_offset_segment(seg, -half, samples_per_segment))

    if len(left_pts) < 2:
        return svg_path

    # Detect if the original path is closed
    start = svg_path.start
    end = svg_path.end
    is_closed = abs(start - end) <= close_tolerance

    if is_closed:
        # Two concentric closed loops (outer + inner in opposite winding)
        outer = _pts_to_closed_loop(left_pts)
        right_pts.reverse()
        inner = _pts_to_closed_loop(right_pts)
        # Combine into one Path (two sub-loops — fill-rule:evenodd cuts hole)
        return Path(*list(outer) + list(inner))
    else:
        # Open path: strip — left forward → right backward → close
        right_pts.reverse()
        all_pts = left_pts + right_pts
        return _pts_to_closed_loop(all_pts)
