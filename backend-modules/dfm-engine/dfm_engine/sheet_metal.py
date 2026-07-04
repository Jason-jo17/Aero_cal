from typing import Dict, List
from dataclasses import dataclass, asdict
import numpy as np

from . import geometry_analysis as ga


@dataclass
class SheetMetalIssue:
    severity: str
    category: str
    description: str
    location: Dict
    recommendation: str
    cost_impact: float


class SheetMetalAnalyzer:
    """DFM analysis for Sheet Metal, backed by real geometry measurements."""

    def __init__(self):
        self.min_bend_radius = 1.0  # ratio to thickness
        self.min_hole_dist = 2.0  # ratio to thickness (thickness = min hole diameter proxy)

    def analyze(self, geometry) -> List[Dict]:
        issues = []
        issues.extend(self._check_uniform_thickness(geometry))
        issues.extend(self._check_hole_distances(geometry))
        return [asdict(issue) for issue in issues]

    def _check_uniform_thickness(self, geometry) -> List[SheetMetalIssue]:
        """Real per-region thickness variation check: sheet metal parts
        should have one thickness everywhere; flag regions that deviate from
        the part's modal thickness instead of a single global average."""
        issues = []
        samples = ga.compute_wall_thickness_samples(geometry, sample_count=800)
        if len(samples) < 5:
            return issues

        thicknesses = np.array([s["thickness"] for s in samples])
        nominal = float(np.median(thicknesses))
        deviating = [s for s, t in zip(samples, thicknesses) if abs(t - nominal) > max(nominal * 0.15, 0.1)]

        grid = geometry.scale * 0.03 if geometry.scale > 0 else 1.0
        for region in ga.cluster_by_location(deviating, grid):
            issues.append(
                SheetMetalIssue(
                    severity="critical",
                    category="thickness",
                    description=(
                        f"Local thickness {region['thickness']:.2f}mm deviates from the part's "
                        f"nominal thickness {nominal:.2f}mm."
                    ),
                    location=region["location"],
                    recommendation="Sheet metal parts must have a single uniform thickness throughout.",
                    cost_impact=2.0,
                )
            )
        return issues

    def _check_hole_distances(self, geometry) -> List[SheetMetalIssue]:
        """Real hole detection (via geometry_analysis) with distance-to-edge
        check, instead of a face-count-triggered fabricated issue."""
        issues = []
        holes = ga.find_small_holes(geometry, min_diameter=float("inf"))  # detect all holes regardless of size
        if not holes:
            return issues

        min_thickness_samples = ga.compute_wall_thickness_samples(geometry, sample_count=500)
        thickness = float(np.median([s["thickness"] for s in min_thickness_samples])) if min_thickness_samples else 1.0
        min_edge_distance = self.min_hole_dist * thickness

        bounds = geometry.bounds
        for hole in holes:
            loc = hole["location"]
            point = np.array([loc["x"], loc["y"], loc["z"]])
            dist_to_edge = float(
                min(
                    abs(point[0] - bounds[0][0]), abs(bounds[1][0] - point[0]),
                    abs(point[1] - bounds[0][1]), abs(bounds[1][1] - point[1]),
                )
            )
            if dist_to_edge < min_edge_distance:
                issues.append(
                    SheetMetalIssue(
                        severity="warning",
                        category="hole_distance",
                        description=(
                            f"Hole (~{hole['diameter']:.2f}mm) is {dist_to_edge:.2f}mm from the part edge, "
                            f"below the recommended {min_edge_distance:.2f}mm ({self.min_hole_dist}x thickness)."
                        ),
                        location=loc,
                        recommendation="Move holes further from edges and bends.",
                        cost_impact=0.1,
                    )
                )
        return issues
