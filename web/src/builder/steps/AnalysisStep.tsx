import { useState } from "react";
import { DataTable, TextField } from "../fields";
import type { StepProps } from "./types";

export function AnalysisStep({ model, setModel }: StepProps) {
  const [id, setId] = useState("");
  const [selectedCases, setSelectedCases] = useState<string[]>([]);

  const canAdd =
    id.trim() !== "" && selectedCases.length > 0 && !model.analysis_cases.some((a) => a.id === id.trim());

  const toggleCase = (caseId: string) => {
    setSelectedCases((prev) =>
      prev.includes(caseId) ? prev.filter((c) => c !== caseId) : [...prev, caseId],
    );
  };

  const handleAdd = () => {
    if (!canAdd) return;
    setModel((prev) => ({
      ...prev,
      analysis_cases: [
        ...prev.analysis_cases,
        { id: id.trim(), load_case_ids: selectedCases, method: "linear_static" },
      ],
    }));
    setId("");
    setSelectedCases([]);
  };

  return (
    <div className="step">
      <h2>Analysis cases</h2>
      <p className="step__hint">
        Combines one or more load cases into a single analysis run. Only <code>linear_static</code>{" "}
        is supported in this alpha.
      </p>
      <form
        className="add-row-form"
        onSubmit={(e) => {
          e.preventDefault();
          handleAdd();
        }}
      >
        <TextField label="ID" value={id} onChange={setId} placeholder="AC1" />
        <div className="dof-checkboxes">
          {model.load_cases.map((c) => (
            <label key={c.id}>
              <input
                type="checkbox"
                checked={selectedCases.includes(c.id)}
                onChange={() => toggleCase(c.id)}
              />
              {c.id}
            </label>
          ))}
          {model.load_cases.length === 0 && <span className="step__hint">Add a load case first.</span>}
        </div>
        <button type="submit" disabled={!canAdd}>
          Add
        </button>
      </form>
      <DataTable
        columns={[
          { key: "id", label: "ID" },
          { key: "load_case_ids", label: "Load cases" },
          { key: "method", label: "Method" },
        ]}
        rows={model.analysis_cases}
        rowKey={(a) => a.id}
        renderCell={(a, key) => {
          if (key === "load_case_ids") return a.load_case_ids.join(", ");
          return (a as unknown as Record<string, unknown>)[key] as string;
        }}
        onRemove={(a) =>
          setModel((prev) => ({
            ...prev,
            analysis_cases: prev.analysis_cases.filter((x) => x.id !== a.id),
          }))
        }
        emptyMessage="No analysis cases yet."
      />
    </div>
  );
}
