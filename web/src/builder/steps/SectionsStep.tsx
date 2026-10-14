import { useState } from "react";
import { AddRowForm, DataTable, NumberField, SelectField, TextField } from "../fields";
import { SectionDiagram } from "../SectionDiagram";
import { H_BEAM_PRESETS, rectangularSection, SQUARE_TUBE_PRESETS } from "../presets/steelSections";
import type { StepProps } from "./types";

const SECTION_PRESETS = [...H_BEAM_PRESETS, ...SQUARE_TUBE_PRESETS];

interface DraftBar {
  y: number;
  z: number;
  diameter: number;
}

/** Symmetric (about y=0 and/or z=0) layouts only -- matches the
 * backend's mirror-symmetry requirement (docs/ADR/0006-rebar-transformed-section.md)
 * so anyone using these generators always gets a layout the backend
 * will accept. */
function cornerBars(width: number, depth: number, dia: number, cover: number): DraftBar[] {
  const y0 = width / 2 - cover - dia / 2;
  const z0 = depth / 2 - cover - dia / 2;
  return [
    { y: y0, z: z0, diameter: dia },
    { y: -y0, z: z0, diameter: dia },
    { y: y0, z: -z0, diameter: dia },
    { y: -y0, z: -z0, diameter: dia },
  ];
}

function topBottomBars(
  width: number,
  depth: number,
  dia: number,
  cover: number,
  perRow: number,
): DraftBar[] {
  const y0 = width / 2 - cover - dia / 2;
  const z0 = depth / 2 - cover - dia / 2;
  const ys =
    perRow === 1
      ? [0]
      : Array.from({ length: perRow }, (_, i) => -y0 + (2 * y0 * i) / (perRow - 1));
  return ys.flatMap((y) => [
    { y, z: z0, diameter: dia },
    { y, z: -z0, diameter: dia },
  ]);
}

const REBAR_PATTERNS: {
  label: string;
  generate: (width: number, depth: number, dia: number, cover: number) => DraftBar[];
}[] = [
  { label: "4 角鋼筋", generate: cornerBars },
  { label: "6 根 (3上3下)", generate: (w, d, dia, c) => topBottomBars(w, d, dia, c, 3) },
  { label: "8 根 (4上4下)", generate: (w, d, dia, c) => topBottomBars(w, d, dia, c, 4) },
];

export function SectionsStep({ model, setModel }: StepProps) {
  const [id, setId] = useState("");
  const [A, setA] = useState<number | "">("");
  const [Iy, setIy] = useState<number | "">("");
  const [Iz, setIz] = useState<number | "">("");
  const [J, setJ] = useState<number | "">("");
  const [preset, setPreset] = useState("");
  const [rectWidth, setRectWidth] = useState<number | "">("");
  const [rectDepth, setRectDepth] = useState<number | "">("");

  const [rebarMaterialId, setRebarMaterialId] = useState("");
  const [rebarBars, setRebarBars] = useState<DraftBar[]>([]);
  const [barY, setBarY] = useState<number | "">("");
  const [barZ, setBarZ] = useState<number | "">("");
  const [barDiameter, setBarDiameter] = useState<number | "">(0.016);
  const [patternCover, setPatternCover] = useState<number | "">(0.04);

  const applyPreset = (label: string) => {
    setPreset(label);
    const p = SECTION_PRESETS.find((s) => s.label === label);
    if (!p) return;
    setA(p.A);
    setIy(p.Iy);
    setIz(p.Iz);
    setJ(p.J);
    if (id.trim() === "") setId(p.id);
    // H-beams/tubes are steel, not RC -- rebar is an RC-only concept.
    setRebarBars([]);
  };

  const applyRectangular = () => {
    if (rectWidth === "" || rectDepth === "") return;
    const { A: rA, Iy: rIy, Iz: rIz, J: rJ } = rectangularSection(
      Number(rectWidth),
      Number(rectDepth),
    );
    setA(rA);
    setIy(rIy);
    setIz(rIz);
    setJ(rJ);
  };

  const applyPattern = (generate: (typeof REBAR_PATTERNS)[number]["generate"]) => {
    if (rectWidth === "" || rectDepth === "" || barDiameter === "" || patternCover === "") return;
    setRebarBars(
      generate(Number(rectWidth), Number(rectDepth), Number(barDiameter), Number(patternCover)),
    );
  };

  const addBar = () => {
    if (barY === "" || barZ === "" || barDiameter === "") return;
    setRebarBars((prev) => [...prev, { y: Number(barY), z: Number(barZ), diameter: Number(barDiameter) }]);
  };

  const canAdd =
    id.trim() !== "" &&
    A !== "" &&
    Iy !== "" &&
    Iz !== "" &&
    J !== "" &&
    !model.sections.some((s) => s.id === id.trim());

  const handleAdd = () => {
    if (!canAdd) return;
    const rebar =
      rebarBars.length > 0 && rebarMaterialId !== ""
        ? { material_id: rebarMaterialId, bars: rebarBars }
        : undefined;
    setModel((prev) => ({
      ...prev,
      sections: [
        ...prev.sections,
        {
          id: id.trim(),
          A: Number(A),
          Iy: Number(Iy),
          Iz: Number(Iz),
          J: Number(J),
          ...(rebar ? { rebar } : {}),
        },
      ],
    }));
    setId("");
    setA("");
    setIy("");
    setIz("");
    setJ("");
    setRebarBars([]);
  };

  const hasRectDims = rectWidth !== "" && rectDepth !== "";

  return (
    <div className="step">
      <h2>Sections</h2>
      <p className="step__hint">
        A, Iy, Iz, J in SI units (m², m⁴). Local-axis orientation (for 3D frame analysis) uses a
        default fallback when not set explicitly here -- see the viewer's warnings after running
        an analysis if that matters for your model.
      </p>
      <div className="add-row-form">
        <SelectField
          label="常用鋼斷面預設 (H型鋼／方形鋼管)"
          value={preset}
          options={SECTION_PRESETS.map((p) => p.label)}
          onChange={applyPreset}
          placeholder="選擇斷面…"
        />
      </div>
      <div className="add-row-form">
        <NumberField label="矩形寬 b (m)" value={rectWidth} onChange={setRectWidth} />
        <NumberField label="矩形深 h (m)" value={rectDepth} onChange={setRectDepth} />
        <button type="button" onClick={applyRectangular} disabled={!hasRectDims}>
          套用矩形斷面 (RC 常用)
        </button>
      </div>

      {hasRectDims && (
        <div className="step__rebar">
          <h3>配筋 (選填，RC 矩形斷面)</h3>
          <p className="step__hint">
            配筋會透過換算斷面法真正影響分析結果（見 ADR 0006），不只是示意。鋼筋座標必須對稱於
            y=0 或 z=0 軸（下面的常用配筋產生器已自動滿足這個條件）。
          </p>
          <div className="add-row-form">
            <SelectField
              label="鋼筋材料"
              value={rebarMaterialId}
              options={model.materials.map((m) => m.id)}
              onChange={setRebarMaterialId}
              placeholder="選擇材料…"
            />
            <NumberField label="鋼筋直徑 (m)" value={barDiameter} onChange={setBarDiameter} />
            <NumberField label="保護層 cover (m)" value={patternCover} onChange={setPatternCover} />
          </div>
          {model.materials.length === 0 && (
            <p className="step__warning">
              尚未建立任何材料 -- 先到「Materials」步驟加入鋼筋材料（例如 SD420）才能選取。
            </p>
          )}
          <div className="add-row-form">
            {REBAR_PATTERNS.map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => applyPattern(p.generate)}
                disabled={barDiameter === "" || patternCover === ""}
              >
                {p.label}
              </button>
            ))}
            <button type="button" onClick={() => setRebarBars([])} disabled={rebarBars.length === 0}>
              清空
            </button>
          </div>
          <div className="add-row-form">
            <NumberField label="y (m)" value={barY} onChange={setBarY} />
            <NumberField label="z (m)" value={barZ} onChange={setBarZ} />
            <button type="button" onClick={addBar} disabled={barY === "" || barZ === "" || barDiameter === ""}>
              手動加一根
            </button>
          </div>
          <div className="section-rebar-preview">
            <SectionDiagram widthM={Number(rectWidth)} depthM={Number(rectDepth)} bars={rebarBars} />
            <DataTable
              columns={[
                { key: "y", label: "y" },
                { key: "z", label: "z" },
                { key: "diameter", label: "直徑" },
              ]}
              rows={rebarBars}
              rowKey={(b) => `${b.y},${b.z},${b.diameter}`}
              renderCell={(b, key) => (key === "y" ? b.y : key === "z" ? b.z : b.diameter)}
              onRemove={(b) =>
                setRebarBars((prev) =>
                  prev.filter((x) => !(x.y === b.y && x.z === b.z && x.diameter === b.diameter)),
                )
              }
              emptyMessage="尚未加入鋼筋 -- 斷面會以純混凝土計算。"
            />
          </div>
        </div>
      )}

      <AddRowForm onAdd={handleAdd} disabled={!canAdd}>
        <TextField label="ID" value={id} onChange={setId} placeholder="S1" />
        <NumberField label="A" value={A} onChange={setA} />
        <NumberField label="Iy" value={Iy} onChange={setIy} />
        <NumberField label="Iz" value={Iz} onChange={setIz} />
        <NumberField label="J" value={J} onChange={setJ} />
      </AddRowForm>
      <DataTable
        columns={[
          { key: "id", label: "ID" },
          { key: "A", label: "A" },
          { key: "Iy", label: "Iy" },
          { key: "Iz", label: "Iz" },
          { key: "J", label: "J" },
          { key: "rebar", label: "配筋" },
        ]}
        rows={model.sections}
        rowKey={(s) => s.id}
        renderCell={(s, key) => {
          switch (key) {
            case "id":
              return s.id;
            case "A":
              return s.A;
            case "Iy":
              return s.Iy;
            case "Iz":
              return s.Iz;
            case "J":
              return s.J;
            default:
              return s.rebar ? `${s.rebar.bars.length} 根` : "—";
          }
        }}
        onRemove={(s) =>
          setModel((prev) => ({ ...prev, sections: prev.sections.filter((x) => x.id !== s.id) }))
        }
        emptyMessage="No sections yet."
      />
    </div>
  );
}
