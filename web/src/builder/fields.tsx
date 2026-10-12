import type { ChangeEvent, ReactNode } from "react";

interface TextFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function TextField({ label, value, onChange, placeholder }: TextFieldProps) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
      />
    </label>
  );
}

interface NumberFieldProps {
  label: string;
  value: number | "";
  onChange: (value: number | "") => void;
  step?: number;
}

export function NumberField({ label, value, onChange, step }: NumberFieldProps) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        value={value}
        step={step ?? "any"}
        onChange={(e: ChangeEvent<HTMLInputElement>) =>
          onChange(e.target.value === "" ? "" : Number(e.target.value))
        }
      />
    </label>
  );
}

interface SelectFieldProps {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
  placeholder?: string;
}

export function SelectField({ label, value, options, onChange, placeholder }: SelectFieldProps) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="" disabled>
          {placeholder ?? "Select…"}
        </option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </label>
  );
}

interface AddRowFormProps {
  onAdd: () => void;
  disabled?: boolean;
  children: ReactNode;
}

export function AddRowForm({ onAdd, disabled, children }: AddRowFormProps) {
  return (
    <form
      className="add-row-form"
      onSubmit={(e) => {
        e.preventDefault();
        onAdd();
      }}
    >
      {children}
      <button type="submit" disabled={disabled}>
        Add
      </button>
    </form>
  );
}

interface DataTableProps<T> {
  columns: { key: string; label: string }[];
  rows: T[];
  renderCell: (row: T, columnKey: string) => ReactNode;
  onRemove: (row: T) => void;
  emptyMessage: string;
  rowKey: (row: T) => string;
}

export function DataTable<T>({
  columns,
  rows,
  renderCell,
  onRemove,
  emptyMessage,
  rowKey,
}: DataTableProps<T>) {
  if (rows.length === 0) {
    return <p className="data-table__empty">{emptyMessage}</p>;
  }
  return (
    <table className="data-table">
      <thead>
        <tr>
          {columns.map((c) => (
            <th key={c.key}>{c.label}</th>
          ))}
          <th />
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={rowKey(row)}>
            {columns.map((c) => (
              <td key={c.key}>{renderCell(row, c.key)}</td>
            ))}
            <td>
              <button type="button" className="data-table__remove" onClick={() => onRemove(row)}>
                Remove
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
