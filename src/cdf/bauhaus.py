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


<<<<<<< Updated upstream
=======
def group_shapes_by_color(shapes, colors):
    """Group shapes by their corresponding colors for Grasshopper baking.

    Returns ``(shape_groups, group_colors, layer_names)``. Each nested list
    in ``shape_groups`` contains the shapes assigned to one exact RGBA color.
    """
    if shapes is None or colors is None:
        raise ValueError("Both shapes and colors must be provided.")

    shapes = list(shapes)
    colors = list(colors)
    if len(shapes) != len(colors):
        raise ValueError("shapes and colors must have the same length.")

    def color_key(color):
        if all(hasattr(color, channel) for channel in ("R", "G", "B")):
            return (
                int(color.R),
                int(color.G),
                int(color.B),
                int(color.A) if hasattr(color, "A") else 255,
            )
        values = tuple(int(value) for value in color)
        if len(values) == 3:
            values += (255,)
        if len(values) != 4:
            raise TypeError("Each color must be a swatch or an RGB/RGBA sequence.")
        return values

    groups = {}
    for shape, color in zip(shapes, colors):
        key = color_key(color)
        groups.setdefault(key, []).append(shape)

    ordered_keys = list(groups)
    shape_groups = [groups[key] for key in ordered_keys]
    group_colors = [key for key in ordered_keys]
    layer_names = [
        "CDF1_{0}_{1}_{2}".format(red, green, blue)
        for red, green, blue, alpha in ordered_keys
    ]
    return shape_groups, group_colors, layer_names


>>>>>>> Stashed changes
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


<<<<<<< Updated upstream
=======
def _require_rhino():
    if rg is None:
        raise RuntimeError("This function requires Rhino.Geometry in Rhino/Grasshopper.")


def _as_point3d(point):
    if hasattr(point, "X"):
        return point
    return rg.Point3d(float(point[0]), float(point[1]), float(point[2]))


def _surface_from_ceiling(ceiling):
    _require_rhino()
    if isinstance(ceiling, rg.Brep):
        if ceiling.Faces.Count != 1:
            raise ValueError("ceiling must be a single planar Brep face or surface.")
        return ceiling.Faces[0]
    if isinstance(ceiling, rg.BrepFace):
        return ceiling
    if isinstance(ceiling, rg.Surface):
        return ceiling
    return None


def _plane_from_rectangle(rectangle):
    if isinstance(rectangle, rg.Plane):
        return rectangle
    if hasattr(rectangle, "TryGetPlane"):
        result = rectangle.TryGetPlane()
        if isinstance(result, tuple):
            if not result[0]:
                raise ValueError("ceiling rectangle must be planar.")
            return result[1]
        if result:
            return result
    raise TypeError("ceiling must be a Rhino surface, planar rectangle curve, or Plane.")


def create_attachment_grid(
    width=1000.0,
    depth=1000.0,
    center_x=None,
    center_y=None,
    height=3000.0,
    u_count=5,
    v_count=5,
):
    """Create a horizontal, fully parametric ceiling attachment grid.

    The grid lies in the XY plane at ``height``. U and V are represented by
    ``u_count`` and ``v_count`` points, including both boundaries.
    """
    _require_rhino()
    width = float(width)
    depth = float(depth)
    center_x = 0.0 if center_x is None else float(center_x)
    center_y = 0.0 if center_y is None else float(center_y)
    height = float(height)
    u_count = int(u_count)
    v_count = int(v_count)
    if width <= 0 or depth <= 0:
        raise ValueError("width and depth must be positive.")
    if u_count < 2 or v_count < 2:
        raise ValueError("u_count and v_count must both be at least 2.")

    min_x = center_x - width / 2.0
    min_y = center_y - depth / 2.0
    points = []
    grid_curves = []
    for row in range(v_count):
        y = min_y + depth * row / float(v_count - 1)
        row_points = [
            rg.Point3d(
                min_x + width * column / float(u_count - 1),
                y,
                height,
            )
            for column in range(u_count)
        ]
        points.extend(row_points)
        grid_curves.append(rg.Polyline(row_points).ToNurbsCurve())
    for column in range(u_count):
        column_points = [
            rg.Point3d(
                min_x + width * column / float(u_count - 1),
                min_y + depth * row / float(v_count - 1),
                height,
            )
            for row in range(v_count)
        ]
        grid_curves.append(rg.Polyline(column_points).ToNurbsCurve())
    return points, grid_curves


def create_ceiling_surface(
    width=1000.0,
    depth=1000.0,
    center_x=0.0,
    center_y=0.0,
    height=3000.0,
):
    """Create a planar ceiling surface matching the attachment grid."""
    _require_rhino()
    width = float(width)
    depth = float(depth)
    center_x = 0.0 if center_x is None else float(center_x)
    center_y = 0.0 if center_y is None else float(center_y)
    height = float(height)
    if width <= 0 or depth <= 0:
        raise ValueError("width and depth must be positive.")

    plane = rg.Plane(rg.Point3d(center_x, center_y, height), rg.Vector3d.ZAxis)
    corners = [
        plane.PointAt(-width / 2.0, -depth / 2.0),
        plane.PointAt(width / 2.0, -depth / 2.0),
        plane.PointAt(width / 2.0, depth / 2.0),
        plane.PointAt(-width / 2.0, depth / 2.0),
        plane.PointAt(-width / 2.0, -depth / 2.0),
    ]
    boundary = rg.Polyline(corners).ToNurbsCurve()
    surfaces = rg.Brep.CreatePlanarBreps(boundary)
    if not surfaces:
        raise RuntimeError("Could not create the ceiling surface.")
    return [surfaces[0]]


def boolean_difference_touching(solids, tolerance=0.001):
    """Remove intersections between every pair of closed Brep solids.

    Each intersecting pair is replaced by the two remaining difference
    results. Non-intersecting solids are returned unchanged.
    """
    _require_rhino()
    if solids is None:
        raise ValueError("solids must be provided.")
    tolerance = float(tolerance)
    if tolerance <= 0:
        raise ValueError("tolerance must be positive.")
    if isinstance(solids, rg.Brep):
        solids = [solids]
    else:
        try:
            solids = list(solids)
        except TypeError as error:
            raise TypeError(
                "solids must be a closed Brep or an iterable of closed Breps."
            ) from error
    current = solids
    if any(solid is None or not solid.IsSolid for solid in current):
        raise ValueError("Every input must be a non-null, closed Rhino Brep solid.")

    def bbox_overlaps(first, second):
        a = first.GetBoundingBox(True)
        b = second.GetBoundingBox(True)
        return not (
            a.Max.X < b.Min.X - tolerance or b.Max.X < a.Min.X - tolerance
            or a.Max.Y < b.Min.Y - tolerance or b.Max.Y < a.Min.Y - tolerance
            or a.Max.Z < b.Min.Z - tolerance or b.Max.Z < a.Min.Z - tolerance
        )

    def difference(target, cutter):
        result = rg.Brep.CreateBooleanDifference(target, cutter, tolerance)
        if result is None:
            return []
        return [result] if isinstance(result, rg.Brep) else list(result)

    index = 0
    while index < len(current):
        other_index = index + 1
        while other_index < len(current):
            first, second = current[index], current[other_index]
            if not bbox_overlaps(first, second):
                other_index += 1
                continue
            intersection = rg.Brep.CreateBooleanIntersection(first, second, tolerance)
            if not intersection:
                other_index += 1
                continue
            first_result = difference(first, second)
            second_result = difference(second, first)
            if not first_result and not second_result:
                other_index += 1
                continue
            current = (
                current[:index]
                + first_result
                + current[index + 1:other_index]
                + second_result
                + current[other_index + 1:]
            )
            other_index = index + 1
        index += 1
    return current


def clip_geometries_to_grid_box(
    geometries,
    width,
    depth,
    center_x,
    center_y,
    height,
    tolerance=0.001,
    boundary_tolerance=0.0,
):
    """Keep only the solid portions below and inside the grid footprint.

    The grid plane is the top of a vertical box. The bottom of the box is
    placed below the lowest input geometry, so the box is effectively open
    downward for the supplied set of geometries.
    """
    _require_rhino()
    if geometries is None:
        raise ValueError("geometries must be provided.")
    if isinstance(geometries, rg.Brep):
        geometries = [geometries]
    else:
        geometries = list(geometries)
    if not geometries:
        return []

    width = float(width)
    depth = float(depth)
    center_x = float(center_x)
    center_y = float(center_y)
    height = float(height)
    tolerance = float(tolerance)
    boundary_tolerance = float(boundary_tolerance)
    if width <= 0 or depth <= 0:
        raise ValueError("width and depth must be positive.")
    if tolerance <= 0:
        raise ValueError("tolerance must be positive.")
    if boundary_tolerance < 0:
        raise ValueError("boundary_tolerance must be non-negative.")
    if any(geometry is None or not geometry.IsSolid for geometry in geometries):
        raise ValueError("Every input must be a non-null, closed Rhino Brep solid.")

    footprint_min_x = center_x - width / 2.0
    footprint_max_x = center_x + width / 2.0
    footprint_min_y = center_y - depth / 2.0
    footprint_max_y = center_y + depth / 2.0
    boxes = [geometry.GetBoundingBox(True) for geometry in geometries]
    inside_footprint = []
    outside_footprint_count = 0
    for geometry, bbox in zip(geometries, boxes):
        geometry_center = bbox.Center
        if (
            geometry_center.X < footprint_min_x - boundary_tolerance
            or geometry_center.X > footprint_max_x + boundary_tolerance
            or geometry_center.Y < footprint_min_y - boundary_tolerance
            or geometry_center.Y > footprint_max_y + boundary_tolerance
        ):
            outside_footprint_count += 1
            continue
        inside_footprint.append(geometry)

    if not inside_footprint:
        return [], outside_footprint_count, 0

    bottom = min(
        geometry.GetBoundingBox(True).Min.Z for geometry in inside_footprint
    ) - tolerance
    clipped = []
    above_ceiling_count = 0
    for geometry in inside_footprint:
        bbox = geometry.GetBoundingBox(True)
        if bbox.Min.Z >= height - tolerance:
            above_ceiling_count += 1
            continue
        if bbox.Max.Z <= height + tolerance:
            clipped.append(geometry)
            continue

        box_plane = rg.Plane(rg.Point3d(bbox.Center.X, bbox.Center.Y, 0), rg.Vector3d.ZAxis)
        cutter = rg.Box(
            box_plane,
            rg.Interval(bbox.Min.X - bbox.Center.X - tolerance, bbox.Max.X - bbox.Center.X + tolerance),
            rg.Interval(bbox.Min.Y - bbox.Center.Y - tolerance, bbox.Max.Y - bbox.Center.Y + tolerance),
            rg.Interval(bottom, height),
        ).ToBrep()
        pieces = rg.Brep.CreateBooleanIntersection(geometry, cutter, tolerance)
        if pieces is None:
            clipped.append(geometry)
            continue
        if isinstance(pieces, rg.Brep):
            pieces = [pieces]
        pieces = [piece for piece in pieces if piece is not None and piece.IsSolid]
        clipped.extend(pieces if pieces else [geometry])
    return clipped, outside_footprint_count, above_ceiling_count


def _brep_center(brep):
    try:
        properties = rg.VolumeMassProperties.Compute(brep)
        if properties is not None:
            return properties.Centroid
    except Exception:
        pass
    return brep.GetBoundingBox(True).Center


def _face_closest_point(face, point):
    result = face.ClosestPoint(point)
    if isinstance(result, tuple):
        if len(result) == 3:
            success, u, v = result
            if not success:
                return None
        elif len(result) == 2:
            u, v = result
        else:
            return None
    else:
        return None
    return face.PointAt(u, v), face.NormalAt(u, v)


def _top_attachment(brep):
    center = _brep_center(brep)
    bbox = brep.GetBoundingBox(True)
    target = rg.Point3d(center.X, center.Y, bbox.Max.Z + bbox.Diagonal.Length)
    best = None
    best_distance = float("inf")
    for face in brep.Faces:
        closest = _face_closest_point(face, target)
        if closest is None:
            continue
        point, normal = closest
        distance = point.DistanceTo(target)
        if distance < best_distance:
            best, best_distance = (point, normal), distance
    if best is None:
        raise RuntimeError("Could not find a top attachment point on a Brep.")
    point, normal = best
    if rg.Vector3d.Multiply(normal, point - center) < 0:
        normal = -normal
    normal.Unitize()
    return point, normal


def _segment_intersects_box(start, end, bbox, clearance):
    minimum = (bbox.Min.X - clearance, bbox.Min.Y - clearance, bbox.Min.Z - clearance)
    maximum = (bbox.Max.X + clearance, bbox.Max.Y + clearance, bbox.Max.Z + clearance)
    origin = (start.X, start.Y, start.Z)
    direction = (end.X - start.X, end.Y - start.Y, end.Z - start.Z)
    t_min, t_max = 0.0, 1.0
    for axis in range(3):
        if abs(direction[axis]) < 1e-12:
            if origin[axis] < minimum[axis] or origin[axis] > maximum[axis]:
                return False
            continue
        first = (minimum[axis] - origin[axis]) / direction[axis]
        last = (maximum[axis] - origin[axis]) / direction[axis]
        if first > last:
            first, last = last, first
        t_min, t_max = max(t_min, first), min(t_max, last)
        if t_min > t_max:
            return False
    return True


def _segment_is_clear(start, end, obstacles, clearance, tolerance):
    line = rg.LineCurve(start, end)
    for obstacle in obstacles:
        if not _segment_intersects_box(start, end, obstacle.GetBoundingBox(True), clearance):
            continue
        if clearance > 0:
            expanded = obstacle.GetBoundingBox(True)
            expanded.Inflate(clearance)
            if _segment_intersects_box(start, end, expanded, 0.0):
                return False
        intersections = rg.Intersect.Intersection.CurveBrep(
            line,
            obstacle,
            tolerance,
        )
        if intersections and len(intersections) > 0:
            return False
    return True


def _route_wire(start, end, obstacles, clearance, tolerance):
    if _segment_is_clear(start, end, obstacles, clearance, tolerance):
        return rg.LineCurve(start, end), False

    if obstacles:
        safe_z = max(
            obstacle.GetBoundingBox(True).Max.Z
            for obstacle in obstacles
        ) + clearance + tolerance
        high_start = rg.Point3d(start.X, start.Y, safe_z)
        high_end = rg.Point3d(end.X, end.Y, safe_z)
        safe_path = [start, high_start, high_end, end]
        if all(
            _segment_is_clear(first, second, obstacles, clearance, tolerance)
            for first, second in zip(safe_path, safe_path[1:])
        ):
            return rg.Polyline(safe_path).ToNurbsCurve(), True

    direction = end - start
    if not direction.Unitize():
        return None, True
    vertical = rg.Vector3d.ZAxis
    side = rg.Vector3d.CrossProduct(direction, vertical)
    if not side.Unitize():
        side = rg.Vector3d.XAxis
    candidates = []
    for obstacle in obstacles:
        bbox = obstacle.GetBoundingBox(True)
        center = bbox.Center
        along = rg.Vector3d.Multiply(center - start, direction)
        base = start + direction * along
        radius = 0.5 * bbox.Diagonal.Length + clearance
        candidates.extend((base + side * radius, base - side * radius))

    for candidate in candidates:
        if (
            _segment_is_clear(start, candidate, obstacles, clearance, tolerance)
            and _segment_is_clear(candidate, end, obstacles, clearance, tolerance)
        ):
            return rg.Polyline([start, candidate, end]).ToNurbsCurve(), True
    return None, True


def create_hanging_system(
    geometries,
    width=1000.0,
    depth=1000.0,
    center_x=None,
    center_y=None,
    height=3000.0,
    u_count=5,
    v_count=5,
    clearance=100.0,
    tolerance=0.001,
    boundary_tolerance=100.0,
):
    """Clean solids and create collision-free ceiling wires.

    Returns ``(cleaned_geometries, grid_points, grid_curves, wires, diagnostics)``.
    Geometry count must not exceed the number of grid points.
    """
    _require_rhino()
    if geometries is None:
        raise ValueError("geometries must be provided.")
    if isinstance(geometries, rg.Brep):
        geometries = [geometries]
    else:
        geometries = list(geometries)
    if not geometries:
        raise ValueError("geometries must contain at least one closed Brep.")
    clearance = float(clearance)
    if clearance < 0:
        raise ValueError("clearance must be non-negative.")
    raw_boxes = [geometry.GetBoundingBox(True) for geometry in geometries]
    domain_min = rg.Point3d(
        min(box.Min.X for box in raw_boxes),
        min(box.Min.Y for box in raw_boxes),
        min(box.Min.Z for box in raw_boxes),
    )
    domain_max = rg.Point3d(
        max(box.Max.X for box in raw_boxes),
        max(box.Max.Y for box in raw_boxes),
        max(box.Max.Z for box in raw_boxes),
    )
    if center_x is None:
        center_x = (domain_min.X + domain_max.X) / 2.0
    if center_y is None:
        center_y = (domain_min.Y + domain_max.Y) / 2.0

    grid_points, grid_curves = create_attachment_grid(
        width,
        depth,
        center_x,
        center_y,
        height,
        u_count,
        v_count,
    )
    clipped, outside_footprint_count, above_ceiling_count = clip_geometries_to_grid_box(
        geometries,
        width,
        depth,
        center_x,
        center_y,
        height,
        tolerance,
        boundary_tolerance,
    )
    diagnostics = []
    if outside_footprint_count:
        diagnostics.append(
            "{0} geometry(ies) removed because their center is outside the "
            "grid footprint.".format(
                outside_footprint_count
            )
        )
    if above_ceiling_count:
        diagnostics.append(
            "{0} geometry(ies) removed because they are entirely above the "
            "ceiling height.".format(above_ceiling_count)
        )
    cleaned = boolean_difference_touching(clipped, tolerance)
    if not cleaned:
        diagnostics.append("No geometry remains inside the grid box.")
        return [], grid_points, grid_curves, [], diagnostics
    if len(cleaned) > len(grid_points):
        raise ValueError("There are more geometries than available grid attachment points.")

    while cleaned:
        centers = [_brep_center(geometry) for geometry in cleaned]
        distance_pairs = sorted(
            (
                (center.DistanceTo(point), geometry_index, point_index)
                for geometry_index, center in enumerate(centers)
                for point_index, point in enumerate(grid_points)
            ),
            key=lambda item: item[0],
        )
        assigned_geometries = set()
        assigned_points = set()
        ordered_points = [None] * len(cleaned)
        for distance, geometry_index, point_index in distance_pairs:
            if geometry_index in assigned_geometries or point_index in assigned_points:
                continue
            ordered_points[geometry_index] = grid_points[point_index]
            assigned_geometries.add(geometry_index)
            assigned_points.add(point_index)
            if len(assigned_geometries) == len(cleaned):
                break

        wires = []
        rejected = []
        for index, (geometry, start) in enumerate(zip(cleaned, ordered_points)):
            if start is None:
                rejected.append(index)
                continue
            contact, normal = _top_attachment(geometry)
            contact += normal * tolerance
            obstacles = [other for other in cleaned if other is not geometry]
            wire, detoured = _route_wire(start, contact, obstacles, clearance, tolerance)
            if wire is None:
                rejected.append(index)
                diagnostics.append(
                    "Geometry {0}: removed because no collision-free wire route exists.".format(
                        index
                    )
                )
                continue
            wires.append(wire)
            diagnostics.append(
                "Geometry {0}: attachment point ({1:.3f}, {2:.3f}, {3:.3f}).".format(
                    index,
                    start.X,
                    start.Y,
                    start.Z,
                )
            )
            if detoured:
                diagnostics.append("Geometry {0}: direct route blocked; detour created.".format(index))
            else:
                diagnostics.append("Geometry {0}: direct route is clear.".format(index))
        if not rejected:
            break
        cleaned = [
            geometry for index, geometry in enumerate(cleaned)
            if index not in rejected
        ]
    return cleaned, grid_points, grid_curves, wires, diagnostics
>>>>>>> Stashed changes
