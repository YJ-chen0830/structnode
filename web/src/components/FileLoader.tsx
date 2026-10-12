import { useId, type ChangeEvent } from "react";

interface FileLoaderProps {
  label: string;
  accept?: string;
  onLoad: (text: string, fileName: string) => void;
  loadedFileName: string | null;
}

export function FileLoader({ label, accept = ".json", onLoad, loadedFileName }: FileLoaderProps) {
  const inputId = useId();

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        onLoad(reader.result, file.name);
      }
    };
    reader.readAsText(file);
    event.target.value = ""; // allow re-selecting the same file
  };

  return (
    <div className="file-loader">
      <label htmlFor={inputId}>{label}</label>
      <input id={inputId} type="file" accept={accept} onChange={handleChange} />
      {loadedFileName && <span className="file-loader__name">{loadedFileName}</span>}
    </div>
  );
}
