import { useState } from "react";
import { AddRowForm, DataTable, NumberField, TextField } from "../fields";
import type { StepProps } from "./types";

export function SectionsStep({ model, setModel }: StepProps) {
  const [id, setId] = useState("");
  const [A, setA] = useState<number | "">("");
  const [Iy, setIy] = useState<number | "">("");
  const [Iz, setIz] = useState<number | "">("");
  const [J, setJ] = useState<number | "">("");

  const canAdd =
    id.trim() !== "" &&
    A !== "" &&
    Iy !== "" &&
    Iz !== "" &&
    J !== "" &&
    !model.sections.some((s) => s.id === id.trim());

  const handleAdd = () => {
    if (!canAdd) return;
    setModel((prev) => ({
      ...prev,
      sections: [
        ...prev.sections,
        { id: id.trim(), A: Number(A), Iy: Number(Iy), Iz: Number(Iz), J: Number(J) },
      ],
    }));
    setId("");
    setA("");
    setIy("");
    setIz("");
    setJ("");
  };

  return (
    <div className="step">
      <h2>Sections</h2>
      <p className="step__hint">
        A, Iy, Iz, J in SI units (m², m⁴). Local-axis orientation (for 3D frame analysis) uses a
        default fallback when not set explicitly here -- see the viewer's warnings after running
        an analysis if that matters for your model.
      </p>
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
            default:
              return s.J;
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
