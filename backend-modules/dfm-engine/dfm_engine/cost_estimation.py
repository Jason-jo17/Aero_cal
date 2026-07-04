"""
Cost/time estimation shared by all DFM analyzers. All estimates are driven by
real geometry (trimesh volume/surface-area/bounding-box/measured wall
thickness), not fabricated constants — but they are still first-pass
approximations (as combinedbuild.md's own spec describes them), not
quotation-grade numbers.
"""

from typing import Dict, Optional
import numpy as np

from . import geometry_analysis as ga

# g/cm^3
MATERIAL_DENSITY_G_CM3 = {
    "aluminum_6061": 2.70, "aluminum_7075": 2.81, "steel_1018": 7.87,
    "stainless_304": 8.00, "titanium_grade5": 4.43, "brass": 8.50,
    "copper": 8.96, "abs_plastic": 1.04, "pla": 1.24,
    "abs": 1.04, "pc": 1.20, "pp": 0.90, "nylon": 1.14, "pet": 1.38,
    "steel": 7.87,
}

# mm^3/min material removal rate for CNC
CNC_MRR_MM3_MIN = {
    "aluminum_6061": 50000, "aluminum_7075": 40000, "steel_1018": 25000,
    "stainless_304": 15000, "titanium_grade5": 8000, "brass": 60000,
    "copper": 55000, "abs_plastic": 80000,
}

# USD/kg raw material cost (rough, for estimation purposes only)
MATERIAL_PRICE_USD_KG = {
    "aluminum_6061": 4.5, "aluminum_7075": 7.0, "steel_1018": 1.8,
    "stainless_304": 3.5, "titanium_grade5": 35.0, "brass": 6.0,
    "copper": 8.5, "abs_plastic": 3.0, "pla": 20.0,
    "abs": 3.5, "pc": 5.0, "pp": 2.5, "nylon": 6.0, "pet": 3.0,
    "steel": 1.8,
}


def estimate_cnc_cost(mesh, material: str = "aluminum_6061") -> Dict:
    volume = float(mesh.volume)  # mm^3
    surface_area = float(mesh.area)  # mm^2
    stock_volume = float(np.prod(mesh.bounding_box.extents))
    removal_volume = max(stock_volume - volume, 0.0)

    mrr = CNC_MRR_MM3_MIN.get(material, 30000)
    roughing_time = (removal_volume * 1.3) / mrr if mrr > 0 else 0.0

    finishing_rate = 5000  # mm^2/min
    corners = ga.find_sharp_internal_corners(mesh)
    complexity = float(np.clip(1 + len(corners) / 20, 1.0, 3.0))
    finishing_time = (surface_area / finishing_rate) * complexity

    setup_time = 30.0
    num_tools = 1 + min(len(corners), 5)
    tool_change_time = num_tools * 2.0

    total_time = setup_time + roughing_time + finishing_time + tool_change_time

    density = MATERIAL_DENSITY_G_CM3.get(material, 2.7)
    price_per_kg = MATERIAL_PRICE_USD_KG.get(material, 4.5)
    material_weight_g = (stock_volume / 1000.0) * density
    material_cost = (material_weight_g / 1000.0) * price_per_kg

    machine_rate = 85.0  # USD/hr
    labor_cost = (total_time / 60.0) * machine_rate
    overhead = labor_cost * 0.15
    total_cost = material_cost + labor_cost + overhead

    return {
        "time_breakdown": {
            "setup_min": setup_time,
            "roughing_min": roughing_time,
            "finishing_min": finishing_time,
            "tool_changes_min": tool_change_time,
            "total_min": total_time,
        },
        "cost_breakdown": {
            "material_usd": material_cost,
            "labor_usd": labor_cost,
            "overhead_usd": overhead,
            "total_usd": total_cost,
        },
        "metrics": {
            "volume_mm3": volume,
            "surface_area_mm2": surface_area,
            "complexity_score": complexity,
            "num_tools": num_tools,
        },
    }


def estimate_fdm_cost(mesh, settings: Optional[Dict] = None) -> Dict:
    settings = settings or {}
    layer_height = settings.get("layer_height", 0.2)
    print_speed = settings.get("print_speed", 60)  # mm/s
    infill_percentage = settings.get("infill", 20)
    shell_thickness = settings.get("shell_thickness", 1.2)
    material = settings.get("material", "pla")

    part_volume = float(mesh.volume)
    surface_area = float(mesh.area)
    shell_volume = surface_area * shell_thickness
    infill_volume = max(part_volume - shell_volume, 0.0) * (infill_percentage / 100.0)
    total_material = shell_volume + infill_volume

    height_mm = float(mesh.bounding_box.extents[2])
    num_layers = max(height_mm / layer_height, 1.0)
    footprint_perimeter = 2 * (mesh.bounding_box.extents[0] + mesh.bounding_box.extents[1])
    perimeter_length = footprint_perimeter * num_layers
    extrusion_width = 0.4
    infill_length = infill_volume / (layer_height * extrusion_width) if layer_height > 0 else 0.0
    total_length = perimeter_length + infill_length

    print_time_s = (total_length / print_speed) if print_speed > 0 else 0.0
    layer_change_time = num_layers * 0.5
    travel_time = total_length * 0.1
    total_time_s = print_time_s + layer_change_time + travel_time
    total_time_h = total_time_s / 3600.0

    overhangs = ga.find_overhang_faces(mesh)
    support_volume = surface_area * 0.05 * len(overhangs) if overhangs else 0.0

    density = MATERIAL_DENSITY_G_CM3.get(material, 1.24)
    price_per_kg = MATERIAL_PRICE_USD_KG.get(material, 20.0)
    material_weight_g = (total_material / 1000.0) * density
    material_cost = (material_weight_g / 1000.0) * price_per_kg
    support_weight_g = (support_volume / 1000.0) * density
    support_cost = (support_weight_g / 1000.0) * price_per_kg

    machine_cost_per_hour = 5.0
    machine_cost = total_time_h * machine_cost_per_hour
    total_cost = material_cost + machine_cost + support_cost

    return {
        "time_breakdown": {
            "printing_hours": total_time_h,
            "num_layers": int(num_layers),
        },
        "cost_breakdown": {
            "material_usd": material_cost,
            "support_material_usd": support_cost,
            "machine_usd": machine_cost,
            "total_usd": total_cost,
        },
        "metrics": {
            "part_grams": material_weight_g,
            "support_grams": support_weight_g,
            "num_overhang_regions": len(overhangs),
        },
    }


def estimate_injection_molding_cost(mesh, material: str = "abs", production_volume: int = 1000) -> Dict:
    volume = float(mesh.volume)
    surface_area = float(mesh.area)

    density = MATERIAL_DENSITY_G_CM3.get(material, 1.04)
    price_per_kg = MATERIAL_PRICE_USD_KG.get(material, 3.5)
    part_weight_g = (volume / 1000.0) * density

    corners = ga.find_sharp_internal_corners(mesh)
    complexity = float(np.clip(len(corners) / 10, 0.0, 3.0))

    base_mold_cost = 5000.0
    complexity_multiplier = 1 + (complexity * 0.5)
    size_multiplier = 1 + (surface_area / 10000.0)

    if production_volume < 1000:
        cavities = 1
    elif production_volume < 10000:
        cavities = 2
    elif production_volume < 50000:
        cavities = 4
    else:
        cavities = 8
    cavity_multiplier = 1 + (cavities - 1) * 0.6

    mold_cost = base_mold_cost * complexity_multiplier * size_multiplier * cavity_multiplier

    part_material_cost = (part_weight_g / 1000.0) * price_per_kg

    thickness_samples = ga.compute_wall_thickness_samples(mesh, sample_count=500)
    max_wall_thickness = max((s["thickness"] for s in thickness_samples), default=2.0)
    cooling_time = max_wall_thickness**2 * 2
    injection_time = 2.0
    ejection_time = 3.0
    cycle_time = cooling_time + injection_time + ejection_time

    machine_cost_per_hour = 40.0
    parts_per_hour = (3600 / cycle_time) * cavities if cycle_time > 0 else 0
    labor_cost_per_part = machine_cost_per_hour / parts_per_hour if parts_per_hour > 0 else 0.0

    part_cost = part_material_cost + labor_cost_per_part
    mold_cost_per_part = mold_cost / production_volume if production_volume > 0 else mold_cost
    total_cost_per_part = part_cost + mold_cost_per_part

    return {
        "time_breakdown": {
            "cycle_time_s": cycle_time,
            "lead_time_weeks": 6 + (complexity * 2),
        },
        "cost_breakdown": {
            "mold_usd": mold_cost,
            "material_usd_per_part": part_material_cost,
            "labor_usd_per_part": labor_cost_per_part,
            "mold_amortized_usd_per_part": mold_cost_per_part,
            "total_usd_per_part": total_cost_per_part,
        },
        "metrics": {
            "cavities": cavities,
            "complexity_score": complexity,
            "parts_per_hour": parts_per_hour,
            "break_even_volume": int(mold_cost / part_cost) if part_cost > 0 else 0,
        },
    }


def estimate_sheet_metal_cost(mesh, material: str = "steel", thickness_mm: float = 1.0) -> Dict:
    """No cost model exists in combinedbuild.md for sheet metal; this is an
    original first-pass estimate: material cost by weight + a cutting-length
    proxy (bounding-box perimeter, since true flat-pattern unrolling isn't
    implemented) + a per-bend cost from real detected sharp edges."""
    volume = float(mesh.volume)
    density = MATERIAL_DENSITY_G_CM3.get(material, 7.87)
    price_per_kg = MATERIAL_PRICE_USD_KG.get(material, 1.8)
    weight_g = (volume / 1000.0) * density
    material_cost = (weight_g / 1000.0) * price_per_kg

    cutting_length_mm = 2 * (mesh.bounding_box.extents[0] + mesh.bounding_box.extents[1])
    cutting_rate_usd_per_m = 0.5
    cutting_cost = (cutting_length_mm / 1000.0) * cutting_rate_usd_per_m

    bends = ga.find_sharp_internal_corners(mesh, angle_threshold_deg=20.0)
    bend_cost_each = 2.0
    bending_cost = len(bends) * bend_cost_each

    total_cost = material_cost + cutting_cost + bending_cost

    return {
        "time_breakdown": {},
        "cost_breakdown": {
            "material_usd": material_cost,
            "cutting_usd": cutting_cost,
            "bending_usd": bending_cost,
            "total_usd": total_cost,
        },
        "metrics": {
            "weight_g": weight_g,
            "estimated_bend_count": len(bends),
            "cutting_length_mm": cutting_length_mm,
        },
    }
