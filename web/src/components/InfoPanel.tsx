import type { AnalysisResults, CemModel } from "../cem/types";

interface InfoPanelProps {
  model: CemModel | null;
  results: AnalysisResults | null;
}

export function InfoPanel({ model, results }: InfoPanelProps) {
  if (!model) {
    return <p className="info-panel__empty">Load a CEM model file to begin.</p>;
  }

  return (
    <dl className="info-panel">
      <div>
        <dt>Model</dt>
        <dd>{model.model_id}</dd>
      </div>
      <div>
        <dt>Nodes / Elements</dt>
        <dd>
          {model.nodes.length} / {model.elements.length}
        </dd>
      </div>
      {results ? (
        <>
          <div>
            <dt>Analysis case</dt>
            <dd>{results.analysis_case_id}</dd>
          </div>
          <div>
            <dt>Solver</dt>
            <dd>
              {results.solver_name} {results.solver_version}
            </dd>
          </div>
          {results.warnings.length > 0 && (
            <div>
              <dt>Warnings</dt>
              <dd>
                <ul className="info-panel__warnings">
                  {results.warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </dd>
            </div>
          )}
        </>
      ) : (
        <div>
          <dt>Results</dt>
          <dd>none loaded (geometry only)</dd>
        </div>
      )}
    </dl>
  );
}
