#!/usr/bin/env python
"""
Join Paths – Inkscape Extension

Joins selected open paths whose endpoints coincide (within a tolerance).
Paths are chained end-to-end: if the end of path A is within tolerance of the
start (or end) of path B, the two are merged into a single continuous path.

Works with the modern inkex API (Inkscape 1.0+).
"""

__version__ = "1.0"
__author__ = "CJ"

import sys
import math
import inkex


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

    # ── helpers ────────────────────────────────────────────────────────
    @staticmethod
    def _distance(p1, p2):
        """Euclidean distance between two (x, y) points."""
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    @staticmethod
    def _start(path_cmds):
        """Return the first point of an inkex.Path (after converting to absolute)."""
        for cmd in path_cmds:
            if hasattr(cmd, "x") and hasattr(cmd, "y"):
                return (cmd.x, cmd.y)
        return None

    @staticmethod
    def _end(path_cmds):
        """Return the last on-curve point of an inkex.Path."""
        last = None
        for cmd in path_cmds:
            if hasattr(cmd, "x") and hasattr(cmd, "y"):
                last = (cmd.x, cmd.y)
        return last

    @staticmethod
    def _reverse_path(path):
        """Return the reversed inkex.Path."""
        return path.reverse()

    def _to_document_units(self, value, units):
        """Convert *value* given in *units* to SVG user units (px at 96 dpi)."""
        return self.svg.unittouu(f"{value}{units}")

    @staticmethod
    def _count_nodes(path):
        """Count the number of on-curve nodes in an inkex.Path."""
        return sum(1 for cmd in path if hasattr(cmd, 'x') and hasattr(cmd, 'y'))

    # ── main logic ─────────────────────────────────────────────────────
    def effect(self):
        # Collect selected path elements
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

        # We work with a list of "chain" dicts so we can merge freely.
        # Each chain: {'node': original SVG element, 'path': inkex.Path (absolute)}
        chains = []
        paths_before = len(paths)
        nodes_before = 0
        for node in paths:
            abs_path = node.path.to_absolute()
            nodes_before += self._count_nodes(abs_path)
            chains.append({"node": node, "path": abs_path})

        joins = 0
        changed = True
        while changed:
            changed = False
            i = 0
            while i < len(chains):
                j = i + 1
                while j < len(chains):
                    merged = self._try_merge(chains[i], chains[j], tolerance)
                    if merged is not None:
                        # Remove the second element from the SVG tree
                        parent = chains[j]["node"].getparent()
                        if parent is not None:
                            parent.remove(chains[j]["node"])

                        # Replace chain i with the merged result, drop chain j
                        chains[i] = merged
                        chains.pop(j)
                        changed = True
                        joins += 1
                        # Restart inner loop — new endpoints on chain i
                        j = i + 1
                    else:
                        j += 1
                i += 1

        # Write final paths back to the SVG
        nodes_after = 0
        for chain in chains:
            chain["node"].path = chain["path"]
            nodes_after += self._count_nodes(chain["path"])

        # Print stats
        paths_after = len(chains)
        inkex.errormsg(
            f"Join Paths stats:\n"
            f"  Joins performed: {joins}\n"
            f"  Paths before: {paths_before}  →  after: {paths_after}\n"
            f"  Nodes before: {nodes_before}  →  after: {nodes_after}"
        )

    def _try_merge(self, a, b, tol):
        """
        Try to join two chains.  Returns a new chain dict on success, None otherwise.

        Four cases (A=chain a, B=chain b):
          A.end   ≈ B.start  →  A + B
          A.end   ≈ B.end    →  A + reverse(B)
          A.start ≈ B.start  →  reverse(B) + A  (equivalently reverse(A) + B → keep A node)
          A.start ≈ B.end    →  B + A
        """
        a_start = self._start(a["path"])
        a_end = self._end(a["path"])
        b_start = self._start(b["path"])
        b_end = self._end(b["path"])

        if None in (a_start, a_end, b_start, b_end):
            return None

        keep_node = a["node"]  # always keep a's SVG element

        # Case 1: A.end ≈ B.start  →  A + B
        if self._distance(a_end, b_start) <= tol:
            new_path = self._concat_paths(a["path"], b["path"])
            return {"node": keep_node, "path": new_path}

        # Case 2: A.end ≈ B.end  →  A + reverse(B)
        if self._distance(a_end, b_end) <= tol:
            new_path = self._concat_paths(a["path"], self._reverse_path(b["path"]))
            return {"node": keep_node, "path": new_path}

        # Case 3: A.start ≈ B.end  →  B + A
        if self._distance(a_start, b_end) <= tol:
            new_path = self._concat_paths(b["path"], a["path"])
            return {"node": keep_node, "path": new_path}

        # Case 4: A.start ≈ B.start  →  reverse(B) + A
        if self._distance(a_start, b_start) <= tol:
            new_path = self._concat_paths(
                self._reverse_path(b["path"]), a["path"]
            )
            return {"node": keep_node, "path": new_path}

        return None

    @staticmethod
    def _concat_paths(path_a, path_b):
        """
        Concatenate two inkex.Path objects into one continuous path.

        The first Move command of path_b is dropped so the pen just continues
        from where path_a left off, creating a single connected subpath.
        """
        new_cmds = list(path_a)
        first_b = True
        for cmd in path_b:
            if first_b and isinstance(cmd, inkex.paths.Move):
                # Skip the initial M of the second path – we're already there
                first_b = False
                continue
            first_b = False
            new_cmds.append(cmd)
        return inkex.Path(new_cmds)


if __name__ == "__main__":
    JoinPaths().run()
