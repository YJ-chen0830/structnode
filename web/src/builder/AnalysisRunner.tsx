import { useState } from "react";
import { runAnalysis } from "../api/client";
import { InfoPanel } from "../components/InfoPanel";
import { SceneViewer } from "../components/SceneViewer";
import { suggestedScale } from "../cem/geometry";
import type { AnalysisResults } from "../cem/types";
import type { FullCemModel } from "../cem/fullTypes";
import { downloadJson } from "./download";

const SOLVERS = ["native-2d", "native-3d", "opensees"];

interface AnalysisRunnerProps {
  model: FullCemModel;
  onBack: () => void;
  onResultsReady: (results: AnalysisResults) => void;
}

export function AnalysisRunner({ model, onBack, onResultsReady }: AnalysisRunnerProps) {
  const [analysisCaseId, setAnalysisCaseId] = useState(model.analysis_cases[0]?.id ?? "");
  const [solver, setSolver] = useState("native-2d");
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<AnalysisResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scale, setScale] = useState(1);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    setResults(null);
    const result = await runAnalysis(model, analysisCaseId, solver);
    setRunning(false);

    if (!result.ok || !result.data) {
      setError(result.networkError ?? `Request failed (HTTP ${result.status})`);
      return;
    }
    if (result.data.status === "error") {
      const message = result.data.errors?.map((e) => `${e.code}: ${e.message}`).join("; ");
      setError(message || "Analysis failed");
      return;
    }
    setResults(result.data);
    setScale(suggestedScale(model, result.data));
  };

  return (
    <div className="app__body">
      <aside className="app__sidebar">
        <button type="button" onClick={onBack}>
          ← Back to builder
        </button>

        <div className="field">
          <span>Analysis case</span>
          <select value={analysisCaseId} onChange={(e) => setAnalysisCaseId(e.target.value)}>
            {model.analysis_cases.map((ac) => (
              <option key={ac.id} value={ac.id}>
                {ac.id}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <span>Solver</span>
          <select value={solver} onChange={(e) => setSolver(e.target.value)}>
            {SOLVERS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <button type="button" onClick={handleRun} disabled={running || !analysisCaseId}>
          {running ? "Running…" : "Run analysis"}
        </button>

        {error && <p className="app__error">{error}</p>}

        {results && (
          <>
            <div className="app__scale">
              <label htmlFor="runner-scale">
                Displacement scale: <span className="mono">{scale.toFixed(1)}x</span>
              </label>
              <input
                id="runner-scale"
                type="range"
                min={0}
                max={Math.max(scale * 4, 10)}
                step={scale / 20 || 0.1}
                value={scale}
                onChange={(e) => setScale(Number(e.target.value))}
              />
            </div>
            <InfoPanel model={model} results={results} />
            <button type="button" onClick={() => onResultsReady(results)}>
              Export report →
            </button>
            <button
              type="button"
              onClick={() => downloadJson(`${model.model_id || "model"}.cem.json`, model)}
            >
              Download CEM model
            </button>
            <button
              type="button"
              onClick={() =>
                downloadJson(`${model.model_id || "model"}.${analysisCaseId}.results.json`, results)
              }
            >
              Download results
            </button>
          </>
        )}
      </aside>

      <main className="app__viewport">
        <SceneViewer model={model} results={results} scale={scale} />
      </main>
    </div>
  );
}
