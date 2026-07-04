"""
Real trimesh-based geometry analysis primitives shared by all DFM analyzers.

These replace the previous per-analyzer heuristics that used a single
whole-mesh volume/area average as "thickness" or fabricated issues purely
from face count. Every function here measures an actual property of the
mesh (ray-cast distances, real dihedral angles, real topology) at specific
locations, so results reflect the part that was actually uploaded.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import networkx as nx
import trimesh


def _ray_intersector(mesh: "trimesh.Trimesh"):
    """Use the accelerated pyembree intersector if available, else trimesh's
    default (rtree-backed) intersector."""
    if getattr(trimesh.ray, "has_embree", False):
        return trimesh.ray.ray_pyembree.RayMeshIntersector(mesh)
    return mesh.ray


def _adaptive_sample_count(mesh: "trimesh.Trimesh", requested: int) -> int:
    """Cap sample density for very large meshes to keep ray-casting fast."""
    n_faces = max(len(mesh.faces), 1)
    return int(max(100, min(requested, 300_000 / n_faces * requested)))


def cluster_by_location(items: List[Dict], grid_size: float) -> List[Dict]:
    """Collapse near-duplicate hits on the same physical feature into one
    reported issue instead of one per sample point/edge."""
    if grid_size <= 0:
        grid_size = 1.0
    clusters: Dict[Tuple[int, int, int], Dict] = {}
    for item in items:
        loc = item["location"]
        key = (
            round(loc["x"] / grid_size),
            round(loc["y"] / grid_size),
            round(loc["z"] / grid_size),
        )
        clusters.setdefault(key, item)
    return list(clusters.values())


def compute_wall_thickness_samples(mesh: "trimesh.Trimesh", sample_count: int = 1500) -> List[Dict]:
    """Sample points on the surface and cast a ray inward along each point's
    normal; the first hit distance is that point's local wall thickness."""
    if len(mesh.faces) == 0:
        return []

    n_samples = _adaptive_sample_count(mesh, sample_count)
    points, face_indices = trimesh.sample.sample_surface(mesh, n_samples)
    normals = mesh.face_normals[face_indices]

    eps = mesh.scale * 1e-4 if mesh.scale > 0 else 1e-6
    origins = points - normals * eps
    directions = -normals

    intersector = _ray_intersector(mesh)
    locations, index_ray, _ = intersector.intersects_location(
        origins, directions, multiple_hits=False
    )

    results = []
    for ray_idx, hit_point in zip(index_ray, locations):
        origin = origins[ray_idx]
        thickness = float(np.linalg.norm(hit_point - origin))
        if 0 < thickness < np.inf:
            results.append(
                {
                    "thickness": thickness,
                    "location": {"x": float(origin[0]), "y": float(origin[1]), "z": float(origin[2])},
                }
            )
    return results


def find_thin_regions(
    mesh: "trimesh.Trimesh", min_thickness: float, sample_count: int = 1500, max_results: int = 20
) -> List[Dict]:
    """Real per-region thin-wall detection (replaces the old global
    volume/area average that reported one issue for the whole part).
    Clustered on a coarse grid (~10% of the mesh's bounding diagonal) and
    capped to the worst `max_results` regions so a uniformly-thin part
    reports one issue per distinct region, not one per sample point."""
    samples = compute_wall_thickness_samples(mesh, sample_count)
    thin = [s for s in samples if s["thickness"] < min_thickness]
    if not thin:
        return []
    grid = mesh.scale * 0.1 if mesh.scale > 0 else 1.0
    clustered = sorted(cluster_by_location(thin, grid), key=lambda s: s["thickness"])
    return clustered[:max_results]


def find_sharp_internal_corners(
    mesh: "trimesh.Trimesh", angle_threshold_deg: float = 30.0, max_results: int = 20
) -> List[Dict]:
    """Find genuinely concave edges via real dihedral angles + convexity,
    instead of fabricating one corner whenever face_count > 1000. Clustered
    and capped to the sharpest `max_results` edges."""
    if len(mesh.face_adjacency) == 0:
        return []

    angles_deg = np.degrees(mesh.face_adjacency_angles)
    concave = ~mesh.face_adjacency_convex
    sharp_mask = concave & (angles_deg > angle_threshold_deg)

    edges = mesh.face_adjacency_edges[sharp_mask]
    sharp_angles = angles_deg[sharp_mask]

    results = []
    for (v0, v1), angle in zip(edges, sharp_angles):
        midpoint = (mesh.vertices[v0] + mesh.vertices[v1]) / 2
        results.append(
            {
                "angle_deg": float(angle),
                "location": {"x": float(midpoint[0]), "y": float(midpoint[1]), "z": float(midpoint[2])},
            }
        )
    grid = mesh.scale * 0.08 if mesh.scale > 0 else 1.0
    clustered = sorted(cluster_by_location(results, grid), key=lambda r: -r["angle_deg"])
    return clustered[:max_results]


def find_overhang_faces(
    mesh: "trimesh.Trimesh", max_overhang_angle_deg: float = 45.0, max_results: int = 20
) -> List[Dict]:
    """Real per-face overhang check for FDM printing: a downward-facing face
    needs support if it is closer to horizontal than the printer's
    self-supporting limit (angle measured from straight-down). Clustered and
    capped to the worst `max_results` regions."""
    normals = mesh.face_normals
    down = np.array([0.0, 0.0, -1.0])
    cos_angle = normals @ down
    angle_from_down_deg = np.degrees(np.arccos(np.clip(cos_angle, -1, 1)))

    downward_facing = cos_angle > 0.05
    unsupported_limit = 90.0 - max_overhang_angle_deg
    needs_support = downward_facing & (angle_from_down_deg < unsupported_limit)

    centers = mesh.triangles_center[needs_support]
    angles = angle_from_down_deg[needs_support]

    results = [
        {
            "overhang_angle_from_vertical_deg": float(90 - a),
            "location": {"x": float(c[0]), "y": float(c[1]), "z": float(c[2])},
        }
        for c, a in zip(centers, angles)
    ]
    grid = mesh.scale * 0.1 if mesh.scale > 0 else 1.0
    clustered = sorted(cluster_by_location(results, grid), key=lambda r: r["overhang_angle_from_vertical_deg"])
    return clustered[:max_results]


def find_small_holes(mesh: "trimesh.Trimesh", min_diameter: float) -> List[Dict]:
    """Detect small through-holes as closed loops of sharp concave edges with
    an approximately circular boundary, estimating diameter from the loop's
    mean radius. This only catches holes bounded by a genuinely sharp edge
    loop (true of essentially all drilled/CNC/printed circular holes), unlike
    the previous 'if face_count > 5000: fabricate a 0.5mm hole' stub."""
    if len(mesh.face_adjacency) == 0:
        return []

    angles_deg = np.degrees(mesh.face_adjacency_angles)
    concave = ~mesh.face_adjacency_convex
    sharp_mask = concave & (angles_deg > 60.0)
    edges = mesh.face_adjacency_edges[sharp_mask]
    if len(edges) == 0:
        return []

    graph = nx.Graph()
    graph.add_edges_from([tuple(e) for e in edges])

    results = []
    for component in nx.connected_components(graph):
        if len(component) < 6:
            continue
        sub = graph.subgraph(component)
        degrees = [d for _, d in sub.degree()]
        if max(degrees) > 2:
            continue  # not a simple loop
        verts = mesh.vertices[list(component)]
        center = verts.mean(axis=0)
        radii = np.linalg.norm(verts - center, axis=1)
        if radii.mean() <= 0 or radii.std() / radii.mean() > 0.35:
            continue  # not roughly circular
        diameter = float(2 * radii.mean())
        if diameter < min_diameter:
            results.append(
                {
                    "diameter": diameter,
                    "location": {"x": float(center[0]), "y": float(center[1]), "z": float(center[2])},
                }
            )
    return results


def estimate_pocket_geometry(mesh: "trimesh.Trimesh") -> List[Dict]:
    """Identify local concave pockets via connected components of the
    concave-face adjacency graph, measuring each pocket's own depth/width
    (real per-feature measurement) instead of the whole part's bounding-box
    aspect ratio."""
    if len(mesh.face_adjacency) == 0:
        return []
    concave_mask = ~mesh.face_adjacency_convex
    if not np.any(concave_mask):
        return []

    graph = nx.Graph()
    graph.add_edges_from([tuple(e) for e in mesh.face_adjacency[concave_mask]])

    results = []
    for component in nx.connected_components(graph):
        if len(component) < 4:
            continue
        face_indices = np.array(list(component))
        verts_idx = np.unique(mesh.faces[face_indices].flatten())
        pts = mesh.vertices[verts_idx]
        extents = pts.max(axis=0) - pts.min(axis=0)
        sorted_extents = np.sort(extents)
        depth = float(sorted_extents[-1])
        width = float(max(sorted_extents[0], 1e-6))
        if width <= 1e-6:
            continue
        centroid = pts.mean(axis=0)
        results.append(
            {
                "depth": depth,
                "width": width,
                "aspect_ratio": depth / width,
                "location": {"x": float(centroid[0]), "y": float(centroid[1]), "z": float(centroid[2])},
            }
        )
    return results


def detect_undercuts_by_direction(mesh: "trimesh.Trimesh", directions: Optional[List[np.ndarray]] = None) -> Dict:
    """Convex-hull volume deficit is a legitimate coarse undercut signal
    (kept), strengthened with a real per-direction accessibility check: for
    each candidate pull direction, measure the fraction of outward-facing
    faces that are 're-hit' by a ray leaving along that direction (meaning
    they're shadowed by other geometry and can't be reached from a single
    straight pull)."""
    if directions is None:
        directions = [
            np.array([0, 0, 1.0]), np.array([0, 0, -1.0]),
            np.array([1.0, 0, 0]), np.array([-1.0, 0, 0]),
            np.array([0, 1.0, 0]), np.array([0, -1.0, 0]),
        ]

    hull_ratio = None
    try:
        hull_volume = mesh.convex_hull.volume
        if hull_volume > 0:
            hull_ratio = float(mesh.volume / hull_volume)
    except Exception:
        pass

    face_centers = mesh.triangles_center
    face_normals = mesh.face_normals
    if len(face_centers) == 0:
        return {"hull_volume_ratio": hull_ratio, "best_direction": None, "shadowed_fraction": None}

    intersector = _ray_intersector(mesh)
    best_direction = None
    best_shadowed_fraction = 1.0

    for direction in directions:
        direction = direction / np.linalg.norm(direction)
        facing = face_normals @ direction > 0.1
        if not np.any(facing):
            continue
        origins = face_centers[facing] + face_normals[facing] * (mesh.scale * 1e-4 if mesh.scale > 0 else 1e-6)
        directions_arr = np.tile(direction, (len(origins), 1))
        _, index_ray, _ = intersector.intersects_location(origins, directions_arr, multiple_hits=False)
        shadowed_fraction = len(set(index_ray)) / len(origins)
        if shadowed_fraction < best_shadowed_fraction:
            best_shadowed_fraction = shadowed_fraction
            best_direction = direction

    return {
        "hull_volume_ratio": hull_ratio,
        "best_direction": best_direction.tolist() if best_direction is not None else None,
        "shadowed_fraction": best_shadowed_fraction if best_direction is not None else None,
    }
