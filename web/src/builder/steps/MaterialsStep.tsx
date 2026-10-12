import { useState } from "react";
import { AddRowForm, DataTable, NumberField, TextField } from "../fields";
import type { StepProps } from "./types";

export function MaterialsStep({ model, setModel }: StepProps) {
  const [id, setId] = useState("");
  const [E, setE] = useState<number | "">("");
  const [G, setG] = useState<number | "">("");
  const [rho, setRho] = useState<number | "">("");

  const canAdd = id.trim() !== "" && E !== "" && !model.materials.some((m) => m.id === id.trim());

  const handleAdd = () => {
    if (!canAdd) return;
    setModel((prev) => ({
      ...prev,
      materials: [
        ...prev.materials,
        {
          id: id.trim(),
          E: Number(E),
          ...(G !== "" ? { G: Number(G) } : {}),
          ...(rho !== "" ? { rho: Number(rho) } : {}),
        },
      ],
    }));
    setId("");
    setE("");
    setG("");
    setRho("");
  };

  return (
    <div className="step">
      <h2>Materials</h2>
      <p className="step__hint">
        E, G in Pa; rho in kg/m³. G is optional -- 3D frame analysis derives it from E and Poisson's
        ratio if omitted.
      </p>
      <AddRowForm onAdd={handleAdd} disabled={!canAdd}>
        <TextField label="ID" value={id} onChange={setId} placeholder="M1" />
        <NumberField label="E" value={E} onChange={setE} />
        <NumberField label="G (optional)" value={G} onChange={setG} />
        <NumberField label="rho (optional)" value={rho} onChange={setRho} />
      </AddRowForm>
      <DataTable
        columns={[
          { key: "id", label: "ID" },
          { key: "E", label: "E" },
          { key: "G", label: "G" },
          { key: "rho", label: "rho" },
        ]}
        rows={model.materials}
        rowKey={(m) => m.id}
        renderCell={(m, key) => {
          if (key === "id") return m.id;
          if (key === "E") return m.E;
          if (key === "G") return m.G ?? "—";
          return m.rho ?? "—";
        }}
        onRemove={(m) =>
          setModel((prev) => ({
            ...prev,
            materials: prev.materials.filter((x) => x.id !== m.id),
          }))
        }
        emptyMessage="No materials yet."
      />
    </div>
  );
}
