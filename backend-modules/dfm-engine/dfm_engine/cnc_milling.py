from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from . import geometry_analysis as ga


@dataclass
class CNCMillingIssue:
    severity: str
    category: str
    description: str
    location: Dict
    recommendation: str
    cost_impact: float


class CNCMillingAnalyzer:
    """DFM analysis for CNC milling, backed by real per-feature geometry
    measurements (see geometry_analysis.py) rather than whole-mesh averages."""

    def __init__(self):
        self.min_wall_thickness = 0.5
        self.min_inside_radius = 0.5
        self.max_depth_to_width = 4

    def analyze(self, geometry, toleranced_features: Optional[List[Dict]] = None) -> List[Dict]:
        issues = []
        issues.extend(self._check_wall_thickness(geometry))
        issues.extend(self._check_internal_corners(geometry))
        issues.extend(self._check_pocket_aspect_ratios(geometry))
        issues.extend(self._check_undercuts(geometry))
        issues.extend(self._check_tolerances(toleranced_features))
        return [asdict(issue) for issue in issues]

    def _check_wall_thickness(self, geometry) -> List[CNCMillingIssue]:
        issues = []
        for wall in ga.find_thin_regions(geometry, self.min_wall_thickness):
            issues.append(
                CNCMillingIssue(
                    severity="critical",
                    category="wall_thickness",
                    description=f"Wall thickness {wall['thickness']:.2f}mm below minimum {self.min_wall_thickness}mm",
                    location=wall["location"],
                    recommendation=f"Increase wall thickness to at least {self.min_wall_thickness}mm or consider reinforcement ribs",
                    cost_impact=0.15,
                )
            )
        return issues

    def _check_internal_corners(self, geometry) -> List[CNCMillingIssue]:
        issues = []
        for corner in ga.find_sharp_internal_corners(geometry):
            issues.append(
                CNCMillingIssue(
                    severity="warning",
                    category="internal_corners",
                    description=f"Sharp internal corner ({corner['angle_deg']:.0f}° dihedral angle) requires a smaller tool or fillet",
                    location=corner["location"],
                    recommendation="Add a fillet radius matching an available end-mill radius, or accept a smaller/custom tool",
                    cost_impact=0.08,
                )
            )
        return issues

    def _check_pocket_aspect_ratios(self, geometry) -> List[CNCMillingIssue]:
        issues = []
        for pocket in ga.estimate_pocket_geometry(geometry):
            if pocket["aspect_ratio"] > self.max_depth_to_width:
                issues.append(
                    CNCMillingIssue(
                        severity="warning",
                        category="pocket_geometry",
                        description=f"Deep pocket (depth/width={pocket['aspect_ratio']:.1f}) exceeds recommended ratio of {self.max_depth_to_width}",
                        location=pocket["location"],
                        recommendation="Widen the pocket or reduce its depth to improve tool accessibility and reduce deflection",
                        cost_impact=0.12,
                    )
                )
        return issues

    def _check_undercuts(self, geometry) -> List[CNCMillingIssue]:
        result = ga.detect_undercuts_by_direction(geometry)
        issues = []
        hull_ratio = result.get("hull_volume_ratio")
        shadowed = result.get("shadowed_fraction")
        if hull_ratio is not None and hull_ratio < 0.7 and shadowed is not None and shadowed > 0.05:
            centroid = geometry.centroid
            issues.append(
                CNCMillingIssue(
                    severity="critical",
                    category="undercut",
                    description=(
                        f"Geometry has significant re-entrant features (convex-hull volume ratio "
                        f"{hull_ratio:.2f}, {shadowed * 100:.0f}% of surface unreachable from the best single pull direction)"
                    ),
                    location={"x": float(centroid[0]), "y": float(centroid[1]), "z": float(centroid[2])},
                    recommendation="Redesign to eliminate undercuts, or accept 4/5-axis machining cost (2-3x)",
                    cost_impact=2.0,
                )
            )
        return issues

    def _check_tolerances(self, toleranced_features: Optional[List[Dict]]) -> List[CNCMillingIssue]:
        """Tolerance callouts cannot be extracted from an STL mesh (it carries
        no GD&T/tolerance metadata) — only check tolerances the caller
        explicitly supplies, rather than fabricating one."""
        if not toleranced_features:
            return []

        very_tight_tolerance = 0.01
        tight_tolerance = 0.05
        standard_tolerance = 0.1

        issues = []
        for feature in toleranced_features:
            tolerance = feature["tolerance"]
            location = feature.get("location", {"x": 0.0, "y": 0.0, "z": 0.0})
            if tolerance < very_tight_tolerance:
                issues.append(
                    CNCMillingIssue(
                        severity="critical",
                        category="tolerance",
                        description=f"Tolerance ±{tolerance}mm extremely difficult with standard CNC",
                        location=location,
                        recommendation=f"Relax to ±{very_tight_tolerance}mm or specify a grinding/finishing operation",
                        cost_impact=0.5,
                    )
                )
            elif tolerance < tight_tolerance:
                issues.append(
                    CNCMillingIssue(
                        severity="warning",
                        category="tolerance",
                        description=f"Tight tolerance ±{tolerance}mm requires precision machining",
                        location=location,
                        recommendation=f"Consider relaxing to ±{standard_tolerance}mm if not critical",
                        cost_impact=0.20,
                    )
                )
        return issues
