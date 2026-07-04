from typing import Dict, List
from dataclasses import dataclass, asdict
import numpy as np

from . import geometry_analysis as ga


@dataclass
class InjectionMoldingIssue:
    severity: str
    category: str
    description: str
    location: Dict
    recommendation: str
    cost_impact: float


class InjectionMoldingAnalyzer:
    """DFM analysis for Injection Molding, backed by real per-region geometry
    measurements rather than a single whole-mesh average."""

    def __init__(self):
        self.min_wall_thickness = 1.0
        self.max_wall_thickness = 4.0
        self.min_draft_angle = 1.0  # degrees
        self.min_boss_ratio = 0.5

    def analyze(self, geometry) -> List[Dict]:
        issues = []
        issues.extend(self._check_wall_thickness(geometry))
        issues.extend(self._check_draft_angles(geometry))
        issues.extend(self._check_undercuts(geometry))
        return [asdict(issue) for issue in issues]

    def _check_wall_thickness(self, geometry) -> List[InjectionMoldingIssue]:
        issues = []
        samples = ga.compute_wall_thickness_samples(geometry)
        if not samples:
            return issues

        thin = [s for s in samples if s["thickness"] < self.min_wall_thickness]
        thick = [s for s in samples if s["thickness"] > self.max_wall_thickness]

        for wall in ga.cluster_by_location(thin, geometry.scale * 0.03 if geometry.scale > 0 else 1.0):
            issues.append(
                InjectionMoldingIssue(
                    severity="critical",
                    category="wall_thickness",
                    description=f"Wall thickness {wall['thickness']:.2f}mm is too thin (min {self.min_wall_thickness}mm). May cause short shots.",
                    location=wall["location"],
                    recommendation=f"Increase wall thickness to at least {self.min_wall_thickness}mm.",
                    cost_impact=0.5,
                )
            )
        for wall in ga.cluster_by_location(thick, geometry.scale * 0.03 if geometry.scale > 0 else 1.0):
            issues.append(
                InjectionMoldingIssue(
                    severity="warning",
                    category="wall_thickness",
                    description=f"Wall thickness {wall['thickness']:.2f}mm is too thick (max {self.max_wall_thickness}mm). May cause sink marks.",
                    location=wall["location"],
                    recommendation="Core out thick sections to maintain uniform wall thickness.",
                    cost_impact=0.3,
                )
            )
        return issues

    def _check_draft_angles(self, geometry) -> List[InjectionMoldingIssue]:
        issues = []
        try:
            normals = geometry.face_normals
            vertical_mask = np.abs(normals[:, 2]) < np.sin(np.radians(self.min_draft_angle))
            if np.any(vertical_mask):
                centers = geometry.triangles_center[vertical_mask]
                raw = [
                    {"location": {"x": float(c[0]), "y": float(c[1]), "z": float(c[2])}}
                    for c in centers
                ]
                grid = geometry.scale * 0.05 if geometry.scale > 0 else 1.0
                for cluster in ga.cluster_by_location(raw, grid):
                    issues.append(
                        InjectionMoldingIssue(
                            severity="warning",
                            category="draft_angle",
                            description=f"Vertical surface detected without draft angle (min {self.min_draft_angle}°).",
                            location=cluster["location"],
                            recommendation="Add draft angles to all surfaces parallel to the parting line.",
                            cost_impact=0.4,
                        )
                    )
        except Exception:
            pass
        return issues

    def _check_undercuts(self, geometry) -> List[InjectionMoldingIssue]:
        issues = []
        result = ga.detect_undercuts_by_direction(geometry)
        hull_ratio = result.get("hull_volume_ratio")
        shadowed = result.get("shadowed_fraction")
        if hull_ratio is not None and hull_ratio < 0.6 and shadowed is not None and shadowed > 0.05:
            centroid = geometry.centroid
            issues.append(
                InjectionMoldingIssue(
                    severity="critical",
                    category="undercut",
                    description=(
                        f"Severe undercut detected (convex-hull volume ratio {hull_ratio:.2f}, "
                        f"{shadowed * 100:.0f}% of surface unreachable from the best single pull direction) "
                        "requiring side-action cams or lifters."
                    ),
                    location={"x": float(centroid[0]), "y": float(centroid[1]), "z": float(centroid[2])},
                    recommendation="Redesign to eliminate undercuts if possible to reduce mold cost.",
                    cost_impact=5.0,
                )
            )
        return issues
