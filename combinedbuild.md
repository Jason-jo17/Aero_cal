# DFM-Analyzer: Production-Ready Specification

## Executive Summary

Standalone Design for Manufacturing analysis tool that identifies manufacturability issues, estimates costs, and recommends design improvements across multiple manufacturing processes. Bridges the gap between CAD design and production.

**Target Users**: Product designers, mechanical engineers, manufacturing engineers, procurement teams, engineering students
**Market Gap**: No comprehensive open-source DFM tool; commercial options (SolidWorks Costing, aPriori) are expensive and locked to specific CAD platforms
**Unique Value**: Process-agnostic, platform-independent, AI-powered recommendations, open-source
**Monetization**: Freemium (basic analysis) + Pro (advanced features) + Enterprise (API + integrations)

---

## Technical Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────┐
│              Web/Desktop Application                      │
│        (Electron for desktop, Next.js for web)           │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  CAD Import  │  │     DFM      │  │    Cost      │  │
│  │   Module     │  │   Analysis   │  │  Estimation  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└──────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼──────┐  ┌──────▼──────┐  ┌──────▼────────┐
│  Geometry    │  │   Rules     │  │   Material    │
│  Analyzer    │  │   Engine    │  │   Database    │
│  (Python)    │  │  (Python)   │  │  (Postgres)   │
└──────────────┘  └─────────────┘  └───────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼──────┐  ┌──────▼──────┐  ┌──────▼────────┐
│  CAD Parser  │  │  Knowledge  │  │    Reports    │
│  (pythonOCC) │  │    Base     │  │   Generator   │
│              │  │  (AI/RAG)   │  │   (PDF/HTML)  │
└──────────────┘  └─────────────┘  └───────────────┘
```

### Tech Stack

**Frontend (Web + Desktop)**
- **Web**: Next.js 14 + TypeScript
- **Desktop**: Electron + React
- **UI Library**: shadcn/ui + Tailwind CSS
- **3D Viewer**: Three.js + React Three Fiber
- **Charts**: Recharts
- **Forms**: React Hook Form + Zod

**Backend**
- **API**: FastAPI (Python 3.11+)
- **CAD Processing**: pythonOCC (OpenCascade Community Edition)
- **Geometry Analysis**: CadQuery
- **AI Recommendations**: LangChain + Claude/GPT-4
- **Task Queue**: Celery + Redis (for batch processing)

**Database**
- **Primary**: PostgreSQL 15 (analysis results, projects)
- **Cache**: Redis (computation results)
- **Vector DB**: Qdrant (manufacturing knowledge base)
- **File Storage**: S3 / MinIO (CAD files)

**Manufacturing Knowledge**
- **DFM Rules**: JSON/YAML rule definitions
- **Material Database**: Comprehensive properties
- **Process Database**: Capabilities, tolerances, costs
- **Standards**: ASME, ISO, DIN references

**CAD Integrations**
- **FreeCAD**: Python plugin/workbench
- **Fusion 360**: API extension
- **SolidWorks**: COM/API plugin (C#)
- **Blender**: Python addon
- **OnShape**: REST API integration

**Infrastructure**
- **Hosting**: AWS (web) + GitHub Releases (desktop)
- **CDN**: CloudFlare
- **Monitoring**: Sentry + Prometheus
- **CI/CD**: GitHub Actions

---

## Product Architecture

### Manufacturing Processes Supported

#### 1. CNC Milling

**Analysis Checks:**
```python
# services/dfm/cnc_milling.py

from typing import Dict, List
import numpy as np
from dataclasses import dataclass

@dataclass
class CNCMillingIssue:
    severity: str  # 'critical', 'warning', 'suggestion'
    category: str
    description: str
    location: Dict  # Coordinates or face IDs
    recommendation: str
    cost_impact: float  # Estimated cost increase

class CNCMillingAnalyzer:
    """DFM analysis for CNC milling"""
    
    def __init__(self):
        self.min_wall_thickness = 0.5  # mm, 3-axis
        self.min_inside_radius = 0.5   # mm, end mill radius
        self.max_depth_to_width = 4    # Aspect ratio for pockets
        
    def analyze(self, geometry) -> List[CNCMillingIssue]:
        """Run all CNC milling checks"""
        
        issues = []
        
        # Check 1: Wall thickness
        issues.extend(self._check_wall_thickness(geometry))
        
        # Check 2: Internal corners (sharp corners)
        issues.extend(self._check_internal_corners(geometry))
        
        # Check 3: Deep narrow pockets
        issues.extend(self._check_pocket_aspect_ratios(geometry))
        
        # Check 4: Undercuts
        issues.extend(self._check_undercuts(geometry))
        
        # Check 5: Thread specifications
        issues.extend(self._check_threads(geometry))
        
        # Check 6: Tolerance feasibility
        issues.extend(self._check_tolerances(geometry))
        
        # Check 7: Surface finish requirements
        issues.extend(self._check_surface_finish(geometry))
        
        # Check 8: Material selection
        issues.extend(self._check_material_machinability(geometry))
        
        return issues
    
    def _check_wall_thickness(self, geometry) -> List[CNCMillingIssue]:
        """Check for walls thinner than minimum"""
        
        issues = []
        
        # Detect thin walls using topology analysis
        thin_walls = self._detect_thin_features(
            geometry, 
            min_thickness=self.min_wall_thickness
        )
        
        for wall in thin_walls:
            thickness = wall['thickness']
            location = wall['location']
            
            if thickness < self.min_wall_thickness:
                issues.append(CNCMillingIssue(
                    severity='critical',
                    category='wall_thickness',
                    description=f"Wall thickness {thickness:.2f}mm below minimum {self.min_wall_thickness}mm",
                    location=location,
                    recommendation=f"Increase wall thickness to at least {self.min_wall_thickness}mm or consider reinforcement ribs",
                    cost_impact=0.15  # 15% cost increase due to difficulty/breakage risk
                ))
        
        return issues
    
    def _check_internal_corners(self, geometry) -> List[CNCMillingIssue]:
        """Check for sharp internal corners that need fillets"""
        
        issues = []
        
        # Find internal corners
        internal_corners = self._find_internal_corners(geometry)
        
        for corner in internal_corners:
            radius = corner.get('radius', 0)
            
            if radius < self.min_inside_radius:
                # Calculate recommended radius based on wall depth
                depth = corner.get('depth', 10)
                recommended_radius = min(depth * 0.1, 3.0)  # 10% of depth, max 3mm
                
                issues.append(CNCMillingIssue(
                    severity='warning',
                    category='internal_corners',
                    description=f"Sharp internal corner (R{radius:.2f}mm) requires smaller tool",
                    location=corner['location'],
                    recommendation=f"Add R{recommended_radius:.1f}mm fillet to allow standard tooling",
                    cost_impact=0.08  # 8% increase for tool changes or custom tools
                ))
        
        return issues
    
    def _check_pocket_aspect_ratios(self, geometry) -> List[CNCMillingIssue]:
        """Check depth-to-width ratios of pockets"""
        
        issues = []
        
        pockets = self._identify_pockets(geometry)
        
        for pocket in pockets:
            depth = pocket['depth']
            width = pocket['width']
            aspect_ratio = depth / width
            
            if aspect_ratio > self.max_depth_to_width:
                issues.append(CNCMillingIssue(
                    severity='warning',
                    category='pocket_geometry',
                    description=f"Deep pocket (depth/width = {aspect_ratio:.1f}) exceeds recommended ratio of {self.max_depth_to_width}",
                    location=pocket['location'],
                    recommendation="Widen pocket or reduce depth to improve tool accessibility and reduce deflection",
                    cost_impact=0.12  # 12% increase due to multiple passes
                ))
        
        return issues
    
    def _check_undercuts(self, geometry) -> List[CNCMillingIssue]:
        """Detect features requiring 4/5-axis machining"""
        
        issues = []
        
        # Analyze part orientation and accessibility
        undercuts = self._detect_undercuts(geometry)
        
        for undercut in undercuts:
            issues.append(CNCMillingIssue(
                severity='critical',
                category='undercut',
                description=f"Undercut feature requires multi-axis machining or special tooling",
                location=undercut['location'],
                recommendation="Redesign to eliminate undercut or accept 4/5-axis machining cost (2-3x)",
                cost_impact=2.0  # 200% cost increase for 4/5-axis
            ))
        
        return issues
    
    def _check_tolerances(self, geometry) -> List[CNCMillingIssue]:
        """Validate tolerance specifications against CNC capabilities"""
        
        issues = []
        
        # Standard CNC tolerances
        standard_tolerance = 0.1  # ±0.1mm typical
        tight_tolerance = 0.05    # ±0.05mm achievable
        very_tight_tolerance = 0.01  # ±0.01mm requires precision machining
        
        # Extract tolerances from geometry metadata
        toleranced_features = self._extract_tolerances(geometry)
        
        for feature in toleranced_features:
            tolerance = feature['tolerance']
            feature_type = feature['type']
            
            if tolerance < very_tight_tolerance:
                issues.append(CNCMillingIssue(
                    severity='critical',
                    category='tolerance',
                    description=f"Tolerance ±{tolerance}mm extremely difficult with standard CNC",
                    location=feature['location'],
                    recommendation=f"Relax to ±{very_tight_tolerance}mm or specify grinding/finishing operation",
                    cost_impact=0.5  # 50% increase for secondary operations
                ))
            elif tolerance < tight_tolerance:
                issues.append(CNCMillingIssue(
                    severity='warning',
                    category='tolerance',
                    description=f"Tight tolerance ±{tolerance}mm requires precision machining",
                    location=feature['location'],
                    recommendation=f"Consider relaxing to ±{standard_tolerance}mm if not critical",
                    cost_impact=0.20  # 20% increase for precision work
                ))
        
        return issues
    
    def estimate_machining_time(self, geometry, material: str) -> Dict:
        """Estimate CNC machining time and cost"""
        
        # Extract geometry metrics
        volume = self._calculate_volume(geometry)
        surface_area = self._calculate_surface_area(geometry)
        bounding_box = self._get_bounding_box(geometry)
        complexity = self._assess_complexity(geometry)
        
        # Material removal rate (mm³/min) varies by material
        mrr_database = {
            'aluminum_6061': 50000,
            'aluminum_7075': 40000,
            'steel_1018': 25000,
            'stainless_304': 15000,
            'titanium_grade5': 8000,
            'brass': 60000,
            'copper': 55000,
            'abs_plastic': 80000
        }
        
        mrr = mrr_database.get(material, 30000)
        
        # Calculate material to remove (rough estimate)
        # Assuming starting from rectangular stock
        stock_volume = np.prod(bounding_box['dimensions'])
        removal_volume = stock_volume - volume
        
        # Roughing time
        roughing_time = (removal_volume * 1.3) / mrr  # 1.3 factor for inefficiency
        
        # Finishing time (based on surface area and complexity)
        finishing_rate = 5000  # mm²/min
        finishing_time = (surface_area / finishing_rate) * complexity
        
        # Setup time
        setup_time = 30  # minutes
        
        # Tool changes
        num_tools = self._estimate_tool_changes(geometry)
        tool_change_time = num_tools * 2  # 2 min per tool change
        
        total_time = setup_time + roughing_time + finishing_time + tool_change_time
        
        # Cost estimation
        machine_rate = 85  # USD per hour
        material_cost = self._estimate_material_cost(material, stock_volume)
        
        labor_cost = (total_time / 60) * machine_rate
        overhead = labor_cost * 0.15
        
        total_cost = material_cost + labor_cost + overhead
        
        return {
            'time_breakdown': {
                'setup_min': setup_time,
                'roughing_min': roughing_time,
                'finishing_min': finishing_time,
                'tool_changes_min': tool_change_time,
                'total_min': total_time,
                'total_hours': total_time / 60
            },
            'cost_breakdown': {
                'material_usd': material_cost,
                'labor_usd': labor_cost,
                'overhead_usd': overhead,
                'total_usd': total_cost
            },
            'metrics': {
                'volume_removed_mm3': removal_volume,
                'surface_area_mm2': surface_area,
                'complexity_score': complexity,
                'num_tools': num_tools
            }
        }
```

#### 2. 3D Printing (FDM/SLA)

**Analysis Checks:**
```python
# services/dfm/additive_manufacturing.py

class FDMAnalyzer:
    """DFM analysis for FDM 3D printing"""
    
    def __init__(self):
        self.min_wall_thickness = 0.8  # mm for 0.4mm nozzle
        self.max_overhang_angle = 45   # degrees without support
        self.min_feature_size = 0.4    # mm (nozzle diameter)
        
    def analyze(self, geometry) -> List:
        """Run FDM-specific checks"""
        
        issues = []
        
        # Check 1: Overhangs requiring support
        issues.extend(self._check_overhangs(geometry))
        
        # Check 2: Bridging distances
        issues.extend(self._check_bridges(geometry))
        
        # Check 3: Wall thickness for strength
        issues.extend(self._check_wall_thickness(geometry))
        
        # Check 4: Small features that may not print well
        issues.extend(self._check_feature_size(geometry))
        
        # Check 5: Orientation optimization
        issues.extend(self._suggest_orientation(geometry))
        
        # Check 6: Warping risk (large flat surfaces)
        issues.extend(self._check_warping_risk(geometry))
        
        return issues
    
    def _check_overhangs(self, geometry) -> List:
        """Identify overhangs requiring support material"""
        
        issues = []
        
        # Analyze geometry at different orientations
        orientations = self._generate_candidate_orientations(geometry)
        
        best_orientation = None
        min_support_volume = float('inf')
        
        for orientation in orientations:
            oriented_geometry = self._rotate_geometry(geometry, orientation)
            overhangs = self._detect_overhangs(oriented_geometry, self.max_overhang_angle)
            
            support_volume = sum(overhang['support_volume'] for overhang in overhangs)
            
            if support_volume < min_support_volume:
                min_support_volume = support_volume
                best_orientation = orientation
        
        # Analyze best orientation
        oriented_geometry = self._rotate_geometry(geometry, best_orientation)
        overhangs = self._detect_overhangs(oriented_geometry, self.max_overhang_angle)
        
        if overhangs:
            total_support_volume = sum(o['support_volume'] for o in overhangs)
            part_volume = self._calculate_volume(geometry)
            support_ratio = total_support_volume / part_volume
            
            issues.append({
                'severity': 'warning' if support_ratio < 0.2 else 'critical',
                'category': 'overhangs',
                'description': f"{len(overhangs)} overhangs detected requiring support material",
                'recommendation': f"Orient part at {best_orientation} to minimize support (ratio: {support_ratio:.1%})",
                'support_volume_mm3': total_support_volume,
                'cost_impact': support_ratio * 0.3  # Support material adds 30% of ratio to cost
            })
        
        return issues
    
    def _check_bridges(self, geometry) -> List:
        """Check bridging distances"""
        
        issues = []
        
        max_bridge_distance = 10  # mm without sagging
        
        bridges = self._detect_bridges(geometry)
        
        for bridge in bridges:
            distance = bridge['distance']
            
            if distance > max_bridge_distance:
                issues.append({
                    'severity': 'warning',
                    'category': 'bridging',
                    'description': f"Bridge span of {distance:.1f}mm may sag (max recommended: {max_bridge_distance}mm)",
                    'location': bridge['location'],
                    'recommendation': "Add support or reduce unsupported span",
                    'cost_impact': 0.05  # Minor cost for support
                })
        
        return issues
    
    def estimate_print_time(self, geometry, settings: Dict) -> Dict:
        """Estimate FDM print time and cost"""
        
        # Extract settings
        layer_height = settings.get('layer_height', 0.2)  # mm
        print_speed = settings.get('print_speed', 60)     # mm/s
        infill_percentage = settings.get('infill', 20)    # %
        
        # Calculate volumes
        part_volume = self._calculate_volume(geometry)
        shell_thickness = settings.get('shell_thickness', 1.2)  # mm
        shell_volume = self._calculate_shell_volume(geometry, shell_thickness)
        infill_volume = (part_volume - shell_volume) * (infill_percentage / 100)
        total_material = shell_volume + infill_volume
        
        # Calculate print path length
        surface_area = self._calculate_surface_area(geometry)
        num_layers = self._get_bounding_box(geometry)['dimensions'][2] / layer_height
        
        perimeter_length = self._estimate_perimeter_length(geometry) * num_layers
        infill_length = self._estimate_infill_length(infill_volume, layer_height)
        
        total_length = perimeter_length + infill_length
        
        # Time calculation
        print_time = total_length / print_speed  # seconds
        
        # Add overheads
        layer_change_time = num_layers * 0.5  # 0.5s per layer
        travel_time = total_length * 0.1      # 10% travel moves
        
        total_time_s = print_time + layer_change_time + travel_time
        total_time_h = total_time_s / 3600
        
        # Cost calculation
        material_density = 1.24  # g/cm³ for PLA
        material_weight = (total_material / 1000) * material_density  # grams
        material_cost_per_kg = 20  # USD
        material_cost = (material_weight / 1000) * material_cost_per_kg
        
        machine_cost_per_hour = 5  # USD
        machine_cost = total_time_h * machine_cost_per_hour
        
        # Support material if needed
        support_volume = self._calculate_support_volume(geometry, settings)
        support_material = (support_volume / 1000) * material_density
        support_cost = (support_material / 1000) * material_cost_per_kg
        
        total_cost = material_cost + machine_cost + support_cost
        
        return {
            'time': {
                'printing_hours': total_time_h,
                'num_layers': int(num_layers)
            },
            'material': {
                'part_grams': material_weight,
                'support_grams': support_material,
                'total_grams': material_weight + support_material
            },
            'cost': {
                'material_usd': material_cost,
                'support_material_usd': support_cost,
                'machine_usd': machine_cost,
                'total_usd': total_cost
            }
        }
```

#### 3. Injection Molding

**Analysis Checks:**
```python
# services/dfm/injection_molding.py

class InjectionMoldingAnalyzer:
    """DFM analysis for injection molding"""
    
    def __init__(self):
        self.nominal_wall_thickness = 2.5  # mm, varies by material
        self.max_wall_variation = 0.25     # Max difference between sections
        self.min_draft_angle = 1           # degrees
        self.min_radius = 0.5              # mm
        
    def analyze(self, geometry, material: str = 'ABS') -> List:
        """Run injection molding checks"""
        
        issues = []
        
        # Check 1: Wall thickness uniformity
        issues.extend(self._check_wall_uniformity(geometry, material))
        
        # Check 2: Draft angles
        issues.extend(self._check_draft_angles(geometry))
        
        # Check 3: Sharp corners (stress concentrations)
        issues.extend(self._check_corner_radii(geometry))
        
        # Check 4: Undercuts (requiring slides/lifters)
        issues.extend(self._check_undercuts(geometry))
        
        # Check 5: Gate location feasibility
        issues.extend(self._suggest_gate_locations(geometry))
        
        # Check 6: Sink marks potential
        issues.extend(self._check_sink_marks(geometry))
        
        # Check 7: Weld lines
        issues.extend(self._predict_weld_lines(geometry))
        
        return issues
    
    def _check_wall_uniformity(self, geometry, material: str) -> List:
        """Check for uniform wall thickness"""
        
        issues = []
        
        # Material-specific nominal wall thickness
        nominal_walls = {
            'ABS': 2.5,
            'PC': 2.0,
            'PP': 3.0,
            'Nylon': 2.0,
            'PET': 2.5
        }
        
        nominal = nominal_walls.get(material, 2.5)
        
        # Analyze wall thickness distribution
        wall_analysis = self._analyze_wall_thickness(geometry)
        
        for section in wall_analysis['sections']:
            thickness = section['thickness']
            location = section['location']
            
            # Check if too thin
            if thickness < nominal * 0.5:
                issues.append({
                    'severity': 'critical',
                    'category': 'wall_thickness',
                    'description': f"Wall thickness {thickness:.2f}mm too thin (nominal: {nominal}mm for {material})",
                    'location': location,
                    'recommendation': f"Increase to {nominal}mm for proper flow and strength",
                    'cost_impact': 0  # Thinner is actually cheaper but quality issue
                })
            
            # Check if too thick
            elif thickness > nominal * 1.5:
                issues.append({
                    'severity': 'warning',
                    'category': 'wall_thickness',
                    'description': f"Wall thickness {thickness:.2f}mm too thick (nominal: {nominal}mm)",
                    'location': location,
                    'recommendation': f"Reduce to {nominal}mm to prevent sink marks and reduce cycle time",
                    'cost_impact': 0.15  # Thick sections increase cycle time
                })
            
            # Check variation between sections
            if 'adjacent_thickness' in section:
                variation = abs(thickness - section['adjacent_thickness'])
                if variation > self.max_wall_variation * nominal:
                    issues.append({
                        'severity': 'warning',
                        'category': 'wall_variation',
                        'description': f"Wall thickness variation {variation:.2f}mm between adjacent sections",
                        'location': location,
                        'recommendation': "Transition gradually to avoid flow issues and warping",
                        'cost_impact': 0.10
                    })
        
        return issues
    
    def _check_draft_angles(self, geometry) -> List:
        """Check for adequate draft angles on vertical walls"""
        
        issues = []
        
        # Identify vertical or near-vertical faces
        vertical_faces = self._identify_vertical_faces(geometry)
        
        for face in vertical_faces:
            draft_angle = face['draft_angle']
            depth = face['depth']
            
            # Deeper features need more draft
            required_draft = self.min_draft_angle + (depth / 100) * 0.5
            
            if draft_angle < required_draft:
                issues.append({
                    'severity': 'critical',
                    'category': 'draft_angle',
                    'description': f"Insufficient draft angle {draft_angle:.2f}° (required: {required_draft:.2f}°)",
                    'location': face['location'],
                    'recommendation': f"Add {required_draft - draft_angle:.2f}° draft to allow ejection",
                    'cost_impact': 0  # No draft = can't mold
                })
        
        return issues
    
    def estimate_molding_cost(
        self,
        geometry,
        material: str,
        production_volume: int
    ) -> Dict:
        """Estimate injection molding costs"""
        
        # Part analysis
        volume = self._calculate_volume(geometry)  # mm³
        surface_area = self._calculate_surface_area(geometry)  # mm²
        complexity = self._assess_complexity(geometry)
        
        # Mold cost estimation
        # Based on cavity count, complexity, and size
        part_weight = (volume / 1000) * self._get_material_density(material)  # grams
        
        # Mold cost (one-time)
        base_mold_cost = 5000  # USD for simple single-cavity mold
        
        # Adjustments
        complexity_multiplier = 1 + (complexity * 0.5)  # 50% increase per complexity point
        size_multiplier = 1 + (surface_area / 10000)    # Larger = more expensive
        
        # Determine cavity count based on volume
        if production_volume < 1000:
            cavities = 1
        elif production_volume < 10000:
            cavities = 2
        elif production_volume < 50000:
            cavities = 4
        else:
            cavities = 8
        
        cavity_multiplier = 1 + (cavities - 1) * 0.6  # Each additional cavity adds 60%
        
        mold_cost = base_mold_cost * complexity_multiplier * size_multiplier * cavity_multiplier
        
        # Per-part cost
        material_cost_per_kg = {
            'ABS': 3.50,
            'PC': 5.00,
            'PP': 2.50,
            'Nylon': 6.00,
            'PET': 3.00
        }
        
        material_price = material_cost_per_kg.get(material, 4.00)
        part_material_cost = (part_weight / 1000) * material_price
        
        # Cycle time estimation (seconds)
        max_wall_thickness = self._get_max_wall_thickness(geometry)
        cooling_time = max_wall_thickness**2 * 2  # Rough estimate
        injection_time = 2
        ejection_time = 3
        
        cycle_time = cooling_time + injection_time + ejection_time
        
        # Labor cost
        parts_per_hour = (3600 / cycle_time) * cavities
        machine_cost_per_hour = 40  # USD
        labor_cost_per_part = machine_cost_per_hour / parts_per_hour
        
        # Total per-part cost
        part_cost = part_material_cost + labor_cost_per_part
        
        # Amortize mold cost
        mold_cost_per_part = mold_cost / production_volume
        
        total_cost_per_part = part_cost + mold_cost_per_part
        
        return {
            'mold': {
                'total_usd': mold_cost,
                'cavities': cavities,
                'complexity': complexity,
                'lead_time_weeks': 6 + (complexity * 2)
            },
            'production': {
                'cycle_time_s': cycle_time,
                'parts_per_hour': parts_per_hour,
                'material_cost_per_part': part_material_cost,
                'labor_cost_per_part': labor_cost_per_part,
                'total_per_part': part_cost
            },
            'economics': {
                'mold_cost_amortized': mold_cost_per_part,
                'total_cost_per_part': total_cost_per_part,
                'total_project_cost': mold_cost + (part_cost * production_volume),
                'break_even_volume': int(mold_cost / part_cost) if part_cost > 0 else 0
            }
        }
```

#### 4. Sheet Metal

```python
# services/dfm/sheet_metal.py

class SheetMetalAnalyzer:
    """DFM analysis for sheet metal fabrication"""
    
    def __init__(self):
        self.min_bend_radius = 1.0     # mm, material dependent
        self.min_flange_length = 4.0   # mm
        self.min_hole_diameter = 1.0   # mm
        self.min_hole_to_edge = 2.0    # mm
        
    def analyze(self, geometry, material: str, thickness: float) -> List:
        """Run sheet metal DFM checks"""
        
        issues = []
        
        # Check 1: Bend radius vs thickness
        issues.extend(self._check_bend_radii(geometry, material, thickness))
        
        # Check 2: Minimum flange dimensions
        issues.extend(self._check_flange_dimensions(geometry))
        
        # Check 3: Hole sizes and placement
        issues.extend(self._check_holes(geometry, thickness))
        
        # Check 4: Bend relief requirements
        issues.extend(self._check_bend_relief(geometry))
        
        # Check 5: Flat pattern feasibility
        issues.extend(self._validate_unfoldability(geometry))
        
        # Check 6: Tab/slot tolerances
        issues.extend(self._check_tab_slots(geometry, thickness))
        
        return issues
    
    def _check_bend_radii(self, geometry, material: str, thickness: float) -> List:
        """Verify bend radii are appropriate for material and thickness"""
        
        issues = []
        
        # Material-specific minimum bend radius (as multiple of thickness)
        min_radius_factors = {
            'aluminum': 1.0,   # 1× thickness
            'steel': 1.5,      # 1.5× thickness
            'stainless': 2.0,  # 2× thickness
            'copper': 0.5      # 0.5× thickness
        }
        
        factor = min_radius_factors.get(material.lower(), 1.5)
        min_radius = thickness * factor
        
        bends = self._identify_bends(geometry)
        
        for bend in bends:
            radius = bend['radius']
            angle = bend['angle']
            
            if radius < min_radius:
                issues.append({
                    'severity': 'critical',
                    'category': 'bend_radius',
                    'description': f"Bend radius {radius:.2f}mm too small for {thickness}mm {material}",
                    'location': bend['location'],
                    'recommendation': f"Increase to minimum {min_radius:.2f}mm ({factor}× thickness)",
                    'cost_impact': 0  # Tight radius causes cracking
                })
            
            # Check for very sharp bends (>90°)
            if angle > 90 and radius < min_radius * 1.5:
                issues.append({
                    'severity': 'warning',
                    'category': 'sharp_bend',
                    'description': f"{angle}° bend requires larger radius for {material}",
                    'location': bend['location'],
                    'recommendation': f"Increase radius to {min_radius * 1.5:.2f}mm for sharp bends",
                    'cost_impact': 0.05
                })
        
        return issues
```

---

## Frontend Design

### UI Components

#### Main Analysis Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  DFM-Analyzer - Project: Drone_Frame_v3                    │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌────────────────────────────────┐  │
│  │  Upload CAD      │  │                                │  │
│  │  [Drop or Click] │  │   3D Model Preview             │  │
│  │                  │  │   [Interactive viewer]         │  │
│  │  Supported:      │  │                                │  │
│  │  • STEP          │  │   Rotate | Pan | Zoom          │  │
│  │  • STL           │  │                                │  │
│  │  • IGES          │  │   [Issue highlights toggle]    │  │
│  └──────────────────┘  └────────────────────────────────┘  │
│                                                             │
│  Manufacturing Process: [CNC Milling ▼]                    │
│  Material: [Aluminum 6061-T6 ▼]                            │
│  Quantity: [___100___] units                               │
│                                                             │
│  [Run Analysis]                                            │
├─────────────────────────────────────────────────────────────┤
│  Results Summary:                                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ⛔ 3 Critical Issues    ⚠️  7 Warnings                │  │
│  │ 💡 12 Suggestions       ✅ Overall Score: 7.2/10      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Issues List:                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ⛔ Critical                                           │  │
│  │ • Wall thickness 0.4mm below minimum (1.5mm)         │  │
│  │   Location: Bottom plate, Section A                  │  │
│  │   Impact: Part may deform during machining           │  │
│  │   → [Show in 3D] [Recommendation]                    │  │
│  │                                                       │  │
│  │ ⚠️  Warning                                           │  │
│  │ • Sharp internal corner requires R0.5mm fillet       │  │
│  │   Location: Pocket entrance                          │  │
│  │   Impact: +8% cost for tool change                   │  │
│  │   → [Auto-fix] [Show details]                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Cost Estimate:                                             │
│  Material: $15.20 | Labor: $42.50 | Total: $57.70/part    │
│  [View Breakdown] [Compare Processes]                      │
│                                                             │
│  [Generate Report] [Export Issues CSV] [Save Project]     │
└─────────────────────────────────────────────────────────────┘
```

#### Process Comparison Tool

```
┌─────────────────────────────────────────────────────────────┐
│  Manufacturing Process Comparison                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┬──────────────┬──────────────┐           │
│  │  CNC Milling │  3D Printing │  Injection   │           │
│  │              │    (FDM)     │   Molding    │           │
│  ├──────────────┼──────────────┼──────────────┤           │
│  │ Unit Cost    │ Unit Cost    │ Unit Cost    │           │
│  │ $57.70       │ $12.40       │ $8.25        │           │
│  │              │              │ (+ $8500 mold)│           │
│  ├──────────────┼──────────────┼──────────────┤           │
│  │ Lead Time    │ Lead Time    │ Lead Time    │           │
│  │ 3-5 days     │ 1-2 days     │ 6-8 weeks    │           │
│  ├──────────────┼──────────────┼──────────────┤           │
│  │ MOQ: 1       │ MOQ: 1       │ MOQ: 500     │           │
│  ├──────────────┼──────────────┼──────────────┤           │
│  │ ✅ Strength  │ ⚠️  Medium   │ ✅ Excellent │           │
│  │ ✅ Finish    │ ⚠️  Layered  │ ✅ Smooth    │           │
│  │ ⚠️  Cost @100│ ✅ Low cost  │ ⛔ High setup│           │
│  └──────────────┴──────────────┴──────────────┘           │
│                                                             │
│  Recommendation for 100 units:                              │
│  🏆 CNC Milling - Best for this quantity and requirements  │
│                                                             │
│  Break-even Analysis:                                       │
│  [Chart showing cost per part vs quantity]                 │
│  Injection molding becomes cheaper at 150+ units           │
└─────────────────────────────────────────────────────────────┘
```

---

## API Design

```http
# Authentication
POST   /api/auth/login
POST   /api/auth/register
POST   /api/auth/refresh

# Analysis
POST   /api/analysis/upload          # Upload CAD file
POST   /api/analysis/run              # Run DFM analysis
GET    /api/analysis/{id}             # Get analysis results
GET    /api/analysis/{id}/report      # Download PDF report

# Processes
GET    /api/processes                 # List supported processes
GET    /api/processes/{id}/rules      # Get DFM rules for process
POST   /api/processes/compare         # Compare multiple processes

# Materials
GET    /api/materials                 # List materials
GET    /api/materials/{id}            # Material properties

# Cost Estimation
POST   /api/cost/estimate             # Estimate manufacturing cost
POST   /api/cost/compare              # Compare cost across processes

# Projects
GET    /api/projects                  # List user projects
POST   /api/projects                  # Create project
GET    /api/projects/{id}             # Get project
PATCH  /api/projects/{id}             # Update project
DELETE /api/projects/{id}             # Delete project

# CAD Integrations
POST   /api/integrations/freecad      # FreeCAD plugin endpoint
POST   /api/integrations/fusion360    # Fusion 360 endpoint
POST   /api/integrations/solidworks   # SolidWorks endpoint
```

---

## Monetization

### Pricing

**Free**
- 10 analyses per month
- CNC and 3D printing only
- Basic reports
- Web interface only

**Pro ($49/month)**
- Unlimited analyses
- All processes
- Advanced reports (PDF with recommendations)
- Desktop app
- API access (1000 calls/month)
- CAD plugin integrations
- Priority support

**Enterprise (Custom)**
- Unlimited analyses
- Custom DFM rules
- White-label reports
- API (unlimited)
- On-premise deployment
- Custom integrations
- Training & support
- SLA guarantees

### Revenue Streams

1. **SaaS Subscriptions** ($10-50k MRR target)
2. **CAD Plugin Marketplace** (sell via CAD app stores)
3. **API Licensing** (other platforms integrate DFM)
4. **Consulting** (custom rule development)
5. **Training** (courses on DFM best practices)

---

## Go-to-Market

### Launch Strategy

**Phase 1: Engineers (Month 1-3)**
- Free tier launch
- Post to r/engineering, r/cad, r/3Dprinting
- YouTube tutorials
- Case studies

**Phase 2: CAD Integration (Month 4-6)**
- FreeCAD workbench
- Fusion 360 add-in
- Product Hunt launch

**Phase 3: B2B Sales (Month 7-12)**
- Target design consultancies
- Manufacturing companies
- Engineering firms
- Academic institutions

---

## Success Metrics

**Product**
- Analysis accuracy vs expert review (>85%)
- Analysis completion time (<60 seconds)
- False positive rate (<10%)

**User**
- MAU (target: 2000 in 6 months)
- Analyses per user (target: 8/month)
- Free to Pro conversion (target: 5%)

**Business**
- MRR (target: $10k in 12 months)
- Enterprise customers (target: 5-10)
- GitHub stars (target: 2000+)

---

This production-ready specification provides a comprehensive blueprint for building an industry-leading DFM analysis tool that serves individual engineers, design firms, and manufacturing companies with actionable insights to improve manufacturability and reduce costs.