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

    year = 2023
    font_size = 5
    font_size_1 = 4
    font_size_2 = 3
    font_family = "Arial"
    size = 10
    w_days = ["L", "M", "M", "J", "V", "S", "D"]

    gap = 1

    def add_arguments(self, pars):
        pars.add_argument(
            "--mybool",
            type=inkex.Boolean,
            help="An example option, put your options here",
        )

    def Square_with_text(self, x, y, size, text: str, font_size, font_family):
        t = TextElement.new(
            style=f"font-size:{font_size};fill:#000000; text-anchor:middle; dominant-baseline:middle;"
        )
        t.text = text
        t.set("font-family", font_family)
        t.set("x", x + size / 2)
        t.set("y", y + size / 2)
        r = Rectangle.new(
            (x), y, size, size, style="fill:none;stroke:#000000;stroke-width:0.1mm"
        )
        g = Group.new("Week Day", t, r)
        return g

    def Square_with_squares(self, x, y, size):
        q = 5
        s_1 = Rectangle.new(
            (x), y, size, size, style="fill:none;stroke:#000000;stroke-width:0.1mm"
        )
        s_a = []
        for i in range(q):
            s_a.append(
                Rectangle.new(
                    x + (i * size / q),
                    y,
                    size / q,
                    size / q,
                    style="fill:none;stroke:#000000;stroke-width:0.1mm",
                )
            )
        g = Group.new("Week Day", s_1, *s_a)
        return g

    def Generate_week(self, x, y, size, week_number: int, year: int):
        week_number = self.Square_with_week_number(
            x, y, size, 5, "Arial", week_number, year
        )  # TODO: change this to take values from user input
        week = []
        for i in range(7):
            week.append(self.Square_with_squares(i * size + size, y, size))
        return Group.new("Week", week_number, *week)

    # function that gets the year, the week nomber and returns the dates of the monday and sunday of that week
    def get_week_dates(self, year: int, week_number: int):
        d = datetime.date(year, 1, 1)
        if d.weekday() <= 3:
            d = d - datetime.timedelta(d.weekday())
        else:
            d = d + datetime.timedelta(7 - d.weekday())
        dlt = datetime.timedelta(days=(week_number - 1) * 7)
        return d + dlt, d + dlt + datetime.timedelta(days=6)

    def Square_with_week_number(
        self, x, y, size, font_size, font_family, week_number=24, year=2023
    ):
        dates = self.get_week_dates(year, week_number)

        t1 = TextElement.new(
            style=f"font-size:{self.font_size_2};fill:#000000; text-anchor:middle; dominant-baseline: hanging ;"
        )
        t1.text = dates[0].strftime("%b%d").upper()
        t1.set("font-family", font_family)
        t1.set("x", x + size / 2)
        t1.set("y", y + self.gap)  # TODO: change this to take values to variable

        t2 = TextElement.new(
            style=f"font-size:{self.font_size_1};fill:#000000; text-anchor:middle; dominant-baseline:middle;"
        )

        t2.text = str(week_number)
        t2.set("font-family", font_family)
        t2.set("x", x + size / 2)
        t2.set("y", y + size / 2)

        t3 = TextElement.new(
            style=f"font-size:{self.font_size_2};fill:#000000; text-anchor:middle; dominant-baseline: auto;"
        )
        t3.text = dates[1].strftime("%b%d").upper()
        t3.set("font-family", font_family)
        t3.set("x", x + size / 2)
        t3.set("y", y + size - self.gap)

        r = Rectangle.new(
            (x), y, size, size, style="fill:none;stroke:#000000;stroke-width:0.1mm"
        )
        g = Group.new("Week Day", t1, t2, t3, r)
        return g

    def generate(self):

        # Temporal arguments for generating the grid, TODO: change this to take values from user input
        font_size = 5
        font_family = "Arial"
        size = 10
        w_days = ["L", "M", "M", "J", "V", "S", "D"]

        # Generate Week Headers as a group
        week_square = []
        for i in range(7):
            g = self.Square_with_text(
                i * size + size, 0, size, w_days[i], font_size, font_family
            )
            week_square.append(g)

        # Generate Week Headers as a group

        week_days_header = Group.new("Week Header", *week_square)

        # Getting today's week number
        week_number = datetime.date.today().isocalendar()[1]

        # Get last week number of the year
        last_week_number = datetime.date(
            datetime.date.today().year, 12, 28
        ).isocalendar()[1]

        # Generate all weeks 24-52
        n_weeks = last_week_number - week_number + 1
        days_grid = []
        for i in range(0, n_weeks):
            days_grid.append(
                self.Generate_week(0, i * size + size, size, i + week_number, self.year)
            )

        # Group all weeks
        group = Group.new("Weeks", week_days_header, *days_grid)

        return group

    # def effect(self):
    #     self.msg("This is an empty extension, please see tutorials for more details.")


if __name__ == "__main__":
    StrpsExtension().run()
