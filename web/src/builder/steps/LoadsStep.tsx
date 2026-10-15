import { useState } from "react";
import { AddRowForm, DataTable, NumberField, SelectField, TextField } from "../fields";
import type { CoordinateBasis, LoadKind } from "../../cem/fullTypes";
import { LIVE_LOAD_TABLE } from "../presets/loadCombinations";
import type { StepProps } from "./types";

const LOAD_KINDS: LoadKind[] = ["nodal_force", "nodal_moment", "member_distributed", "gravity"];
const BASES: CoordinateBasis[] = ["global", "local"];
const GRAVITY_ALL_ELEMENTS = "*";
const STANDARD_GRAVITY = 9.80665;
const KGF_TO_N = 9.80665;

export function LoadsStep({ model, setModel }: StepProps) {
  const [caseId, setCaseId] = useState("");
  const [caseDescription, setCaseDescription] = useState("");

  const [loadId, setLoadId] = useState("");
  const [loadCaseId, setLoadCaseId] = useState("");
  const [kind, setKind] = useState<LoadKind | "">("");
  const [targetId, setTargetId] = useState("");
  const [vx, setVx] = useState<number | "">(0);
  const [vy, setVy] = useState<number | "">(0);
  const [vz, setVz] = useState<number | "">(0);
  const [basis, setBasis] = useState<CoordinateBasis>("global");

  const canAddCase = caseId.trim() !== "" && !model.load_cases.some((c) => c.id === caseId.trim());
  const handleAddCase = () => {
    if (!canAddCase) return;
    setModel((prev) => ({
      ...prev,
      load_cases: [
        ...prev.load_cases,
        { id: caseId.trim(), ...(caseDescription ? { description: caseDescription } : {}) },
      ],
    }));
    setCaseId("");
    setCaseDescription("");
  };

  const elementIds = model.elements.map((e) => e.id);
  const targetOptions =
    kind === "member_distributed"
      ? elementIds
      : kind === "gravity"
        ? [GRAVITY_ALL_ELEMENTS, ...elementIds]
        : model.nodes.map((n) => n.id);
  // Only member_distributed may be given in member-local axes; nodal loads
  // and gravity are global-only (ADR 0007).
  const basisSelectable = kind === "member_distributed";

  const handleKindChange = (next: LoadKind) => {
    setKind(next);
    setTargetId(next === "gravity" ? GRAVITY_ALL_ELEMENTS : "");
    setBasis("global");
    if (next === "gravity") {
      setVx(0);
      setVy(-STANDARD_GRAVITY);
      setVz(0);
    }
  };
  const canAddLoad =
    loadId.trim() !== "" &&
    loadCaseId !== "" &&
    kind !== "" &&
    targetId !== "" &&
    !model.loads.some((l) => l.id === loadId.trim());

  const handleAddLoad = () => {
    if (!canAddLoad) return;
    setModel((prev) => ({
      ...prev,
      loads: [
        ...prev.loads,
        {
          id: loadId.trim(),
          case_id: loadCaseId,
          // canAddLoad already guarantees kind !== ""
          kind: kind as LoadKind,
          target_id: targetId,
          values: [Number(vx) || 0, Number(vy) || 0, Number(vz) || 0],
          coordinate_basis: basisSelectable ? basis : "global",
        },
      ],
    }));
    setLoadId("");
    setKind("");
    setTargetId("");
    setVx(0);
    setVy(0);
    setVz(0);
    setBasis("global");
  };

  return (
    <div className="step">
      <h2>Load cases &amp; loads</h2>

      <h3>Load cases</h3>
      <AddRowForm onAdd={handleAddCase} disabled={!canAddCase}>
        <TextField label="ID" value={caseId} onChange={setCaseId} placeholder="LC1" />
        <TextField label="Description (optional)" value={caseDescription} onChange={setCaseDescription} />
      </AddRowForm>
      <DataTable
        columns={[
          { key: "id", label: "ID" },
          { key: "description", label: "Description" },
        ]}
        rows={model.load_cases}
        rowKey={(c) => c.id}
        renderCell={(c, key) => (key === "id" ? c.id : (c.description ?? "—"))}
        onRemove={(c) =>
          setModel((prev) => ({
            ...prev,
            load_cases: prev.load_cases.filter((x) => x.id !== c.id),
            loads: prev.loads.filter((l) => l.case_id !== c.id),
          }))
        }
        emptyMessage="No load cases yet."
      />

      <h3>Loads</h3>
      <p className="step__hint">
        <code>member_distributed</code>: uniform load per unit member length (N/m), global or
        member-local axes. <code>gravity</code>: acceleration (m/s², e.g. Y = -9.80665) applied to
        each targeted element's material density × gross section area; target <code>*</code> means
        every element (materials need a density). On truss elements both are lumped to the end
        nodes and the analysis reports a warning.
      </p>
      <AddRowForm onAdd={handleAddLoad} disabled={!canAddLoad}>
        <TextField label="ID" value={loadId} onChange={setLoadId} placeholder="F1" />
        <SelectField
          label="Load case"
          value={loadCaseId}
          options={model.load_cases.map((c) => c.id)}
          onChange={setLoadCaseId}
        />
        <SelectField label="Kind" value={kind} options={LOAD_KINDS} onChange={(v) => handleKindChange(v as LoadKind)} />
        <SelectField label="Target" value={targetId} options={targetOptions} onChange={setTargetId} />
        {basisSelectable && (
          <SelectField label="Basis" value={basis} options={BASES} onChange={(v) => setBasis(v as CoordinateBasis)} />
        )}
        <NumberField label="X" value={vx} onChange={setVx} />
        <NumberField label="Y" value={vy} onChange={setVy} />
        <NumberField label="Z" value={vz} onChange={setVz} />
      </AddRowForm>
      <DataTable
        columns={[
          { key: "id", label: "ID" },
          { key: "case_id", label: "Case" },
          { key: "kind", label: "Kind" },
          { key: "target_id", label: "Target" },
          { key: "values", label: "Values" },
          { key: "coordinate_basis", label: "Basis" },
        ]}
        rows={model.loads}
        rowKey={(l) => l.id}
        renderCell={(l, key) => {
          if (key === "values") return l.values.join(", ");
          return (l as unknown as Record<string, unknown>)[key] as string;
        }}
        onRemove={(l) =>
          setModel((prev) => ({ ...prev, loads: prev.loads.filter((x) => x.id !== l.id) }))
        }
        emptyMessage="No loads yet."
      />

      <h3>活載重速查表 (建築技術規則建築構造編 第17條)</h3>
      <p className="step__hint">
        供查閱用的樓地板單位面積活載重 (kgf/m²)，乘上受載面積後再換算為本模型的集中力單位，才是
        <code>nodal_force</code> 的輸入值。本表為常見用途之代表性子集，非窮舉；特殊用途請查閱條文全文。
      </p>
      <table className="data-table">
        <thead>
          <tr>
            <th>組別</th>
            <th>用途</th>
            <th>kgf/m²</th>
            <th>N/m²</th>
          </tr>
        </thead>
        <tbody>
          {LIVE_LOAD_TABLE.map((row) => (
            <tr key={row.category}>
              <td>{row.group}</td>
              <td>{row.category}</td>
              <td>{row.kgfPerM2}</td>
              <td>{Math.round(row.kgfPerM2 * KGF_TO_N)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
