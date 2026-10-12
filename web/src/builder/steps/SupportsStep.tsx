import { useState } from "react";
import { DataTable, SelectField } from "../fields";
import type { StepProps } from "./types";

const DOF_LABELS = ["Tx", "Ty", "Tz", "Rx", "Ry", "Rz"] as const;

export function SupportsStep({ model, setModel }: StepProps) {
  const [nodeId, setNodeId] = useState("");
  const [dofs, setDofs] = useState<boolean[]>([true, true, true, true, true, true]);

  const nodeIds = model.nodes.map((n) => n.id);
  const canAdd = nodeId !== "" && !model.constraints.some((c) => c.node_id === nodeId);

  const toggle = (index: number) => {
    setDofs((prev) => prev.map((v, i) => (i === index ? !v : v)));
  };

  const handleAdd = () => {
    if (!canAdd) return;
    setModel((prev) => ({
      ...prev,
      constraints: [
        ...prev.constraints,
        { node_id: nodeId, dofs: dofs as [boolean, boolean, boolean, boolean, boolean, boolean] },
      ],
    }));
    setNodeId("");
    setDofs([true, true, true, true, true, true]);
  };

  return (
    <div className="step">
      <h2>Supports</h2>
      <p className="step__hint">
        At least one node needs a translational restraint, or the model is an unrestrained
        mechanism (the solver will reject it rather than guess).
      </p>
      <form
        className="add-row-form"
        onSubmit={(e) => {
          e.preventDefault();
          handleAdd();
        }}
      >
        <SelectField label="Node" value={nodeId} options={nodeIds} onChange={setNodeId} />
        <div className="dof-checkboxes">
          {DOF_LABELS.map((label, i) => (
            <label key={label}>
              <input type="checkbox" checked={dofs[i]} onChange={() => toggle(i)} />
              {label}
            </label>
          ))}
        </div>
        <button type="submit" disabled={!canAdd}>
          Add
        </button>
      </form>
      <DataTable
        columns={[
          { key: "node_id", label: "Node" },
          ...DOF_LABELS.map((l) => ({ key: l, label: l })),
        ]}
        rows={model.constraints}
        rowKey={(c) => c.node_id}
        renderCell={(c, key) => {
          if (key === "node_id") return c.node_id;
          const i = DOF_LABELS.indexOf(key as (typeof DOF_LABELS)[number]);
          return c.dofs[i] ? "✓" : "";
        }}
        onRemove={(c) =>
          setModel((prev) => ({
            ...prev,
            constraints: prev.constraints.filter((x) => x.node_id !== c.node_id),
          }))
        }
        emptyMessage="No supports yet."
      />
    </div>
  );
}
