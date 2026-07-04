import json
import os
import tempfile
import shutil
from contextlib import contextmanager
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
import trimesh

from dfm_engine.cnc_milling import CNCMillingAnalyzer
from dfm_engine.additive_manufacturing import FDMAnalyzer
from dfm_engine.injection_molding import InjectionMoldingAnalyzer
from dfm_engine.sheet_metal import SheetMetalAnalyzer
from dfm_engine.cost_estimation import (
    estimate_cnc_cost,
    estimate_fdm_cost,
    estimate_injection_molding_cost,
    estimate_sheet_metal_cost,
)

router = APIRouter(prefix="/dfm", tags=["DFM Analysis"])


@contextmanager
def _load_mesh_from_upload(file: UploadFile):
    """Shared upload -> trimesh.load -> cleanup helper (previously duplicated
    verbatim across all four analyze-* endpoints)."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".stl") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        geometry = trimesh.load(tmp_path)
        yield geometry
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _parse_tolerances(tolerances_json: Optional[str]):
    if not tolerances_json:
        return None
    try:
        return json.loads(tolerances_json)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="tolerances_json must be valid JSON")


@router.post("/analyze-cnc")
async def analyze_cnc(
    file: UploadFile = File(...),
    material: str = Form("aluminum_6061"),
    include_cost: bool = Form(True),
    tolerances_json: Optional[str] = Form(None),
):
    analyzer = CNCMillingAnalyzer()
    tolerances = _parse_tolerances(tolerances_json)
    try:
        with _load_mesh_from_upload(file) as geometry:
            issues = analyzer.analyze(geometry, toleranced_features=tolerances)
            cost_estimate = estimate_cnc_cost(geometry, material) if include_cost else None
        return {"filename": file.filename, "issues": issues, "cost_estimate": cost_estimate}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze-fdm")
async def analyze_fdm(
    file: UploadFile = File(...),
    material: str = Form("pla"),
    include_cost: bool = Form(True),
):
    analyzer = FDMAnalyzer()
    try:
        with _load_mesh_from_upload(file) as geometry:
            issues = analyzer.analyze(geometry)
            cost_estimate = estimate_fdm_cost(geometry, {"material": material}) if include_cost else None
        return {"filename": file.filename, "issues": issues, "cost_estimate": cost_estimate}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze-injection")
async def analyze_injection(
    file: UploadFile = File(...),
    material: str = Form("abs"),
    production_volume: int = Form(1000),
    include_cost: bool = Form(True),
):
    analyzer = InjectionMoldingAnalyzer()
    try:
        with _load_mesh_from_upload(file) as geometry:
            issues = analyzer.analyze(geometry)
            cost_estimate = (
                estimate_injection_molding_cost(geometry, material, production_volume) if include_cost else None
            )
        return {"filename": file.filename, "issues": issues, "cost_estimate": cost_estimate}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/analyze-sheet-metal")
async def analyze_sheet_metal(
    file: UploadFile = File(...),
    material: str = Form("steel"),
    thickness_mm: float = Form(1.0),
    include_cost: bool = Form(True),
):
    analyzer = SheetMetalAnalyzer()
    try:
        with _load_mesh_from_upload(file) as geometry:
            issues = analyzer.analyze(geometry)
            cost_estimate = estimate_sheet_metal_cost(geometry, material, thickness_mm) if include_cost else None
        return {"filename": file.filename, "issues": issues, "cost_estimate": cost_estimate}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
