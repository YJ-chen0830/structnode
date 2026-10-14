import { useState } from "react";
import { AddRowForm, DataTable, NumberField, TextField } from "../fields";
import { NodeImport } from "../NodeImport";
import type { StepProps } from "./types";

export function NodesStep(props: StepProps) {
  const { model, setModel } = props;
  const [id, setId] = useState("");
  const [x, setX] = useState<number | "">(0);
  const [y, setY] = useState<number | "">(0);
  const [z, setZ] = useState<number | "">(0);

  const canAdd = id.trim() !== "" && !model.nodes.some((n) => n.id === id.trim());

  const handleAdd = () => {
    if (!canAdd) return;
    setModel((prev) => ({
      ...prev,
      nodes: [...prev.nodes, { id: id.trim(), position: [Number(x) || 0, Number(y) || 0, Number(z) || 0] }],
    }));
    setId("");
    setX(0);
    setY(0);
    setZ(0);
  };

  return (
    <div className="step">
      <h2>Nodes</h2>
      <p className="step__hint">Global coordinates, in the units declared on the Info step.</p>
      <NodeImport {...props} />
      <AddRowForm onAdd={handleAdd} disabled={!canAdd}>
        <TextField label="ID" value={id} onChange={setId} placeholder="N1" />
        <NumberField label="X" value={x} onChange={setX} />
        <NumberField label="Y" value={y} onChange={setY} />
        <NumberField label="Z" value={z} onChange={setZ} />
      </AddRowForm>
      <DataTable
        columns={[
          { key: "id", label: "ID" },
          { key: "x", label: "X" },
          { key: "y", label: "Y" },
          { key: "z", label: "Z" },
        ]}
        rows={model.nodes}
        rowKey={(n) => n.id}
        renderCell={(n, key) => {
          if (key === "id") return n.id;
          if (key === "x") return n.position[0];
          if (key === "y") return n.position[1];
          return n.position[2];
        }}
        onRemove={(n) =>
          setModel((prev) => ({ ...prev, nodes: prev.nodes.filter((x2) => x2.id !== n.id) }))
        }
        emptyMessage="No nodes yet."
      />
    </div>
  );
}
