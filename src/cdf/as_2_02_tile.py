"""Dendritic floor pattern for Rhino 8 Grasshopper Python 3 components."""

import math
import random
from collections import deque

import Rhino.Geometry as rg


# ---------------------------------------------------------------------------
# Grasshopper input declarations (type hints and defaults).
# ---------------------------------------------------------------------------
def grow_dla(
    nx: int,
    ny: int,
    seed: int,
    n_particles: int,
    stickiness: float,
    bias: float,
    bias_dir,
    seed_mode: int,
):
    """Fait croitre une structure DLA deterministe sur une grille 4-voisins."""
    nx = max(0, int(nx))
    ny = max(0, int(ny))
    n_particles = max(0, int(n_particles))
    stickiness = min(1.0, max(0.0, float(stickiness)))
    bias = min(1.0, max(0.0, float(bias)))
    seed_mode = 1 if int(seed_mode) == 1 else 0

    rng = random.Random(int(seed))
    occupied = set()
    parents = {}
    ranks = {}

    def in_bounds(i, j):
        return 0 <= i < nx and 0 <= j < ny

    if nx <= 0 or ny <= 0:
        return occupied, parents, ranks

    if seed_mode == 1:
        center_i = (nx - 1) // 2
        center_j = (ny - 1) // 2
        occupied.add((center_i, center_j))
        ranks[(center_i, center_j)] = 0
    else:
        for i in range(nx):
            occupied.add((i, 0))
            occupied.add((i, ny - 1))
            ranks[(i, 0)] = 0
            ranks[(i, ny - 1)] = 0
        for j in range(ny):
            occupied.add((0, j))
            occupied.add((nx - 1, j))
            ranks[(0, j)] = 0
            ranks[(nx - 1, j)] = 0

    neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1))

    def random_free_border():
        free = []
        for i in range(nx):
            if (i, 0) not in occupied:
                free.append((i, 0))
            if (i, ny - 1) not in occupied:
                free.append((i, ny - 1))
        for j in range(1, ny - 1):
            if (0, j) not in occupied:
                free.append((0, j))
            if (nx - 1, j) not in occupied:
                free.append((nx - 1, j))
        if free:
            return rng.choice(free)
        for j in range(ny):
            for i in range(nx):
                if (i, j) not in occupied:
                    return (i, j)
        return None

    def random_free_interior():
        candidates = []
        for j in range(ny):
            for i in range(nx):
                if seed_mode == 0 and (i == 0 or i == nx - 1 or j == 0 or j == ny - 1):
                    continue
                if (i, j) not in occupied:
                    candidates.append((i, j))
        return rng.choice(candidates) if candidates else None

    bx = 1.0
    by = 0.0
    if bias_dir is not None:
        vx = float(getattr(bias_dir, "X", 0.0))
        vy = float(getattr(bias_dir, "Y", 0.0))
        length = math.sqrt(vx * vx + vy * vy)
        if length > 1e-12:
            bx = vx / length
            by = vy / length

    arrival_rank = 1
    for _ in range(n_particles):
        if seed_mode == 1:
            position = random_free_border()
        else:
            position = random_free_interior()
        if position is None:
            break

        i, j = position
        stuck = False
        for _step in range(20000):
            adjacent = []
            for di, dj in neighbors:
                ni = i + di
                nj = j + dj
                if in_bounds(ni, nj) and (ni, nj) in occupied:
                    adjacent.append((ni, nj))

            if adjacent and rng.random() < stickiness:
                parent = rng.choice(adjacent)
                occupied.add((i, j))
                ranks[(i, j)] = arrival_rank
                parents[(i, j)] = parent
                arrival_rank += 1
                stuck = True
                break

            if rng.random() < bias:
                if abs(bx) >= abs(by):
                    directional = ((1, 0) if bx >= 0 else (-1, 0))
                else:
                    directional = ((0, 1) if by >= 0 else (0, -1))
                di, dj = directional
                ni = i + di
                nj = j + dj
                if in_bounds(ni, nj):
                    i, j = ni, nj
                    continue

            di, dj = rng.choice(neighbors)
            ni = i + di
            nj = j + dj
            if in_bounds(ni, nj):
                i, j = ni, nj

        if stuck:
            continue

    return occupied, parents, ranks


def compute_distance(nx: int, ny: int, occupied):
    """Calcule les distances Manhattan 4-voisins et le voisin occupe le plus proche."""
    dist = [[-1 for _ in range(ny)] for _ in range(nx)]
    nearest = [[None for _ in range(ny)] for _ in range(nx)]
    queue = deque()

    for i, j in occupied:
        if 0 <= i < nx and 0 <= j < ny:
            dist[i][j] = 0
            nearest[i][j] = (i, j)
            queue.append((i, j))

    neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1))
    while queue:
        i, j = queue.popleft()
        for di, dj in neighbors:
            ni = i + di
            nj = j + dj
            if 0 <= ni < nx and 0 <= nj < ny:
                if dist[ni][nj] < 0:
                    dist[ni][nj] = dist[i][j] + 1
                    nearest[ni][nj] = nearest[i][j]
                    queue.append((ni, nj))

    return dist, nearest


def classify_cells(
    nx: int,
    ny: int,
    occupied,
    parents,
    ranks,
    halo1: int,
    halo2: int,
    polarity_threshold: float,
):
    """Traduit les cases occupees et les halos en types, polarites et ages."""
    dist, nearest = compute_distance(nx, ny, occupied)

    if ranks:
        max_rank = max(ranks.values())
    else:
        max_rank = 1
    if max_rank <= 0:
        max_rank = 1

    polarity_threshold = min(1.0, max(0.0, float(polarity_threshold)))
    halo1 = max(0, int(halo1))
    halo2 = max(halo1, int(halo2))
    classification = {}
    neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1))

    for j in range(ny):
        for i in range(nx):
            if (i, j) in occupied:
                neighbor_count = sum(
                    1
                    for di, dj in neighbors
                    if (i + di, j + dj) in occupied
                )
                age = 0.0 if ranks.get((i, j), 0) == 0 else ranks[(i, j)] / float(max_rank)
                polarity = 1 if age < polarity_threshold else 0
                if neighbor_count >= 3:
                    classification[(i, j)] = ("FULL", polarity, age)
                else:
                    classification[(i, j)] = ("HALF", polarity, age)
            else:
                distance = dist[i][j]
                if 0 <= distance <= halo1:
                    origin = nearest[i][j]
                    if origin is not None:
                        origin_age = (
                            0.0
                            if ranks.get(origin, 0) == 0
                            else ranks.get(origin, 0) / float(max_rank)
                        )
                        polarity = 1 if origin_age < polarity_threshold else 0
                        classification[(i, j)] = ("CROSS", polarity, 0.0)
                elif 0 <= distance <= halo2:
                    origin = nearest[i][j]
                    if origin is not None:
                        origin_age = (
                            0.0
                            if ranks.get(origin, 0) == 0
                            else ranks.get(origin, 0) / float(max_rank)
                        )
                        polarity = 1 if origin_age < polarity_threshold else 0
                        classification[(i, j)] = ("DOT", polarity, 0.0)

    return classification


def merge_full_blocks(classification, nx: int, ny: int):
    """Fusionne les FULL en blocs rectangulaires par rangées, puis par colonnes."""
    row_blocks = []

    for j in range(ny):
        i = 0
        while i < nx:
            if (i, j) in classification and classification[(i, j)][0] == "FULL":
                i0 = i
                while i + 1 < nx:
                    key = (i + 1, j)
                    if key not in classification or classification[key][0] != "FULL":
                        break
                    i += 1
                row_blocks.append((i0, j, i, j))
            i += 1

    merged = list(row_blocks)
    for j in range(ny):
        i = 0
        while i < nx:
            matches = [
                block
                for block in merged
                if block[1] == j and block[3] == j and block[0] == i
            ]
            if matches:
                block = matches[0]
                x0, y0, x1, y1 = block
                while y1 + 1 < ny:
                    below_matches = [
                        candidate
                        for candidate in merged
                        if candidate[0] == x0
                        and candidate[2] == x1
                        and candidate[1] == y1 + 1
                        and candidate[3] == y1 + 1
                    ]
                    if not below_matches:
                        break
                    below = below_matches[0]
                    merged.remove(below)
                    y1 += 1
                merged.remove(block)
                merged.append((x0, y0, x1, y1))
                i = x1 + 1
            else:
                i += 1

    covered = set()
    for x0, y0, x1, y1 in merged:
        for j in range(y0, y1 + 1):
            for i in range(x0, x1 + 1):
                covered.add((i, j))

    return merged, covered


def _closed_polyline(points):
    """Cre une PolylineCurve fermee sans point parasite et sans doublon."""
    if not points:
        return None
    unique = []
    for point in points:
        if not unique or point.DistanceTo(unique[-1]) > 1e-10:
            unique.append(point)
    if len(unique) < 3:
        return None
    if unique[0].DistanceTo(unique[-1]) > 1e-10:
        unique.append(rg.Point3d(unique[0]))
    if len(unique) < 4:
        return None
    curve = rg.PolylineCurve(rg.Polyline(unique))
    if curve is None or not curve.IsValid:
        return None
    return curve if curve.IsClosed else None


def build_curves(
    nx: int,
    ny: int,
    cell: float,
    plane,
    classification,
    parents,
    merge: bool,
):
    """Construit les courbes fermees, en conservant les listes alignees."""
    cell = max(0.0, float(cell))
    if plane is None:
        plane = rg.Plane.WorldXY

    full_blocks = []
    full_covered = set()
    if merge:
        full_blocks, full_covered = merge_full_blocks(classification, nx, ny)

    curves = []
    types = []
    polarity = []
    ages = []
    seen = set()

    def local_point(u, v):
        return plane.PointAt(u, v)

    def square_curve(i, j, local_scale=1.0):
        cx = (i + 0.5) * cell
        cy = (j + 0.5) * cell
        h = 0.5 * cell * local_scale
        points = [
            local_point(cx - h, cy - h),
            local_point(cx + h, cy - h),
            local_point(cx + h, cy + h),
            local_point(cx - h, cy + h),
        ]
        return _closed_polyline(points)

    def half_curve(i, j):
        cx = (i + 0.5) * cell
        cy = (j + 0.5) * cell
        h = 0.5 * cell
        nw = (cx - h, cy - h)
        ne = (cx + h, cy - h)
        sw = (cx - h, cy + h)
        se = (cx + h, cy + h)
        # Les noms sont cales sur les axes locaux; parent indique le cote partage.
        parent = parents.get((i, j))
        if parent is not None:
            pi, pj = parent
            dx = pi - i
            dy = pj - j
        else:
            dx = -1 if (i + j) % 2 == 0 else 1
            dy = 0

        if (i + j) % 2 == 0:
            if dx < 0 or dy > 0:
                triangle = (nw, sw, se)
            else:
                triangle = (nw, ne, se)
        else:
            if dx < 0 or dy < 0:
                triangle = (sw, nw, ne)
            else:
                triangle = (sw, se, ne)

        points = [local_point(u, v) for u, v in triangle]
        return _closed_polyline(points)

    def cross_curve(i, j):
        cx = (i + 0.5) * cell
        cy = (j + 0.5) * cell
        h = 0.5 * cell
        t = 0.25 * 0.5 * cell
        offsets = [
            (-t, -h), (t, -h), (t, -t), (h, -t),
            (h, t), (t, t), (t, h), (-t, h),
            (-t, t), (-h, t), (-h, -t), (-t, -t),
        ]
        points = [local_point(cx + u, cy + v) for u, v in offsets]
        return _closed_polyline(points)

    def add_curve(curve, tile_type, tile_polarity, tile_age, signature):
        if curve is None or signature in seen:
            return
        seen.add(signature)
        curves.append(curve)
        types.append(tile_type)
        polarity.append(tile_polarity)
        ages.append(float(tile_age))

    if merge:
        for x0, y0, x1, y1 in full_blocks:
            cx0 = x0 * cell
            cy0 = y0 * cell
            cx1 = (x1 + 1) * cell
            cy1 = (y1 + 1) * cell
            points = [
                local_point(cx0, cy0),
                local_point(cx1, cy0),
                local_point(cx1, cy1),
                local_point(cx0, cy1),
            ]
            curve = _closed_polyline(points)
            block_ages = []
            block_polarities = []
            for j in range(y0, y1 + 1):
                for i in range(x0, x1 + 1):
                    item = classification.get((i, j))
                    if item is not None:
                        block_polarities.append(item[1])
                        block_ages.append(item[2])
            tile_age = sum(block_ages) / float(len(block_ages)) if block_ages else 0.0
            tile_polarity = 1 if block_polarities and sum(block_polarities) > len(block_polarities) / 2.0 else 0
            signature = ("FULL", x0, y0, x1, y1)
            add_curve(curve, "FULL", tile_polarity, tile_age, signature)

    for j in range(ny):
        for i in range(nx):
            if (i, j) in full_covered:
                continue
            item = classification.get((i, j))
            if item is None:
                continue
            tile_type, tile_polarity, tile_age = item
            if tile_type == "FULL":
                if merge:
                    continue
                curve = square_curve(i, j)
                signature = ("FULL", i, j)
            elif tile_type == "HALF":
                curve = half_curve(i, j)
                signature = ("HALF", i, j)
            elif tile_type == "CROSS":
                curve = cross_curve(i, j)
                signature = ("CROSS", i, j)
            else:
                curve = square_curve(i, j, 0.30)
                signature = ("DOT", i, j)
            add_curve(curve, tile_type, tile_polarity, tile_age, signature)

    return curves, types, polarity, ages


def build_floor(
    nx: int = 80,
    ny: int = 80,
    cell: float = 0.2,
    seed: int = 0,
    n_particles: int = 2500,
    stickiness: float = 0.6,
    bias: float = 0.0,
    bias_dir=None,
    seed_mode: int = 1,
    halo1: int = 1,
    halo2: int = 2,
    polarity_threshold: float = 0.5,
    merge: bool = True,
    plane=None,
):
    """Fonction principale : construit toutes les sorties alignees du sol."""
    nx = max(0, int(nx))
    ny = max(0, int(ny))
    cell = max(0.0, float(cell))
    n_particles = max(0, int(n_particles))

    if plane is None:
        plane = rg.Plane.WorldXY
    if bias_dir is None:
        bias_dir = rg.Vector3d.XAxis

    occupied, parents, ranks = grow_dla(
        nx,
        ny,
        seed,
        n_particles,
        stickiness,
        bias,
        bias_dir,
        seed_mode,
    )

    classification = classify_cells(
        nx,
        ny,
        occupied,
        parents,
        ranks,
        halo1,
        halo2,
        polarity_threshold,
    )

    curves, types, polarity, ages = build_curves(
        nx,
        ny,
        cell,
        plane,
        classification,
        parents,
        merge,
    )

    counts = {
        "FULL": types.count("FULL"),
        "HALF": types.count("HALF"),
        "CROSS": types.count("CROSS"),
        "DOT": types.count("DOT"),
    }
    stats = (
        "nx={0}; ny={1}; seed={2}; particles={3}; stickiness={4:.2f}; "
        "bias={5:.2f}; seed_mode={6}; halo1={7}; halo2={8}; "
        "merge={9}; FULL={10}; HALF={11}; CROSS={12}; DOT={13}; occupied={14}"
    ).format(
        nx,
        ny,
        int(seed),
        n_particles,
        float(stickiness),
        float(bias),
        int(seed_mode),
        int(halo1),
        int(halo2),
        bool(merge),
        counts["FULL"],
        counts["HALF"],
        counts["CROSS"],
        counts["DOT"],
        len(occupied),
    )

    print("Nombre total de courbes : {}".format(len(curves)))
    if not (len(curves) == len(types) == len(polarity) == len(ages)):
        raise RuntimeError("Les sorties curves/types/polarity/ages ne sont pas alignees.")

    return curves, types, polarity, ages, stats

