import math
import sys
import uuid

import attr

from . import errors
from .trig import calc_distance, deg2rad, rotate_coords


class FakeValidator:
    def check_all_svg_attribute_values(self, *args):
        return True

    def check_svg_type(self, *args):
        return True

    def check_svg_attribute_value(self, *args):
        return True

    def check_valid_children(self, *args):
        return True


@attr.s
class LogTurtleEnv:

    initialized = attr.ib(default=False)
    screen = attr.ib(default=None)
    output_file = attr.ib(default=None)
    html_folder = attr.ib(default=None)
    turtle = attr.ib(default=None)
    html_args = attr.ib(default=attr.Factory(dict))

    @classmethod
    def create_turtle_env(cls):
        """
        Create the Deferred TK turtle environment.
        """
        return cls()

    def initialize(self, **kwargs):
        """
        Initialize the turtle environment.
        """
        self.screen = LogTurtleScreen.create_screen()
        self.output_file = kwargs.get("output_file")
        self.html_folder = kwargs.get("html_folder")
        self.html_args = kwargs.get("html_args", {})
        self.initialized = True

    def create_turtle(self):
        """
        Create a turtle.
        """
        turtle = self.turtle
        if turtle is None:
            turtle = LogTurtle.create_turtle(self.screen)
            self.turtle = turtle
        return turtle

    def wait_complete(self):
        """
        The main program will wait until this turtle backend
        method returns.
        For a GUI backend, this could mean the user has exited the GUI.
        """
        output_file = self.output_file
        if output_file is not None:
            self.turtle.write_svg(output_file)
        html_folder = self.html_folder
        if html_folder is not None:
            self.create_html_()

    def create_html_(self):
        pass

    @property
    def stdout(self):
        return sys.stdout

    @property
    def stderr(self):
        return sys.stderr

    @property
    def halt(self):
        return False

    @halt.setter
    def halt(self, value):
        raise NotImplementedError(
            "HALT is not implemented for the SVG Turtle environment."
        )

    def process_events(self):
        """
        Process any events for the turtle backend.
        """
        pass

    def cartesian_heading(self, theta):
        """
        Return the aubsolute Cartesian heading for the turtle in degrees.
        """
        return theta

    def turtle_heading_from_cartesian_heading(self, theta):
        """
        Return an absolute turtle heading from a Cartesian heading.
        """
        return theta


@attr.s
class LogTurtleScreen:
    """
    Screen abstraction for batch SVG turtles.
    """

    drawing = attr.ib(default=None)
    _mode = attr.ib(default=None)
    _colormode = attr.ib(default=None)
    _bgcolor = attr.ib(default="black")

    @classmethod
    def create_screen(cls, size=(1000, 1000), viewbox="-500 -500 1000 1000"):
        screen = cls()
        return screen

    def mode(self, mode=None):
        if mode is None:
            return self._mode
        else:
            self._mode = mode

    def colormode(self, colormode=None):
        if colormode is None:
            return self._colormode
        elif colormode not in (1.0, 255):
            raise Exception("Color mode must be `1.0` or `255`.")
        else:
            self._colormode = colormode

    def bgcolor(self, *args):
        """
        Get or set background color.
        """
        arg_count = len(args)
        if arg_count == 0:
            return self._bgcolor
        elif arg_count == 1:
            arg = args[0]
            if isinstance(arg, tuple):
                arg = rgb2hex(*arg, mode=self._colormode)
            self._bgcolor = arg
        elif arg_count == 3:
            self._bgcolor = rgb2hex(*args, mode=self._colormode)
        else:
            raise Exception("Invalid color specification `{}`.".format(tuple(*args)))


@attr.s
class LogTurtle:
    """
    Turtle for drawing to an SVG image.
    """

    screen = attr.ib(default=None)
    _pendown = attr.ib(default=True)
    _pencolor = attr.ib(default="white")
    _pensize = attr.ib(default=1)
    _fillcolor = attr.ib(default="white")
    _pos = attr.ib(default=(0, 0))
    home_heading = attr.ib(default=90)
    _heading = attr.ib(default=90)
    _visible = attr.ib(default=True)
    _speed = attr.ib(default=5)
    _components = attr.ib(default=attr.Factory(list))
    _bounds = attr.ib(default=(0, 0, 0, 0))
    _current_polyline = attr.ib(default=None)
    _history = attr.ib(default=attr.Factory(list))
    # Fill attributes.
    # _fill_mode: off, fill, or unfill
    # _filled_components: index 0 is always a polygon
    # _hole components: always a polygons; may not have any entries
    # _complete_hole_components: Holes of complete figures (arcs, ellipses, circles).
    _fill_mode = attr.ib(default="off")  # off, fill, or unfill
    _filled_components = attr.ib(default=None)
    _hole_components = attr.ib(default=None)
    _complete_hole_components = attr.ib(default=None)
    _text_alignments = attr.ib(default=dict(left="start", right="end", center="middle"))

    @classmethod
    def create_turtle(cls, screen):
        turtle = cls()
        turtle.screen = screen
        return turtle

    def write_svg(self, fout):
        """
        Write SVG output to file object `fout`.
        """
        drawing = self.screen.drawing
        g = self.screen.drawing.g()
        g["transform"] = "matrix(0 1 1 0 0 0) rotate(90)"
        drawing.add(g)
        xmin, xmax, ymin, ymax = self._bounds
        w = xmax - xmin
        h = ymax - ymin
        vb = "{} {} {} {}".format(xmin, ymin, w, h)
        drawing["width"] = "100%"
        drawing["height"] = "100%"
        drawing["viewBox"] = vb
        components = self._components
        for component in components:
            if hasattr(component, "points") and len(component.points) == 0:
                continue
            g.add(component)
        drawing.write(fout)

    def get_bounds(self):
        """
        Return the current bounds of the graphics as a tuple of
        (x, y, w, h)
        """
        return self._bounds

    def isdown(self):
        return self._pendown

    def pos(self):
        return self._pos

    def xcor(self):
        return self._pos[0]

    def ycor(self):
        return self._pos[1]

    def _get_xy(self, x, y=None):
        """
        Normalize X, Y coordinate inputs.
        """
        if y is None:
            if len(x) != 2:
                raise Exception(
                    "Expected coordinates `(x, y)` or `x, y`, but received `{}`.".format(
                        x
                    )
                )
            else:
                x, y = x
        return (x, y)

    def setpos(self, x, y=None):
        self._line_to(x, y)

    def _line_to(self, x1, y1, no_stroke=False):
        """
        Set the new pos.
        If the pen is down, add a new line.
        """
        x0, y0 = self._pos
        pendown = self._pendown

        if self._pendown and not no_stroke:
            ## calculate angle between x1, y1, x0, y0 and the current heading of the turtle to calculate the angle to turn and also calculate distance and use fd or bk
            dx = x1 - x0
            dy = y1 - y0
            dist = math.sqrt(dx**2 + dy**2)
            if dist > 0:
                theta = math.atan2(dy, dx)
                theta = theta * 180.0 / math.pi
                heading = self._heading
                angle = heading - theta
                self.left(angle)
                self._heading = theta
                self.forward(dist)
            else:
                self._pos = (x1, y1)

        self._pos = (x1, y1)

    def _get_current_polyline(self):
        """
        Get the current polyline or create a new one if it doesn't exist.
        """
        polyline = self._current_polyline
        if polyline is None:
            polyline = self.screen.drawing.polyline()
            polyline["stroke"] = self._pencolor
            polyline["stroke-width"] = self._pensize
            polyline["stroke-linecap"] = "square"
            polyline["class"] = "hole"
            polyline["fill-opacity"] = 0
            x, y = self._pos
            polyline.points.append((x, y))
            polyline["class"] = "no-fill"
            polyline["fill-opacity"] = 0
            self._components.append(polyline)
            self._current_polyline = polyline
        return polyline

    def _adjust_bounds(self, x, y):
        """
        Adjust the bounds of the drawing.
        """
        xmin, xmax, ymin, ymax = self._bounds
        xmin = min(x, xmin)
        xmax = max(x, xmax)
        ymin = min(y, ymin)
        ymax = max(y, ymax)
        self._bounds = (xmin, xmax, ymin, ymax)

    def heading(self):
        return self._heading

    def setheading(self, heading):
        self._heading = heading

    def towards(self, x, y=None):
        x1, y1 = self._get_xy(x, y)
        x0, y0 = self._pos
        theta = math.atan2(y1 - y0, x1 - x0)
        return theta * 180.0 / math.pi

    def penup(self):
        if not self._pendown:
            return
        else:
            self._pendown = False
        self._history.append(("pu"))

    def pendown(self):
        if self._pendown:
            return
        else:
            self._pendown = True
        self._history.append(("pd"))

    def right(self, angle):
        heading = self._heading - angle
        self._heading = heading % 360
        self._history.append(("rt", angle))

    def left(self, angle):
        heading = self._heading + angle
        self._heading = heading % 360
        self._history.append(("lt", angle))

    def forward(self, dist):
        dx, dy = calc_distance(self._heading, dist)
        x, y = self._pos
        x += dx
        y += dy
        self._pos = (x, y)
        self._history.append(("fd", dist))

    def backward(self, dist):
        dx, dy = calc_distance(self._heading, -dist)
        x, y = self._pos
        x += dx
        y += dy
        self._pos = (x, y)
        self._history.append(("bk", dist))

    def clear(self):
        self.components = []
        self._pos = (0, 0)
        self._heading = self.home_heading

    def home(self):
        self._line_to(0, 0)
        self._heading = self.home_heading

    def pencolor(self, *args):
        arg_count = len(args)
        if arg_count == 0:
            return self._pencolor
        elif arg_count == 1:
            arg = args[0]
            if isinstance(arg, tuple):
                arg = rgb2hex(*arg, mode=self.screen.colormode())
            self._pencolor = arg
        elif arg_count == 3:
            self._pencolor = rgb2hex(*args, mode=self.screen.colormode())
        else:
            raise Exception("Invalid color specification `{}`.".format(tuple(*args)))
        self._current_polyline = None

    def pensize(self, width=None):
        if width is None:
            return self._pensize
        else:
            self._pensize = width
            self._current_polyline = None

    def fillcolor(self, *args):
        arg_count = len(args)
        if arg_count == 0:
            return self._fillcolor
        elif arg_count == 1:
            arg = args[0]
            if isinstance(arg, tuple):
                arg = rgb2hex(*arg, mode=self.screen.colormode())
            self._fillcolor = arg
        elif arg_count == 3:
            self._fillcolor = rgb2hex(*args, mode=self.screen.colormode())
        else:
            raise Exception("Invalid color specification `{}`.".format(tuple(*args)))

    def begin_fill(self):
        pass

    def end_fill(self):
        pass

    def get_mask_(self):
        """
        Generate a mask_group and its ID as (mask_id, mask_group).
        """
        dwg = self.screen.drawing
        mask_id = uuid.uuid4().hex
        mask = dwg.defs.add(dwg.mask(id=mask_id))
        mask_group = dwg.g()
        mask.add(mask_group)
        return (mask_id, mask_group)

    def add_hole_component_(self, component=None):
        """
        Add a hole component and return it.
        """
        if component is not None:
            self.add_complete_hole_component_(component)
            return
        hole_components = self._hole_components
        if len(hole_components) > 0:
            container = hole_components[-1]
            if len(container.points) <= 2:
                hole_components.pop()
        hole_polygon = self.screen.drawing.polygon()
        hole_components.append(hole_polygon)
        return hole_polygon

    def add_complete_hole_component_(self, component):
        """
        Add independent hole components.
        """
        self._complete_hole_components.append(component)

    def get_hole_component_(self):
        """
        Get the current hole component.
        Raise error if no current holes.
        """
        hole_components = self._hole_components
        if len(hole_components) == 0:
            raise Exception("No hole components.  No UNFILL command.")
        return hole_components[-1]

    def begin_unfilled(self):
        """
        Only valid within `begin_fill()` and `end_fill()` context.
        Shapes drawn in between inocations of this method and `end_unfilled()`
        will not be filled but instead will behave as holes in the current fill.
        """
        if self._fill_mode != "fill":
            raise Exception(
                "`begin_unfilled()` can only be called within "
                "`begin_fill()` ... `end_fill()` context."
            )
        self._fill_mode = "unfill"
        self.add_hole_component_()

    def end_unfilled(self):
        """
        Only valid within `begin_fill()` and `end_fill()` context.
        Shapes drawn in between inocations of `begin_unfilled()` and this method
        will not be filled but instead will behave as holes in the current fill.
        """
        if self._fill_mode != "unfill":
            raise Exception(
                "`end_unfilled()` can only be called after `begin_unfilled()`."
            )
        self._fill_mode = "fill"

    def hideturtle(self):
        self._visible = False

    def showturtle(self):
        self._visible = True

    def isvisible(self):
        return self._visible

    def speed(self, num=None):
        if num is None:
            return self._speed
        else:
            self._speed = num

    def circle(self, radius, angle, steps=5):
        """
        The center of the circle with be `radius` units to 90 degrees left of
        the turtle's current heading.
        The turtle will trace out an arc that sweeps out `angle` degrees.
        """
        x, y = self._pos
        theta = (self._heading + 90) % 360
        xcenter = x + math.cos(deg2rad(theta)) * radius
        ycenter = y + math.sin(deg2rad(theta)) * radius
        self._adjust_bounds(xcenter - radius, ycenter - radius)
        self._adjust_bounds(xcenter + radius, ycenter + radius)

        self.regular_polygon_(radius, steps, angle, xcenter, ycenter)

        # component["stroke"] = self._pencolor
        # component["stroke-width"] = self._pensize
        # if self._fill_mode == "unfill":
        #     self.add_hole_component_(component)
        # elif self._fill_mode == "fill":
        #     self._filled_components.append(component)
        # else:
        #     component["class"] = "no-fill"
        #     component["fill-opacity"] = 0
        #     self._components.append(component)

    def regular_polygon_(self, radius, sides, angle, xcenter, ycenter):
        """
        Add the coordinates of a regular polygon (or segments of it)
        to the primary component.
        """
        heading = self._heading
        step_angle = angle / sides
        angle = abs(angle)
        alpha = heading
        angle_offset = 0
        for n in range(sides + 1):
            angle_offset = step_angle * n
            theta = deg2rad(alpha + angle_offset)
            x = xcenter + radius * math.cos(theta)
            y = ycenter + radius * math.sin(theta)
            if n == 0:
                no_stroke = True
            else:
                no_stroke = False
            self._line_to(x, y, no_stroke=no_stroke)
            if abs(angle_offset) >= angle:
                break
        if angle == 360:
            polyline = self._get_current_polyline()
            polyline["stroke-linecap"] = "round"

    def circle_arc_(self, radius, angle, theta, xcenter, ycenter):
        """
        Create a circular arc component and return it.
        """
        x, y = self._pos
        xrot = 0
        if abs(angle) > 180.0:
            large_arc = 1
        else:
            large_arc = 0
        if angle < 0:
            sweep_flag = 1
        else:
            sweep_flag = 0
        theta = theta - 180 + angle
        xdest = xcenter + math.cos(deg2rad(theta)) * radius
        ydest = ycenter + math.sin(deg2rad(theta)) * radius
        component = self.screen.drawing.path()
        command = "M {} {}".format(x, y)
        component.push(command)
        command = "A {} {} {} {} {} {} {}".format(
            abs(radius), abs(radius), xrot, large_arc, sweep_flag, xdest, ydest
        )
        component.push(command)
        return component

    def setundobuffer(self, num):
        pass

    def undo(self):
        pass

    def undobufferentries(self):
        return 0

    def write(self, text, move=False, align="left", font=("Arial", 8, "normal")):
        """
        Write text to the image.
        """
        if move:
            raise errors.LogoError(
                "Moving the turtle to the end of the "
                "text is not supported by the SVG Turtle back end."
            )
        x, y = self._pos
        x, y = rotate_coords(0, 0, y, x, -90)
        txt_obj = self.screen.drawing.text(text, insert=(x, y))
        txt_obj["fill"] = self._pencolor
        txt_obj["text-anchor"] = self._text_alignments[align]
        font_face, font_size, font_weight = font
        txt_obj["style"] = "font-family:{};font-weight:{};".format(
            font_face, font_weight
        )
        txt_obj["font-size"] = "{}pt".format(font_size)
        txt_obj["transform"] = "matrix(0 1 1 0 0 0) rotate(90)"
        self._components.append(txt_obj)

    def getHistory(self):
        return self._history


def hexpair(x):
    """
    Return 2 hex digits for integers 0-255.
    """
    return ("0{}".format(hex(x)[2:]))[-2:]


def rgb2hex(r, g, b, mode=255):
    """
    Return a hex color suitble for SVG given RGB components.
    """
    return "#{}{}{}".format(hexpair(r), hexpair(g), hexpair(b))


def _round1(x):
    return int(x * 10) / 10


def svg2cartesian(x, y):
    return rotate_coords(0, 0, y, x, 90)


def cartesian2svg(x, y):
    return rotate_coords(0, 0, y, x, -90)
