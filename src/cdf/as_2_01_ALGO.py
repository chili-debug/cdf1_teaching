"""Deterministic recursive growth geometry for Grasshopper."""

import math

import Rhino.Geometry as rg
from System import Array


def create_recursive_hyperbolic_growth(
    base_point=None,
    trunk_radius=5.0,
    trunk_height=10.0,
    trunk_loops=6,
    base_points=12,
    growth_levels=4,
    x=3,
    level_height=4.0,
    radial_growth=1.5,
    growth_exponent=2.0,
    amplitude=0.35,
    undulation_frequency=2.0,
    spiral_turns=0.35,
    phase=0.0,
    curve_samples=12,
    max_branches=2000,
):
    """Create a deterministic, recursively growing hyperbolic-like tree.

    The trunk consists of ``trunk_loops`` circular rings with a constant
    number of points. Above the trunk, every point creates ``x`` children at
    each level, so the point count follows ``base_points * x ** level``.
    Child radius and height are varied by sine waves, which creates an
    organic shape without using random values.

    Args:
        base_point: Bottom center as ``Rhino.Geometry.Point3d``. Defaults to
            the world origin.
        trunk_radius: Radius of the constant-radius trunk.
        trunk_height: Height of the trunk before recursive growth begins.
        trunk_loops: Number of circular rings in the trunk.
        base_points: Points in each trunk ring and the first growth level.
        growth_levels: Number of recursive levels above the trunk.
        x: Number of children created by every point at each level.
        level_height: Average vertical distance between growth levels.
        radial_growth: Radius increase per growth level.
        growth_exponent: Exponent controlling the hyperbolic radial opening.
        amplitude: Amplitude of deterministic radial and vertical undulation.
        undulation_frequency: Number of sine-wave cycles around a ring.
        spiral_turns: Number of additional turns made by each branch.
        phase: Angular phase offset in radians.
        curve_samples: Number of points used to draw each undulating branch.
        max_branches: Safety limit for generated growth branches.

    Returns:
        tuple: ``(rings, growth_lines, growth_points)``. ``rings`` contains
        trunk and growth ``PolylineCurve`` rings, ``growth_lines`` contains
        undulating ``PolylineCurve`` branches, and ``growth_points`` contains
        points by level.

    Example for a Grasshopper Python 3 component::

        import cdf.as_2_01_ALGO as algo

        rings, lines, points = algo.create_recursive_hyperbolic_growth(
            trunk_loops=Loops,
            x=X,
            growth_levels=Levels,
            amplitude=A,
        )
    """
    if base_point is None:
        base_point = rg.Point3d.Origin

    integer_values = {
        "trunk_loops": trunk_loops,
        "base_points": base_points,
        "growth_levels": growth_levels,
        "x": x,
        "curve_samples": curve_samples,
        "max_branches": max_branches,
    }
    for name, value in integer_values.items():
        if int(value) != value:
            raise ValueError("{} must be an integer.".format(name))

    if trunk_radius <= 0 or trunk_height <= 0 or level_height <= 0:
        raise ValueError("trunk_radius, trunk_height, and level_height must be positive.")
    if trunk_loops < 2 or base_points < 3:
        raise ValueError("trunk_loops must be at least 2 and base_points at least 3.")
    if growth_levels < 1 or x < 1 or curve_samples < 3:
        raise ValueError(
            "growth_levels and x must be at least 1, and curve_samples at least 3."
        )
    if max_branches < 1:
        raise ValueError("max_branches must be at least 1.")
    if (
        radial_growth < 0
        or growth_exponent < 1
        or amplitude < 0
        or undulation_frequency < 0
        or spiral_turns < 0
    ):
        raise ValueError(
            "radial_growth, amplitude, undulation_frequency, and spiral_turns "
            "cannot be negative; growth_exponent must be at least 1."
        )
    if amplitude >= trunk_radius:
        raise ValueError("amplitude must be smaller than trunk_radius.")

    trunk_loops = int(trunk_loops)
    base_points = int(base_points)
    growth_levels = int(growth_levels)
    x = int(x)
    curve_samples = int(curve_samples)
    max_branches = int(max_branches)
    branch_count = sum(base_points * x ** level for level in range(1, growth_levels + 1))
    if branch_count > max_branches:
        raise ValueError(
            "This setup creates {} branches, above the safety limit of {}. "
            "Reduce growth_levels, x, or base_points.".format(
                branch_count, max_branches
            )
        )
    center = rg.Point3d(base_point)

    def point_on_ring(radius, angle, z):
        return rg.Point3d(
            center.X + radius * math.cos(angle),
            center.Y + radius * math.sin(angle),
            center.Z + z,
        )

    def closed_ring(points):
        ring_points = list(points)
        ring_points.append(ring_points[0])
        if len(ring_points) < 4:
            raise RuntimeError("A ring needs at least three unique points.")
        ring = rg.PolylineCurve(rg.Polyline(ring_points))
        if ring is None or not ring.IsValid:
            raise RuntimeError("Rhino could not create a valid closed ring curve.")
        return ring

    rings = []
    trunk_step = trunk_height / float(trunk_loops - 1)
    for loop_index in range(trunk_loops):
        z = loop_index * trunk_step
        points = [
            point_on_ring(
                trunk_radius,
                phase + 2.0 * math.pi * index / base_points,
                z,
            )
            for index in range(base_points)
        ]
        rings.append(closed_ring(points))

    current_level = [
        point_on_ring(
            trunk_radius,
            phase + 2.0 * math.pi * index / base_points,
            trunk_height,
        )
        for index in range(base_points)
    ]
    growth_points = [current_level]
    growth_lines = []

    def undulating_branch(start, end, wave_phase, level):
        start_radius = math.hypot(
            start.X - center.X,
            start.Y - center.Y,
        )
        end_radius = math.hypot(
            end.X - center.X,
            end.Y - center.Y,
        )
        start_angle = math.atan2(
            start.Y - center.Y,
            start.X - center.X,
        )
        end_angle = math.atan2(
            end.Y - center.Y,
            end.X - center.X,
        )
        angle_delta = math.atan2(
            math.sin(end_angle - start_angle),
            math.cos(end_angle - start_angle),
        )
        branch_points = []

        for sample in range(curve_samples):
            progress = sample / float(curve_samples - 1)
            wave = math.sin(
                2.0 * math.pi * undulation_frequency * progress + wave_phase
            )
            envelope = math.sin(math.pi * progress)
            radial_wave = amplitude * (1.0 + 0.5 * level) * envelope * wave
            spiral = (
                2.0
                * math.pi
                * spiral_turns
                * envelope
                * math.sin(wave_phase)
            )
            angle = start_angle + angle_delta * progress + spiral
            radius = (
                start_radius
                + (end_radius - start_radius) * progress
                + radial_wave
            )
            branch_points.append(
                rg.Point3d(
                    center.X + radius * math.cos(angle),
                    center.Y + radius * math.sin(angle),
                    start.Z
                    + (end.Z - start.Z) * progress
                    + 0.5 * radial_wave * envelope,
                )
            )

        point_array = Array[rg.Point3d](branch_points)
        spline = rg.Curve.CreateInterpolatedCurve(
            point_array,
            3,
        )
        if spline is None or not spline.IsValid:
            raise RuntimeError("Rhino could not create a valid spline branch.")
        return spline

    for level in range(1, growth_levels + 1):
        next_level = []
        level_progress = level / float(growth_levels)
        radius = trunk_radius * (
            1.0 + radial_growth * level_progress ** growth_exponent
        )
        z = trunk_height + level_height * level
        child_count = len(current_level) * x
        level_twist = 2.0 * math.pi * spiral_turns * level_progress

        for child_number in range(child_count):
            parent_index = child_number // x
            child_index = child_number % x
            parent = current_level[parent_index]
            angle = (
                phase
                + level_twist
                + 2.0 * math.pi * child_number / child_count
            )
            wave_phase = (
                angle * undulation_frequency
                + level_progress * 2.0 * math.pi
                + phase
            )
            radial_offset = amplitude * math.sin(wave_phase)
            vertical_offset = amplitude * math.sin(wave_phase + math.pi / 2.0)
            child = point_on_ring(
                max(0.001, radius + radial_offset),
                angle,
                z + vertical_offset,
            )
            next_level.append(child)
            growth_lines.append(
                undulating_branch(
                    parent,
                    child,
                    wave_phase + child_index * math.pi / max(x, 1),
                    level,
                )
            )

        current_level = next_level
        rings.append(closed_ring(current_level))
        growth_points.append(current_level)

    return rings, growth_lines, growth_points