// Common Taiwan normal-weight concrete grades. Ec follows 建築物混凝土結構
// 設計規範 §19.2.2.1(b) for normal-weight concrete (density 2300 kg/m3):
//   Ec = 4700 * sqrt(fc') MPa, fc' in MPa.
// Poisson's ratio taken as 0.20 (standard assumption for concrete), so
// G = E / (2*(1+0.20)) = E / 2.4.
//
// Rebar yield strengths (CNS 560) are included for reference only -- they
// are a strength-design input, not an elastic-analysis one, so they are not
// written into the CEM Material (which only carries E/G/rho). Use them when
// labeling reinforcement, not when filling this wizard's Material fields.
const CONCRETE_RHO = 2300; // kg/m3
const CONCRETE_NU = 0.2;

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

/** CNS 560 reinforcing bar grades -- fy for reference only (strength
 * design, not used by this tool's elastic analysis). */
export const REBAR_GRADES: { id: string; fy: number }[] = [
  { id: "SD280", fy: 280 },
  { id: "SD420", fy: 420 },
  { id: "SD490", fy: 490 },
];
