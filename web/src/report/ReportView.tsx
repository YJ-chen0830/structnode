import { useEffect, useRef, useState } from "react";
import { SceneViewer, type SceneViewerHandle } from "../components/SceneViewer";
import { suggestedScale } from "../cem/geometry";
import type { AnalysisResults } from "../cem/types";
import type { FullCemModel } from "../cem/fullTypes";
import "./ReportView.css";

interface ReportViewProps {
  model: FullCemModel;
  results: AnalysisResults;
  onBack: () => void;
}

/** Full-page printable report. The 3D view here is a static PNG
 * snapshot, not the live WebGL canvas -- browsers' print/PDF pipelines
 * don't reliably rasterize WebGL canvases, so this captures one frame
 * from a viewer rendered off to the side (see `.report__capture-rig`
 * in the CSS: visually hidden, but still laid out and rendered, which
 * is what a live WebGL context needs). */
export function ReportView({ model, results, onBack }: ReportViewProps) {
  const viewerRef = useRef<SceneViewerHandle>(null);
  const [snapshot, setSnapshot] = useState<string | null>(null);
  const [generatedOn] = useState(() => new Date().toLocaleDateString());
  const scale = suggestedScale(model, results);

  useEffect(() => {
    // Polls rather than waiting a single fixed delay: the off-screen
    // viewer needs its own mount effect, OrbitControls setup, and at
    // least one post-geometry animation frame to all land before a
    // capture is meaningful, and how long that takes varies (dev-mode
    // double-effects, cold module eval, etc.). `hasContent()` checks
    // actual pixel content rather than guessing a delay -- PNG byte
    // size is not a reliable signal here, since antialiasing noise on
    // an otherwise-empty frame can compress to a similar size as one
    // with real geometry.
    let cancelled = false;
    let attempts = 0;
    const MAX_ATTEMPTS = 20;

    const tryCapture = () => {
      if (cancelled) return;
      attempts += 1;
      const ready = viewerRef.current?.hasContent() ?? false;
      if (ready || attempts >= MAX_ATTEMPTS) {
        setSnapshot(viewerRef.current?.capture() ?? null);
      } else {
        setTimeout(tryCapture, 150);
      }
    };

    const initial = setTimeout(tryCapture, 150);
    return () => {
      cancelled = true;
      clearTimeout(initial);
    };
  }, []);

  const allCategories: Array<{
    title: string;
    data: Record<string, Record<string, number>>;
    rowLabel: string;
  }> = [
    { title: "Displacements", data: results.displacements as Record<string, Record<string, number>>, rowLabel: "Node" },
    { title: "Reactions", data: results.reactions, rowLabel: "Node" },
    { title: "Element end forces", data: results.element_forces, rowLabel: "Element" },
  ];

  return (
    <div className="report-page">
      <div className="report-page__toolbar no-print">
        <button type="button" onClick={onBack}>
          ← Back to results
        </button>
        <button type="button" onClick={() => window.print()}>
          Print / Save as PDF
        </button>
      </div>

      <div className="report__capture-rig" aria-hidden="true">
        <SceneViewer ref={viewerRef} model={model} results={results} scale={scale} />
      </div>

      <article className="report">
        <header className="report__title-block">
          <div className="report__eyebrow">StructNode — Structural Analysis Report</div>
          <h1>{model.model_id}</h1>
          <p className="report__disclaimer">
            EXPERIMENTAL — NOT FOR ENGINEERING DESIGN WITHOUT INDEPENDENT REVIEW
          </p>
          <dl className="report__fields">
            <div>
              <dt>Date</dt>
              <dd>{generatedOn}</dd>
            </div>
            <div>
              <dt>Analysis case</dt>
              <dd>{results.analysis_case_id}</dd>
            </div>
            <div>
              <dt>Element kind</dt>
              <dd>{results.element_kind}</dd>
            </div>
            <div>
              <dt>Solver</dt>
              <dd>
                {results.solver_name} {results.solver_version}
              </dd>
            </div>
            {results.model_hash && (
              <div>
                <dt>Model hash</dt>
                <dd className="mono">{results.model_hash}</dd>
              </div>
            )}
          </dl>
        </header>

        {snapshot && (
          <figure className="report__figure">
            <img src={snapshot} alt={`Deformed shape of ${model.model_id}`} />
            <figcaption>
              Undeformed (grey, dashed) vs. deformed (red), displacement scale ×{scale.toFixed(1)}.
            </figcaption>
          </figure>
        )}

        {results.warnings.length > 0 && (
          <section className="report__section">
            <h2>Warnings</h2>
            <ul>
              {results.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </section>
        )}

        {allCategories.map(
          (cat) =>
            Object.keys(cat.data).length > 0 && (
              <section className="report__section" key={cat.title}>
                <h2>{cat.title}</h2>
                <ReportTable rowLabel={cat.rowLabel} data={cat.data} />
              </section>
            ),
        )}

        <footer className="report__footer">
          Generated by StructNode {results.solver_name} {results.solver_version} — not an
          engineering-approved output. See docs/MASTER_PLAN.md for the project's non-negotiables.
        </footer>
      </article>
    </div>
  );
}

function ReportTable({
  rowLabel,
  data,
}: {
  rowLabel: string;
  data: Record<string, Record<string, number>>;
}) {
  const columns = Array.from(
    new Set(Object.values(data).flatMap((row) => Object.keys(row))),
  );

  return (
    <div className="report__table-wrap">
      <table className="report__table">
        <thead>
          <tr>
            <th>{rowLabel}</th>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Object.entries(data).map(([key, row]) => (
            <tr key={key}>
              <td>{key}</td>
              {columns.map((c) => (
                <td key={c}>{c in row ? row[c].toPrecision(6) : ""}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
