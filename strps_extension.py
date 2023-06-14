#!/usr/bin/env python
# coding=utf-8
#
# Copyright (C) [YEAR] [YOUR NAME], [YOUR EMAIL]
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
"""
Description of this extension
"""

import datetime
import inkex
from inkex.elements import TextElement, Rectangle, Group


class StrpsExtension(inkex.GenerateExtension):
    """Please rename this class, don't keep it unnamed"""
    def add_arguments(self, pars):
        pars.add_argument("--mybool", type=inkex.Boolean,\
            help="An example option, put your options here")
        
    def Square_with_text(self, x, y, size, text, font_size, font_family):
        t =TextElement.new(style=f"font-size:{font_size};fill:#000000; text-anchor:middle; dominant-baseline:middle;")
        t.text = text
        t.set('font-family', font_family)
        t.set('x' , x + size/2 )
        t.set('y' , y + size/2)
        r = Rectangle.new((x), y, size, size, style="fill:none;stroke:#000000;stroke-width:0.1mm")
        g = Group.new("Week Day", t , r)
        return g
    
    def Square_with_squares(self, x, y, size):
        q = 5
        s_1 = Rectangle.new((x), y, size/2, size/2, style="fill:none;stroke:#000000;stroke-width:0.1mm")
        s_a = []
        for i in range(q):
            s_a.append(Rectangle.new(x+(i*size/q), y, size/q, size/q, style="fill:none;stroke:#000000;stroke-width:0.1mm"))
        g = Group.new("Week Day", s_1 , *s_a)
        return g
    
    def Generate_week(self, x, y, size, week_number):
        




    def generate(self):
        #Temporal arguments for generating the grid, TODO: change this to take values from user input 
        font_size = 5
        font_family = "Arial"
        size = 10
        w_days = ["L", "M", "M", "J", "V", "S", "D"]

        #Generate Week Headers as a group
        week_square = []
        for i in range(7):
            g = self.Square_with_text(i*size+size, 0, size, w_days[i], font_size, font_family)
            week_square.append(g)

        #Generate Week Headers as a group

        week_days_header = Group.new("Week Header", *week_square)


        #Getting today's week number
        week_number = datetime.date.today().isocalendar()[1]

        #Get last week number of the year
        last_week_number = datetime.date(datetime.date.today().year, 12, 28).isocalendar()[1]

    




        return week_days_header



    # def effect(self):
    #     self.msg("This is an empty extension, please see tutorials for more details.")

if __name__ == '__main__':
    StrpsExtension().run()
