"""
Creates Truchet pattern from symbols in the document's <defs>.
Updated for modern Inkscape (1.3+ / inkex 1.3+).
"""

import random
import inkex
from inkex import Use, Group, Symbol


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
                

                # Force the tile to the chosen size
                #use.set("width", str(size))
                #use.set("height", str(size))

                truchet.append(use)

        # Wrap everything in a group
        group = Group.new("Truchet Pattern", *truchet)
        return group

if __name__ == "__main__":
    TruchetPattern().run()
