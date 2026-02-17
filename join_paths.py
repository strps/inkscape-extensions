#!/usr/bin/env python
"""
Join Paths – Inkscape Extension

Joins selected open paths whose endpoints coincide (within a tolerance).
Paths are chained end-to-end: if the end of path A is within tolerance of the
start (or end) of path B, the two are merged into a single continuous path.

Handles:
  - Paths with transforms (rotate, translate, etc.) – endpoints are compared
    in document-space after applying the composed transform.
  - Sodipodi arc elements – arc metadata is stripped after merging so Inkscape
    does not regenerate the old single-arc path data.
  - ZoneClose (Z) commands – trailing Z is stripped before concatenation;
    if the final merged path's end meets its start, Z is re-added.

Works with the modern inkex API (Inkscape 1.0+).
"""

__version__ = "1.1"
__author__ = "CJ & GitHub Copilot (Claude Opus 4.6)"

import math
import inkex

# Sodipodi / Inkscape arc attributes that must be removed after merging
_SODIPODI_ARC_ATTRS = [
    inkex.addNS("type", "sodipodi"),
    inkex.addNS("cx", "sodipodi"),
    inkex.addNS("cy", "sodipodi"),
    inkex.addNS("rx", "sodipodi"),
    inkex.addNS("ry", "sodipodi"),
    inkex.addNS("start", "sodipodi"),
    inkex.addNS("end", "sodipodi"),
    inkex.addNS("open", "sodipodi"),
    inkex.addNS("arc-type", "sodipodi"),
]


# ── reusable helpers (importable by other extensions) ──────────────

def _distance(p1, p2):
    """Euclidean distance between two (x, y) points."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def _start(path_cmds):
    """Return the first on-curve point of an inkex.Path."""
    for cmd in path_cmds:
        if hasattr(cmd, "x") and hasattr(cmd, "y"):
            return (cmd.x, cmd.y)
    return None


def _end(path_cmds):
    """Return the last on-curve point of an inkex.Path."""
    last = None
    for cmd in path_cmds:
        if hasattr(cmd, "x") and hasattr(cmd, "y"):
            last = (cmd.x, cmd.y)
    return last


def _is_closed(path):
    """Return True if the path ends with a ZoneClose (Z) command."""
    cmds = list(path)
    return len(cmds) > 0 and isinstance(cmds[-1], inkex.paths.ZoneClose)


def _strip_close(path):
    """Return a copy of path with any trailing ZoneClose removed."""
    cmds = list(path)
    while cmds and isinstance(cmds[-1], inkex.paths.ZoneClose):
        cmds.pop()
    return inkex.Path(cmds)


def _reverse_path(path):
    """Return the reversed inkex.Path."""
    return path.reverse()


def _count_nodes(path):
    """Count the number of on-curve nodes in an inkex.Path."""
    return sum(1 for cmd in path if hasattr(cmd, "x") and hasattr(cmd, "y"))


def _flatten_path(node):
    """Return the path of *node* in document-space (transform baked in)."""
    abs_path = node.path.to_absolute()
    ctm = node.composed_transform()
    if ctm is not None and ctm != inkex.Transform():
        abs_path = abs_path.transform(ctm)
    return abs_path


def _strip_sodipodi(node):
    """Remove sodipodi arc metadata from *node*."""
    for attr in _SODIPODI_ARC_ATTRS:
        if attr in node.attrib:
            del node.attrib[attr]


def _concat_paths(path_a, path_b):
    """Concatenate two inkex.Path objects into one continuous path.

    The first Move of path_b is dropped so the pen continues from
    where path_a ended.
    """
    new_cmds = list(path_a)
    first_b = True
    for cmd in path_b:
        if first_b and isinstance(cmd, inkex.paths.Move):
            first_b = False
            continue
        first_b = False
        if isinstance(cmd, inkex.paths.ZoneClose):
            continue
        new_cmds.append(cmd)
    return inkex.Path(new_cmds)


def _try_merge(a, b, tol):
    """Try to join two chains.  Returns a new chain dict or None."""
    pa = _strip_close(a["path"])
    pb = _strip_close(b["path"])

    a_start = _start(pa)
    a_end = _end(pa)
    b_start = _start(pb)
    b_end = _end(pb)

    if None in (a_start, a_end, b_start, b_end):
        return None

    keep_node = a["node"]

    if _distance(a_end, b_start) <= tol:
        return {"node": keep_node, "path": _concat_paths(pa, pb)}
    if _distance(a_end, b_end) <= tol:
        return {"node": keep_node, "path": _concat_paths(pa, _reverse_path(pb))}
    if _distance(a_start, b_end) <= tol:
        return {"node": keep_node, "path": _concat_paths(pb, pa)}
    if _distance(a_start, b_start) <= tol:
        return {"node": keep_node, "path": _concat_paths(_reverse_path(pb), pa)}

    return None


def join_path_elements(path_nodes, tolerance, auto_close=True):
    """Join a list of inkex.PathElement nodes whose endpoints overlap.

    This is the core reusable routine.  It mutates the nodes in-place:
    merged paths are written to the surviving node, consumed nodes are
    removed from their parent.

    Returns a dict with stats: joins, closed, paths_before, paths_after,
    nodes_before, nodes_after.
    """
    chains = []
    nodes_before = 0
    for node in path_nodes:
        doc_path = _flatten_path(node)
        nodes_before += _count_nodes(doc_path)
        chains.append({"node": node, "path": doc_path})

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
                    parent = chains[j]["node"].getparent()
                    if parent is not None:
                        parent.remove(chains[j]["node"])
                    chains[i] = merged
                    chains.pop(j)
                    changed = True
                    joins += 1
                    j = i + 1
                else:
                    j += 1
            i += 1

    closed_count = 0
    nodes_after = 0
    for chain in chains:
        path = chain["path"]
        node = chain["node"]

        if auto_close:
            p_start = _start(path)
            p_end = _end(path)
            if (
                p_start is not None
                and p_end is not None
                and not _is_closed(path)
                and _distance(p_start, p_end) <= tolerance
            ):
                cmds = list(path)
                cmds.append(inkex.paths.ZoneClose())
                path = inkex.Path(cmds)
                closed_count += 1

        nodes_after += _count_nodes(path)
        node.path = path
        if "transform" in node.attrib:
            del node.attrib["transform"]
        _strip_sodipodi(node)

    return {
        "joins": joins,
        "closed": closed_count,
        "paths_before": len(path_nodes),
        "paths_after": len(chains),
        "nodes_before": nodes_before,
        "nodes_after": nodes_after,
    }


# ── Inkscape extension wrapper ─────────────────────────────────────

class JoinPaths(inkex.EffectExtension):
    """Join selected paths whose endpoints overlap."""

    # ── arguments ──────────────────────────────────────────────────────
    def add_arguments(self, pars):
        pars.add_argument(
            "--tolerance",
            type=float,
            default=0.1,
            help="Maximum distance between endpoints to consider them overlapping",
        )
        pars.add_argument(
            "--units",
            type=str,
            default="mm",
            help="Unit for the tolerance value",
        )
        pars.add_argument(
            "--keep_style",
            type=inkex.Boolean,
            default=True,
            help="Keep the style of the first path in every joined pair",
        )

    # ── helpers (delegate to module-level functions) ───────────────────

    def _to_document_units(self, value, units):
        """Convert *value* given in *units* to SVG user units (px at 96 dpi)."""
        return self.svg.unittouu(f"{value}{units}")

    # ── main logic ─────────────────────────────────────────────────────
    def effect(self):
        paths = [
            node
            for node in self.svg.selected.values()
            if isinstance(node, inkex.PathElement)
        ]

        if len(paths) < 2:
            inkex.errormsg("Please select at least two path objects to join.")
            return

        tolerance = self._to_document_units(
            self.options.tolerance, self.options.units
        )

        stats = join_path_elements(paths, tolerance)

        inkex.errormsg(
            f"Join Paths stats:\n"
            f"  Joins performed: {stats['joins']}\n"
            f"  Paths auto-closed: {stats['closed']}\n"
            f"  Paths before: {stats['paths_before']}  ->  after: {stats['paths_after']}\n"
            f"  Nodes before: {stats['nodes_before']}  ->  after: {stats['nodes_after']}"
        )


if __name__ == "__main__":
    JoinPaths().run()
