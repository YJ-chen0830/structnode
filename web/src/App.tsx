import { useState } from "react";
import "./App.css";
import { ApiStatus } from "./components/ApiStatus";
import { AnalysisRunner } from "./builder/AnalysisRunner";
import { ModelBuilder } from "./builder/ModelBuilder";
import { ReportView } from "./report/ReportView";
import { FileViewer } from "./viewer/FileViewer";
import type { AnalysisResults } from "./cem/types";
import type { FullCemModel } from "./cem/fullTypes";

type Mode = "view" | "build" | "analyze" | "report";

function App() {
  const [mode, setMode] = useState<Mode>("view");
  const [builtModel, setBuiltModel] = useState<FullCemModel | null>(null);
  const [builtResults, setBuiltResults] = useState<AnalysisResults | null>(null);

  const builderActive = mode === "build" || mode === "analyze" || mode === "report";

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__header-row">
          <div>
            <h1>StructNode Viewer</h1>
            <p className="app__disclaimer">
              EXPERIMENTAL -- not an engineering-approved output. Not the source of truth for the
              model (that's the CEM JSON file, or whatever your REST API server has in memory).
            </p>
          </div>
          <div className="app__header-actions">
            <nav className="app__nav">
              <button type="button" aria-pressed={mode === "view"} onClick={() => setMode("view")}>
                View files
              </button>
              <button type="button" aria-pressed={builderActive} onClick={() => setMode("build")}>
                Build model
              </button>
            </nav>
            {builderActive && <ApiStatus />}
          </div>
        </div>
      </header>

      {mode === "view" && <FileViewer />}

      {mode === "build" && (
        <ModelBuilder
          onReadyToAnalyze={(model) => {
            setBuiltModel(model);
            setMode("analyze");
          }}
        />
      )}

      {mode === "analyze" && builtModel && (
        <AnalysisRunner
          model={builtModel}
          onBack={() => setMode("build")}
          onResultsReady={(results) => {
            setBuiltResults(results);
            setMode("report");
          }}
        />
      )}

      {mode === "report" && builtModel && builtResults && (
        <ReportView
          model={builtModel}
          results={builtResults}
          onBack={() => setMode("analyze")}
        />
      )}
    </div>
  );
}

export default App;
