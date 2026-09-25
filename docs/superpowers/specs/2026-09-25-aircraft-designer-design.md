# Fixed-Wing Aircraft Configurator — Design Spec

**Date:** 2026-09-25
**Status:** Approved for implementation planning
**Author:** Jason (with Claude)

## 1. Purpose & Scope

Add a new calculator tab to `aerocalc-web`, **Aircraft Designer**, that lets a
student or researcher parametrically define a fixed-wing aircraft
(conventional, flying-wing/tailless, canard, T-tail, or V-tail), see it drawn
as an engineering blueprint (2D three-view + interactive 3D wireframe), and
read a full static stability analysis (longitudinal, lateral, directional).

This is explicitly **lower-fidelity than OpenVSP/Aviary/FLOPS/Cart3D**: no
CFD, no panel-method aero for the whole aircraft, no mission sizing. It uses
classical semi-empirical component-buildup methods (the same family of
formulas taught in Roskam's *Airplane Design* series and Raymer's *Aircraft
Design: A Conceptual Approach*), matching the fidelity level of this repo's
existing `wing_planform.py` and `polar_curves.py` modules. The stated goal is
educational supplementation, not production aircraft certification — every
result the UI shows must be traceable to a named formula so a student can
hand-check it.

**Out of scope for v1:** dynamic stability (eigenvalue/mode analysis),
trim/control-surface sizing, propulsion integration, mass/inertia buildup
beyond a single CG point mass, persistence (save/load), fuselage aerodynamic
contributions beyond a simple outline, twin vertical tails.

## 2. Configuration Model

New Pydantic models in `aero_engine/aircraft/models.py`:

```python
class Surface(BaseModel):
    span: float              # full span, meters (single fin: use height instead — see VerticalTail)
    root_chord: float        # meters
    tip_chord: float         # meters
    sweep_deg: float = 0.0   # quarter-chord sweep, degrees
    dihedral_deg: float = 0.0
    twist_deg: float = 0.0   # washout, negative = tip washout
    airfoil: str = "0012"    # NACA 4-digit, used for Cl_alpha estimate
    x_position: float        # LE root position, meters aft of nose
    z_position: float = 0.0  # vertical position, meters (fuselage waterline)
    mount: Literal["high", "mid", "low"] = "mid"

class VerticalTail(BaseModel):
    height: float             # single-fin span, meters
    root_chord: float
    tip_chord: float
    sweep_deg: float = 0.0
    airfoil: str = "0012"
    x_position: float
    z_position: float = 0.0

class VTail(BaseModel):
    span: float                # full span of both panels combined, meters
    root_chord: float
    tip_chord: float
    dihedral_v_deg: float      # angle of each panel from horizontal, typically 35-45deg
    sweep_deg: float = 0.0
    airfoil: str = "0012"
    x_position: float
    z_position: float = 0.0

class Fuselage(BaseModel):
    length: float
    max_width: float
    max_height: float
    nose_length: float   # length of nose taper section
    tail_length: float   # length of tail taper section

class MassProperties(BaseModel):
    mass_kg: float
    cg_x_position: float    # meters aft of nose
    cruise_speed_ms: float  # used only to estimate trim CL for the Cl-beta sweep term (4.2);
                             # sea-level standard density (rho=1.225 kg/m^3) is assumed —
                             # no altitude/atmosphere model in v1

class AircraftConfig(BaseModel):
    configuration_type: Literal[
        "conventional", "flying_wing", "canard", "t_tail", "v_tail"
    ]
    wing: Surface
    horizontal_tail: Surface | None = None   # conventional, t_tail
    vertical_tail: VerticalTail | None = None  # conventional, t_tail, canard
    canard: Surface | None = None              # canard only
    v_tail: VTail | None = None                # v_tail only
    fuselage: Fuselage
    mass: MassProperties
```

A validator enforces the right surfaces are present/absent for each
`configuration_type` (e.g. `v_tail` requires `v_tail` and forbids
`horizontal_tail`/`vertical_tail`; `flying_wing` forbids all tail surfaces)
and raises a 400 with a clear message otherwise — mirrors the existing
`HTTPException(400, str(e))` pattern in `aero.py`.

All positions are in a single coordinate frame: origin at the nose tip,
**x** aft, **y** starboard (right), **z** up — standard aircraft-body-ish
convention, consistent for both the 2D and 3D geometry output.

## 3. Geometry Module (`aero_engine/aircraft/geometry.py`)

### 3.1 Shared planform helper
Refactor the area/AR/taper/MAC/y_mac/x_mac_le math currently inline in
`wing_planform.calculate_wing_planform` into a new shared function:

```python
def calculate_surface_planform(span, root_chord, tip_chord, sweep_angle_deg) -> dict
```

`wing_planform.calculate_wing_planform` becomes a thin wrapper calling this
and returning its existing dict shape unchanged — **existing `/aero/wing-planform`
endpoint behavior and response schema is untouched**, verified by the
existing `test_api.py` wing-planform assertion continuing to pass.

The aircraft module calls `calculate_surface_planform` for the wing,
horizontal tail, canard, and (using effective areas, §4.4) the V-tail.

### 3.2 Per-surface point generation
For each present surface, generate:

- **Planform corners** (root LE, root TE, tip LE, tip TE) using span/2 (mirrored
  for the other half), sweep (converted from quarter-chord to leading-edge
  sweep using root/tip chord), dihedral (z-offset at tip = `(span/2) *
  tan(dihedral_rad)`), and twist (stored for reference, not drawn).
- **3-view projections**: `top_view` (x,y pairs — planform as seen from above),
  `front_view` (y,z pairs — as seen from the nose), `side_view` (x,z pairs —
  as seen from the side), each as a closed polygon (root LE → tip LE → tip TE
  → root TE → root LE) for the surface and its mirror.
- **3D wireframe**: vertex list `[[x,y,z], ...]` and edge index pairs
  `[[i,j], ...]` outlining the same quadrilateral(s) for the Three.js view.

### 3.3 Fuselage outline
A simple longitudinal profile: nose taper (linear from a point to
`max_width`/`max_height` over `nose_length`), constant mid-section, tail
taper (linear down to a point over `tail_length`) — enough for a
recognizable blueprint silhouette in side/top view, and a stadium-shaped
(rounded rectangle) cross-section in front view. Not used in any stability
calculation (documented limitation, §4).

### 3.4 Output shape
```python
class SurfaceGeometry(BaseModel):
    top_view: list[list[float]]
    front_view: list[list[float]]
    side_view: list[list[float]]
    vertices: list[list[float]]
    edges: list[list[int]]
    planform: dict  # calculate_surface_planform() output

class AircraftGeometry(BaseModel):
    wing: SurfaceGeometry
    horizontal_tail: SurfaceGeometry | None
    vertical_tail: SurfaceGeometry | None
    canard: SurfaceGeometry | None
    v_tail: SurfaceGeometry | None
    fuselage: SurfaceGeometry  # planform=None for fuselage
```

## 4. Stability Module (`aero_engine/aircraft/stability.py`)

All formulas below are standard subsonic-conceptual-design estimates
(Roskam Part VI / Raymer Ch. 16 style). Each is a named, independently
testable function. `Cl_alpha` per surface (2D lift-curve slope) is estimated
from thin-airfoil theory (`2*pi` per radian) corrected to 3D finite-span via
the standard Polhamus/DATCOM approximation:

```
CL_alpha_3D = (2*pi*AR) / (2 + sqrt(4 + (AR^2 * beta^2 / eta^2) * (1 + tan^2(sweep_half_chord)/beta^2)))
```
(with `beta = sqrt(1 - M^2)`, `M = 0` assumed — incompressible — and
`eta ≈ 0.95`), falling back to `2*pi*AR/(AR+2)` (simpler low-AR-safe form)
if that expression is undefined for degenerate inputs.

### 4.1 Longitudinal — neutral point & static margin
Uses the general two-lifting-surface formula, which handles canards as the
same equation with a signed moment arm (canard ahead of wing ⇒ negative
`l`):

```
h_ac_wing = 0.25   (quarter-chord AC, standard subsonic assumption)
downwash: deps_dalpha = 2 * CL_alpha_wing / (pi * AR_wing)
l = (other_surface_AC_x - wing_AC_x)   # signed: positive if aft (tail), negative if fwd (canard)
V_H = (S_other * l) / (S_wing * MAC_wing)   # tail volume coefficient (or canard volume coeff)

h_n = h_ac_wing + (CL_alpha_other / CL_alpha_wing) * (S_other/S_wing) * (l/MAC_wing) * (1 - deps_dalpha)
static_margin = h_n - h_cg      # h_cg = (cg_x - wing_AC_x) / MAC_wing, expressed as fraction of MAC
Cm_alpha = -CL_alpha_wing * static_margin    # per radian, whole-aircraft
```

For `flying_wing`: `h_n = h_ac_wing` (no other-surface term); UI must show a
note that reflex/washout trim is not modeled.

Classification: `static_margin < 0` → **unstable**; `0 ≤ sm < 0.05` →
**marginal**; `0.05 ≤ sm ≤ 0.20` → **stable**; `sm > 0.20` → **stable
(sluggish — very high control forces)**.

### 4.2 Lateral — dihedral effect (Cl-β)
```
CL_trim = (mass_kg * 9.81) / (0.5 * 1.225 * cruise_speed_ms^2 * S_wing)   # sea-level, steady level flight

Cl_beta_dihedral ≈ -(CL_alpha_wing / 4) * dihedral_rad
Cl_beta_sweep    ≈ -CL_trim * tan(sweep_deg) / (pi * AR_wing)
Cl_beta_total = Cl_beta_dihedral + Cl_beta_sweep
```
Negative = stable (restoring roll moment). Classification: `< -0.02` stable,
`-0.02..0` marginal, `> 0` unstable (thresholds documented as rule-of-thumb,
not exact — shown alongside the raw number, not as the only output).

### 4.3 Directional — weathercock stability (Cn-β)
```
V_V = (S_vtail * l_vtail) / (S_wing * span_wing)     # vertical tail volume coefficient
Cn_beta ≈ CL_alpha_vtail * V_V * (1 - dsigma_dbeta)   # dsigma_dbeta ≈ 0 (no sidewash model, documented limitation)
```
Positive = stable. Fuselage side-area destabilizing contribution is
explicitly **not modeled** (would need fuselage side-profile area + moment
arm we don't collect) — documented as a known simplification in both the
spec and a UI tooltip, so results read slightly optimistic versus a real
aircraft.

### 4.4 V-tail equivalent-area projection
Standard V-tail decomposition (Raymer 6.7):
```
S_h_eff = S_vtail_total * cos(dihedral_v_rad)^2
S_v_eff = S_vtail_total * sin(dihedral_v_rad)^2
```
These effective areas + the V-tail's `x_position`/span feed directly into
the §4.1 and §4.3 formulas in place of `horizontal_tail`/`vertical_tail`.

### 4.5 Output shape
```python
class StabilityResult(BaseModel):
    neutral_point_mac: float          # fraction of MAC from wing LE
    cg_mac: float                     # fraction of MAC from wing LE
    static_margin_percent: float
    static_margin_classification: Literal["unstable","marginal","stable","stable_sluggish"]
    cm_alpha: float
    tail_volume_coefficient: float | None
    cl_beta: float
    cl_beta_classification: Literal["unstable","marginal","stable"]
    cn_beta: float
    cn_beta_classification: Literal["unstable","marginal","stable"]
    vertical_tail_volume_coefficient: float | None
    warnings: list[str]   # e.g. "Flying wing: trim/reflex not modeled", "CG aft of neutral point: UNSTABLE"
```

## 5. API

New `apps/api-gateway/api_gateway/routers/aircraft.py`:

```python
router = APIRouter(prefix="/aircraft", tags=["Aircraft Design"])

@router.post("/design")
def design_aircraft(config: AircraftConfig) -> AircraftDesignResponse:
    ...
```

```python
class AircraftDesignResponse(BaseModel):
    geometry: AircraftGeometry
    stability: StabilityResult
```

Registered in `main.py` alongside the existing routers
(`app.include_router(aircraft.router)`). Errors follow the existing
`try/except Exception -> HTTPException(400, str(e))` convention used
throughout `aero.py`.

## 6. Frontend

### 6.1 Navigation
`Sidebar.tsx` gets a new item, tab id `"aircraft"`, icon `DraftingCompass`
(lucide-react, already available in the installed version) or `PlaneTakeoff`
if unavailable — resolved at implementation time by checking the installed
icon set. `page.tsx` renders `<AircraftDesigner />` for that tab, same
pattern as every other calculator.

### 6.2 Types (`lib/types.ts`)
Add TypeScript interfaces mirroring the new Pydantic models 1:1 (matching
the existing `/** Mirrors aero_engine.multirotor_performance.PerformanceResults */`
convention): `AircraftConfig`, `SurfaceGeometry`, `AircraftGeometry`,
`StabilityResult`, `AircraftDesignResponse`.

### 6.3 Components (`components/aircraft/`)

- **`AircraftDesigner.tsx`** — top-level container. Local `useState` for the
  config object (same pattern as `WingPlanformDesigner`/`MultirotorConfigurator`,
  no new context needed — this doesn't need to be shared across tabs the way
  drone config is). A `configuration_type` selector (`<select>`) conditionally
  renders the wing/htail/vtail/canard/v-tail sub-forms. "Calculate" button →
  `POST /aircraft/design` → `results` state → passed down to the three view
  components. Client-side validation before submit: span/chords > 0, CG
  within `[0, fuselage.length]`, mirrors the light validation style already
  used (inline `error` state + banner).
- **`BlueprintView.tsx`** — SVG three-view. Auto-computed `viewBox` from the
  returned point extents (padding for dimension lines). Drafting-table
  aesthetic: dark navy background (`#0a1628`-ish), thin cyan/white stroke
  lines (`stroke-width: 1`), dimension arrows + text for span, overall
  length, and MAC — a deliberate departure from the app's default
  light/dark theme toward a literal blueprint look, contained entirely
  within this component's CSS module so it doesn't affect global theming.
- **`Blueprint3D.tsx`** — `@react-three/fiber` `<Canvas>` with `OrbitControls`
  (from `@react-three/drei`, already a dependency), rendering each surface's
  edges as `<Line>` segments (wireframe) with an option to toggle a
  semi-transparent shaded mesh. Reuses the same client-only dynamic-import
  pattern as `DroneFlightSimulator` (`ssr: false`) since R3F/WebGL can't
  SSR.
- **`StabilityPanel.tsx`** — numeric readouts grouped by axis
  (longitudinal/lateral/directional), color-coded badges per
  classification (green/yellow/red, reusing existing `AlertCircle`/
  `CheckCircle2` icon conventions from `MultirotorConfigurator.tsx`), and a
  `recharts` horizontal bar showing the wing MAC with CG and neutral-point
  markers (same library already used in `AirfoilAnalyzer`/`NacaGenerator`/
  `PolarCurveGenerator`, so no new dependency). Every derivative shows its
  formula name as a `title` tooltip, consistent with existing input-field
  tooltips in this app.

### 6.4 Styling
One `.module.css` per component, following the existing per-component CSS
Modules convention (no new styling system introduced).

## 7. Testing

### 7.1 Backend unit tests (new `backend-modules/aero-engine/tests/`)
`pytest` added as a dev dependency in `aero-engine/pyproject.toml`
(`[project.optional-dependencies] test = ["pytest>=8"]`).

- `test_geometry.py`: mirrored half-spans produce symmetric y-coordinates;
  dihedral produces correct tip z-offset sign; sweep produces correct tip
  x-offset direction; point/vertex counts match expectations for a known
  config.
- `test_stability.py`:
  - A conventional-aircraft config with Cessna-172-like proportions (wing
    AR ≈ 7.3, tail volume coefficient ≈ 0.5, CG at 25% MAC) yields a
    positive static margin in the 5–15% range.
  - Moving `mass.cg_x_position` aft past the computed neutral point flips
    `static_margin_classification` to `"unstable"`.
  - A canard config (negative `l`) still produces a finite, correctly-signed
    neutral point via the same formula path (regression check that the
    signed-arm generalization works).
  - V-tail effective-area projection: a `dihedral_v_deg = 90` V-tail
    (degenerate case) reduces to a pure vertical tail (`S_h_eff ≈ 0`); `0`
    reduces to a pure horizontal tail (`S_v_eff ≈ 0`).

### 7.2 Backend integration smoke test
Append `test_aircraft_endpoint()` to the existing root `test_api.py`,
following its existing print-based OK/FAIL convention: POST a conventional
config to `/aircraft/design`, assert 200 and that `stability.static_margin_percent`
is present and numeric.

### 7.3 Frontend
No new test framework (matches current repo state — `aerocalc-web` has no
test runner configured today). Verification is `tsc --noEmit` +
`eslint --max-warnings 0` (fixing the pre-existing 30 warnings is **out of
scope** for this feature unless new code triggers new ones) + manual
`npm run dev` check that all three views render and update on Calculate for
each of the 5 configuration types.

## 8. File Inventory

**New files:**
- `backend-modules/aero-engine/aero_engine/aircraft/__init__.py`
- `backend-modules/aero-engine/aero_engine/aircraft/models.py`
- `backend-modules/aero-engine/aero_engine/aircraft/geometry.py`
- `backend-modules/aero-engine/aero_engine/aircraft/stability.py`
- `backend-modules/aero-engine/tests/__init__.py`
- `backend-modules/aero-engine/tests/test_geometry.py`
- `backend-modules/aero-engine/tests/test_stability.py`
- `apps/api-gateway/api_gateway/routers/aircraft.py`
- `apps/aerocalc-web/components/aircraft/AircraftDesigner.tsx` (+ `.module.css`)
- `apps/aerocalc-web/components/aircraft/BlueprintView.tsx` (+ `.module.css`)
- `apps/aerocalc-web/components/aircraft/Blueprint3D.tsx` (+ `.module.css`)
- `apps/aerocalc-web/components/aircraft/StabilityPanel.tsx` (+ `.module.css`)

**Modified files:**
- `backend-modules/aero-engine/aero_engine/wing_planform.py` (extract shared helper, behavior-preserving)
- `backend-modules/aero-engine/pyproject.toml` (add pytest dev dependency)
- `apps/api-gateway/api_gateway/main.py` (register new router)
- `apps/aerocalc-web/components/Sidebar.tsx` (new nav item)
- `apps/aerocalc-web/app/page.tsx` (new tab render branch)
- `apps/aerocalc-web/lib/types.ts` (new interfaces)
- `test_api.py` (new smoke test function)

## 9. Known Limitations (surfaced in-app, not hidden)

- No fuselage aerodynamic contribution to Cn-β (slightly optimistic directional stability).
- No sidewash (`dsigma/dbeta = 0` assumed).
- Flying-wing trim (reflex/washout) not modeled — CG-vs-AC check only.
- Incompressible flow only (M = 0); no compressibility correction.
- Static analysis only — no dynamic modes (phugoid, short-period, dutch roll, spiral).
- Single vertical tail only (no twin-tail configs in v1).
- Fuselage is a visual outline only, not a lifting/moment-contributing body.
