"""
Creates truchet patter from symbols.
"""

from lxml.etree import tostring

import random
import inkex
import math
from inkex.elements import Group, Circle


class PhyllotaxisPattern(inkex.GenerateExtension):

    angle = 137.5

    def add_arguments(self, pars):
        pars.add_argument(
            "-c", "--constant", type=float, default=5, help="constant for phyllotaxis"
        )
        pars.add_argument(
            "-i", "--iterations", type=int, default=10, help="number of tiles in x direction"
        )
        pars.add_argument(
            "-r", "--radius", type=float, default=5, help="circle radius for phyllotaxis"
        )
        pars.add_argument(
            "-s", "--scale_radius", type=float, default=1, help="scaling radius for each iteration of phyllotaxis"
        )
        pars.add_argument(
            "-v", "--scale_constant", type=float, default=1, help="scaling constant for each iteration of phyllotaxis"
        )
        pars.add_argument(
            "-a", "--angle", type=float, default=137.5, help="angle for each iteration of phyllotaxis"
        )


    def generate(self):


        phyllotaxis_group = []
        for i in range(self.options.iterations):
            x= (self.options.constant + i * self.options.scale_constant) * math.sqrt(i) * math.cos(self.options.angle * i)
            y= (self.options.constant + i * self.options.scale_constant) * math.sqrt(i) * math.sin(self.options.angle * i)
            circle = Circle.new([x,y], self.options.radius + self.options.scale_radius * i)
            phyllotaxis_group.append(circle)


        phyllotaxis_group = Group.new("Phyllotaxis", *phyllotaxis_group)


        return phyllotaxis_group


if __name__ == "__main__":
    PhyllotaxisPattern().run()
