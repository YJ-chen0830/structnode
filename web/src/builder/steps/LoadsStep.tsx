import { useState } from "react";
import { AddRowForm, DataTable, NumberField, SelectField, TextField } from "../fields";
import type { LoadKind } from "../../cem/fullTypes";
import type { StepProps } from "./types";

const LOAD_KINDS: LoadKind[] = ["nodal_force", "nodal_moment", "member_distributed", "gravity"];
const SOLVED_LOAD_KINDS = new Set(["nodal_force", "nodal_moment"]);

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

  const targetOptions = kind === "member_distributed" ? model.elements.map((e) => e.id) : model.nodes.map((n) => n.id);
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
          coordinate_basis: "global",
        },
      ],
    }));
    setLoadId("");
    setKind("");
    setTargetId("");
    setVx(0);
    setVy(0);
    setVz(0);
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
        Only <code>nodal_force</code>/<code>nodal_moment</code> with global basis are solved today
        -- <code>member_distributed</code>/<code>gravity</code> are accepted into the model but
        will be rejected by `analyze` (not silently dropped).
      </p>
      <AddRowForm onAdd={handleAddLoad} disabled={!canAddLoad}>
        <TextField label="ID" value={loadId} onChange={setLoadId} placeholder="F1" />
        <SelectField
          label="Load case"
          value={loadCaseId}
          options={model.load_cases.map((c) => c.id)}
          onChange={setLoadCaseId}
        />
        <SelectField label="Kind" value={kind} options={LOAD_KINDS} onChange={(v) => setKind(v as LoadKind)} />
        <SelectField label="Target" value={targetId} options={targetOptions} onChange={setTargetId} />
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
          { key: "solved", label: "" },
        ]}
        rows={model.loads}
        rowKey={(l) => l.id}
        renderCell={(l, key) => {
          if (key === "values") return l.values.join(", ");
          if (key === "solved") return SOLVED_LOAD_KINDS.has(l.kind) ? "" : "⚠ not solved yet";
          return (l as unknown as Record<string, unknown>)[key] as string;
        }}
        onRemove={(l) =>
          setModel((prev) => ({ ...prev, loads: prev.loads.filter((x) => x.id !== l.id) }))
        }
        emptyMessage="No loads yet."
      />
    </div>
  );
}
