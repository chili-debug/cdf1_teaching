"""Small Rhino/Grasshopper helpers for generating Bauhaus-inspired geometry."""

import random

try:
    import Rhino.Geometry as rg
except ImportError:  # pragma: no cover - Rhino is available in Grasshopper runtime.
    rg = None

try:
    from System.Drawing import Color as DrawingColor
except ImportError:  # pragma: no cover - System.Drawing is available in Rhino.
    DrawingColor = None


class _FallbackPoint3d:
    """Very small stand-in used when Rhino is not available."""

    def __init__(self, x, y, z):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __iter__(self):
        return iter((self.x, self.y, self.z))

    def __repr__(self):
        return f"Point3d({self.x}, {self.y}, {self.z})"


class _FallbackPointCloud(list):
    """List-like point cloud used when Rhino.Geometry is unavailable."""

    def __init__(self, points=None):
        super().__init__(points or [])

    def Add(self, point):
        self.append(point)


def _as_min_max(domain):
    """Normalize a domain into two 3D corner points."""
    if domain is None:
        return (0.0, 0.0, 0.0), (10.0, 10.0, 10.0)

    if rg is not None:
        if isinstance(domain, rg.Box):
            bbox = domain.BoundingBox
            return (bbox.Min.X, bbox.Min.Y, bbox.Min.Z), (bbox.Max.X, bbox.Max.Y, bbox.Max.Z)
        if isinstance(domain, rg.BoundingBox):
            return (domain.Min.X, domain.Min.Y, domain.Min.Z), (domain.Max.X, domain.Max.Y, domain.Max.Z)

    if hasattr(domain, "Min") and hasattr(domain, "Max"):
        min_point = domain.Min
        max_point = domain.Max
        return (min_point.X, min_point.Y, min_point.Z), (max_point.X, max_point.Y, max_point.Z)

    if isinstance(domain, (list, tuple)) and len(domain) == 2:
        a, b = domain
        if hasattr(a, "X") and hasattr(b, "X"):
            return (a.X, a.Y, a.Z), (b.X, b.Y, b.Z)
        if hasattr(a, "x") and hasattr(b, "x"):
            return (a.x, a.y, a.z), (b.x, b.y, b.z)
        if len(a) == 3 and len(b) == 3:
            return tuple(a), tuple(b)

    if isinstance(domain, (list, tuple)) and len(domain) == 6:
        min_x, min_y, min_z, max_x, max_y, max_z = domain
        return (min_x, min_y, min_z), (max_x, max_y, max_z)

    raise TypeError(
        "domain must be a Rhino Box/BoundingBox, a pair of 3D points, or a "
        "(min_x, min_y, min_z, max_x, max_y, max_z) tuple."
    )


def create_random_point_cloud(domain=None, count=100, seed=None):
    """Create a random point cloud within a rectangular domain.

    domain : Rhino.Geometry.Box | Rhino.Geometry.BoundingBox | tuple
        A 3D domain defined by its minimum and maximum corners. If omitted,
        a 10x10x10 box from the origin is used.
    count  : int
        Number of points to generate.
    seed   : int or None
        Optional random seed for reproducible output.

    Returns:
        Rhino.Geometry.PointCloud or a list-like fallback when Rhino is not
        available.
    """
    count = int(count)
    if count < 0:
        raise ValueError("count must be non-negative.")

    min_corner, max_corner = _as_min_max(domain)
    rng = random.Random(seed)

    if rg is not None:
        cloud = rg.PointCloud()
        for _ in range(count):
            x = rng.uniform(min_corner[0], max_corner[0])
            y = rng.uniform(min_corner[1], max_corner[1])
            z = rng.uniform(min_corner[2], max_corner[2])
            cloud.Add(rg.Point3d(x, y, z))
        return cloud

    points = []
    for _ in range(count):
        x = rng.uniform(min_corner[0], max_corner[0])
        y = rng.uniform(min_corner[1], max_corner[1])
        z = rng.uniform(min_corner[2], max_corner[2])
        points.append(_FallbackPoint3d(x, y, z))
    return _FallbackPointCloud(points)




def create_cone(base_point=None, height=10.0, radius=5.0, cap_bottom=True):
    """
    Build a cone as a Brep.

    base_point : Rhino.Geometry.Point3d -- center of the cone's base circle
    height     : float -- cone height along the base plane's normal (Z by default)
    radius     : float -- base circle radius
    cap_bottom : bool  -- whether to cap the base circle (closed vs open cone)

    Returns a Rhino.Geometry.Brep.
    """
    if base_point is None:
        if rg is None:
            raise RuntimeError("create_cone requires Rhino.Geometry.")
        base_point = rg.Point3d(0, 0, 0)

    plane = rg.Plane(base_point, rg.Vector3d.ZAxis)
    cone = rg.Cone(plane, height, radius)
    return cone.ToBrep(cap_bottom)

##SPHERE FUNCTION##

def create_sphere(center=None, radius=5.0):
    """
    Build a sphere as a Brep.

    center : Rhino.Geometry.Point3d -- the center of the sphere
    radius : float -- the radius of the sphere

    Returns a Rhino.Geometry.Brep.
    """

    if center is None:
        center = (0.0, 0.0, 0.0) if rg is None else rg.Point3d(0, 0, 0)

    if rg is None:
        return {"type": "sphere", "center": tuple(center), "radius": float(radius)}

    if not hasattr(center, "X"):
        center = rg.Point3d(float(center[0]), float(center[1]), float(center[2]))

    sphere = rg.Sphere(center, radius)
    return sphere.ToBrep()


def create_cube(center=None, length=10.0, width=None, height=None):
    """Create a parametrizable rectangular prism centered at ``center``.

    Length, width, and height are aligned with the world X, Y, and Z axes.
    Width and height default to length, producing a cube.
    """
    length = 10.0 if length is None else float(length)
    width = length if width is None else float(width)
    height = length if height is None else float(height)
    if min(length, width, height) <= 0:
        raise ValueError("length, width, and height must be positive.")

    if center is None:
        center = (0.0, 0.0, 0.0) if rg is None else rg.Point3d(0, 0, 0)

    if rg is None:
        try:
            center_coordinates = tuple(center)
        except TypeError as error:
            raise TypeError("center must be a 3D point or a sequence of three coordinates.") from error
        if len(center_coordinates) != 3:
            raise TypeError("center must be a 3D point or a sequence of three coordinates.")
        return {
            "type": "cube",
            "center": center_coordinates,
            "length": length,
            "width": width,
            "height": height,
        }

    if not hasattr(center, "X"):
        center = rg.Point3d(float(center[0]), float(center[1]), float(center[2]))
    plane = rg.Plane(center, rg.Vector3d.XAxis, rg.Vector3d.YAxis)
    return rg.Box(
        plane,
        rg.Interval(-length / 2.0, length / 2.0),
        rg.Interval(-width / 2.0, width / 2.0),
        rg.Interval(-height / 2.0, height / 2.0),
    ).ToBrep()


def create_random_cube_sphere_mix(
    point_cloud,
    cube_length=10.0,
    cube_width=None,
    cube_height=None,
    sphere_radius=5.0,
    cube_probability=0.5,
    seed=None,
):
    """Create a randomly chosen cube or sphere at each point in a cloud.

    ``point_cloud`` may be a Rhino PointCloud or an iterable of points.
    Returns a list of Rhino Breps when running in Rhino.
    """
    cube_probability = float(cube_probability)
    if not 0.0 <= cube_probability <= 1.0:
        raise ValueError("cube_probability must be between 0 and 1.")
    if point_cloud is None:
        raise ValueError("point_cloud must be provided.")

    points = point_cloud.GetPoints() if hasattr(point_cloud, "GetPoints") else point_cloud
    rng = random.Random(seed)
    shapes = []
    for item in points:
        point = item.Location if hasattr(item, "Location") else item
        if rng.random() < cube_probability:
            shape = create_cube(point, cube_length, cube_width, cube_height)
        else:
            shape = create_sphere(point, sphere_radius)
        shapes.append(shape)
    return shapes


def randomize_shape_colors(
    shapes,
    base_color=None,
    variation=0.25,
    seed=None,
    palette=None,
):
    """Assign reproducible colors to shapes, optionally choosing from a palette.

    Use the returned colors as the material input of Grasshopper's Custom
    Preview component, alongside the original ``shapes`` list as geometry.
    When ``palette`` is provided, one of its colors is selected for each
    shape. Otherwise ``base_color`` is shaded using ``variation``.
    """
    if shapes is None:
        raise ValueError("shapes must be provided.")

    shapes = list(shapes)
    rng = random.Random(seed)

    def as_color(color):
        if all(hasattr(color, channel) for channel in ("R", "G", "B")):
            components = (
                color.R,
                color.G,
                color.B,
                color.A if hasattr(color, "A") else 255,
            )
        else:
            components = tuple(color)
            if len(components) not in (3, 4):
                raise TypeError("Each color must be a swatch or an RGB/RGBA sequence.")
            if len(components) == 3:
                components += (255,)
        return tuple(max(0, min(255, int(value))) for value in components)

    if palette is not None:
        if base_color is not None:
            raise ValueError("Provide either base_color or palette, not both.")
        palette = list(palette)
        if not palette:
            raise ValueError("palette must contain at least one color.")
        palette = [as_color(color) for color in palette]
        selected_colors = [rng.choice(palette) for _ in shapes]
    else:
        variation = float(variation)
        if not 0.0 <= variation <= 1.0:
            raise ValueError("variation must be between 0 and 1.")
        base_color = (180, 180, 180, 255) if base_color is None else base_color
        red, green, blue, alpha = as_color(base_color)
        selected_colors = []
        for _ in shapes:
            brightness = rng.uniform(1.0 - variation, 1.0 + variation)
            rgb = tuple(
                max(0, min(255, int(channel * brightness)))
                for channel in (red, green, blue)
            )
            selected_colors.append((rgb[0], rgb[1], rgb[2], alpha))

    result = []
    for red, green, blue, alpha in selected_colors:
        if DrawingColor is not None:
            result.append(DrawingColor.FromArgb(alpha, red, green, blue))
        else:
            result.append((red, green, blue, alpha))
    return result


def random_boolean_difference(solids, probability=0.5, seed=None, tolerance=0.001):
    """Randomly subtract overlapping solids and replace successful pairs.

    Potential pairs are tested in a seeded random order, rather than pairing
    arbitrary solids first. Each solid is used in at most one successful
    difference. The two originals are replaced by the boolean result. Solids
    without a successful difference remain unchanged.

    Inputs must be closed Rhino Breps. Use ``seed`` to reproduce the same
    pair selection and subtraction directions.
    """
    if rg is None:
        raise RuntimeError("random_boolean_difference requires Rhino.Geometry.")
    if solids is None:
        raise ValueError("solids must be provided.")

    probability = float(probability)
    tolerance = float(tolerance)
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between 0 and 1.")
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive.")

    solids = list(solids)
    if any(solid is None or not solid.IsSolid for solid in solids):
        raise ValueError("Every input must be a non-null, closed Rhino Brep solid.")

    rng = random.Random(seed)
    candidate_pairs = [
        (first, second)
        for first in range(len(solids))
        for second in range(first + 1, len(solids))
    ]
    rng.shuffle(candidate_pairs)
    used = set()
    result = []

    def bounding_boxes_overlap(first, second):
        first_box = first.GetBoundingBox(True)
        second_box = second.GetBoundingBox(True)
        return (
            first_box.Min.X <= second_box.Max.X
            and first_box.Max.X >= second_box.Min.X
            and first_box.Min.Y <= second_box.Max.Y
            and first_box.Max.Y >= second_box.Min.Y
            and first_box.Min.Z <= second_box.Max.Z
            and first_box.Max.Z >= second_box.Min.Z
        )

    def boolean_result(target, cutter):
        pieces = rg.Brep.CreateBooleanDifference(target, cutter, tolerance)
        if pieces is None:
            return []
        if isinstance(pieces, rg.Brep):
            return [pieces]
        return list(pieces)

    for first, second in candidate_pairs:
        if first in used or second in used or rng.random() >= probability:
            continue

        solid_a, solid_b = solids[first], solids[second]
        if not bounding_boxes_overlap(solid_a, solid_b):
            continue

        if rng.random() < 0.5:
            target, cutter = solid_a, solid_b
        else:
            target, cutter = solid_b, solid_a

        difference = boolean_result(target, cutter)
        if not difference:
            difference = boolean_result(cutter, target)

        if difference:
            used.update((first, second))
            result.extend(difference)

    result.extend(solid for index, solid in enumerate(solids) if index not in used)
    return result


