/** Triggers a browser download of `data` as pretty-printed JSON --
 * lets a model built in the wizard, or results from a run, round-trip
 * into the file-based "View files" mode (or just be kept/shared as a
 * plain CEM JSON / results JSON file). */
export function downloadJson(filename: string, data: unknown): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
