// Common Taiwan structural steel grades, sourced from the official CNS/JIS
// physical-property table (東和鋼鐵 "CNS、JIS、ASTM & AS/NZS 結構用材質規範
// 物理性質", covering CNS 13812/JIS G3136 建築結構用鋼, CNS 2473/JIS G3101
// 一般結構用鋼, CNS 2947/JIS G3106 銲接結構用鋼). Fy/Fu are the guaranteed
// minimum values (lower bound of the thickness-dependent range, t<=40mm) --
// shown for reference only, since the CEM Material schema is purely elastic
// (E/G/rho) and carries no strength fields. Every grade below shares the
// same elastic constants (steel's E/G/rho barely vary by grade); what
// differs is Fy/Fu, which is why this preset list still has one entry per
// grade rather than collapsing to a single "steel" row.
const STEEL_E = 2.0e11; // Pa (200 GPa)
const STEEL_G = 7.7e10; // Pa (77 GPa, from E/(2(1+nu)), nu=0.3)
const STEEL_RHO = 7850; // kg/m3

export interface SteelMaterialPreset {
  id: string;
  label: string;
  /** Guaranteed minimum yield strength, MPa -- reference only. */
  fy: number;
  /** Guaranteed minimum tensile strength, MPa -- reference only. */
  fu: number;
  E: number;
  G: number;
  rho: number;
}

export const STEEL_MATERIAL_PRESETS: SteelMaterialPreset[] = [
  { id: "SS400", label: "SS400 (CNS 2473 一般構造用鋼材)", fy: 235, fu: 400, E: STEEL_E, G: STEEL_G, rho: STEEL_RHO },
  { id: "SN400A", label: "SN400A (CNS 13812 建築結構用鋼材)", fy: 235, fu: 400, E: STEEL_E, G: STEEL_G, rho: STEEL_RHO },
  { id: "SN400B", label: "SN400B (CNS 13812，一般樑柱常用)", fy: 235, fu: 400, E: STEEL_E, G: STEEL_G, rho: STEEL_RHO },
  { id: "SN490B", label: "SN490B (CNS 13812，高強度樑柱)", fy: 325, fu: 490, E: STEEL_E, G: STEEL_G, rho: STEEL_RHO },
  { id: "SM490", label: "SM490A/B (CNS 2947 銲接結構用鋼材)", fy: 315, fu: 490, E: STEEL_E, G: STEEL_G, rho: STEEL_RHO },
  { id: "A36", label: "A36 (ASTM A36，美規常用)", fy: 250, fu: 400, E: STEEL_E, G: STEEL_G, rho: STEEL_RHO },
];
