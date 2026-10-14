// Taiwan code load combinations and the standard live-load reference
// table. Sources:
//   - LRFD combinations: 建築物混凝土結構設計規範 (112年/2023) §5.3.1,
//     equations (5.3.1a)-(5.3.1g). The same factor set is shared by
//     Taiwan's steel ultimate-strength design code (鋼結構極限設計法規範).
//   - ASD combinations: 鋼結構容許應力設計法規範 §2.2, equations
//     (2.2-1)-(2.2-5).
//   - Live load table: 建築技術規則建築構造編 第17條 (current A-I
//     occupancy-group table), kgf/m2.
//
// "Lr" below stands in for the code's "(Lr or S or R)" roof-live/snow/rain
// term -- Taiwan's lowland building stock is overwhelmingly roof-live-
// governed rather than snow-governed, so this wizard doesn't offer a
// separate snow role. If a project genuinely needs S or R, tag that load
// case as "Lr" too; the combination math is identical (they're mutually
// exclusive alternatives in the code, not summed).

export type LoadRole = "D" | "L" | "Lr" | "W" | "E";

export const LOAD_ROLES: { role: LoadRole; label: string }[] = [
  { role: "D", label: "靜載重 D (結構自重與固定荷載)" },
  { role: "L", label: "活載重 L" },
  { role: "Lr", label: "屋頂活載重/雪載重/雨載重 Lr" },
  { role: "W", label: "風力 W" },
  { role: "E", label: "地震力 E" },
];

export interface ComboTerm {
  role: LoadRole;
  factor: number;
}

export interface LoadCombination {
  id: string;
  formula: string;
  terms: ComboTerm[];
  /** Roles whose factor may act with either sign (wind/seismic reversal). */
  reversibleRoles?: LoadRole[];
  source: string;
}

export const LRFD_COMBINATIONS: LoadCombination[] = [
  { id: "5.3.1a", formula: "1.4D", terms: [{ role: "D", factor: 1.4 }], source: "建築物混凝土結構設計規範 §5.3.1a" },
  {
    id: "5.3.1b",
    formula: "1.2D + 1.6L + 0.5Lr",
    terms: [{ role: "D", factor: 1.2 }, { role: "L", factor: 1.6 }, { role: "Lr", factor: 0.5 }],
    source: "建築物混凝土結構設計規範 §5.3.1b",
  },
  {
    id: "5.3.1c",
    formula: "1.2D + 1.6Lr + 1.0L",
    terms: [{ role: "D", factor: 1.2 }, { role: "Lr", factor: 1.6 }, { role: "L", factor: 1.0 }],
    source: "建築物混凝土結構設計規範 §5.3.1c",
  },
  {
    id: "5.3.1d",
    formula: "1.2D + 1.6W + 1.0L + 0.5Lr",
    terms: [
      { role: "D", factor: 1.2 },
      { role: "W", factor: 1.6 },
      { role: "L", factor: 1.0 },
      { role: "Lr", factor: 0.5 },
    ],
    reversibleRoles: ["W"],
    source: "建築物混凝土結構設計規範 §5.3.1d",
  },
  {
    id: "5.3.1e",
    formula: "1.2D + 1.0E + 1.0L",
    terms: [{ role: "D", factor: 1.2 }, { role: "E", factor: 1.0 }, { role: "L", factor: 1.0 }],
    reversibleRoles: ["E"],
    source: "建築物混凝土結構設計規範 §5.3.1e (原式含 0.2S，台灣低地案例通常無雪載重)",
  },
  { id: "5.3.1f", formula: "0.9D + 1.6W", terms: [{ role: "D", factor: 0.9 }, { role: "W", factor: 1.6 }], reversibleRoles: ["W"], source: "建築物混凝土結構設計規範 §5.3.1f" },
  { id: "5.3.1g", formula: "0.9D + 1.0E", terms: [{ role: "D", factor: 0.9 }, { role: "E", factor: 1.0 }], reversibleRoles: ["E"], source: "建築物混凝土結構設計規範 §5.3.1g" },
];

export const ASD_COMBINATIONS: LoadCombination[] = [
  { id: "2.2-1", formula: "D + L", terms: [{ role: "D", factor: 1.0 }, { role: "L", factor: 1.0 }], source: "鋼結構容許應力設計法規範 §2.2-1" },
  {
    id: "2.2-2",
    formula: "D + 0.75L + 0.9375W",
    terms: [{ role: "D", factor: 1.0 }, { role: "L", factor: 0.75 }, { role: "W", factor: 0.75 * 1.25 }],
    reversibleRoles: ["W"],
    source: "鋼結構容許應力設計法規範 §2.2-2：D + 0.75(L ± 1.25W)",
  },
  {
    id: "2.2-3",
    formula: "D + 0.75L + 0.6E",
    terms: [{ role: "D", factor: 1.0 }, { role: "L", factor: 0.75 }, { role: "E", factor: 0.75 * 0.8 }],
    reversibleRoles: ["E"],
    source: "鋼結構容許應力設計法規範 §2.2-3：D + 0.75(L ± 0.8E)",
  },
  {
    id: "2.2-4",
    formula: "0.7D + 1.25W",
    terms: [{ role: "D", factor: 0.7 }, { role: "W", factor: 1.25 }],
    reversibleRoles: ["W"],
    source: "鋼結構容許應力設計法規範 §2.2-4",
  },
  {
    id: "2.2-5",
    formula: "0.7D + 0.8E",
    terms: [{ role: "D", factor: 0.7 }, { role: "E", factor: 0.8 }],
    reversibleRoles: ["E"],
    source: "鋼結構容許應力設計法規範 §2.2-5",
  },
];

export interface LiveLoadEntry {
  group: string;
  category: string;
  kgfPerM2: number;
}

/** 建築技術規則建築構造編 第17條 -- representative subset of the current
 * (A-I occupancy group) table, not exhaustive. Consult the full article
 * text for anything not listed here. */
export const LIVE_LOAD_TABLE: LiveLoadEntry[] = [
  { group: "A-1", category: "集會表演（具固定座位之戲院、電影院、禮堂等）", kgfPerM2: 300 },
  { group: "A-1", category: "集會表演（無固定座位、體育館觀眾席）", kgfPerM2: 400 },
  { group: "A-2", category: "運輸場所（車站、航空站）", kgfPerM2: 400 },
  { group: "B-2", category: "百貨商場、展覽場、量販店", kgfPerM2: 500 },
  { group: "B-3", category: "餐飲場所", kgfPerM2: 300 },
  { group: "B-4", category: "旅館客房", kgfPerM2: 200 },
  { group: "C-1/C-2", category: "工廠、工作場", kgfPerM2: 500 },
  { group: "—", category: "倉庫、書庫", kgfPerM2: 600 },
  { group: "D-1", category: "健身休閒（撞球、健身房等）", kgfPerM2: 400 },
  { group: "D-2", category: "文教設施（圖書館、博物館、集會堂）", kgfPerM2: 300 },
  { group: "D-3/D-4", category: "國小／國高中大學教室、教學大樓", kgfPerM2: 250 },
  { group: "F-1", category: "醫院病房", kgfPerM2: 200 },
  { group: "G-1/G-2/G-3", category: "辦公室、金融機構、一般零售店舖", kgfPerM2: 300 },
  { group: "H-1/H-2", category: "集合住宅、住宅、宿舍", kgfPerM2: 200 },
  { group: "—", category: "車庫及停車場", kgfPerM2: 500 },
  { group: "—", category: "走廊、樓梯（與室同，人群聚集場所不得少於）", kgfPerM2: 500 },
  { group: "—", category: "屋頂露臺（室載重減 50，人群聚集場所不得少於 300）", kgfPerM2: 300 },
];
