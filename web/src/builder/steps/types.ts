import type { Dispatch, SetStateAction } from "react";
import type { FullCemModel } from "../../cem/fullTypes";

export interface StepProps {
  model: FullCemModel;
  setModel: Dispatch<SetStateAction<FullCemModel>>;
}
