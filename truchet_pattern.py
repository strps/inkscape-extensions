"""
Creates Truchet pattern from symbols in the document's <defs>.
Updated for modern Inkscape (1.3+ / inkex 1.3+).
"""

import random
import copy
import inkex
from inkex import Use, Group, Symbol, PathElement, ShapeElement
from join_paths import join_path_elements


class TruchetPattern(inkex.GenerateExtension):
    def add_arguments(self, pars):
        pars.add_argument(
            "-c", "--columns", type=int, default=10,
            help="Number of tiles horizontally"
        )
        pars.add_argument(
            "-r", "--rows", type=int, default=10,
            help="Number of tiles vertically"
        )
        pars.add_argument(
            "-s", "--tile_size", type=float, default=40.0,
            help="Size of each tile (in document units)"
        )
        pars.add_argument(
            "-p", "--convert_to_paths", type=inkex.Boolean, default=False,
            help="Convert symbol references to paths"
        )
        pars.add_argument(
            "-j", "--join_paths", type=inkex.Boolean, default=False,
            help="Join adjacent paths whose endpoints overlap"
        )
        pars.add_argument(
            "-t", "--join_tolerance", type=float, default=0.1,
            help="Tolerance for joining path endpoints"
        )
        pars.add_argument(
            "--replace_stroke_width", type=inkex.Boolean, default=False,
            help="Override the stroke width on all paths"
        )
        pars.add_argument(
            "--stroke_width", type=float, default=1.0,
            help="New stroke width value"
        )

    def generate(self):
        # Get only <symbol> elements from defs
        symbols = [el for el in self.svg.defs if isinstance(el, Symbol)]
        if not symbols:
            inkex.errormsg("No symbols found in the document's <defs>.\n"
                           "Create some symbols (Object → Symbol) and try again.")
            return

        truchet = []
        size = self.options.tile_size
        half = size / 2.0

        for i in range(self.options.columns):
            for j in range(self.options.rows):
                # Pick a random symbol
                symbol = random.choice(symbols)

                # Create <use> — now with the required x=0, y=0
                use = Use.new(symbol, 0, 0)

                # Build transform: position + rotate around own center
                angle = 90 * random.randrange(4)
                px = i * size
                py = j * size

                t = inkex.Transform()
                t.add_rotate(angle, [px, py])                  # ← rotate FIRST, in place around (0,0)
                t.add_translate(px, py)              # ← then translate to position

                # t = inkex.Transform()
                # t.add_translate(px, py)           # move to grid position
                # t.add_translate(half, half)       # move to center
                # t.add_rotate(angle)               # rotate
                # t.add_translate(-half, -half)     # move back

                use.transform = t
                use._symbol_ref = symbol  # store for convert_to_paths

                truchet.append(use)

        # Wrap everything in a group
        group = Group.new("Truchet Pattern", *truchet)

        if self.options.convert_to_paths:
            group = self._convert_uses_to_paths(group)

        if self.options.join_paths:
            if not self.options.convert_to_paths:
                inkex.errormsg("Join Paths requires 'Convert symbols to paths' to be enabled.")
            else:
                self._join_paths_in_group(group)

        if self.options.replace_stroke_width:
            self._replace_stroke_width(group)

        return group

    def _convert_uses_to_paths(self, group):
        """Replace each <use> referencing a symbol with a deep copy of the symbol's children."""
        for use in list(group):
            if not isinstance(use, Use):
                continue
            ref = getattr(use, '_symbol_ref', None)
            if ref is None:
                continue

            # Copy the symbol's children directly into the main group
            transform = use.transform
            idx = list(group).index(use)
            group.remove(use)
            for child in ref:
                clone = copy.deepcopy(child)
                clone.transform = transform @ clone.transform
                group.insert(idx, clone)
                idx += 1

        return group

    def _join_paths_in_group(self, group):
        """Join overlapping paths inside the group using the shared join logic."""
        path_nodes = [child for child in group if isinstance(child, PathElement)]
        if len(path_nodes) < 2:
            return
        tolerance = self.options.join_tolerance
        stats = join_path_elements(path_nodes, tolerance)
        inkex.errormsg(
            f"Truchet Join stats: {stats['joins']} joins, "
            f"{stats['paths_before']} -> {stats['paths_after']} paths"
        )

    def _replace_stroke_width(self, group):
        """Set the stroke-width on every shape element in the group."""
        width = str(self.options.stroke_width)
        for child in group.iter():
            if isinstance(child, ShapeElement):
                style = child.style
                style["stroke-width"] = width
                child.style = style

if __name__ == "__main__":
    TruchetPattern().run()
