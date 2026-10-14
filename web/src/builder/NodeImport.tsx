import { useState } from "react";
import * as XLSX from "xlsx";
import { SelectField } from "./fields";
import type { StepProps } from "./steps/types";

// RTK/total-station data collectors (Hi-Target, CHCNAV, South, etc.) export
// point lists in all sorts of column orders and naming conventions -- and
// commonly in surveying axis convention (X=North, Y=East, Z/H=elevation),
// not this app's model axes. Rather than guess one fixed layout, this is a
// column-mapping importer: read whatever sheet the user has, let them pick
// which column is the point ID and which column feeds which model axis.

const UNIT_TO_METERS: Record<string, number> = { m: 1, mm: 0.001, cm: 0.01, ft: 0.3048, in: 0.0254 };
const NONE = "(無/0)";

interface ParsedSheet {
  columns: string[];
  rows: Record<string, string>[];
}

function parseWorkbook(file: File, data: ArrayBuffer): ParsedSheet {
  // .csv has no embedded encoding/codepage info the way .xlsx/.xls do, and
  // SheetJS's byte-level auto-detection guesses wrong for BOM-less UTF-8
  // (the common case for RTK/data-collector exports with Chinese headers,
  // e.g. mangling "點名" into mojibake) -- decode as UTF-8 text ourselves
  // and hand SheetJS a string instead of raw bytes.
  const wb = file.name.toLowerCase().endsWith(".csv")
    ? XLSX.read(new TextDecoder("utf-8").decode(data), { type: "string" })
    : XLSX.read(data, { type: "array" });
  const sheet = wb.Sheets[wb.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json<Record<string, string>>(sheet, { defval: "" });
  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];
  return { columns, rows };
}

export function NodeImport({ model, setModel }: StepProps) {
  const [open, setOpen] = useState(false);
  const [sheet, setSheet] = useState<ParsedSheet | null>(null);
  const [fileName, setFileName] = useState("");
  const [idCol, setIdCol] = useState("");
  const [xCol, setXCol] = useState("");
  const [yCol, setYCol] = useState("");
  const [zCol, setZCol] = useState("");
  const [sourceUnit, setSourceUnit] = useState<string>(model.units.length);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const handleFile = async (file: File) => {
    setError(null);
    setResult(null);
    try {
      const buf = await file.arrayBuffer();
      const parsed = parseWorkbook(file, buf);
      if (parsed.columns.length === 0) {
        setError(`${file.name} 沒有可用的欄位 (空檔案或格式不支援)`);
        return;
      }
      setSheet(parsed);
      setFileName(file.name);
      setIdCol(parsed.columns[0]);
      setXCol(parsed.columns[1] ?? "");
      setYCol(parsed.columns[2] ?? "");
      setZCol(parsed.columns[3] ?? NONE);
    } catch {
      setError(`${file.name} 無法解析，請確認是有效的 Excel (.xlsx) 或 CSV 檔案。`);
    }
  };

  const canImport = sheet !== null && idCol !== "" && xCol !== "" && yCol !== "";

  const doImport = () => {
    if (!sheet || !canImport) return;
    const scale = (UNIT_TO_METERS[sourceUnit] ?? 1) / (UNIT_TO_METERS[model.units.length] ?? 1);
    const existingIds = new Set(model.nodes.map((n) => n.id));
    const newNodes: { id: string; position: [number, number, number] }[] = [];
    let skipped = 0;

    for (const row of sheet.rows) {
      const id = String(row[idCol] ?? "").trim();
      const xRaw = Number(row[xCol]);
      const yRaw = Number(row[yCol]);
      const zRaw = zCol === NONE || zCol === "" ? 0 : Number(row[zCol]);
      if (id === "" || existingIds.has(id) || Number.isNaN(xRaw) || Number.isNaN(yRaw) || Number.isNaN(zRaw)) {
        skipped += 1;
        continue;
      }
      existingIds.add(id);
      newNodes.push({ id, position: [xRaw * scale, yRaw * scale, zRaw * scale] });
    }

    setModel((prev) => ({ ...prev, nodes: [...prev.nodes, ...newNodes] }));
    setResult(`已匯入 ${newNodes.length} 個節點${skipped > 0 ? `，略過 ${skipped} 筆 (ID 重複或座標無法解析)` : ""}。`);
    setSheet(null);
    setFileName("");
  };

  return (
    <div className="node-import">
      <button type="button" onClick={() => setOpen((o) => !o)}>
        {open ? "收起 Excel/CSV 匯入" : "從 Excel/CSV 匯入節點座標"}
      </button>
      {open && (
        <div className="node-import__panel">
          <p className="step__hint">
            支援 .xlsx / .csv，第一列需為欄位標題。RTK/測量儀器匯出的座標常用測量座標系（例如
            X=北、Y=東、Z=高程），請依實際欄位對應到模型的 X/Y/Z 軸 -- 不必和模型軸名稱一致。
          </p>
          <input
            type="file"
            accept=".xlsx,.xls,.csv"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void handleFile(file);
            }}
          />
          {error && <p className="app__error">{error}</p>}
          {sheet && (
            <>
              <p className="step__hint">
                {fileName}：偵測到 {sheet.rows.length} 列資料，{sheet.columns.length} 個欄位。
              </p>
              <div className="add-row-form">
                <SelectField label="節點 ID 欄位" value={idCol} options={sheet.columns} onChange={setIdCol} />
                <SelectField label="→ 模型 X 欄位" value={xCol} options={sheet.columns} onChange={setXCol} />
                <SelectField label="→ 模型 Y 欄位" value={yCol} options={sheet.columns} onChange={setYCol} />
                <SelectField
                  label="→ 模型 Z 欄位"
                  value={zCol}
                  options={[NONE, ...sheet.columns]}
                  onChange={setZCol}
                />
                <SelectField
                  label="來源座標單位"
                  value={sourceUnit}
                  options={Object.keys(UNIT_TO_METERS)}
                  onChange={setSourceUnit}
                />
              </div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>X</th>
                    <th>Y</th>
                    <th>Z</th>
                  </tr>
                </thead>
                <tbody>
                  {sheet.rows.slice(0, 5).map((row, i) => (
                    <tr key={i}>
                      <td>{String(row[idCol] ?? "")}</td>
                      <td>{String(row[xCol] ?? "")}</td>
                      <td>{String(row[yCol] ?? "")}</td>
                      <td>{zCol === NONE ? "0" : String(row[zCol] ?? "")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <button type="button" onClick={doImport} disabled={!canImport}>
                匯入 {sheet.rows.length} 筆節點
              </button>
            </>
          )}
          {result && <p className="step__hint">{result}</p>}
        </div>
      )}
    </div>
  );
}
