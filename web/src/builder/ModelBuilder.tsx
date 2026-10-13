import { useState, type ReactElement } from "react";
import { validateModel, type ValidateResult } from "../api/client";
import { SceneViewer } from "../components/SceneViewer";
import { emptyModel, type FullCemModel } from "../cem/fullTypes";
import { AnalysisStep } from "./steps/AnalysisStep";
import { ElementsStep } from "./steps/ElementsStep";
import { InfoStep } from "./steps/InfoStep";
import { LoadsStep } from "./steps/LoadsStep";
import { MaterialsStep } from "./steps/MaterialsStep";
import { NodesStep } from "./steps/NodesStep";
import { SectionsStep } from "./steps/SectionsStep";
import { SupportsStep } from "./steps/SupportsStep";
import type { StepProps } from "./steps/types";

const STEPS: { label: string; Component: (props: StepProps) => ReactElement }[] = [
  { label: "Info", Component: InfoStep },
  { label: "Nodes", Component: NodesStep },
  { label: "Materials", Component: MaterialsStep },
  { label: "Sections", Component: SectionsStep },
  { label: "Elements", Component: ElementsStep },
  { label: "Supports", Component: SupportsStep },
  { label: "Loads", Component: LoadsStep },
  { label: "Analysis", Component: AnalysisStep },
];

interface ModelBuilderProps {
  onReadyToAnalyze: (model: FullCemModel) => void;
}

export function ModelBuilder({ onReadyToAnalyze }: ModelBuilderProps) {
  const [model, setModel] = useState<FullCemModel>(() => emptyModel("new-model"));
  const [stepIndex, setStepIndex] = useState(0);
  const [validation, setValidation] = useState<ValidateResult | null>(null);
  const [validating, setValidating] = useState(false);

  const { Component } = STEPS[stepIndex];
  const isLastStep = stepIndex === STEPS.length - 1;

  const handleValidate = async () => {
    setValidating(true);
    const result = await validateModel(model);
    setValidating(false);
    if (result.data) setValidation(result.data);
  };

  const canAnalyze = validation?.status === "ok" && model.analysis_cases.length > 0;

  return (
    <div className="builder">
      <nav className="builder__steps">
        {STEPS.map((s, i) => (
          <button
            key={s.label}
            type="button"
            aria-pressed={i === stepIndex}
            onClick={() => setStepIndex(i)}
          >
            {i + 1}. {s.label}
          </button>
        ))}
      </nav>

      <div className="builder__body">
        <div className="builder__form">
          <Component model={model} setModel={setModel} />

          <div className="builder__nav-buttons">
            <button type="button" disabled={stepIndex === 0} onClick={() => setStepIndex((i) => i - 1)}>
              Back
            </button>
            {isLastStep ? (
              <button type="button" onClick={handleValidate} disabled={validating}>
                {validating ? "Validating…" : "Validate model"}
              </button>
            ) : (
              <button type="button" onClick={() => setStepIndex((i) => i + 1)}>
                Next
              </button>
            )}
          </div>

          {validation && (
            <div className={`validation-result validation-result--${validation.status}`}>
              <p className="mono">
                {validation.status === "ok" ? "Valid." : "Validation failed."}
                {validation.model_hash && ` hash: ${validation.model_hash.slice(0, 12)}…`}
              </p>
              {validation.errors.length > 0 && (
                <ul>
                  {validation.errors.map((e) => (
                    <li key={`${e.code}-${e.path}`} className="validation-result__error">
                      <span className="mono">{e.code}</span> ({e.path}): {e.message}
                    </li>
                  ))}
                </ul>
              )}
              {validation.warnings.length > 0 && (
                <ul>
                  {validation.warnings.map((w) => (
                    <li key={`${w.code}-${w.path}`} className="validation-result__warning">
                      <span className="mono">{w.code}</span> ({w.path}): {w.message}
                    </li>
                  ))}
                </ul>
              )}
              {canAnalyze && (
                <button type="button" onClick={() => onReadyToAnalyze(model)}>
                  Continue to analysis →
                </button>
              )}
            </div>
          )}
        </div>

        <div className="builder__preview">
          {model.nodes.length > 0 ? (
            <SceneViewer model={model} results={null} scale={1} />
          ) : (
            <div className="app__placeholder">Add nodes to see a preview</div>
          )}
        </div>
      </div>
    </div>
  );
}
