"""
Creates truchet patter from symbols.
"""

from lxml.etree import tostring

import random
import inkex
from inkex import TextElement, FlowRoot
from inkex.utils import KeyDict
from inkex.elements import Use, Group, Rectangle


class TruchetPattern(inkex.GenerateExtension):


    tile_edge = 40

    def add_arguments(self, pars):
        pars.add_argument(
            "-c", "--columns", type=int, default=5, help="number of tiles in x direction"
        )
        pars.add_argument(
            "-r", "--rows", type=int, default=5, help="number of tiles in y direction"
        )
        pars.add_argument(
            "-t", "--tile_size", type=float, default=5, help="number of tiles in y direction"
        )


    def ttt(self, element): ...

    def generate(self):

        symbols = self.svg.defs

        if len(symbols) == 0:
            inkex.errormsg("No symbols found in the document.")
            return

        truchet = []
        for i in range(self.options.columns):
            for j in range(self.options.rows):
                symbol = symbols[random.randrange(len(symbols))]
                use = Use.new(symbol, 0, 0)
                use.transform.add_translate(self.options.tile_size * i, self.options.tile_size * j)
                # use.transform.add_rotate(deg=90 * random.randrange(4), center_x = 0, center_y =0)
                use.transform.add_rotate(deg=90 * random.randrange(4))
                # use.transform.add_rotate(deg=90 * random.randrange(4))
                # use.transform.add_translate(-self.tile_edge/2, -self.tile_edge/2)
                truchet.append(use)

        truchet_group = Group.new("Truchet", *truchet)

        return truchet_group


if __name__ == "__main__":
    TruchetPattern().run()
