/** Schematic cross-section diagram for a rectangular RC section: outline
 * + rebar bars as circles, at their actual (y,z) positions. Purely
 * illustrative (not used by analysis) -- but the coordinates it draws
 * are the same ones that feed the transformed-section calculation, not
 * a separate mock, so what's shown here is what the backend actually
 * sees.
 *
 * Local-axis convention matches FrameSection (Iy=∫z²dA, Iz=∫y²dA): y is
 * the horizontal extent (`widthM`), z the vertical extent (`depthM`).
 * SVG y-coordinates increase downward, so z is flipped when mapping to
 * screen space -- positive z (commonly "top" reinforcement) is drawn
 * near the top of the diagram. */

interface Bar {
  y: number;
  z: number;
  diameter: number;
}

interface SectionDiagramProps {
  widthM: number;
  depthM: number;
  bars: Bar[];
}

const PADDING = 16;
const DIAGRAM_SIZE = 160;
const MIN_BAR_RADIUS_PX = 3;

export function SectionDiagram({ widthM, depthM, bars }: SectionDiagramProps) {
  if (widthM <= 0 || depthM <= 0) {
    return null;
  }

  const scale = DIAGRAM_SIZE / Math.max(widthM, depthM);
  const w = widthM * scale;
  const h = depthM * scale;
  const viewW = w + PADDING * 2;
  const viewH = h + PADDING * 2;

  const toScreen = (y: number, z: number): [number, number] => [
    PADDING + (y + widthM / 2) * scale,
    PADDING + (depthM / 2 - z) * scale,
  ];

  const [rectX, rectY] = toScreen(-widthM / 2, depthM / 2);

  return (
    <svg
      className="section-diagram"
      viewBox={`0 0 ${viewW} ${viewH}`}
      width={viewW}
      height={viewH}
      role="img"
      aria-label={`Cross-section ${widthM}m x ${depthM}m with ${bars.length} rebar`}
    >
      <rect
        x={rectX}
        y={rectY}
        width={w}
        height={h}
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
      />
      {bars.map((bar, i) => {
        const [cx, cy] = toScreen(bar.y, bar.z);
        const r = Math.max((bar.diameter / 2) * scale, MIN_BAR_RADIUS_PX);
        return (
          // Bars have no stable id of their own in this preview-only list.
          // eslint-disable-next-line react/no-array-index-key
          <circle key={i} cx={cx} cy={cy} r={r} fill="currentColor" />
        );
      })}
    </svg>
  );
}
