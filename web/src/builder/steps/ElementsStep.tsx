import { useState } from "react";
import { AddRowForm, DataTable, SelectField, TextField } from "../fields";
import type { StepProps } from "./types";

export function ElementsStep({ model, setModel }: StepProps) {
  const [id, setId] = useState("");
  const [type, setType] = useState<"truss" | "frame" | "">("");
  const [node1, setNode1] = useState("");
  const [node2, setNode2] = useState("");
  const [materialId, setMaterialId] = useState("");
  const [sectionId, setSectionId] = useState("");

  const nodeIds = model.nodes.map((n) => n.id);
  const materialIds = model.materials.map((m) => m.id);
  const sectionIds = model.sections.map((s) => s.id);

  const canAdd =
    id.trim() !== "" &&
    type !== "" &&
    node1 !== "" &&
    node2 !== "" &&
    node1 !== node2 &&
    materialId !== "" &&
    sectionId !== "" &&
    !model.elements.some((e) => e.id === id.trim());

  const missingPrereqs = nodeIds.length < 2 || materialIds.length === 0 || sectionIds.length === 0;

  const handleAdd = () => {
    if (!canAdd) return;
    setModel((prev) => ({
      ...prev,
      elements: [
        ...prev.elements,
        {
          id: id.trim(),
          // canAdd already guarantees type !== ""
          type: type as "truss" | "frame",
          node_ids: [node1, node2],
          material_id: materialId,
          section_id: sectionId,
        },
      ],
    }));
    setId("");
    setType("");
    setNode1("");
    setNode2("");
    setMaterialId("");
    setSectionId("");
  };

  return (
    <div className="step">
      <h2>Elements</h2>
      <p className="step__hint">
        Connects two nodes with a material and a section. A model must use only one element type
        throughout (all truss, or all frame) -- the solvers reject mixed models.
      </p>
      {missingPrereqs && (
        <p className="step__warning">Add at least 2 nodes, 1 material, and 1 section first.</p>
      )}
      <AddRowForm onAdd={handleAdd} disabled={!canAdd}>
        <TextField label="ID" value={id} onChange={setId} placeholder="E1" />
        <SelectField label="Type" value={type} options={["truss", "frame"]} onChange={(v) => setType(v as "truss" | "frame")} />
        <SelectField label="Node 1" value={node1} options={nodeIds} onChange={setNode1} />
        <SelectField label="Node 2" value={node2} options={nodeIds} onChange={setNode2} />
        <SelectField label="Material" value={materialId} options={materialIds} onChange={setMaterialId} />
        <SelectField label="Section" value={sectionId} options={sectionIds} onChange={setSectionId} />
      </AddRowForm>
      <DataTable
        columns={[
          { key: "id", label: "ID" },
          { key: "type", label: "Type" },
          { key: "nodes", label: "Nodes" },
          { key: "material_id", label: "Material" },
          { key: "section_id", label: "Section" },
        ]}
        rows={model.elements}
        rowKey={(e) => e.id}
        renderCell={(e, key) => {
          if (key === "nodes") return e.node_ids.join(" – ");
          return (e as unknown as Record<string, unknown>)[key] as string;
        }}
        onRemove={(e) =>
          setModel((prev) => ({ ...prev, elements: prev.elements.filter((x) => x.id !== e.id) }))
        }
        emptyMessage="No elements yet."
      />
    </div>
  );
}
