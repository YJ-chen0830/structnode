import { useState } from "react";
import { DataTable, SelectField, TextField } from "../fields";
import {
  ASD_COMBINATIONS,
  LOAD_ROLES,
  LRFD_COMBINATIONS,
  type LoadCombination,
  type LoadRole,
} from "../presets/loadCombinations";
import type { StepProps } from "./types";

function uniqueId(base: string, taken: Set<string>): string {
  if (!taken.has(base)) return base;
  let n = 1;
  while (taken.has(`${base}-${n}`)) n += 1;
  return `${base}-${n}`;
}

export function AnalysisStep({ model, setModel }: StepProps) {
  const [id, setId] = useState("");
  const [selectedCases, setSelectedCases] = useState<string[]>([]);
  const [roleAssignment, setRoleAssignment] = useState<Record<string, LoadRole | "">>({});

  const applyCombo = (combo: LoadCombination, reversed: boolean) => {
    const resolved = combo.terms
      .map((t) => ({ ...t, caseId: Object.entries(roleAssignment).find(([, r]) => r === t.role)?.[0] }))
      .filter((t): t is typeof t & { caseId: string } => Boolean(t.caseId));
    if (resolved.length === 0) return;
    const taken = new Set(model.analysis_cases.map((a) => a.id));
    const newId = uniqueId(`${combo.id}${reversed ? "R" : ""}`, taken);
    setModel((prev) => ({
      ...prev,
      analysis_cases: [
        ...prev.analysis_cases,
        {
          id: newId,
          load_case_ids: resolved.map((t) => t.caseId),
          method: "linear_static",
          factors: resolved.map((t) => (reversed && combo.reversibleRoles?.includes(t.role) ? -t.factor : t.factor)),
        },
      ],
    }));
  };

  const renderComboList = (title: string, combos: LoadCombination[]) => (
    <>
      <h3>{title}</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>組合</th>
            <th>依據</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {combos.map((combo) => (
            <tr key={combo.id}>
              <td className="mono">{combo.formula}</td>
              <td>{combo.source}</td>
              <td>
                <button type="button" onClick={() => applyCombo(combo, false)}>
                  套用
                </button>
                {combo.reversibleRoles && combo.reversibleRoles.length > 0 && (
                  <button type="button" onClick={() => applyCombo(combo, true)}>
                    套用 (反向)
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );

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
          if (key === "load_case_ids") {
            return a.load_case_ids
              .map((caseId, i) => `${caseId}×${a.factors?.[i] ?? 1}`)
              .join(", ");
          }
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

      <h3>台灣規範載重組合精靈</h3>
      <p className="step__hint">
        先將已建立的 Load case 標記為 D／L／Lr／W／E 角色，再從下面套用規範組合 -- 會以
        <code>factors</code> 做線性疊加，自動產生新的 Analysis case，不需另外複製或縮放載重。
      </p>
      <div className="add-row-form">
        {model.load_cases.length === 0 && <span className="step__hint">請先在 Loads 步驟建立 Load case。</span>}
        {model.load_cases.map((c) => (
          <SelectField
            key={c.id}
            label={c.id}
            value={roleAssignment[c.id] ?? ""}
            options={LOAD_ROLES.map((r) => r.role)}
            onChange={(v) => setRoleAssignment((prev) => ({ ...prev, [c.id]: v as LoadRole }))}
            placeholder="角色…"
          />
        ))}
      </div>
      {renderComboList("極限設計法 LRFD (建築物混凝土結構設計規範 §5.3.1)", LRFD_COMBINATIONS)}
      {renderComboList("容許應力設計法 ASD (鋼結構容許應力設計法規範 §2.2)", ASD_COMBINATIONS)}
    </div>
  );
}
