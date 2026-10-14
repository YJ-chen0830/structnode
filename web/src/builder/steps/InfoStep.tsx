import { SelectField, TextField } from "../fields";
import type { Units } from "../../cem/fullTypes";
import type { StepProps } from "./types";

const LENGTH_UNITS = ["m", "mm", "cm", "ft", "in"];
const FORCE_UNITS = ["N", "kN", "lbf", "kip", "kgf"];

export function InfoStep({ model, setModel }: StepProps) {
  return (
    <div className="step">
      <h2>Model info</h2>
      <p className="step__hint">
        Units declare what the numbers you'll enter mean -- the backend stores everything in SI
        internally regardless of what you pick here.
      </p>
      <div className="add-row-form">
        <TextField
          label="Model ID"
          value={model.model_id}
          onChange={(v) => setModel((prev) => ({ ...prev, model_id: v }))}
        />
        <SelectField
          label="Length unit"
          value={model.units.length}
          options={LENGTH_UNITS}
          onChange={(v) =>
            setModel((prev) => ({
              ...prev,
              units: { ...prev.units, length: v as Units["length"] },
            }))
          }
        />
        <SelectField
          label="Force unit"
          value={model.units.force}
          options={FORCE_UNITS}
          onChange={(v) =>
            setModel((prev) => ({
              ...prev,
              units: { ...prev.units, force: v as Units["force"] },
            }))
          }
        />
      </div>
    </div>
  );
}
