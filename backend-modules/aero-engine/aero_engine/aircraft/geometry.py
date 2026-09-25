import math


def generate_surface_geometry(
    span: float,
    root_chord: float,
    tip_chord: float,
    sweep_deg: float,
    dihedral_deg: float,
    x_position: float,
    z_position: float = 0.0,
) -> dict:
    """
    Generate 2D three-view points and 3D wireframe vertices/edges for one
    lifting surface, mirrored across the centerline for both half-spans.
    Coordinate frame: x aft from the nose, y = starboard(+)/port(-), z up.
    """
    half_span = span / 2.0
    sweep_rad = math.radians(sweep_deg)
    dihedral_rad = math.radians(dihedral_deg)

    le_sweep_offset = half_span * math.tan(sweep_rad)
    # half_span is the panel's true (unrotated) length; project it into
    # spanwise (y) and vertical (z) components via cos/sin of the dihedral
    # angle. This is correct for ANY dihedral angle, including 90 degrees
    # (a pure V-tail panel) -- unlike `half_span * tan(dihedral)`, which
    # only approximates the vertical offset correctly for small angles and
    # diverges to infinity as dihedral approaches 90 degrees.
    tip_y_offset = half_span * math.cos(dihedral_rad)
    tip_z_offset = half_span * math.sin(dihedral_rad)

    root_le = (x_position, 0.0, z_position)
    root_te = (x_position + root_chord, 0.0, z_position)

    def tip_corners(sign: int):
        y = sign * tip_y_offset
        tip_le_x = x_position + le_sweep_offset
        tip_te_x = tip_le_x + tip_chord
        tip_z = z_position + tip_z_offset
        return (tip_le_x, y, tip_z), (tip_te_x, y, tip_z)

    tip_le_pos, tip_te_pos = tip_corners(1)
    tip_le_neg, tip_te_neg = tip_corners(-1)

    def polygon(tip_le, tip_te):
        return [root_le, tip_le, tip_te, root_te, root_le]

    poly_pos = polygon(tip_le_pos, tip_te_pos)
    poly_neg = polygon(tip_le_neg, tip_te_neg)

    top_view = [[p[0], p[1]] for p in poly_pos] + [[p[0], p[1]] for p in poly_neg]
    front_view = [[p[1], p[2]] for p in poly_pos] + [[p[1], p[2]] for p in poly_neg]
    side_view = [[p[0], p[2]] for p in poly_pos] + [[p[0], p[2]] for p in poly_neg]

    vertices = [
        list(root_le), list(tip_le_pos), list(tip_te_pos), list(root_te),
        list(tip_le_neg), list(tip_te_neg),
    ]
    edges = [
        [0, 1], [1, 2], [2, 3], [3, 0],  # right half loop
        [0, 4], [4, 5], [5, 3],          # left half loop (shares root_le/root_te)
    ]

    return {
        "top_view": top_view,
        "front_view": front_view,
        "side_view": side_view,
        "vertices": vertices,
        "edges": edges,
    }


def generate_vertical_surface_geometry(
    height: float,
    root_chord: float,
    tip_chord: float,
    sweep_deg: float,
    x_position: float,
    z_position: float = 0.0,
) -> dict:
    """
    Generate geometry for a single (unmirrored) vertical fin standing up
    from z_position to z_position + height.
    """
    sweep_rad = math.radians(sweep_deg)
    le_sweep_offset = height * math.tan(sweep_rad)

    root_le = (x_position, 0.0, z_position)
    root_te = (x_position + root_chord, 0.0, z_position)
    tip_le = (x_position + le_sweep_offset, 0.0, z_position + height)
    tip_te = (tip_le[0] + tip_chord, 0.0, z_position + height)

    polygon = [root_le, tip_le, tip_te, root_te, root_le]

    top_view = [[p[0], p[1]] for p in polygon]
    front_view = [[p[1], p[2]] for p in polygon]
    side_view = [[p[0], p[2]] for p in polygon]

    vertices = [list(root_le), list(tip_le), list(tip_te), list(root_te)]
    edges = [[0, 1], [1, 2], [2, 3], [3, 0]]

    return {
        "top_view": top_view,
        "front_view": front_view,
        "side_view": side_view,
        "vertices": vertices,
        "edges": edges,
    }


def generate_fuselage_geometry(
    length: float,
    max_width: float,
    max_height: float,
    nose_length: float,
    tail_length: float,
) -> dict:
    """
    Simple fuselage outline for blueprint visualization only: a linear
    nose taper, a constant mid-section, and a linear tail taper. This is
    never consumed by any stability calculation.
    """
    mid_start = nose_length
    mid_end = length - tail_length

    half_h = max_height / 2.0
    side_view = [
        [0.0, 0.0],
        [mid_start, half_h],
        [mid_end, half_h],
        [length, 0.0],
        [mid_end, -half_h],
        [mid_start, -half_h],
        [0.0, 0.0],
    ]

    half_w = max_width / 2.0
    top_view = [
        [0.0, 0.0],
        [mid_start, half_w],
        [mid_end, half_w],
        [length, 0.0],
        [mid_end, -half_w],
        [mid_start, -half_w],
        [0.0, 0.0],
    ]

    # Widest cross-section, approximated as an ellipse (16 segments).
    n = 16
    front_view = [
        [half_w * math.cos(2 * math.pi * i / n), half_h * math.sin(2 * math.pi * i / n)]
        for i in range(n + 1)
    ]

    vertices = [
        [0.0, 0.0, 0.0],                    # 0 nose tip
        [mid_start, half_w, 0.0],           # 1 mid start, right
        [mid_start, -half_w, 0.0],          # 2 mid start, left
        [mid_start, 0.0, half_h],           # 3 mid start, top
        [mid_start, 0.0, -half_h],          # 4 mid start, bottom
        [mid_end, half_w, 0.0],             # 5 mid end, right
        [mid_end, -half_w, 0.0],            # 6 mid end, left
        [mid_end, 0.0, half_h],             # 7 mid end, top
        [mid_end, 0.0, -half_h],            # 8 mid end, bottom
        [length, 0.0, 0.0],                 # 9 tail tip
    ]
    edges = [
        [0, 1], [0, 2], [0, 3], [0, 4],
        [1, 5], [2, 6], [3, 7], [4, 8],
        [5, 9], [6, 9], [7, 9], [8, 9],
    ]

    return {
        "top_view": top_view,
        "front_view": front_view,
        "side_view": side_view,
        "vertices": vertices,
        "edges": edges,
    }


from .models import AircraftConfig, Surface
from ..wing_planform import calculate_surface_planform


def _surface_geometry_with_planform(surface: Surface) -> dict:
    geom = generate_surface_geometry(
        span=surface.span,
        root_chord=surface.root_chord,
        tip_chord=surface.tip_chord,
        sweep_deg=surface.sweep_deg,
        dihedral_deg=surface.dihedral_deg,
        x_position=surface.x_position,
        z_position=surface.z_position,
    )
    geom["planform"] = calculate_surface_planform(
        surface.span, surface.root_chord, surface.tip_chord, surface.sweep_deg
    )
    return geom


def generate_aircraft_geometry(config: AircraftConfig) -> dict:
    """
    Assemble the full geometry payload for an AircraftConfig: every
    present surface's 2D/3D points plus its planform metrics, dispatched
    by configuration_type.
    """
    geometry: dict = {
        "wing": _surface_geometry_with_planform(config.wing),
        "horizontal_tail": None,
        "vertical_tail": None,
        "canard": None,
        "v_tail": None,
        "fuselage": {
            **generate_fuselage_geometry(
                length=config.fuselage.length,
                max_width=config.fuselage.max_width,
                max_height=config.fuselage.max_height,
                nose_length=config.fuselage.nose_length,
                tail_length=config.fuselage.tail_length,
            ),
            "planform": None,
        },
    }

    if config.horizontal_tail is not None:
        geometry["horizontal_tail"] = _surface_geometry_with_planform(config.horizontal_tail)

    if config.vertical_tail is not None:
        vt = config.vertical_tail
        geom = generate_vertical_surface_geometry(
            height=vt.height, root_chord=vt.root_chord, tip_chord=vt.tip_chord,
            sweep_deg=vt.sweep_deg, x_position=vt.x_position, z_position=vt.z_position,
        )
        # The single-fin planform is computed by treating `height` as
        # `span` in the shared helper (a one-sided trapezoid, no
        # mirroring). This gives a self-consistent area/AR for this
        # module's own CL_alpha estimate; it does not match published
        # "effective AR with image effect" conventions for vertical tails.
        geom["planform"] = calculate_surface_planform(vt.height, vt.root_chord, vt.tip_chord, vt.sweep_deg)
        geometry["vertical_tail"] = geom

    if config.canard is not None:
        geometry["canard"] = _surface_geometry_with_planform(config.canard)

    if config.v_tail is not None:
        vtail = config.v_tail
        geom = generate_surface_geometry(
            span=vtail.span, root_chord=vtail.root_chord, tip_chord=vtail.tip_chord,
            sweep_deg=vtail.sweep_deg, dihedral_deg=vtail.dihedral_v_deg,
            x_position=vtail.x_position, z_position=vtail.z_position,
        )
        geom["planform"] = calculate_surface_planform(vtail.span, vtail.root_chord, vtail.tip_chord, vtail.sweep_deg)
        geometry["v_tail"] = geom

    return geometry
