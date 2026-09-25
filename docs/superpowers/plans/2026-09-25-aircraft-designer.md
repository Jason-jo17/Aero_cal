# Fixed-Wing Aircraft Configurator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an "Aircraft Designer" tab to `aerocalc-web` that lets a user parametrically configure a fixed-wing aircraft (conventional/flying-wing/canard/T-tail/V-tail) and see a blueprint (2D three-view + 3D wireframe) plus a full static stability analysis (longitudinal/lateral/directional).

**Architecture:** Backend-authoritative (Approach A from the design doc). New `aero_engine/aircraft/` package computes geometry and stability from a Pydantic `AircraftConfig`; one new FastAPI endpoint (`POST /aircraft/design`) returns everything in one payload; the frontend is a pure renderer (SVG three-view + `react-three-fiber` wireframe + a stats panel) driven by that response, following the existing "fill form → Calculate → render" pattern used by every other calculator in this app.

**Tech Stack:** Python 3.11 / FastAPI / Pydantic v2 / pytest (backend), Next.js 16 / React 19 / TypeScript / `@react-three/fiber` + `@react-three/drei` / `recharts` (frontend, all already installed).

**Spec:** `docs/superpowers/specs/2026-09-25-aircraft-designer-design.md`

## Global Constraints

- Coordinate frame for all geometry: origin at the nose tip, **x** aft, **y** starboard(+)/port(-), **z** up.
- Incompressible flow only (Mach = 0); no altitude/atmosphere model beyond sea-level standard density (`rho = 1.225 kg/m^3`) for the one place that needs it (lateral trim-CL estimate).
- Static analysis only — no dynamic modes, no persistence, no propulsion integration in v1.
- Single vertical tail only (no twin-tail configs).
- The existing `/aero/wing-planform` endpoint's request/response schema must not change — `calculate_wing_planform` stays a thin wrapper around the new shared helper.
- `aero_engine.aircraft.models.AircraftConfig` uses Pydantic `BaseModel` directly (not the flat-dataclass pattern `MultirotorConfig` uses) because the nested, conditionally-optional surfaces need FastAPI's native nested validation; `pydantic` is added as an explicit `aero-engine` dependency to support this.
- New `aero_engine.aircraft.*` submodules are imported directly by the router (`from aero_engine.aircraft.models import AircraftConfig`), matching how every existing router in `aero.py` imports submodules directly rather than through `aero_engine/__init__.py`'s re-exports — `aero_engine/__init__.py` is intentionally left unmodified.
- No new frontend test framework is introduced — `aerocalc-web` has none today; verification is `tsc --noEmit` + `eslint --max-warnings 0` + manual dev-server check, matching the rest of the repo.
- CSS: the new "Aircraft Designer" tab's form/stats panels follow the existing light-card convention (`#3b82f6` blue accent, `#f8fafc` card background — see `WingPlanformDesigner.module.css`); only `BlueprintView` and `Blueprint3D` deliberately break from this into a dark "drafting table" look (per the design spec), scoped entirely to their own CSS modules.

## Review Focus

- **Zero/negative surface dimensions** (e.g. `span: 0`) — a student fat-fingering an input should get a clean `422` from Pydantic field validation, not a `500` from a downstream division by zero. → Task 2 (`Field(gt=0)` constraints) + Task 13 (end-to-end 422 test).
- **Zero or negative cruise speed** — would divide by zero in the lateral stability trim-CL calculation (`0.5 * rho * v^2 * S`). → Task 2 (`Field(gt=0)` on `cruise_speed_ms`).
- **`configuration_type` doesn't match the surfaces actually provided** (e.g. `"v_tail"` config that still includes a `horizontal_tail`, or `"t_tail"` missing its `vertical_tail`) — must be rejected before any calculation runs, with a message that says which field is wrong. → Task 2 (cross-field validator, multiple cases tested).
- **CG positioned outside the physical fuselage** (e.g. `cg_x_position` beyond `fuselage.length`) — not fatal (the math still computes a number), but a student should see an explicit warning rather than silently getting a plausible-looking result for a nonsensical aircraft. → Task 12 (`analyze_stability` warning).
- **Canard's reused downwash-correction term** — the unified neutral-point formula generalizes to canards via a signed moment arm, but the `(1 - deps_dalpha)` term is derived for an aft tail sitting in the wing's downwash, which is physically backward for a forward canard surface. This must not be silently more precise-looking than it is. → Task 12 (explicit warning on every `canard` config, tested).

---

## Task 1: Extract shared planform helper; set up pytest for aero-engine

**Files:**
- Modify: `backend-modules/aero-engine/aero_engine/wing_planform.py`
- Modify: `backend-modules/aero-engine/pyproject.toml`
- Create: `backend-modules/aero-engine/tests/__init__.py`
- Create: `backend-modules/aero-engine/tests/test_wing_planform.py`

**Interfaces:**
- Produces: `calculate_surface_planform(span: float, root_chord: float, tip_chord: float, sweep_angle_deg: float) -> dict` with keys `span, root_chord, tip_chord, sweep_angle_deg, taper_ratio, area, aspect_ratio, mac, y_mac, x_mac_le` — this is the shared helper every later geometry/stability task calls for wing, tail, canard, and V-tail planform math.
- `calculate_wing_planform(...)` keeps its existing signature and return shape (regression-tested here), now implemented as a one-line wrapper.

- [ ] **Step 1: Add `pytest` as a dev dependency and create the tests package**

Edit `backend-modules/aero-engine/pyproject.toml`:

```toml
[project]
name = "aero-engine"
version = "0.1.0"
description = "AeroCalc-Suite aerodynamics/propulsion/drone calculation engine"
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.26",
    "scipy>=1.11",
    "pydantic>=2.0",
]

[project.optional-dependencies]
test = ["pytest>=8"]

[tool.setuptools.packages.find]
include = ["aero_engine*"]
```

Create `backend-modules/aero-engine/tests/__init__.py` (empty file).

- [ ] **Step 2: Write the failing regression test**

Create `backend-modules/aero-engine/tests/test_wing_planform.py`:

```python
import pytest
from aero_engine.wing_planform import calculate_wing_planform, calculate_surface_planform


def test_calculate_wing_planform_matches_known_values():
    # These are the exact values already exercised by the repo's root
    # test_api.py smoke test (span=10, root=2, tip=1, sweep=15deg).
    result = calculate_wing_planform(10.0, 2.0, 1.0, 15.0)
    assert result["area"] == pytest.approx(15.0)
    assert result["taper_ratio"] == pytest.approx(0.5)
    assert result["aspect_ratio"] == pytest.approx(6.6667, abs=1e-3)


def test_calculate_wing_planform_wraps_shared_helper():
    wing_result = calculate_wing_planform(8.0, 1.5, 0.9, 10.0)
    surface_result = calculate_surface_planform(8.0, 1.5, 0.9, 10.0)
    assert wing_result == surface_result
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_wing_planform.py -v`
Expected: FAIL (or collection error) — `calculate_surface_planform` does not exist yet, and `pytest` may not be installed in `.venv` yet (install it first: `../../.venv/Scripts/python.exe -m pip install pytest`).

- [ ] **Step 4: Extract the shared helper**

Replace the full contents of `backend-modules/aero-engine/aero_engine/wing_planform.py`:

```python
import math


def calculate_surface_planform(span: float, root_chord: float, tip_chord: float, sweep_angle_deg: float) -> dict:
    """
    Calculate essential planform parameters (area, aspect ratio, taper
    ratio, MAC) for a single lifting surface. Shared by the wing-planform
    calculator and the aircraft designer's tail/canard/V-tail surfaces.
    """
    sweep_rad = math.radians(sweep_angle_deg)

    taper_ratio = tip_chord / root_chord if root_chord > 0 else 0

    area = (root_chord + tip_chord) / 2 * span

    aspect_ratio = (span ** 2) / area if area > 0 else 0

    if root_chord > 0:
        mac = (2 / 3) * root_chord * ((1 + taper_ratio + taper_ratio ** 2) / (1 + taper_ratio))
    else:
        mac = 0

    y_mac = (span / 6) * ((1 + 2 * taper_ratio) / (1 + taper_ratio))
    x_mac_le = y_mac * math.tan(sweep_rad)

    return {
        "span": span,
        "root_chord": root_chord,
        "tip_chord": tip_chord,
        "sweep_angle_deg": sweep_angle_deg,
        "taper_ratio": taper_ratio,
        "area": area,
        "aspect_ratio": aspect_ratio,
        "mac": mac,
        "y_mac": y_mac,
        "x_mac_le": x_mac_le,
    }


def calculate_wing_planform(span: float, root_chord: float, tip_chord: float, sweep_angle_deg: float):
    """
    Calculate essential wing planform parameters. Thin wrapper around
    calculate_surface_planform() kept for backward compatibility with the
    existing /aero/wing-planform endpoint.
    """
    return calculate_surface_planform(span, root_chord, tip_chord, sweep_angle_deg)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_wing_planform.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Run the existing root smoke test to confirm nothing broke**

Run: `cd D:/Downloads2/aerocalcdfm && ./.venv/Scripts/python.exe test_api.py`
Expected: All four `[OK]` lines print exactly as before, including `Wing Planform calculated: 15.0 m2 area`.

- [ ] **Step 7: Commit**

```bash
git add backend-modules/aero-engine/pyproject.toml backend-modules/aero-engine/tests/__init__.py backend-modules/aero-engine/tests/test_wing_planform.py backend-modules/aero-engine/aero_engine/wing_planform.py
git commit -m "refactor: extract calculate_surface_planform shared helper, add pytest to aero-engine"
```

---

## Task 2: Aircraft config models

**Files:**
- Create: `backend-modules/aero-engine/aero_engine/aircraft/__init__.py`
- Create: `backend-modules/aero-engine/aero_engine/aircraft/models.py`
- Create: `backend-modules/aero-engine/tests/test_models.py`
- Create: `backend-modules/aero-engine/tests/conftest.py`

**Interfaces:**
- Consumes: nothing (leaf module, only depends on `pydantic`).
- Produces: `Surface`, `VerticalTail`, `VTail`, `Fuselage`, `MassProperties`, `AircraftConfig` — every later task (geometry, stability, router, frontend types) is built against these exact field names.
- Produces (test fixtures other tasks reuse): `conftest.py`'s `make_conventional_config`, `make_flying_wing_config`, `make_canard_config`, `make_v_tail_config` — imported directly by name in later test files (pytest auto-discovers `conftest.py` but these are plain functions, not fixtures, so later tests `from conftest import make_conventional_config` — see Task 9 for usage).

- [ ] **Step 1: Create the package**

Create `backend-modules/aero-engine/aero_engine/aircraft/__init__.py` (empty file).

- [ ] **Step 2: Write the failing tests**

Create `backend-modules/aero-engine/tests/test_models.py`:

```python
import pytest
from pydantic import ValidationError

from aero_engine.aircraft.models import (
    AircraftConfig, Surface, VerticalTail, VTail, Fuselage, MassProperties,
)


def _base_kwargs(**overrides):
    kwargs = dict(
        configuration_type="conventional",
        wing=Surface(span=11.0, root_chord=1.6, tip_chord=1.6, x_position=2.0),
        horizontal_tail=Surface(span=3.4, root_chord=0.9, tip_chord=0.6, x_position=6.5),
        vertical_tail=VerticalTail(height=1.5, root_chord=1.0, tip_chord=0.5, x_position=6.8),
        fuselage=Fuselage(length=8.0, max_width=1.2, max_height=1.4, nose_length=1.5, tail_length=2.0),
        mass=MassProperties(mass_kg=1000.0, cg_x_position=2.5, cruise_speed_ms=60.0),
    )
    kwargs.update(overrides)
    return kwargs


def test_valid_conventional_config_parses():
    config = AircraftConfig(**_base_kwargs())
    assert config.configuration_type == "conventional"
    assert config.horizontal_tail is not None
    assert config.canard is None


def test_v_tail_config_with_horizontal_tail_is_rejected():
    with pytest.raises(ValidationError):
        AircraftConfig(**_base_kwargs(
            configuration_type="v_tail",
            v_tail=VTail(span=2.5, root_chord=0.9, tip_chord=0.5, dihedral_v_deg=40.0, x_position=6.7),
        ))


def test_t_tail_config_missing_vertical_tail_is_rejected():
    kwargs = _base_kwargs(configuration_type="t_tail")
    kwargs["vertical_tail"] = None
    with pytest.raises(ValidationError):
        AircraftConfig(**kwargs)


def test_flying_wing_config_with_horizontal_tail_is_rejected():
    kwargs = _base_kwargs(configuration_type="flying_wing")
    with pytest.raises(ValidationError):
        AircraftConfig(**kwargs)


def test_canard_config_with_horizontal_tail_is_rejected():
    kwargs = _base_kwargs(
        configuration_type="canard",
        canard=Surface(span=2.0, root_chord=0.6, tip_chord=0.4, x_position=0.3),
    )
    with pytest.raises(ValidationError):
        AircraftConfig(**kwargs)


def test_zero_span_wing_is_rejected():
    with pytest.raises(ValidationError):
        Surface(span=0, root_chord=1.6, tip_chord=1.6, x_position=2.0)


def test_zero_cruise_speed_is_rejected():
    with pytest.raises(ValidationError):
        MassProperties(mass_kg=1000.0, cg_x_position=2.5, cruise_speed_ms=0)


def test_fuselage_taper_sections_longer_than_fuselage_is_rejected():
    with pytest.raises(ValidationError):
        Fuselage(length=3.0, max_width=1.0, max_height=1.0, nose_length=2.0, tail_length=2.0)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_models.py -v`
Expected: FAIL/ERROR — `aero_engine.aircraft.models` does not exist yet.

- [ ] **Step 4: Implement the models**

Create `backend-modules/aero-engine/aero_engine/aircraft/models.py`:

```python
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class Surface(BaseModel):
    """A single lifting surface (wing, horizontal tail, or canard)."""
    span: float = Field(gt=0)
    root_chord: float = Field(gt=0)
    tip_chord: float = Field(gt=0)
    sweep_deg: float = 0.0
    dihedral_deg: float = 0.0
    twist_deg: float = 0.0
    airfoil: str = "0012"  # NACA 4-digit; reference/display only, not used in v1 stability math
    x_position: float = Field(ge=0)
    z_position: float = 0.0
    mount: Literal["high", "mid", "low"] = "mid"


class VerticalTail(BaseModel):
    """A single (unmirrored) vertical fin."""
    height: float = Field(gt=0)
    root_chord: float = Field(gt=0)
    tip_chord: float = Field(gt=0)
    sweep_deg: float = 0.0
    airfoil: str = "0012"
    x_position: float = Field(ge=0)
    z_position: float = 0.0


class VTail(BaseModel):
    """A V-tail: full span of both panels combined, plus their shared dihedral angle."""
    span: float = Field(gt=0)
    root_chord: float = Field(gt=0)
    tip_chord: float = Field(gt=0)
    dihedral_v_deg: float = Field(ge=0, le=90)
    sweep_deg: float = 0.0
    airfoil: str = "0012"
    x_position: float = Field(ge=0)
    z_position: float = 0.0


class Fuselage(BaseModel):
    length: float = Field(gt=0)
    max_width: float = Field(gt=0)
    max_height: float = Field(gt=0)
    nose_length: float = Field(ge=0)
    tail_length: float = Field(ge=0)

    @model_validator(mode="after")
    def check_taper_sections_fit(self) -> "Fuselage":
        if self.nose_length + self.tail_length >= self.length:
            raise ValueError(
                "nose_length + tail_length must be less than the fuselage length"
            )
        return self


class MassProperties(BaseModel):
    mass_kg: float = Field(gt=0)
    cg_x_position: float = Field(ge=0)
    # Used only to estimate trim CL for the lateral (Cl-beta) sweep term.
    # Sea-level standard density (rho=1.225 kg/m^3) is assumed; there is no
    # altitude/atmosphere model in v1.
    cruise_speed_ms: float = Field(gt=0)


class AircraftConfig(BaseModel):
    configuration_type: Literal["conventional", "flying_wing", "canard", "t_tail", "v_tail"]
    wing: Surface
    horizontal_tail: Optional[Surface] = None
    vertical_tail: Optional[VerticalTail] = None
    canard: Optional[Surface] = None
    v_tail: Optional[VTail] = None
    fuselage: Fuselage
    mass: MassProperties

    @model_validator(mode="after")
    def check_surfaces_match_configuration_type(self) -> "AircraftConfig":
        t = self.configuration_type
        errors: list[str] = []

        def require(name: str, present: bool):
            if not present:
                errors.append(f"{t} configuration requires '{name}'")

        def forbid(name: str, present: bool):
            if present:
                errors.append(f"{t} configuration must not include '{name}'")

        if t in ("conventional", "t_tail"):
            require("horizontal_tail", self.horizontal_tail is not None)
            require("vertical_tail", self.vertical_tail is not None)
            forbid("canard", self.canard is not None)
            forbid("v_tail", self.v_tail is not None)
        elif t == "canard":
            require("canard", self.canard is not None)
            require("vertical_tail", self.vertical_tail is not None)
            forbid("horizontal_tail", self.horizontal_tail is not None)
            forbid("v_tail", self.v_tail is not None)
        elif t == "v_tail":
            require("v_tail", self.v_tail is not None)
            forbid("horizontal_tail", self.horizontal_tail is not None)
            forbid("vertical_tail", self.vertical_tail is not None)
            forbid("canard", self.canard is not None)
        elif t == "flying_wing":
            forbid("horizontal_tail", self.horizontal_tail is not None)
            forbid("vertical_tail", self.vertical_tail is not None)
            forbid("canard", self.canard is not None)
            forbid("v_tail", self.v_tail is not None)

        if errors:
            raise ValueError("; ".join(errors))
        return self
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_models.py -v`
Expected: PASS (8 passed)

- [ ] **Step 6: Create the shared test fixtures used by every later backend task**

Create `backend-modules/aero-engine/tests/conftest.py`:

```python
from aero_engine.aircraft.models import (
    AircraftConfig, Surface, VerticalTail, VTail, Fuselage, MassProperties,
)


def make_fuselage(**overrides) -> Fuselage:
    defaults = dict(length=8.0, max_width=1.2, max_height=1.4, nose_length=1.5, tail_length=2.0)
    defaults.update(overrides)
    return Fuselage(**defaults)


def make_mass(**overrides) -> MassProperties:
    defaults = dict(mass_kg=1000.0, cg_x_position=2.56, cruise_speed_ms=60.0)
    defaults.update(overrides)
    return MassProperties(**defaults)


def make_conventional_config(wing_overrides=None, **mass_overrides) -> AircraftConfig:
    """
    Cessna-172-like proportions: wing AR ~6.9, tail volume coefficient
    ~0.14, giving a static margin in the 5-15% MAC range at the default
    CG (see docs/superpowers/specs/2026-09-25-aircraft-designer-design.md
    Task 9 derivation).
    """
    wing_kwargs = dict(span=11.0, root_chord=1.6, tip_chord=1.6, sweep_deg=0.0,
                        dihedral_deg=5.0, x_position=2.0)
    if wing_overrides:
        wing_kwargs.update(wing_overrides)
    return AircraftConfig(
        configuration_type="conventional",
        wing=Surface(**wing_kwargs),
        horizontal_tail=Surface(span=3.4, root_chord=0.9, tip_chord=0.6,
                                 sweep_deg=5.0, x_position=6.5, z_position=0.9),
        vertical_tail=VerticalTail(height=1.5, root_chord=1.0, tip_chord=0.5,
                                    sweep_deg=15.0, x_position=6.8, z_position=0.3),
        fuselage=make_fuselage(),
        mass=make_mass(**mass_overrides),
    )


def make_flying_wing_config(**mass_overrides) -> AircraftConfig:
    defaults = dict(cg_x_position=2.4)
    defaults.update(mass_overrides)
    return AircraftConfig(
        configuration_type="flying_wing",
        wing=Surface(span=11.0, root_chord=1.6, tip_chord=1.6, sweep_deg=25.0,
                     dihedral_deg=3.0, x_position=2.0),
        fuselage=make_fuselage(),
        mass=make_mass(**defaults),
    )


def make_canard_config(**mass_overrides) -> AircraftConfig:
    defaults = dict(cg_x_position=4.5)
    defaults.update(mass_overrides)
    return AircraftConfig(
        configuration_type="canard",
        wing=Surface(span=8.0, root_chord=1.2, tip_chord=1.2, sweep_deg=0.0, x_position=4.0),
        canard=Surface(span=2.0, root_chord=0.6, tip_chord=0.4, sweep_deg=0.0, x_position=0.3),
        vertical_tail=VerticalTail(height=1.0, root_chord=0.7, tip_chord=0.4,
                                    sweep_deg=10.0, x_position=6.5),
        fuselage=make_fuselage(length=7.0, max_width=1.0, max_height=1.2, nose_length=1.0, tail_length=1.5),
        mass=make_mass(**defaults),
    )


def make_v_tail_config(**mass_overrides) -> AircraftConfig:
    return AircraftConfig(
        configuration_type="v_tail",
        wing=Surface(span=11.0, root_chord=1.6, tip_chord=1.6, sweep_deg=0.0,
                     dihedral_deg=5.0, x_position=2.0),
        v_tail=VTail(span=2.5, root_chord=0.9, tip_chord=0.5, dihedral_v_deg=40.0,
                     sweep_deg=10.0, x_position=6.7),
        fuselage=make_fuselage(),
        mass=make_mass(**mass_overrides),
    )
```

- [ ] **Step 7: Commit**

```bash
git add backend-modules/aero-engine/aero_engine/aircraft/__init__.py backend-modules/aero-engine/aero_engine/aircraft/models.py backend-modules/aero-engine/tests/test_models.py backend-modules/aero-engine/tests/conftest.py
git commit -m "feat: add AircraftConfig models with configuration-type validation"
```

---

## Task 3: Mirrored lifting-surface geometry

**Files:**
- Create: `backend-modules/aero-engine/aero_engine/aircraft/geometry.py`
- Create: `backend-modules/aero-engine/tests/test_geometry.py`

**Interfaces:**
- Consumes: nothing (pure function, plain floats in).
- Produces: `generate_surface_geometry(span, root_chord, tip_chord, sweep_deg, dihedral_deg, x_position, z_position=0.0) -> dict` with keys `top_view, front_view, side_view, vertices, edges` — used by Task 6 for wing/horizontal-tail/canard/V-tail.

- [ ] **Step 1: Write the failing test**

Create `backend-modules/aero-engine/tests/test_geometry.py`:

```python
import pytest
from aero_engine.aircraft.geometry import generate_surface_geometry


def test_generate_surface_geometry_symmetry_sweep_dihedral():
    geom = generate_surface_geometry(
        span=10.0, root_chord=2.0, tip_chord=1.0,
        sweep_deg=30.0, dihedral_deg=10.0,
        x_position=5.0, z_position=0.5,
    )

    # vertices order: [root_le, tip_le_pos, tip_te_pos, root_te, tip_le_neg, tip_te_neg]
    root_le, tip_le_pos, tip_te_pos, root_te, tip_le_neg, tip_te_neg = geom["vertices"]

    assert root_le == pytest.approx([5.0, 0.0, 0.5])
    assert root_te == pytest.approx([7.0, 0.0, 0.5])
    # tip x offset = half_span * tan(sweep); tip z offset = half_span * tan(dihedral)
    assert tip_le_pos == pytest.approx([7.8868, 5.0, 1.3816], abs=1e-3)
    assert tip_te_pos == pytest.approx([8.8868, 5.0, 1.3816], abs=1e-3)

    # Mirror symmetry: the negative-y tip matches the positive-y tip in x
    # and z, with only y negated.
    assert tip_le_neg[0] == pytest.approx(tip_le_pos[0])
    assert tip_le_neg[2] == pytest.approx(tip_le_pos[2])
    assert tip_le_neg[1] == pytest.approx(-tip_le_pos[1])

    assert len(geom["vertices"]) == 6
    assert len(geom["edges"]) == 7
    assert geom["top_view"][0] == pytest.approx([5.0, 0.0])


def test_generate_surface_geometry_no_sweep_no_dihedral_is_flat_rectangle():
    geom = generate_surface_geometry(
        span=4.0, root_chord=1.0, tip_chord=1.0,
        sweep_deg=0.0, dihedral_deg=0.0,
        x_position=0.0, z_position=0.0,
    )
    for v in geom["vertices"]:
        assert v[2] == pytest.approx(0.0)  # no dihedral -> flat in z
    xs = [v[0] for v in geom["vertices"]]
    assert min(xs) == pytest.approx(0.0)
    assert max(xs) == pytest.approx(1.0)  # no sweep -> tip LE stays above root LE
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_geometry.py -v`
Expected: FAIL/ERROR — `aero_engine.aircraft.geometry` does not exist yet.

- [ ] **Step 3: Implement `generate_surface_geometry`**

Create `backend-modules/aero-engine/aero_engine/aircraft/geometry.py`:

```python
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
    tip_z_offset = half_span * math.tan(dihedral_rad)

    root_le = (x_position, 0.0, z_position)
    root_te = (x_position + root_chord, 0.0, z_position)

    def tip_corners(sign: int):
        y = sign * half_span
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_geometry.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend-modules/aero-engine/aero_engine/aircraft/geometry.py backend-modules/aero-engine/tests/test_geometry.py
git commit -m "feat: add mirrored lifting-surface geometry generator"
```

---

## Task 4: Single-fin vertical tail geometry

**Files:**
- Modify: `backend-modules/aero-engine/aero_engine/aircraft/geometry.py`
- Modify: `backend-modules/aero-engine/tests/test_geometry.py`

**Interfaces:**
- Produces: `generate_vertical_surface_geometry(height, root_chord, tip_chord, sweep_deg, x_position, z_position=0.0) -> dict` (same key shape as Task 3, but unmirrored — a single fin standing up from `z_position` to `z_position + height`). Used by Task 6 for the conventional/T-tail/canard vertical tail.

- [ ] **Step 1: Write the failing test**

Append to `backend-modules/aero-engine/tests/test_geometry.py`:

```python
import math
from aero_engine.aircraft.geometry import generate_vertical_surface_geometry


def test_generate_vertical_surface_geometry_single_unmirrored_fin():
    geom = generate_vertical_surface_geometry(
        height=1.5, root_chord=1.0, tip_chord=0.5, sweep_deg=15.0,
        x_position=6.8, z_position=0.3,
    )
    root_le, tip_le, tip_te, root_te = geom["vertices"]

    assert root_le == pytest.approx([6.8, 0.0, 0.3])
    assert root_te == pytest.approx([7.8, 0.0, 0.3])

    expected_tip_le_x = 6.8 + 1.5 * math.tan(math.radians(15.0))
    assert tip_le == pytest.approx([expected_tip_le_x, 0.0, 1.8], abs=1e-6)

    assert len(geom["vertices"]) == 4
    assert len(geom["edges"]) == 4
    assert all(v[1] == 0.0 for v in geom["vertices"])  # unmirrored: y stays 0
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_geometry.py -v`
Expected: FAIL — `generate_vertical_surface_geometry` is not defined.

- [ ] **Step 3: Implement `generate_vertical_surface_geometry`**

Append to `backend-modules/aero-engine/aero_engine/aircraft/geometry.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_geometry.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend-modules/aero-engine/aero_engine/aircraft/geometry.py backend-modules/aero-engine/tests/test_geometry.py
git commit -m "feat: add single-fin vertical tail geometry generator"
```

---

## Task 5: Fuselage outline geometry

**Files:**
- Modify: `backend-modules/aero-engine/aero_engine/aircraft/geometry.py`
- Modify: `backend-modules/aero-engine/tests/test_geometry.py`

**Interfaces:**
- Produces: `generate_fuselage_geometry(length, max_width, max_height, nose_length, tail_length) -> dict` (same key shape, `vertices`/`edges` form a simple nose-mid-tail wireframe). Visual only — never consumed by any stability calculation. Used by Task 6.

- [ ] **Step 1: Write the failing test**

Append to `backend-modules/aero-engine/tests/test_geometry.py`:

```python
from aero_engine.aircraft.geometry import generate_fuselage_geometry


def test_generate_fuselage_geometry_outline():
    geom = generate_fuselage_geometry(
        length=8.0, max_width=1.2, max_height=1.4, nose_length=1.5, tail_length=2.0,
    )
    assert geom["side_view"][1] == pytest.approx([1.5, 0.7])
    assert geom["top_view"][1] == pytest.approx([1.5, 0.6])
    assert geom["vertices"][0] == pytest.approx([0.0, 0.0, 0.0])   # nose tip
    assert geom["vertices"][-1] == pytest.approx([8.0, 0.0, 0.0])  # tail tip
    assert len(geom["front_view"]) == 17  # 16-segment cross-section ellipse + closing point
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_geometry.py -v`
Expected: FAIL — `generate_fuselage_geometry` is not defined.

- [ ] **Step 3: Implement `generate_fuselage_geometry`**

Append to `backend-modules/aero-engine/aero_engine/aircraft/geometry.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_geometry.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend-modules/aero-engine/aero_engine/aircraft/geometry.py backend-modules/aero-engine/tests/test_geometry.py
git commit -m "feat: add fuselage outline geometry generator"
```

---

## Task 6: Full aircraft geometry assembly

**Files:**
- Modify: `backend-modules/aero-engine/aero_engine/aircraft/geometry.py`
- Modify: `backend-modules/aero-engine/tests/test_geometry.py`

**Interfaces:**
- Consumes: `AircraftConfig` (Task 2), `generate_surface_geometry`/`generate_vertical_surface_geometry`/`generate_fuselage_geometry` (Tasks 3-5), `calculate_surface_planform` (Task 1), `make_conventional_config`/`make_flying_wing_config`/`make_canard_config`/`make_v_tail_config` (Task 2's `conftest.py`).
- Produces: `generate_aircraft_geometry(config: AircraftConfig) -> dict` with keys `wing, horizontal_tail, vertical_tail, canard, v_tail, fuselage` — every present surface's dict has an added `"planform"` key holding that surface's `calculate_surface_planform()` result (`None` for `fuselage`); absent surfaces are `None`. This is the object Task 9-12 (stability) and the router (Task 13) consume.

- [ ] **Step 1: Write the failing tests**

Append to `backend-modules/aero-engine/tests/test_geometry.py`:

```python
from aero_engine.aircraft.geometry import generate_aircraft_geometry
from conftest import (
    make_conventional_config, make_flying_wing_config, make_canard_config, make_v_tail_config,
)


def test_generate_aircraft_geometry_conventional_has_wing_tails_no_canard():
    geometry = generate_aircraft_geometry(make_conventional_config())
    assert geometry["wing"] is not None
    assert geometry["wing"]["planform"]["area"] > 0
    assert geometry["horizontal_tail"] is not None
    assert geometry["vertical_tail"] is not None
    assert geometry["canard"] is None
    assert geometry["v_tail"] is None
    assert geometry["fuselage"] is not None
    assert geometry["fuselage"]["planform"] is None


def test_generate_aircraft_geometry_flying_wing_has_only_wing():
    geometry = generate_aircraft_geometry(make_flying_wing_config())
    assert geometry["wing"] is not None
    assert geometry["horizontal_tail"] is None
    assert geometry["vertical_tail"] is None
    assert geometry["canard"] is None
    assert geometry["v_tail"] is None


def test_generate_aircraft_geometry_canard_has_canard_not_horizontal_tail():
    geometry = generate_aircraft_geometry(make_canard_config())
    assert geometry["canard"] is not None
    assert geometry["horizontal_tail"] is None
    assert geometry["vertical_tail"] is not None


def test_generate_aircraft_geometry_v_tail_has_v_tail_not_separate_tails():
    geometry = generate_aircraft_geometry(make_v_tail_config())
    assert geometry["v_tail"] is not None
    assert geometry["horizontal_tail"] is None
    assert geometry["vertical_tail"] is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_geometry.py -v`
Expected: FAIL — `generate_aircraft_geometry` is not defined.

- [ ] **Step 3: Implement `generate_aircraft_geometry`**

Append to `backend-modules/aero-engine/aero_engine/aircraft/geometry.py`:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_geometry.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add backend-modules/aero-engine/aero_engine/aircraft/geometry.py backend-modules/aero-engine/tests/test_geometry.py
git commit -m "feat: assemble full aircraft geometry from AircraftConfig"
```

---

## Task 7: Lift-curve slope estimate and V-tail equivalent-area projection

**Files:**
- Create: `backend-modules/aero-engine/aero_engine/aircraft/stability.py`
- Create: `backend-modules/aero-engine/tests/test_stability.py`

**Interfaces:**
- Produces: `estimate_cl_alpha_3d(aspect_ratio, sweep_half_chord_deg=0.0, eta=0.95, mach=0.0) -> float` (per-radian 3D lift-curve slope) and `project_v_tail_equivalent_areas(total_area, dihedral_v_deg) -> tuple[float, float]` (`(S_h_eff, S_v_eff)`) — both used by every later stability task (8-11).

- [ ] **Step 1: Write the failing tests**

Create `backend-modules/aero-engine/tests/test_stability.py`:

```python
import math
import pytest
from aero_engine.aircraft.stability import estimate_cl_alpha_3d, project_v_tail_equivalent_areas


def test_estimate_cl_alpha_3d_matches_helmbold_equation():
    # Pure Helmbold's equation (eta=1, no sweep, incompressible):
    # CL_alpha = 2*pi*AR / (2 + sqrt(4 + AR^2))
    result = estimate_cl_alpha_3d(aspect_ratio=8.0, sweep_half_chord_deg=0.0, eta=1.0)
    assert result == pytest.approx(4.906, abs=1e-3)


def test_estimate_cl_alpha_3d_rejects_non_positive_aspect_ratio():
    with pytest.raises(ValueError):
        estimate_cl_alpha_3d(aspect_ratio=0)


def test_project_v_tail_equivalent_areas_pure_vertical_at_90_degrees():
    s_h_eff, s_v_eff = project_v_tail_equivalent_areas(total_area=2.0, dihedral_v_deg=90.0)
    assert s_h_eff == pytest.approx(0.0, abs=1e-9)
    assert s_v_eff == pytest.approx(2.0, abs=1e-9)


def test_project_v_tail_equivalent_areas_pure_horizontal_at_0_degrees():
    s_h_eff, s_v_eff = project_v_tail_equivalent_areas(total_area=2.0, dihedral_v_deg=0.0)
    assert s_h_eff == pytest.approx(2.0, abs=1e-9)
    assert s_v_eff == pytest.approx(0.0, abs=1e-9)


def test_project_v_tail_equivalent_areas_at_45_degrees_splits_evenly():
    s_h_eff, s_v_eff = project_v_tail_equivalent_areas(total_area=2.0, dihedral_v_deg=45.0)
    assert s_h_eff == pytest.approx(1.0, abs=1e-6)
    assert s_v_eff == pytest.approx(1.0, abs=1e-6)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_stability.py -v`
Expected: FAIL/ERROR — `aero_engine.aircraft.stability` does not exist yet.

- [ ] **Step 3: Implement both functions**

Create `backend-modules/aero-engine/aero_engine/aircraft/stability.py`:

```python
import math


def estimate_cl_alpha_3d(
    aspect_ratio: float,
    sweep_half_chord_deg: float = 0.0,
    eta: float = 0.95,
    mach: float = 0.0,
) -> float:
    """
    3D lift-curve slope (per radian), from thin-airfoil theory (2*pi per
    radian, camber-independent) corrected to finite span and sweep via
    Helmbold's equation with the standard DATCOM sweep/compressibility
    extension. Incompressible (mach=0) by default.
    """
    if aspect_ratio <= 0:
        raise ValueError("aspect_ratio must be positive")

    beta = math.sqrt(max(1e-6, 1 - mach ** 2))
    tan_sweep = math.tan(math.radians(sweep_half_chord_deg))

    denominator_term = 4 + (aspect_ratio ** 2 * beta ** 2 / eta ** 2) * (1 + (tan_sweep ** 2) / (beta ** 2))
    if denominator_term < 0:
        # Degenerate input - fall back to the simpler low-AR-safe form.
        return 2 * math.pi * aspect_ratio / (aspect_ratio + 2)

    denominator = 2 + math.sqrt(denominator_term)
    return (2 * math.pi * aspect_ratio) / denominator


def project_v_tail_equivalent_areas(total_area: float, dihedral_v_deg: float) -> tuple[float, float]:
    """
    Standard V-tail equivalent-area decomposition (Raymer, Aircraft
    Design: A Conceptual Approach, Ch. 6.7): projects the V-tail's total
    planform area onto an equivalent horizontal-tail area and an
    equivalent vertical-tail area, based on the dihedral angle of each
    panel measured from horizontal.
    """
    dihedral_rad = math.radians(dihedral_v_deg)
    s_h_eff = total_area * (math.cos(dihedral_rad) ** 2)
    s_v_eff = total_area * (math.sin(dihedral_rad) ** 2)
    return s_h_eff, s_v_eff
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_stability.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend-modules/aero-engine/aero_engine/aircraft/stability.py backend-modules/aero-engine/tests/test_stability.py
git commit -m "feat: add lift-curve slope estimate and V-tail equivalent-area projection"
```

---

## Task 8: Longitudinal stability (neutral point, static margin)

**Files:**
- Modify: `backend-modules/aero-engine/aero_engine/aircraft/stability.py`
- Modify: `backend-modules/aero-engine/tests/test_stability.py`

**Interfaces:**
- Consumes: `AircraftConfig` (Task 2), `generate_aircraft_geometry` output shape (Task 6), `estimate_cl_alpha_3d`/`project_v_tail_equivalent_areas` (Task 7), `make_conventional_config`/`make_flying_wing_config`/`make_canard_config` (Task 2's `conftest.py`).
- Produces: `calculate_longitudinal_stability(config: AircraftConfig, geometry: dict) -> dict` with keys `neutral_point_mac, cg_mac, static_margin_percent, static_margin_classification, cm_alpha, tail_volume_coefficient`. Also produces the internal helper `_surface_ac_x(x_position, planform) -> float`, reused by Task 10 (directional stability).

- [ ] **Step 1: Write the failing tests**

Append to `backend-modules/aero-engine/tests/test_stability.py`:

```python
from aero_engine.aircraft.geometry import generate_aircraft_geometry
from aero_engine.aircraft.stability import calculate_longitudinal_stability
from conftest import make_conventional_config, make_flying_wing_config, make_canard_config


def test_conventional_static_margin_in_typical_range():
    config = make_conventional_config()  # default cg_x_position=2.56
    geometry = generate_aircraft_geometry(config)
    result = calculate_longitudinal_stability(config, geometry)
    assert 5.0 <= result["static_margin_percent"] <= 15.0
    assert result["static_margin_classification"] == "stable"
    assert result["cm_alpha"] < 0
    assert result["tail_volume_coefficient"] > 0


def test_cg_aft_of_neutral_point_is_unstable():
    config = make_conventional_config(cg_x_position=2.8)
    geometry = generate_aircraft_geometry(config)
    result = calculate_longitudinal_stability(config, geometry)
    assert result["static_margin_percent"] < 0
    assert result["static_margin_classification"] == "unstable"


def test_flying_wing_neutral_point_equals_wing_aerodynamic_center():
    config = make_flying_wing_config()  # cg_x_position=2.4 -> static margin ~0
    geometry = generate_aircraft_geometry(config)
    result = calculate_longitudinal_stability(config, geometry)
    assert result["neutral_point_mac"] == pytest.approx(0.25, abs=1e-6)
    assert result["tail_volume_coefficient"] is None
    assert result["static_margin_percent"] == pytest.approx(0.0, abs=1e-3)
    assert result["static_margin_classification"] == "marginal"


def test_canard_produces_finite_negative_moment_arm():
    config = make_canard_config()
    geometry = generate_aircraft_geometry(config)
    result = calculate_longitudinal_stability(config, geometry)
    assert result["tail_volume_coefficient"] < 0  # canard AC is forward of wing AC
    assert math.isfinite(result["neutral_point_mac"])
    assert math.isfinite(result["static_margin_percent"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_stability.py -v`
Expected: FAIL — `calculate_longitudinal_stability` is not defined.

- [ ] **Step 3: Implement `calculate_longitudinal_stability`**

Append to `backend-modules/aero-engine/aero_engine/aircraft/stability.py`:

```python
from .models import AircraftConfig


def _surface_ac_x(x_position: float, planform: dict) -> float:
    """Aerodynamic center x-location: the quarter-chord of the surface's MAC."""
    return x_position + planform["x_mac_le"] + 0.25 * planform["mac"]


def calculate_longitudinal_stability(config: AircraftConfig, geometry: dict) -> dict:
    """
    Static longitudinal stability: neutral point, static margin, Cm_alpha.
    Uses the general two-lifting-surface neutral-point equation (Roskam
    Part VI / Raymer Ch. 16), which handles a canard as the same formula
    with a negative (forward) moment arm.
    """
    wing = config.wing
    wing_planform = geometry["wing"]["planform"]
    S_wing = wing_planform["area"]
    AR_wing = wing_planform["aspect_ratio"]
    MAC_wing = wing_planform["mac"]
    wing_ac_x = _surface_ac_x(wing.x_position, wing_planform)

    CL_alpha_wing = estimate_cl_alpha_3d(AR_wing, wing.sweep_deg)
    h_ac_wing = 0.25
    h_cg = (config.mass.cg_x_position - (wing.x_position + wing_planform["x_mac_le"])) / MAC_wing

    if config.configuration_type == "flying_wing":
        h_n = h_ac_wing
        tail_volume_coefficient = None
    else:
        if config.configuration_type == "v_tail":
            vt = config.v_tail
            v_planform = geometry["v_tail"]["planform"]
            S_other, _ = project_v_tail_equivalent_areas(v_planform["area"], vt.dihedral_v_deg)
            other_ac_x = _surface_ac_x(vt.x_position, v_planform)
            AR_other = v_planform["aspect_ratio"]
            sweep_other = vt.sweep_deg
        else:
            if config.configuration_type in ("conventional", "t_tail"):
                other, other_geom = config.horizontal_tail, geometry["horizontal_tail"]
            elif config.configuration_type == "canard":
                other, other_geom = config.canard, geometry["canard"]
            else:
                raise ValueError(f"Unhandled configuration_type: {config.configuration_type}")
            other_planform = other_geom["planform"]
            S_other = other_planform["area"]
            other_ac_x = _surface_ac_x(other.x_position, other_planform)
            AR_other = other_planform["aspect_ratio"]
            sweep_other = other.sweep_deg

        CL_alpha_other = estimate_cl_alpha_3d(AR_other, sweep_other)
        l = other_ac_x - wing_ac_x
        deps_dalpha = 2 * CL_alpha_wing / (math.pi * AR_wing)
        tail_volume_coefficient = (S_other * l) / (S_wing * MAC_wing)

        h_n = h_ac_wing + (CL_alpha_other / CL_alpha_wing) * (S_other / S_wing) * (l / MAC_wing) * (1 - deps_dalpha)

    static_margin = h_n - h_cg

    if static_margin < 0:
        classification = "unstable"
    elif static_margin < 0.05:
        classification = "marginal"
    elif static_margin <= 0.20:
        classification = "stable"
    else:
        classification = "stable_sluggish"

    return {
        "neutral_point_mac": h_n,
        "cg_mac": h_cg,
        "static_margin_percent": static_margin * 100,
        "static_margin_classification": classification,
        "cm_alpha": -CL_alpha_wing * static_margin,
        "tail_volume_coefficient": tail_volume_coefficient,
    }
```

Add `import math` is already present at the top of the file from Task 7 — no change needed there.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_stability.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add backend-modules/aero-engine/aero_engine/aircraft/stability.py backend-modules/aero-engine/tests/test_stability.py
git commit -m "feat: add static longitudinal stability (neutral point, static margin)"
```

---

## Task 9: Lateral stability (dihedral effect)

**Files:**
- Modify: `backend-modules/aero-engine/aero_engine/aircraft/stability.py`
- Modify: `backend-modules/aero-engine/tests/test_stability.py`

**Interfaces:**
- Consumes: `AircraftConfig`, `generate_aircraft_geometry` output, `estimate_cl_alpha_3d`.
- Produces: `calculate_lateral_stability(config: AircraftConfig, geometry: dict) -> dict` with keys `cl_beta, cl_beta_classification`.

- [ ] **Step 1: Write the failing tests**

Append to `backend-modules/aero-engine/tests/test_stability.py`:

```python
from aero_engine.aircraft.models import Surface, Fuselage, MassProperties, AircraftConfig
from aero_engine.aircraft.stability import calculate_lateral_stability


def test_dihedral_dominates_lateral_stability_when_unswept():
    config = make_conventional_config()  # wing sweep_deg=0.0, dihedral_deg=5.0
    geometry = generate_aircraft_geometry(config)
    result = calculate_lateral_stability(config, geometry)
    assert -0.12 <= result["cl_beta"] <= -0.08
    assert result["cl_beta_classification"] == "stable"


def test_sweep_only_contribution_is_small_and_stabilizing():
    config = make_conventional_config(wing_overrides={"sweep_deg": 20.0, "dihedral_deg": 0.0})
    geometry = generate_aircraft_geometry(config)
    result = calculate_lateral_stability(config, geometry)
    # Sweep alone is a much weaker contributor than 5deg of dihedral -
    # expect a small negative (marginal) value, not strongly stable.
    assert -0.02 < result["cl_beta"] < 0
    assert result["cl_beta_classification"] == "marginal"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_stability.py -v`
Expected: FAIL — `calculate_lateral_stability` is not defined.

- [ ] **Step 3: Implement `calculate_lateral_stability`**

Append to `backend-modules/aero-engine/aero_engine/aircraft/stability.py`:

```python
def calculate_lateral_stability(config: AircraftConfig, geometry: dict) -> dict:
    """
    Static lateral stability: dihedral effect (Cl_beta), combining the
    direct-dihedral contribution and the wing-sweep contribution (both
    small-angle rule-of-thumb estimates).
    """
    wing = config.wing
    wing_planform = geometry["wing"]["planform"]
    S_wing = wing_planform["area"]
    AR_wing = wing_planform["aspect_ratio"]
    CL_alpha_wing = estimate_cl_alpha_3d(AR_wing, wing.sweep_deg)

    dihedral_rad = math.radians(wing.dihedral_deg)
    cl_beta_dihedral = -(CL_alpha_wing / 4) * dihedral_rad

    rho = 1.225
    v = config.mass.cruise_speed_ms
    weight_n = config.mass.mass_kg * 9.81
    cl_trim = weight_n / (0.5 * rho * v ** 2 * S_wing)
    sweep_rad = math.radians(wing.sweep_deg)
    cl_beta_sweep = -cl_trim * math.tan(sweep_rad) / (math.pi * AR_wing)

    cl_beta_total = cl_beta_dihedral + cl_beta_sweep

    if cl_beta_total < -0.02:
        classification = "stable"
    elif cl_beta_total <= 0:
        classification = "marginal"
    else:
        classification = "unstable"

    return {
        "cl_beta": cl_beta_total,
        "cl_beta_classification": classification,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_stability.py -v`
Expected: PASS (11 passed)

- [ ] **Step 5: Commit**

```bash
git add backend-modules/aero-engine/aero_engine/aircraft/stability.py backend-modules/aero-engine/tests/test_stability.py
git commit -m "feat: add static lateral stability (dihedral effect)"
```

---

## Task 10: Directional stability (weathercock stability)

**Files:**
- Modify: `backend-modules/aero-engine/aero_engine/aircraft/stability.py`
- Modify: `backend-modules/aero-engine/tests/test_stability.py`

**Interfaces:**
- Consumes: `AircraftConfig`, `generate_aircraft_geometry` output, `estimate_cl_alpha_3d`, `project_v_tail_equivalent_areas`, `_surface_ac_x` (Task 8).
- Produces: `calculate_directional_stability(config: AircraftConfig, geometry: dict) -> dict` with keys `cn_beta, cn_beta_classification, vertical_tail_volume_coefficient`.

- [ ] **Step 1: Write the failing tests**

Append to `backend-modules/aero-engine/tests/test_stability.py`:

```python
from aero_engine.aircraft.stability import calculate_directional_stability


def test_conventional_vertical_tail_gives_stable_weathercock():
    config = make_conventional_config()
    geometry = generate_aircraft_geometry(config)
    result = calculate_directional_stability(config, geometry)
    assert 0.04 < result["cn_beta"] < 0.12
    assert result["cn_beta_classification"] == "stable"
    assert result["vertical_tail_volume_coefficient"] > 0


def test_flying_wing_has_no_directional_stability():
    config = make_flying_wing_config()
    geometry = generate_aircraft_geometry(config)
    result = calculate_directional_stability(config, geometry)
    assert result["cn_beta"] == 0.0
    assert result["cn_beta_classification"] == "unstable"
    assert result["vertical_tail_volume_coefficient"] is None


def test_v_tail_uses_projected_vertical_area():
    config = make_v_tail_config()
    geometry = generate_aircraft_geometry(config)
    result = calculate_directional_stability(config, geometry)
    assert result["cn_beta"] > 0
    assert result["vertical_tail_volume_coefficient"] is not None
    assert result["vertical_tail_volume_coefficient"] > 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_stability.py -v`
Expected: FAIL — `calculate_directional_stability` is not defined.

- [ ] **Step 3: Implement `calculate_directional_stability`**

Append to `backend-modules/aero-engine/aero_engine/aircraft/stability.py`:

```python
def calculate_directional_stability(config: AircraftConfig, geometry: dict) -> dict:
    """
    Static directional (weathercock) stability: Cn_beta from the vertical
    tail volume coefficient. Fuselage side-area destabilizing contribution
    and sidewash are not modeled (see design spec's Known Limitations).
    """
    wing_planform = geometry["wing"]["planform"]
    S_wing = wing_planform["area"]
    span_wing = config.wing.span
    wing_ac_x = _surface_ac_x(config.wing.x_position, wing_planform)

    if config.configuration_type in ("conventional", "t_tail", "canard"):
        vt = config.vertical_tail
        v_planform = geometry["vertical_tail"]["planform"]
        S_v = v_planform["area"]
        v_ac_x = _surface_ac_x(vt.x_position, v_planform)
        AR_v = v_planform["aspect_ratio"]
        sweep_v = vt.sweep_deg
    elif config.configuration_type == "v_tail":
        vtail = config.v_tail
        v_planform = geometry["v_tail"]["planform"]
        _, S_v = project_v_tail_equivalent_areas(v_planform["area"], vtail.dihedral_v_deg)
        v_ac_x = _surface_ac_x(vtail.x_position, v_planform)
        AR_v = v_planform["aspect_ratio"]
        sweep_v = vtail.sweep_deg
    else:  # flying_wing: no vertical surface, no weathercock stability
        return {
            "cn_beta": 0.0,
            "cn_beta_classification": "unstable",
            "vertical_tail_volume_coefficient": None,
        }

    l_v = v_ac_x - wing_ac_x
    V_V = (S_v * l_v) / (S_wing * span_wing)
    CL_alpha_v = estimate_cl_alpha_3d(AR_v, sweep_v)
    cn_beta = CL_alpha_v * V_V

    if cn_beta > 0.05:
        classification = "stable"
    elif cn_beta >= 0:
        classification = "marginal"
    else:
        classification = "unstable"

    return {
        "cn_beta": cn_beta,
        "cn_beta_classification": classification,
        "vertical_tail_volume_coefficient": V_V,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_stability.py -v`
Expected: PASS (14 passed)

- [ ] **Step 5: Commit**

```bash
git add backend-modules/aero-engine/aero_engine/aircraft/stability.py backend-modules/aero-engine/tests/test_stability.py
git commit -m "feat: add static directional stability (weathercock stability)"
```

---

## Task 11: Full stability assembly with warnings

**Files:**
- Modify: `backend-modules/aero-engine/aero_engine/aircraft/stability.py`
- Modify: `backend-modules/aero-engine/tests/test_stability.py`

**Interfaces:**
- Consumes: `calculate_longitudinal_stability` (Task 8), `calculate_lateral_stability` (Task 9), `calculate_directional_stability` (Task 10).
- Produces: `analyze_stability(config: AircraftConfig, geometry: dict) -> dict` — the full `StabilityResult` shape from the design spec (`neutral_point_mac, cg_mac, static_margin_percent, static_margin_classification, cm_alpha, tail_volume_coefficient, cl_beta, cl_beta_classification, cn_beta, cn_beta_classification, vertical_tail_volume_coefficient, warnings`). This is what the router (Task 13) calls and what the frontend's `StabilityResult` type (Task 14) mirrors.

- [ ] **Step 1: Write the failing tests**

Append to `backend-modules/aero-engine/tests/test_stability.py`:

```python
from aero_engine.aircraft.stability import analyze_stability


def test_analyze_stability_returns_full_expected_shape():
    config = make_conventional_config()
    geometry = generate_aircraft_geometry(config)
    result = analyze_stability(config, geometry)
    expected_keys = {
        "neutral_point_mac", "cg_mac", "static_margin_percent", "static_margin_classification",
        "cm_alpha", "tail_volume_coefficient", "cl_beta", "cl_beta_classification",
        "cn_beta", "cn_beta_classification", "vertical_tail_volume_coefficient", "warnings",
    }
    assert expected_keys.issubset(result.keys())
    assert isinstance(result["warnings"], list)


def test_analyze_stability_flying_wing_warns_about_trim():
    config = make_flying_wing_config()
    geometry = generate_aircraft_geometry(config)
    result = analyze_stability(config, geometry)
    assert any("reflex" in w.lower() or "washout" in w.lower() for w in result["warnings"])


def test_analyze_stability_canard_warns_about_downwash_assumption():
    config = make_canard_config()
    geometry = generate_aircraft_geometry(config)
    result = analyze_stability(config, geometry)
    assert any("downwash" in w.lower() or "canard" in w.lower() for w in result["warnings"])


def test_analyze_stability_warns_when_cg_aft_of_neutral_point():
    config = make_conventional_config(cg_x_position=2.8)
    geometry = generate_aircraft_geometry(config)
    result = analyze_stability(config, geometry)
    assert any("neutral point" in w.lower() or "unstable" in w.lower() for w in result["warnings"])


def test_analyze_stability_warns_when_cg_outside_fuselage_length():
    config = make_conventional_config(cg_x_position=20.0)  # fuselage.length is 8.0
    geometry = generate_aircraft_geometry(config)
    result = analyze_stability(config, geometry)
    assert any("fuselage" in w.lower() for w in result["warnings"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_stability.py -v`
Expected: FAIL — `analyze_stability` is not defined.

- [ ] **Step 3: Implement `analyze_stability`**

Append to `backend-modules/aero-engine/aero_engine/aircraft/stability.py`:

```python
def analyze_stability(config: AircraftConfig, geometry: dict) -> dict:
    """
    Runs the full static stability analysis (longitudinal, lateral,
    directional) and assembles warnings for cases the underlying formulas
    don't fully capture, or physically odd inputs that still compute a
    number.
    """
    longitudinal = calculate_longitudinal_stability(config, geometry)
    lateral = calculate_lateral_stability(config, geometry)
    directional = calculate_directional_stability(config, geometry)

    warnings: list[str] = []

    if config.configuration_type == "flying_wing":
        warnings.append(
            "Flying wing: pitch trim requires a reflexed airfoil or washout, "
            "which this tool does not model. Neutral point is based on the "
            "wing's aerodynamic center only."
        )

    if config.configuration_type == "canard":
        warnings.append(
            "Canard: the neutral-point calculation reuses the same downwash "
            "correction term used for an aft tail, which is physically "
            "backward for a forward canard surface. Treat this result as a "
            "rougher approximation than for conventional/T-tail configs."
        )

    if longitudinal["static_margin_percent"] < 0:
        warnings.append(
            "CG is aft of the neutral point: the aircraft is longitudinally "
            "unstable as configured."
        )

    if directional["cn_beta_classification"] == "unstable" and config.configuration_type != "flying_wing":
        warnings.append(
            "No positive weathercock stability: check vertical tail sizing/position."
        )

    if not (0.0 <= config.mass.cg_x_position <= config.fuselage.length):
        warnings.append(
            "CG position is outside the physical fuselage length - check "
            "cg_x_position against fuselage.length."
        )

    return {
        **longitudinal,
        **lateral,
        **directional,
        "warnings": warnings,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/test_stability.py -v`
Expected: PASS (19 passed)

- [ ] **Step 5: Run the full aero-engine test suite to confirm everything still passes together**

Run: `cd backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: All tests pass (test_wing_planform.py, test_models.py, test_geometry.py, test_stability.py).

- [ ] **Step 6: Commit**

```bash
git add backend-modules/aero-engine/aero_engine/aircraft/stability.py backend-modules/aero-engine/tests/test_stability.py
git commit -m "feat: assemble full stability analysis with warnings"
```

---

## Task 12: FastAPI endpoint + integration smoke tests

**Files:**
- Create: `apps/api-gateway/api_gateway/routers/aircraft.py`
- Modify: `apps/api-gateway/api_gateway/main.py`
- Modify: `test_api.py` (repo root)

**Interfaces:**
- Consumes: `AircraftConfig` (Task 2), `generate_aircraft_geometry` (Task 6), `analyze_stability` (Task 11).
- Produces: `POST /aircraft/design` returning `{"geometry": {...}, "stability": {...}}` — this exact response shape is what the frontend's `AircraftDesignResponse` type (Task 14) and `AircraftDesigner.tsx` (Task 15) consume.

- [ ] **Step 1: Write the failing integration tests**

Append to `test_api.py` (repo root), after the existing `test_endpoints()` function and before the `if __name__ == "__main__":` block:

```python
def test_aircraft_design_endpoint():
    print("\nTesting Aircraft Designer (conventional)...")
    res = client.post("/aircraft/design", json={
        "configuration_type": "conventional",
        "wing": {"span": 11.0, "root_chord": 1.6, "tip_chord": 1.6,
                  "sweep_deg": 0.0, "dihedral_deg": 5.0, "x_position": 2.0},
        "horizontal_tail": {"span": 3.4, "root_chord": 0.9, "tip_chord": 0.6,
                              "sweep_deg": 5.0, "x_position": 6.5, "z_position": 0.9},
        "vertical_tail": {"height": 1.5, "root_chord": 1.0, "tip_chord": 0.5,
                            "sweep_deg": 15.0, "x_position": 6.8, "z_position": 0.3},
        "fuselage": {"length": 8.0, "max_width": 1.2, "max_height": 1.4,
                      "nose_length": 1.5, "tail_length": 2.0},
        "mass": {"mass_kg": 1000.0, "cg_x_position": 2.56, "cruise_speed_ms": 60.0},
    })
    if res.status_code == 200:
        data = res.json()
        print("[OK] Aircraft design calculated. Static margin:",
              data["stability"]["static_margin_percent"], "% MAC")
    else:
        print("[FAIL] Error:", res.text)
    assert res.status_code == 200
    data = res.json()
    assert "geometry" in data and "stability" in data
    assert isinstance(data["stability"]["static_margin_percent"], float)


def test_aircraft_design_endpoint_rejects_mismatched_surfaces():
    print("\nTesting Aircraft Designer validation (v_tail config with horizontal_tail)...")
    res = client.post("/aircraft/design", json={
        "configuration_type": "v_tail",
        "wing": {"span": 11.0, "root_chord": 1.6, "tip_chord": 1.6, "x_position": 2.0},
        "horizontal_tail": {"span": 3.4, "root_chord": 0.9, "tip_chord": 0.6, "x_position": 6.5},
        "v_tail": {"span": 2.5, "root_chord": 0.9, "tip_chord": 0.5, "dihedral_v_deg": 40.0, "x_position": 6.7},
        "fuselage": {"length": 8.0, "max_width": 1.2, "max_height": 1.4, "nose_length": 1.5, "tail_length": 2.0},
        "mass": {"mass_kg": 1000.0, "cg_x_position": 2.56, "cruise_speed_ms": 60.0},
    })
    if res.status_code == 422:
        print("[OK] Mismatched surfaces correctly rejected with 422")
    else:
        print("[FAIL] Expected 422, got:", res.status_code, res.text)
    assert res.status_code == 422


def test_aircraft_design_endpoint_rejects_zero_span():
    print("\nTesting Aircraft Designer validation (zero-span wing)...")
    res = client.post("/aircraft/design", json={
        "configuration_type": "flying_wing",
        "wing": {"span": 0, "root_chord": 1.6, "tip_chord": 1.6, "x_position": 2.0},
        "fuselage": {"length": 8.0, "max_width": 1.2, "max_height": 1.4, "nose_length": 1.5, "tail_length": 2.0},
        "mass": {"mass_kg": 1000.0, "cg_x_position": 2.0, "cruise_speed_ms": 60.0},
    })
    if res.status_code == 422:
        print("[OK] Zero-span wing correctly rejected with 422")
    else:
        print("[FAIL] Expected 422, got:", res.status_code, res.text)
    assert res.status_code == 422
```

Also update the `__main__` block at the bottom of `test_api.py` so the manual `python test_api.py` run still exercises everything:

```python
if __name__ == "__main__":
    test_endpoints()
    test_aircraft_design_endpoint()
    test_aircraft_design_endpoint_rejects_mismatched_surfaces()
    test_aircraft_design_endpoint_rejects_zero_span()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest test_api.py -v`
Expected: FAIL — `/aircraft/design` doesn't exist yet (404s), so the assertions fail.

- [ ] **Step 3: Implement the router**

Create `apps/api-gateway/api_gateway/routers/aircraft.py`:

```python
from fastapi import APIRouter, HTTPException

from aero_engine.aircraft.models import AircraftConfig
from aero_engine.aircraft.geometry import generate_aircraft_geometry
from aero_engine.aircraft.stability import analyze_stability

router = APIRouter(prefix="/aircraft", tags=["Aircraft Design"])


@router.post("/design")
def design_aircraft(config: AircraftConfig):
    try:
        geometry = generate_aircraft_geometry(config)
        stability = analyze_stability(config, geometry)
        return {"geometry": geometry, "stability": stability}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 4: Register the router**

In `apps/api-gateway/api_gateway/main.py`, change:

```python
from api_gateway.routers import aero, dfm, propulsion, auth, projects

# Include Routers
app.include_router(aero.router)
app.include_router(dfm.router)
app.include_router(propulsion.router)
app.include_router(auth.router)
app.include_router(projects.router)
```

to:

```python
from api_gateway.routers import aero, dfm, propulsion, auth, projects, aircraft

# Include Routers
app.include_router(aero.router)
app.include_router(dfm.router)
app.include_router(propulsion.router)
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(aircraft.router)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest test_api.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Run the manual smoke-test script too, to confirm the OK/FAIL output convention still works**

Run: `./.venv/Scripts/python.exe test_api.py`
Expected: All `[OK]` lines print, including the three new Aircraft Designer lines.

- [ ] **Step 7: Commit**

```bash
git add apps/api-gateway/api_gateway/routers/aircraft.py apps/api-gateway/api_gateway/main.py test_api.py
git commit -m "feat: add POST /aircraft/design endpoint"
```

---

## Task 13: Frontend TypeScript types

**Files:**
- Modify: `apps/aerocalc-web/lib/types.ts`

**Interfaces:**
- Produces: `AircraftSurface, AircraftVerticalTail, AircraftVTail, AircraftFuselage, AircraftMassProperties, AircraftConfigurationType, AircraftConfig, SurfaceGeometry, AircraftGeometry, StabilityResult, AircraftDesignResponse` — every field name/shape here must exactly mirror Task 2's Pydantic models, Task 6's geometry output, and Task 11's stability output. Consumed by Tasks 14-17.

- [ ] **Step 1: Append the new types**

Append to `apps/aerocalc-web/lib/types.ts`:

```typescript
/** Mirrors aero_engine.aircraft.models.Surface */
export interface AircraftSurface {
  span: number;
  root_chord: number;
  tip_chord: number;
  sweep_deg?: number;
  dihedral_deg?: number;
  twist_deg?: number;
  airfoil?: string;
  x_position: number;
  z_position?: number;
  mount?: "high" | "mid" | "low";
}

/** Mirrors aero_engine.aircraft.models.VerticalTail */
export interface AircraftVerticalTail {
  height: number;
  root_chord: number;
  tip_chord: number;
  sweep_deg?: number;
  airfoil?: string;
  x_position: number;
  z_position?: number;
}

/** Mirrors aero_engine.aircraft.models.VTail */
export interface AircraftVTail {
  span: number;
  root_chord: number;
  tip_chord: number;
  dihedral_v_deg: number;
  sweep_deg?: number;
  airfoil?: string;
  x_position: number;
  z_position?: number;
}

/** Mirrors aero_engine.aircraft.models.Fuselage */
export interface AircraftFuselage {
  length: number;
  max_width: number;
  max_height: number;
  nose_length: number;
  tail_length: number;
}

/** Mirrors aero_engine.aircraft.models.MassProperties */
export interface AircraftMassProperties {
  mass_kg: number;
  cg_x_position: number;
  cruise_speed_ms: number;
}

export type AircraftConfigurationType =
  | "conventional"
  | "flying_wing"
  | "canard"
  | "t_tail"
  | "v_tail";

/** Mirrors aero_engine.aircraft.models.AircraftConfig */
export interface AircraftConfig {
  configuration_type: AircraftConfigurationType;
  wing: AircraftSurface;
  horizontal_tail?: AircraftSurface | null;
  vertical_tail?: AircraftVerticalTail | null;
  canard?: AircraftSurface | null;
  v_tail?: AircraftVTail | null;
  fuselage: AircraftFuselage;
  mass: AircraftMassProperties;
}

/** Mirrors one surface's entry in aero_engine.aircraft.geometry.generate_aircraft_geometry output */
export interface SurfaceGeometry {
  top_view: number[][];
  front_view: number[][];
  side_view: number[][];
  vertices: number[][];
  edges: number[][];
  planform: {
    span: number;
    root_chord: number;
    tip_chord: number;
    sweep_angle_deg: number;
    taper_ratio: number;
    area: number;
    aspect_ratio: number;
    mac: number;
    y_mac: number;
    x_mac_le: number;
  } | null;
}

/** Mirrors aero_engine.aircraft.geometry.generate_aircraft_geometry output */
export interface AircraftGeometry {
  wing: SurfaceGeometry;
  horizontal_tail: SurfaceGeometry | null;
  vertical_tail: SurfaceGeometry | null;
  canard: SurfaceGeometry | null;
  v_tail: SurfaceGeometry | null;
  fuselage: SurfaceGeometry;
}

/** Mirrors aero_engine.aircraft.stability.analyze_stability output */
export interface StabilityResult {
  neutral_point_mac: number;
  cg_mac: number;
  static_margin_percent: number;
  static_margin_classification: "unstable" | "marginal" | "stable" | "stable_sluggish";
  cm_alpha: number;
  tail_volume_coefficient: number | null;
  cl_beta: number;
  cl_beta_classification: "unstable" | "marginal" | "stable";
  cn_beta: number;
  cn_beta_classification: "unstable" | "marginal" | "stable";
  vertical_tail_volume_coefficient: number | null;
  warnings: string[];
}

/** Mirrors the response body of POST /aircraft/design */
export interface AircraftDesignResponse {
  geometry: AircraftGeometry;
  stability: StabilityResult;
}
```

- [ ] **Step 2: Type-check**

Run: `cd apps/aerocalc-web && npx tsc --noEmit`
Expected: No errors (these are pure additive type declarations, nothing consumes them yet).

- [ ] **Step 3: Commit**

```bash
git add apps/aerocalc-web/lib/types.ts
git commit -m "feat: add TypeScript types for the aircraft designer"
```

---

## Task 14: AircraftDesigner form component + navigation wiring

**Files:**
- Create: `apps/aerocalc-web/components/aircraft/AircraftDesigner.tsx`
- Create: `apps/aerocalc-web/components/aircraft/AircraftDesigner.module.css`
- Modify: `apps/aerocalc-web/components/Sidebar.tsx`
- Modify: `apps/aerocalc-web/app/page.tsx`

**Interfaces:**
- Consumes: `AircraftConfig` and friends (Task 13), `POST /aircraft/design` (Task 12).
- Produces: renders `<BlueprintView>`, `<Blueprint3D>` (dynamically imported, `ssr: false`), and `<StabilityPanel>` once results arrive — these three components are built in Tasks 15-17; until then this task's own manual verification step confirms the API round-trip and raw-shape rendering work (the three imports point at files created in the next tasks, so `tsc`/`eslint` for *this* task run after Task 17, not standalone — see Step 2 note).

- [ ] **Step 1: Write the component**

Create `apps/aerocalc-web/components/aircraft/AircraftDesigner.module.css`:

```css
.container {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 1.5rem;
  padding: 1.5rem;
}

@media (max-width: 900px) {
  .container {
    grid-template-columns: 1fr;
  }
}

.controls {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.fieldset {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.75rem;
  background-color: var(--card-bg, #f8fafc);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.5rem;
}

.label {
  font-size: 0.8rem;
  color: #64748b;
}

.input {
  padding: 0.4rem 0.5rem;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  background-color: white;
  color: #0f172a;
}

.button {
  padding: 0.6rem 1rem;
  border-radius: 6px;
  border: none;
  background-color: #3b82f6;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}

.button:hover:not(:disabled) {
  background-color: #2563eb;
}

.button:disabled {
  background-color: #93c5fd;
  cursor: not-allowed;
}

.error {
  background-color: #fef2f2;
  color: #b91c1c;
  padding: 0.5rem;
  border-radius: 6px;
  font-size: 0.85rem;
}

.viewsPanel {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.placeholder {
  color: #64748b;
  font-size: 0.9rem;
}

.simLoading {
  padding: 1rem;
  color: #64748b;
}
```

Create `apps/aerocalc-web/components/aircraft/AircraftDesigner.tsx`:

```tsx
"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import styles from "./AircraftDesigner.module.css";
import BlueprintView from "./BlueprintView";
import StabilityPanel from "./StabilityPanel";
import type {
  AircraftConfig,
  AircraftConfigurationType,
  AircraftSurface,
  AircraftVerticalTail,
  AircraftVTail,
  AircraftFuselage,
  AircraftMassProperties,
  AircraftDesignResponse,
} from "../../lib/types";

// Blueprint3D uses @react-three/fiber's WebGL Canvas, which cannot be
// server-rendered; load it client-only, matching the flight simulator's
// dynamic-import pattern in app/page.tsx.
const Blueprint3D = dynamic(() => import("./Blueprint3D"), {
  ssr: false,
  loading: () => <div className={styles.simLoading}>Loading 3D view…</div>,
});

const DEFAULT_WING: AircraftSurface = {
  span: 10.0, root_chord: 1.5, tip_chord: 1.0, sweep_deg: 0, dihedral_deg: 5,
  x_position: 2.0, z_position: 0,
};
const DEFAULT_HTAIL: AircraftSurface = {
  span: 3.0, root_chord: 0.8, tip_chord: 0.5, sweep_deg: 5,
  x_position: 6.0, z_position: 0.5,
};
const DEFAULT_VTAIL_FIN: AircraftVerticalTail = {
  height: 1.2, root_chord: 0.9, tip_chord: 0.5, sweep_deg: 15,
  x_position: 6.2, z_position: 0.2,
};
const DEFAULT_CANARD: AircraftSurface = {
  span: 2.0, root_chord: 0.6, tip_chord: 0.4, sweep_deg: 0,
  x_position: 0.5, z_position: 0,
};
const DEFAULT_V_TAIL: AircraftVTail = {
  span: 2.5, root_chord: 0.9, tip_chord: 0.5, dihedral_v_deg: 40, sweep_deg: 10,
  x_position: 6.2, z_position: 0.4,
};
const DEFAULT_FUSELAGE: AircraftFuselage = {
  length: 7.5, max_width: 1.1, max_height: 1.3, nose_length: 1.2, tail_length: 1.8,
};
const DEFAULT_MASS: AircraftMassProperties = {
  mass_kg: 900, cg_x_position: 2.5, cruise_speed_ms: 55,
};

function defaultConfigFor(type: AircraftConfigurationType): AircraftConfig {
  const base: AircraftConfig = {
    configuration_type: type,
    wing: { ...DEFAULT_WING },
    fuselage: { ...DEFAULT_FUSELAGE },
    mass: { ...DEFAULT_MASS },
  };
  if (type === "conventional" || type === "t_tail") {
    base.horizontal_tail = { ...DEFAULT_HTAIL };
    base.vertical_tail = { ...DEFAULT_VTAIL_FIN };
  } else if (type === "canard") {
    base.canard = { ...DEFAULT_CANARD };
    base.vertical_tail = { ...DEFAULT_VTAIL_FIN };
  } else if (type === "v_tail") {
    base.v_tail = { ...DEFAULT_V_TAIL };
  }
  return base;
}

function NumberField({
  label, value, onChange, step = 0.1, min,
}: { label: string; value: number; onChange: (v: number) => void; step?: number; min?: number }) {
  return (
    <div className={styles.field}>
      <label className={styles.label}>{label}</label>
      <input
        type="number"
        className={styles.input}
        value={value}
        step={step}
        min={min}
        title={label}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}

export default function AircraftDesigner() {
  const [configType, setConfigType] = useState<AircraftConfigurationType>("conventional");
  const [config, setConfig] = useState<AircraftConfig>(() => defaultConfigFor("conventional"));
  const [results, setResults] = useState<AircraftDesignResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleTypeChange = (type: AircraftConfigurationType) => {
    setConfigType(type);
    setConfig(defaultConfigFor(type));
    setResults(null);
  };

  const updateWing = (patch: Partial<AircraftSurface>) =>
    setConfig((prev) => ({ ...prev, wing: { ...prev.wing, ...patch } }));

  const updateHorizontalTail = (patch: Partial<AircraftSurface>) =>
    setConfig((prev) => ({ ...prev, horizontal_tail: { ...(prev.horizontal_tail as AircraftSurface), ...patch } }));

  const updateCanard = (patch: Partial<AircraftSurface>) =>
    setConfig((prev) => ({ ...prev, canard: { ...(prev.canard as AircraftSurface), ...patch } }));

  const updateVerticalTail = (patch: Partial<AircraftVerticalTail>) =>
    setConfig((prev) => ({ ...prev, vertical_tail: { ...(prev.vertical_tail as AircraftVerticalTail), ...patch } }));

  const updateVTail = (patch: Partial<AircraftVTail>) =>
    setConfig((prev) => ({ ...prev, v_tail: { ...(prev.v_tail as AircraftVTail), ...patch } }));

  const updateFuselage = (patch: Partial<AircraftFuselage>) =>
    setConfig((prev) => ({ ...prev, fuselage: { ...prev.fuselage, ...patch } }));

  const updateMass = (patch: Partial<AircraftMassProperties>) =>
    setConfig((prev) => ({ ...prev, mass: { ...prev.mass, ...patch } }));

  const handleCalculate = async () => {
    setLoading(true);
    setError("");
    try {
      if (config.mass.cg_x_position < 0 || config.mass.cg_x_position > config.fuselage.length) {
        throw new Error("CG position should be within the fuselage length");
      }
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${baseUrl}/aircraft/design`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => null);
        throw new Error(
          detail?.detail ? String(detail.detail) : "Failed to calculate aircraft design"
        );
      }
      const data: AircraftDesignResponse = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.controls}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="configType">Configuration Type</label>
          <select
            id="configType"
            className={styles.input}
            value={configType}
            onChange={(e) => handleTypeChange(e.target.value as AircraftConfigurationType)}
          >
            <option value="conventional">Conventional</option>
            <option value="t_tail">T-Tail</option>
            <option value="canard">Canard</option>
            <option value="v_tail">V-Tail</option>
            <option value="flying_wing">Flying Wing / Tailless</option>
          </select>
        </div>

        <fieldset className={styles.fieldset}>
          <legend>Wing</legend>
          <NumberField label="Span (m)" value={config.wing.span} onChange={(v) => updateWing({ span: v })} />
          <NumberField label="Root Chord (m)" value={config.wing.root_chord} onChange={(v) => updateWing({ root_chord: v })} />
          <NumberField label="Tip Chord (m)" value={config.wing.tip_chord} onChange={(v) => updateWing({ tip_chord: v })} />
          <NumberField label="Sweep (deg)" value={config.wing.sweep_deg ?? 0} onChange={(v) => updateWing({ sweep_deg: v })} />
          <NumberField label="Dihedral (deg)" value={config.wing.dihedral_deg ?? 0} onChange={(v) => updateWing({ dihedral_deg: v })} />
          <NumberField label="X Position (m from nose)" value={config.wing.x_position} onChange={(v) => updateWing({ x_position: v })} />
        </fieldset>

        {(configType === "conventional" || configType === "t_tail") && config.horizontal_tail && (
          <fieldset className={styles.fieldset}>
            <legend>Horizontal Tail</legend>
            <NumberField label="Span (m)" value={config.horizontal_tail.span} onChange={(v) => updateHorizontalTail({ span: v })} />
            <NumberField label="Root Chord (m)" value={config.horizontal_tail.root_chord} onChange={(v) => updateHorizontalTail({ root_chord: v })} />
            <NumberField label="Tip Chord (m)" value={config.horizontal_tail.tip_chord} onChange={(v) => updateHorizontalTail({ tip_chord: v })} />
            <NumberField label="X Position (m from nose)" value={config.horizontal_tail.x_position} onChange={(v) => updateHorizontalTail({ x_position: v })} />
            <NumberField label="Z Position (m)" value={config.horizontal_tail.z_position ?? 0} onChange={(v) => updateHorizontalTail({ z_position: v })} />
          </fieldset>
        )}

        {configType === "canard" && config.canard && (
          <fieldset className={styles.fieldset}>
            <legend>Canard</legend>
            <NumberField label="Span (m)" value={config.canard.span} onChange={(v) => updateCanard({ span: v })} />
            <NumberField label="Root Chord (m)" value={config.canard.root_chord} onChange={(v) => updateCanard({ root_chord: v })} />
            <NumberField label="Tip Chord (m)" value={config.canard.tip_chord} onChange={(v) => updateCanard({ tip_chord: v })} />
            <NumberField label="X Position (m from nose)" value={config.canard.x_position} onChange={(v) => updateCanard({ x_position: v })} />
          </fieldset>
        )}

        {(configType === "conventional" || configType === "t_tail" || configType === "canard") && config.vertical_tail && (
          <fieldset className={styles.fieldset}>
            <legend>Vertical Tail</legend>
            <NumberField label="Height (m)" value={config.vertical_tail.height} onChange={(v) => updateVerticalTail({ height: v })} />
            <NumberField label="Root Chord (m)" value={config.vertical_tail.root_chord} onChange={(v) => updateVerticalTail({ root_chord: v })} />
            <NumberField label="Tip Chord (m)" value={config.vertical_tail.tip_chord} onChange={(v) => updateVerticalTail({ tip_chord: v })} />
            <NumberField label="X Position (m from nose)" value={config.vertical_tail.x_position} onChange={(v) => updateVerticalTail({ x_position: v })} />
          </fieldset>
        )}

        {configType === "v_tail" && config.v_tail && (
          <fieldset className={styles.fieldset}>
            <legend>V-Tail</legend>
            <NumberField label="Span (m)" value={config.v_tail.span} onChange={(v) => updateVTail({ span: v })} />
            <NumberField label="Root Chord (m)" value={config.v_tail.root_chord} onChange={(v) => updateVTail({ root_chord: v })} />
            <NumberField label="Tip Chord (m)" value={config.v_tail.tip_chord} onChange={(v) => updateVTail({ tip_chord: v })} />
            <NumberField label="Dihedral Angle (deg)" value={config.v_tail.dihedral_v_deg} onChange={(v) => updateVTail({ dihedral_v_deg: v })} min={0} />
            <NumberField label="X Position (m from nose)" value={config.v_tail.x_position} onChange={(v) => updateVTail({ x_position: v })} />
          </fieldset>
        )}

        <fieldset className={styles.fieldset}>
          <legend>Fuselage</legend>
          <NumberField label="Length (m)" value={config.fuselage.length} onChange={(v) => updateFuselage({ length: v })} />
          <NumberField label="Max Width (m)" value={config.fuselage.max_width} onChange={(v) => updateFuselage({ max_width: v })} />
          <NumberField label="Max Height (m)" value={config.fuselage.max_height} onChange={(v) => updateFuselage({ max_height: v })} />
          <NumberField label="Nose Length (m)" value={config.fuselage.nose_length} onChange={(v) => updateFuselage({ nose_length: v })} />
          <NumberField label="Tail Length (m)" value={config.fuselage.tail_length} onChange={(v) => updateFuselage({ tail_length: v })} />
        </fieldset>

        <fieldset className={styles.fieldset}>
          <legend>Mass &amp; CG</legend>
          <NumberField label="Mass (kg)" value={config.mass.mass_kg} onChange={(v) => updateMass({ mass_kg: v })} />
          <NumberField label="CG X Position (m from nose)" value={config.mass.cg_x_position} onChange={(v) => updateMass({ cg_x_position: v })} />
          <NumberField label="Cruise Speed (m/s)" value={config.mass.cruise_speed_ms} onChange={(v) => updateMass({ cruise_speed_ms: v })} />
        </fieldset>

        <button type="button" className={styles.button} onClick={handleCalculate} disabled={loading}>
          {loading ? "Calculating..." : "Calculate"}
        </button>
        {error && <p className={styles.error}>{error}</p>}
      </div>

      <div className={styles.viewsPanel}>
        {results ? (
          <>
            <BlueprintView geometry={results.geometry} />
            <Blueprint3D geometry={results.geometry} />
            <StabilityPanel stability={results.stability} />
          </>
        ) : (
          <p className={styles.placeholder}>
            Configure an aircraft and click Calculate to see the blueprint and stability analysis.
          </p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Wire the new tab into navigation**

In `apps/aerocalc-web/components/Sidebar.tsx`, change the import line:

```typescript
import { Plane, Cpu, Activity, LayoutTemplate, Fan, FileBarChart, Rocket } from "lucide-react";
```

to:

```typescript
import { Plane, Cpu, Activity, LayoutTemplate, Fan, FileBarChart, Rocket, DraftingCompass } from "lucide-react";
```

Then insert a new nav item right after the "Wing Planform" `<li>` block (which ends with `</li>` right before the `<li className={styles.navItem}>` that opens the "Multirotor Config" button):

```tsx
          <li className={styles.navItem}>
            <button
              type="button"
              onClick={() => setActiveTab("aircraft")}
              className={`${styles.navButton} ${activeTab === "aircraft" ? styles.navButtonActive : ""}`}
              title="Aircraft Designer"
            >
              <DraftingCompass size={18} />
              Aircraft Designer
            </button>
          </li>
```

- [ ] **Step 3: Render the new tab in the page**

In `apps/aerocalc-web/app/page.tsx`, add the import:

```tsx
import AircraftDesigner from "../components/aircraft/AircraftDesigner";
```

and add the render branch after the Wing Planform branch:

```tsx
          {activeTab === "wing" && <WingPlanformDesigner />}
          {activeTab === "aircraft" && <AircraftDesigner />}
```

- [ ] **Step 4: Note on verification timing**

`AircraftDesigner.tsx` imports `BlueprintView`, `Blueprint3D`, and `StabilityPanel`, which do not exist until Tasks 15-17. Do not run `tsc`/`eslint` yet — Step 2 of Task 17 is the first point all four files exist together. Proceed directly to Task 15.

- [ ] **Step 5: Commit**

```bash
git add apps/aerocalc-web/components/aircraft/AircraftDesigner.tsx apps/aerocalc-web/components/aircraft/AircraftDesigner.module.css apps/aerocalc-web/components/Sidebar.tsx apps/aerocalc-web/app/page.tsx
git commit -m "feat: add AircraftDesigner form component and wire up navigation"
```

---

## Task 15: BlueprintView (SVG three-view)

**Files:**
- Create: `apps/aerocalc-web/components/aircraft/BlueprintView.tsx`
- Create: `apps/aerocalc-web/components/aircraft/BlueprintView.module.css`

**Interfaces:**
- Consumes: `AircraftGeometry`, `SurfaceGeometry` (Task 13).
- Produces: `export default function BlueprintView({ geometry }: { geometry: AircraftGeometry })` — imported by `AircraftDesigner.tsx` (Task 14).

- [ ] **Step 1: Write the component**

Create `apps/aerocalc-web/components/aircraft/BlueprintView.module.css`:

```css
.container {
  background: #0a1628;
  border-radius: 8px;
  padding: 1rem;
  color: #e0f2fe;
}

.heading {
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.dimensions {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  color: #7dd3fc;
  margin-bottom: 0.75rem;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem;
}

.panel {
  background: #0f1f38;
  border: 1px solid #1e3a5f;
  border-radius: 6px;
  padding: 0.5rem;
}

.panelTitle {
  font-size: 0.75rem;
  color: #7dd3fc;
  margin-bottom: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.svg {
  width: 100%;
  height: 200px;
}

.outline {
  fill: none;
  stroke: #e0f2fe;
  stroke-width: 0.02;
  vector-effect: non-scaling-stroke;
}
```

Create `apps/aerocalc-web/components/aircraft/BlueprintView.tsx`:

```tsx
"use client";

import styles from "./BlueprintView.module.css";
import type { AircraftGeometry, SurfaceGeometry } from "../../lib/types";

type ViewKey = "top_view" | "front_view" | "side_view";

function pointsToPath(points: number[][], negateSecond: boolean): string {
  if (points.length === 0) return "";
  const commands = points.map((p, i) => {
    const y = negateSecond ? -p[1] : p[1];
    return `${i === 0 ? "M" : "L"} ${p[0].toFixed(3)} ${y.toFixed(3)}`;
  });
  return commands.join(" ") + " Z";
}

function allSurfaces(geometry: AircraftGeometry): SurfaceGeometry[] {
  return [
    geometry.wing,
    geometry.horizontal_tail,
    geometry.vertical_tail,
    geometry.canard,
    geometry.v_tail,
    geometry.fuselage,
  ].filter((s): s is SurfaceGeometry => s !== null);
}

function ViewPanel({
  title, geometry, view, negateSecond,
}: { title: string; geometry: AircraftGeometry; view: ViewKey; negateSecond: boolean }) {
  const surfaces = allSurfaces(geometry).filter((s) => s[view].length > 0);
  const allPoints = surfaces.flatMap((s) => s[view]);

  if (allPoints.length === 0) {
    return (
      <div className={styles.panel}>
        <p className={styles.panelTitle}>{title}</p>
      </div>
    );
  }

  const xs = allPoints.map((p) => p[0]);
  const ys = allPoints.map((p) => (negateSecond ? -p[1] : p[1]));
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const padX = Math.max((maxX - minX) * 0.15, 0.3);
  const padY = Math.max((maxY - minY) * 0.15, 0.3);
  const viewBox = `${minX - padX} ${minY - padY} ${maxX - minX + padX * 2} ${maxY - minY + padY * 2}`;

  return (
    <div className={styles.panel}>
      <p className={styles.panelTitle}>{title}</p>
      <svg className={styles.svg} viewBox={viewBox} preserveAspectRatio="xMidYMid meet">
        {surfaces.map((s, i) => (
          <path key={i} d={pointsToPath(s[view], negateSecond)} className={styles.outline} />
        ))}
      </svg>
    </div>
  );
}

export default function BlueprintView({ geometry }: { geometry: AircraftGeometry }) {
  const wingSpan = geometry.wing.planform?.span ?? 0;
  const wingMac = geometry.wing.planform?.mac ?? 0;
  const fuselageLength = geometry.fuselage.side_view.reduce((max, p) => Math.max(max, p[0]), 0);

  return (
    <div className={styles.container}>
      <p className={styles.heading}>Blueprint — Three View</p>
      <div className={styles.dimensions}>
        <span>Span: {wingSpan.toFixed(2)} m</span>
        <span>MAC: {wingMac.toFixed(2)} m</span>
        <span>Length: {fuselageLength.toFixed(2)} m</span>
      </div>
      <div className={styles.grid}>
        <ViewPanel title="Top View" geometry={geometry} view="top_view" negateSecond={false} />
        <ViewPanel title="Front View" geometry={geometry} view="front_view" negateSecond={true} />
        <ViewPanel title="Side View" geometry={geometry} view="side_view" negateSecond={true} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/aerocalc-web/components/aircraft/BlueprintView.tsx apps/aerocalc-web/components/aircraft/BlueprintView.module.css
git commit -m "feat: add BlueprintView SVG three-view component"
```

---

## Task 16: Blueprint3D (interactive 3D wireframe)

**Files:**
- Create: `apps/aerocalc-web/components/aircraft/Blueprint3D.tsx`
- Create: `apps/aerocalc-web/components/aircraft/Blueprint3D.module.css`

**Interfaces:**
- Consumes: `AircraftGeometry`, `SurfaceGeometry` (Task 13), `@react-three/fiber`'s `Canvas`, `@react-three/drei`'s `OrbitControls`/`Line` (already installed dependencies).
- Produces: `export default function Blueprint3D({ geometry }: { geometry: AircraftGeometry })` — imported dynamically (`ssr: false`) by `AircraftDesigner.tsx` (Task 14).

- [ ] **Step 1: Write the component**

Create `apps/aerocalc-web/components/aircraft/Blueprint3D.module.css`:

```css
.container {
  background: #0a1628;
  border-radius: 8px;
  padding: 1rem;
}

.heading {
  font-weight: 600;
  color: #e0f2fe;
  margin-bottom: 0.5rem;
}

.canvasWrapper {
  width: 100%;
  height: 320px;
  border-radius: 6px;
  overflow: hidden;
}
```

Create `apps/aerocalc-web/components/aircraft/Blueprint3D.tsx`:

```tsx
"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, Line } from "@react-three/drei";
import styles from "./Blueprint3D.module.css";
import type { AircraftGeometry, SurfaceGeometry } from "../../lib/types";

// AircraftGeometry vertices are [x(aft), y(starboard), z(up)]. Three.js
// uses [x(right), y(up), z(toward viewer)], so we map aircraft (x,y,z) ->
// three (x, z, y): aft along three's x-axis, up stays up, spanwise along
// three's z-axis.
function toThreeCoords(v: number[]): [number, number, number] {
  return [v[0], v[2], v[1]];
}

function SurfaceWireframe({ geometry, color }: { geometry: SurfaceGeometry; color: string }) {
  return (
    <>
      {geometry.edges.map(([a, b], i) => {
        const start = geometry.vertices[a];
        const end = geometry.vertices[b];
        if (!start || !end) return null;
        return (
          <Line
            key={i}
            points={[toThreeCoords(start), toThreeCoords(end)]}
            color={color}
            lineWidth={1.5}
          />
        );
      })}
    </>
  );
}

export default function Blueprint3D({ geometry }: { geometry: AircraftGeometry }) {
  const surfaces: { geom: SurfaceGeometry; color: string }[] = [
    { geom: geometry.wing, color: "#7dd3fc" },
    ...(geometry.horizontal_tail ? [{ geom: geometry.horizontal_tail, color: "#38bdf8" }] : []),
    ...(geometry.vertical_tail ? [{ geom: geometry.vertical_tail, color: "#38bdf8" }] : []),
    ...(geometry.canard ? [{ geom: geometry.canard, color: "#a78bfa" }] : []),
    ...(geometry.v_tail ? [{ geom: geometry.v_tail, color: "#38bdf8" }] : []),
    { geom: geometry.fuselage, color: "#94a3b8" },
  ];

  return (
    <div className={styles.container}>
      <p className={styles.heading}>3D Wireframe</p>
      <div className={styles.canvasWrapper}>
        <Canvas camera={{ position: [8, 4, 8], fov: 45 }}>
          <ambientLight intensity={0.6} />
          <directionalLight position={[5, 5, 5]} intensity={0.8} />
          {surfaces.map((s, i) => (
            <SurfaceWireframe key={i} geometry={s.geom} color={s.color} />
          ))}
          <OrbitControls enableDamping />
        </Canvas>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/aerocalc-web/components/aircraft/Blueprint3D.tsx apps/aerocalc-web/components/aircraft/Blueprint3D.module.css
git commit -m "feat: add Blueprint3D interactive wireframe component"
```

---

## Task 17: StabilityPanel (readouts + CG/NP chart) + full frontend verification

**Files:**
- Create: `apps/aerocalc-web/components/aircraft/StabilityPanel.tsx`
- Create: `apps/aerocalc-web/components/aircraft/StabilityPanel.module.css`

**Interfaces:**
- Consumes: `StabilityResult` (Task 13), `recharts`' `BarChart`/`Bar`/`XAxis`/`ResponsiveContainer`/`ReferenceLine` and `lucide-react`'s icons (already installed dependencies, already used elsewhere in this app).
- Produces: `export default function StabilityPanel({ stability }: { stability: StabilityResult })` — imported by `AircraftDesigner.tsx` (Task 14). This is the last of the three view components, so this task also runs the full verification pass for the whole feature.

- [ ] **Step 1: Write the component**

Create `apps/aerocalc-web/components/aircraft/StabilityPanel.module.css`:

```css
.container {
  background-color: var(--card-bg, #f8fafc);
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
  color: #0f172a;
}

.heading {
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.warnings {
  list-style: none;
  margin: 0 0 0.75rem 0;
  padding: 0.5rem;
  background-color: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
}

.warningItem {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
  color: #b45309;
  padding: 0.15rem 0;
}

.section {
  margin-bottom: 0.75rem;
}

.sectionTitle {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
  margin-bottom: 0.35rem;
}

.statRow {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.25rem 0;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.85rem;
}

.statValue {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.iconStable { color: #16a34a; }
.iconMarginal { color: #d97706; }
.iconUnstable { color: #dc2626; }

.chartWrapper {
  margin-bottom: 0.75rem;
}
```

Create `apps/aerocalc-web/components/aircraft/StabilityPanel.tsx`:

```tsx
"use client";

import { AlertCircle, CheckCircle2, AlertTriangle } from "lucide-react";
import { BarChart, Bar, XAxis, ResponsiveContainer, ReferenceLine } from "recharts";
import styles from "./StabilityPanel.module.css";
import type { StabilityResult } from "../../lib/types";

function ClassificationIcon({ classification }: { classification: string }) {
  if (classification === "stable") return <CheckCircle2 size={16} className={styles.iconStable} />;
  if (classification === "marginal" || classification === "stable_sluggish")
    return <AlertTriangle size={16} className={styles.iconMarginal} />;
  return <AlertCircle size={16} className={styles.iconUnstable} />;
}

function StatRow({
  label, value, unit, classification,
}: { label: string; value: number; unit: string; classification?: string }) {
  return (
    <div className={styles.statRow}>
      <span>{label}</span>
      <span className={styles.statValue}>
        {value.toFixed(3)} {unit}
        {classification && <ClassificationIcon classification={classification} />}
      </span>
    </div>
  );
}

export default function StabilityPanel({ stability }: { stability: StabilityResult }) {
  const cgVsNpData = [
    { name: "MAC", np: stability.neutral_point_mac * 100 },
  ];

  return (
    <div className={styles.container}>
      <p className={styles.heading}>Static Stability Analysis</p>

      {stability.warnings.length > 0 && (
        <ul className={styles.warnings}>
          {stability.warnings.map((w, i) => (
            <li key={i} className={styles.warningItem}>
              <AlertTriangle size={14} /> {w}
            </li>
          ))}
        </ul>
      )}

      <div className={styles.section}>
        <p className={styles.sectionTitle}>Longitudinal</p>
        <StatRow label="Neutral Point" value={stability.neutral_point_mac * 100} unit="% MAC" />
        <StatRow label="CG Position" value={stability.cg_mac * 100} unit="% MAC" />
        <StatRow
          label="Static Margin"
          value={stability.static_margin_percent}
          unit="%"
          classification={stability.static_margin_classification}
        />
        <StatRow label="Cm-alpha" value={stability.cm_alpha} unit="/rad" />
        {stability.tail_volume_coefficient !== null && (
          <StatRow label="Tail Volume Coefficient" value={stability.tail_volume_coefficient} unit="" />
        )}
      </div>

      <div className={styles.chartWrapper} title="Neutral point (blue bar) vs CG (orange line) along the wing MAC, 0-100%">
        <ResponsiveContainer width="100%" height={80}>
          <BarChart layout="vertical" data={cgVsNpData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
            <XAxis type="number" domain={[0, 100]} hide />
            <Bar dataKey="np" fill="#38bdf8" barSize={12} />
            <ReferenceLine x={stability.cg_mac * 100} stroke="#f97316" strokeWidth={2} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className={styles.section}>
        <p className={styles.sectionTitle}>Lateral</p>
        <StatRow
          label="Cl-beta (dihedral effect)"
          value={stability.cl_beta}
          unit="/rad"
          classification={stability.cl_beta_classification}
        />
      </div>

      <div className={styles.section}>
        <p className={styles.sectionTitle}>Directional</p>
        <StatRow
          label="Cn-beta (weathercock)"
          value={stability.cn_beta}
          unit="/rad"
          classification={stability.cn_beta_classification}
        />
        {stability.vertical_tail_volume_coefficient !== null && (
          <StatRow label="Vertical Tail Volume Coefficient" value={stability.vertical_tail_volume_coefficient} unit="" />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Type-check the whole frontend**

Run: `cd apps/aerocalc-web && npx tsc --noEmit`
Expected: No errors. If there are errors in `AircraftDesigner.tsx`'s optional-field spreads (e.g. `prev.horizontal_tail` possibly `null`), fix them with the same `as AircraftSurface`-style assertions already used in that file's updater functions — every call site is already guarded by `config.horizontal_tail &&` (etc.) in the JSX before it can fire.

- [ ] **Step 3: Lint**

Run: `cd apps/aerocalc-web && npx eslint --max-warnings 0 components/aircraft`
Expected: No errors or warnings in the new `components/aircraft/` files specifically (the pre-existing 30 warnings elsewhere in the app, e.g. in `WingPlanformDesigner.tsx` and `DroneFlightSimulator.tsx`, are out of scope for this feature and are not touched by these tasks).

- [ ] **Step 4: Manual verification across all five configuration types**

Run: `cd apps/aerocalc-web && npm run dev` (and, in a separate terminal, start the API gateway: `cd apps/api-gateway && ../../.venv/Scripts/uvicorn.exe api_gateway.main:app --reload`).

Open the app, click "Aircraft Designer" in the sidebar, and for each of the 5 configuration-type options in the dropdown (Conventional, T-Tail, Canard, V-Tail, Flying Wing / Tailless):
- Confirm the correct sub-forms appear/disappear (e.g. Canard's form shows the Canard fieldset and Vertical Tail fieldset, not Horizontal Tail).
- Click Calculate and confirm all three view panels render without a browser console error: the three-view blueprint (dark navy panels with line outlines), the rotatable 3D wireframe (drag to orbit), and the stability panel (numeric readouts with colored classification icons, and — for the Flying Wing and Canard types — the expected warning banner).
- Confirm changing a field and clicking Calculate again updates all three views.

Stop both dev servers once verified.

- [ ] **Step 5: Commit**

```bash
git add apps/aerocalc-web/components/aircraft/StabilityPanel.tsx apps/aerocalc-web/components/aircraft/StabilityPanel.module.css
git commit -m "feat: add StabilityPanel readouts component, completing the aircraft designer tab"
```

---

## Task 18: Full-suite regression check

**Files:** none (verification only).

**Interfaces:** none.

- [ ] **Step 1: Run the full backend test suite**

Run: `cd D:/Downloads2/aerocalcdfm/backend-modules/aero-engine && ../../.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: All tests pass (wing_planform, models, geometry, stability — 30+ tests total).

- [ ] **Step 2: Run the root integration/smoke test**

Run: `cd D:/Downloads2/aerocalcdfm && ./.venv/Scripts/python.exe -m pytest test_api.py -v`
Expected: All 4 tests pass: `test_endpoints` (the original smoke test) plus the 3 new ones added in Task 12 — `test_aircraft_design_endpoint`, `test_aircraft_design_endpoint_rejects_mismatched_surfaces`, `test_aircraft_design_endpoint_rejects_zero_span`.

Also run it directly for the OK/FAIL print convention: `./.venv/Scripts/python.exe test_api.py`
Expected: All `[OK]` lines, no `[FAIL]`.

- [ ] **Step 3: Run the full frontend verification once more**

Run: `cd apps/aerocalc-web && npx tsc --noEmit && npx eslint --max-warnings 0 .`
Expected: `tsc` passes with no errors. `eslint` over the whole app still reports only the same 30 pre-existing warnings that were present before this feature (confirm the count hasn't grown) — this command will still exit non-zero because of `--max-warnings 0` against those pre-existing warnings; that is expected and matches the state before this plan started (see the original verification note in the design spec).

- [ ] **Step 4: Confirm no unrelated files changed**

Run: `cd D:/Downloads2/aerocalcdfm && git status` and `git diff --stat main` (or the appropriate base branch)
Expected: Only the files listed across Tasks 1-17's "Files" sections appear.

This task has no commit of its own — it's a pure verification gate before requesting review/merge.
