import { useMemo, useState } from "react";
import { FileLoader } from "../components/FileLoader";
import { InfoPanel } from "../components/InfoPanel";
import { SceneViewer } from "../components/SceneViewer";
import { suggestedScale } from "../cem/geometry";
import { isAnalysisResults, isCemModel, type AnalysisResults, type CemModel } from "../cem/types";

/** Load-a-file-and-look-at-it mode (S6 scope): entirely local, no
 * backend required. Kept separate from the model-builder flow, which
 * does need the REST API. */
export function FileViewer() {
  const [model, setModel] = useState<CemModel | null>(null);
  const [modelFileName, setModelFileName] = useState<string | null>(null);
  const [results, setResults] = useState<AnalysisResults | null>(null);
  const [resultsFileName, setResultsFileName] = useState<string | null>(null);
  const [scale, setScale] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const autoScale = useMemo(() => (model ? suggestedScale(model, results) : 1), [model, results]);

  const handleModelLoad = (text: string, fileName: string) => {
    setError(null);
    try {
      const parsed: unknown = JSON.parse(text);
      if (!isCemModel(parsed)) {
        setError(`${fileName} doesn't look like a CEM model (missing nodes/elements/model_id).`);
        return;
      }
      setModel(parsed);
      setModelFileName(fileName);
      setResults(null);
      setResultsFileName(null);
      setScale(1);
    } catch {
      setError(`${fileName} is not valid JSON.`);
    }
  };

  const handleResultsLoad = (text: string, fileName: string) => {
    setError(null);
    try {
      const parsed: unknown = JSON.parse(text);
      if (!isAnalysisResults(parsed)) {
        setError(`${fileName} doesn't look like an analyze results file (missing displacements).`);
        return;
      }
      setResults(parsed);
      setResultsFileName(fileName);
      setScale(suggestedScale(model as CemModel, parsed));
    } catch {
      setError(`${fileName} is not valid JSON.`);
    }
  };

  return (
    <div className="app__body">
      <aside className="app__sidebar">
        <FileLoader label="CEM model (.cem.json)" onLoad={handleModelLoad} loadedFileName={modelFileName} />
        <FileLoader
          label="Analysis results (optional)"
          onLoad={handleResultsLoad}
          loadedFileName={resultsFileName}
        />
        {error && <p className="app__error">{error}</p>}

        {results && (
          <div className="app__scale">
            <label htmlFor="scale-slider">
              Displacement scale: <span className="mono">{scale.toFixed(1)}x</span>
            </label>
            <input
              id="scale-slider"
              type="range"
              min={0}
              max={Math.max(autoScale * 4, 10)}
              step={autoScale / 20 || 0.1}
              value={scale}
              onChange={(e) => setScale(Number(e.target.value))}
            />
          </div>
        )}

        <InfoPanel model={model} results={results} />
      </aside>

      <main className="app__viewport">
        {model ? (
          <SceneViewer model={model} results={results} scale={scale} />
        ) : (
          <div className="app__placeholder">No model loaded</div>
        )}
      </main>
    </div>
  );
}
