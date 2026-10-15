// Common Taiwan normal-weight concrete grades. Ec follows 建築物混凝土結構
// 設計規範 §19.2.2.1(b) for normal-weight concrete (density 2300 kg/m3):
//   Ec = 4700 * sqrt(fc') MPa, fc' in MPa.
// Poisson's ratio taken as 0.20 (standard assumption for concrete), so
// G = E / (2*(1+0.20)) = E / 2.4.
//
// CNS 560 reinforcing bar grades: fy is reference-only (strength design,
// not used by this tool's elastic analysis), but E/G/rho ARE used -- the
// rebar transformed-section feature (FrameSection.rebar, see
// docs/ADR/0006-rebar-transformed-section.md) needs a real Material to
// reference for the rebar steel's modular ratio. All CNS 560 grades share
// the same elastic constants as structural steel (only fy differs by grade).
const CONCRETE_RHO = 2300; // kg/m3
const CONCRETE_NU = 0.2;
const REBAR_E = 2.0e11; // Pa (200 GPa)
const REBAR_G = 7.7e10; // Pa (77 GPa, from E/(2(1+nu)), nu=0.3)
const REBAR_RHO = 7850; // kg/m3

function ecFromFcPrimeMPa(fcPrimeMPa: number): number {
  return 4700 * Math.sqrt(fcPrimeMPa) * 1e6; // Pa
}

export interface ConcreteMaterialPreset {
  id: string;
  label: string;
  /** Specified compressive strength, MPa -- shown for reference. */
  fcPrime: number;
  E: number;
  G: number;
  rho: number;
}

export const CONCRETE_MATERIAL_PRESETS: ConcreteMaterialPreset[] = (
  [
    [21, "fc'=21 MPa (約 fc'210 kgf/cm²，常用於非結構配筋)"],
    [24, "fc'=24 MPa (約 fc'245 kgf/cm²)"],
    [28, "fc'=28 MPa (約 fc'280 kgf/cm²，常用樑柱)"],
    [35, "fc'=35 MPa (約 fc'350 kgf/cm²，高層柱常用)"],
    [42, "fc'=42 MPa (約 fc'420 kgf/cm²，高強度混凝土)"],
  ] as const
).map(([fcPrime, label]) => {
  const E = ecFromFcPrimeMPa(fcPrime);
  return {
    id: `C${fcPrime}`,
    label,
    fcPrime,
    E,
    G: E / (2 * (1 + CONCRETE_NU)),
    rho: CONCRETE_RHO,
  };
});

export interface RebarGradePreset {
  id: string;
  label: string;
  /** Guaranteed minimum yield strength, MPa -- reference only. */
  fy: number;
  E: number;
  G: number;
  rho: number;
}

/** CNS 560 reinforcing bar grades. `fy` is reference-only (strength
 * design); `E`/`G`/`rho` are what the rebar transformed-section feature
 * actually uses. */
export const REBAR_GRADES: RebarGradePreset[] = (
  [
    [280, "SD280 (CNS 560)"],
    [420, "SD420 (CNS 560，常用主筋)"],
    [490, "SD490 (CNS 560，高強度)"],
  ] as const
).map(([fy, label]) => ({
  id: `SD${fy}`,
  label,
  fy,
  E: REBAR_E,
  G: REBAR_G,
  rho: REBAR_RHO,
}));
