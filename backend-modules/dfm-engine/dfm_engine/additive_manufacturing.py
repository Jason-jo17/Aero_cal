from typing import Dict, List
from dataclasses import dataclass, asdict

from . import geometry_analysis as ga


@dataclass
class FDMIssue:
    severity: str
    category: str
    description: str
    location: Dict
    recommendation: str
    printability_impact: float


class FDMAnalyzer:
    """DFM analysis for Fused Deposition Modeling (FDM) 3D Printing, backed
    by real per-face/per-region geometry measurements."""

    def __init__(self):
        self.min_wall_thickness = 0.8
        self.max_overhang_angle = 45.0  # degrees from vertical
        self.min_hole_diameter = 1.0
        self.min_feature_size = 0.4

    def analyze(self, geometry) -> List[Dict]:
        issues = []
        issues.extend(self._check_wall_thickness(geometry))
        issues.extend(self._check_overhangs(geometry))
        issues.extend(self._check_hole_diameters(geometry))
        issues.extend(self._check_build_orientation(geometry))
        return [asdict(issue) for issue in issues]

    def _check_wall_thickness(self, geometry) -> List[FDMIssue]:
        issues = []
        for wall in ga.find_thin_regions(geometry, self.min_wall_thickness):
            issues.append(
                FDMIssue(
                    severity="warning",
                    category="wall_thickness",
                    description=f"Wall thickness {wall['thickness']:.2f}mm below minimum {self.min_wall_thickness}mm",
                    location=wall["location"],
                    recommendation=f"Increase wall thickness to at least {self.min_wall_thickness}mm",
                    printability_impact=0.4,
                )
            )
        return issues

    def _check_overhangs(self, geometry) -> List[FDMIssue]:
        issues = []
        for overhang in ga.find_overhang_faces(geometry, self.max_overhang_angle):
            issues.append(
                FDMIssue(
                    severity="warning",
                    category="overhang",
                    description=f"Overhang face at {overhang['overhang_angle_from_vertical_deg']:.1f}° from vertical exceeds the {self.max_overhang_angle}° self-supporting limit",
                    location=overhang["location"],
                    recommendation="Add supports, or reorient/redesign to reduce the overhang angle",
                    printability_impact=0.6,
                )
            )
        return issues

    def _check_hole_diameters(self, geometry) -> List[FDMIssue]:
        issues = []
        for hole in ga.find_small_holes(geometry, self.min_hole_diameter):
            issues.append(
                FDMIssue(
                    severity="critical",
                    category="hole_diameter",
                    description=f"Hole diameter {hole['diameter']:.2f}mm below minimum {self.min_hole_diameter}mm",
                    location=hole["location"],
                    recommendation=f"Increase hole diameter to at least {self.min_hole_diameter}mm",
                    printability_impact=0.8,
                )
            )
        return issues

    def _check_build_orientation(self, geometry) -> List[FDMIssue]:
        extents = geometry.extents
        if extents[2] > max(extents[0], extents[1]) * 2:
            return [
                FDMIssue(
                    severity="warning",
                    category="build_orientation",
                    description="Tall and skinny parts are prone to bed adhesion failure or layer shifting.",
                    location={
                        "x": float(geometry.centroid[0]),
                        "y": float(geometry.centroid[1]),
                        "z": float(geometry.centroid[2]),
                    },
                    recommendation="Consider printing flat or adding a brim/raft.",
                    printability_impact=0.7,
                )
            ]
        return []
