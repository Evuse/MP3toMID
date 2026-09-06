"use client";

import { ChangeEvent, DragEvent, useId, useState } from "react";

const styles = [
  {
    id: "original",
    icon: "◌",
    name: "Original",
    description: "Keep the song's musical shape",
  },
  {
    id: "music_box",
    icon: "✦",
    name: "Music Box",
    description: "Bright, delicate and mechanical",
  },
  {
    id: "solo_piano",
    icon: "♬",
    name: "Solo Piano",
    description: "Expressive two-hand voicings",
  },
  {
    id: "eight_bit",
    icon: "▦",
    name: "8-Bit",
    description: "Bold leads and compact voices",
  },
  {
    id: "lullaby",
    icon: "☾",
    name: "Lullaby",
    description: "Soft, sparse and unhurried",
  },
] as const;

type Settings = {
  fidelity: number;
  complexity: number;
  quantization: string;
  transpose: number;
  humanize: number;
  max_polyphony: number;
  include_drums: boolean;
};

const defaults: Settings = {
  fidelity: 75,
  complexity: 50,
  quantization: "1/16",
  transpose: 0,
  humanize: 10,
  max_polyphony: 6,
  include_drums: false,
};

export default function Home() {
  const inputId = useId();
  const [file, setFile] = useState<File | null>(null);
  const [selectedStyle, setSelectedStyle] = useState("music_box");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState<Settings>(defaults);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const [projectId, setProjectId] = useState<string | null>(null);

  const choose = (candidate?: File) => {
    if (!candidate) return;
    setFile(candidate);
    setProjectId(null);
    setError(false);
    setMessage(`${candidate.name} is ready to upload.`);
  };
  const drop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    choose(event.dataTransfer.files.item(0) ?? undefined);
  };
  const change = (event: ChangeEvent<HTMLInputElement>) =>
    choose(event.target.files?.[0]);
  const updateNumber = (key: keyof Settings, value: number) =>
    setSettings((current) => ({ ...current, [key]: value }));

  const upload = async () => {
    if (!file || busy) return;
    setBusy(true);
    setError(false);
    setProjectId(null);
    setMessage("Creating your private project…");
    let createdId: string | null = null;
    try {
      const created = await fetch("/backend/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ style: selectedStyle, settings }),
      });
      if (!created.ok)
        throw new Error("Backend unavailable. Start it with ‘make backend’. ");
      const project = (await created.json()) as { id: string };
      createdId = project.id;
      setMessage("Uploading and validating audio…");
      const form = new FormData();
      form.append("audio", file);
      const response = await fetch(
        `/backend/api/projects/${project.id}/audio`,
        {
          method: "POST",
          body: form,
        },
      );
      if (!response.ok) {
        const problem = (await response.json().catch(() => ({}))) as {
          detail?: string;
        };
        throw new Error(problem.detail ?? "The audio could not be uploaded.");
      }
      setProjectId(project.id);
      setMessage(
        "Upload complete. Audio was decoded and validated successfully.",
      );
    } catch (reason) {
      if (createdId) {
        await fetch(`/backend/api/projects/${createdId}`, {
          method: "DELETE",
        }).catch(() => undefined);
      }
      setError(true);
      setMessage(
        reason instanceof Error ? reason.message : "Unexpected upload error.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-5 pb-16 pt-6 sm:px-8">
      <nav
        className="flex items-center justify-between"
        aria-label="Main navigation"
      >
        <a
          href="#top"
          className="flex items-center gap-3 text-lg font-semibold tracking-tight"
        >
          <span
            aria-hidden="true"
            className="grid h-9 w-9 place-items-center rounded-full bg-lilac text-ink"
          >
            ♪
          </span>
          TuneMorph
        </a>
        <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/60">
          Upload ready
        </span>
      </nav>

      <section
        id="top"
        className="mx-auto max-w-4xl pb-16 pt-20 text-center sm:pt-28"
      >
        <p className="mb-5 text-xs font-semibold uppercase tracking-[.28em] text-lilac">
          Audio, reimagined
        </p>
        <h1 className="text-balance text-5xl font-medium leading-[1.02] tracking-[-.045em] sm:text-7xl">
          Transform any song into a new MIDI arrangement
        </h1>
        <p className="mx-auto mt-7 max-w-2xl text-balance text-base leading-7 text-white/60 sm:text-lg">
          Turn audio you have the right to use into a recognisable
          arrangement—not a promise of perfect note-for-note transcription.
        </p>
      </section>

      <section
        className="rounded-[2rem] border border-white/10 bg-white/[.035] p-3 shadow-glow backdrop-blur sm:p-5"
        aria-labelledby="upload-title"
      >
        <div
          onDragOver={(event) => event.preventDefault()}
          onDrop={drop}
          className="rounded-[1.5rem] border border-dashed border-white/20 px-6 py-12 text-center transition hover:border-lilac/70 hover:bg-lilac/[.04]"
        >
          <div
            aria-hidden="true"
            className="mx-auto mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-white/10 text-2xl"
          >
            ↥
          </div>
          <h2 id="upload-title" className="break-all text-xl font-medium">
            {file ? file.name : "Drop your audio file here"}
          </h2>
          <p className="mt-2 text-sm text-white/50">
            {file
              ? `${(file.size / 1048576).toFixed(1)} MB selected`
              : "MP3, WAV, FLAC or M4A · up to 200 MB"}
          </p>
          <input
            id={inputId}
            type="file"
            className="sr-only"
            accept="audio/mpeg,audio/wav,audio/flac,audio/mp4,.mp3,.wav,.flac,.m4a"
            onChange={change}
          />
          <label
            htmlFor={inputId}
            className="mt-6 inline-flex cursor-pointer rounded-full bg-cream px-6 py-3 text-sm font-semibold text-ink transition hover:bg-white"
          >
            {file ? "Choose another file" : "Choose file"}
          </label>
        </div>
      </section>

      <section className="py-16" aria-labelledby="styles-title">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[.2em] text-white/40">
              Step two
            </p>
            <h2 id="styles-title" className="mt-2 text-2xl font-medium">
              Choose a new character
            </h2>
          </div>
          <button
            type="button"
            aria-expanded={settingsOpen}
            aria-controls="advanced-settings"
            onClick={() => setSettingsOpen((open) => !open)}
            className="rounded-lg px-2 py-1 text-sm text-white/70 underline decoration-white/20 underline-offset-4 hover:text-white"
          >
            {settingsOpen ? "Hide advanced settings" : "Advanced settings"}
          </button>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {styles.map((style) => {
            const selected = style.id === selectedStyle;
            return (
              <button
                type="button"
                key={style.id}
                aria-pressed={selected}
                onClick={() => setSelectedStyle(style.id)}
                className={`relative min-h-44 rounded-2xl border p-5 text-left transition ${selected ? "border-lilac bg-lilac/15 ring-2 ring-lilac/40" : "border-white/10 bg-white/[.025] hover:border-white/30"}`}
              >
                {selected && (
                  <span className="absolute right-4 top-4 rounded-full bg-lilac px-2 py-1 text-xs font-bold text-ink">
                    Selected ✓
                  </span>
                )}
                <span aria-hidden="true" className="text-2xl text-lilac">
                  {style.icon}
                </span>
                <strong className="mt-8 block font-medium">{style.name}</strong>
                <span className="mt-2 block text-sm leading-5 text-white/45">
                  {style.description}
                </span>
              </button>
            );
          })}
        </div>

        {settingsOpen && (
          <div
            id="advanced-settings"
            className="mt-6 grid gap-6 rounded-2xl border border-white/10 bg-white/[.035] p-6 sm:grid-cols-2 lg:grid-cols-4"
          >
            <Range
              label="Fidelity"
              value={settings.fidelity}
              onChange={(value) => updateNumber("fidelity", value)}
            />
            <Range
              label="Complexity"
              value={settings.complexity}
              onChange={(value) => updateNumber("complexity", value)}
            />
            <Range
              label="Humanize"
              value={settings.humanize}
              onChange={(value) => updateNumber("humanize", value)}
            />
            <label className="grid gap-2 text-sm text-white/70">
              Quantization
              <select
                value={settings.quantization}
                onChange={(event) =>
                  setSettings((current) => ({
                    ...current,
                    quantization: event.target.value,
                  }))
                }
                className="rounded-lg border border-white/15 bg-ink p-2.5 text-white"
              >
                <option value="off">Off</option>
                <option value="1/4">1/4</option>
                <option value="1/8">1/8</option>
                <option value="1/16">1/16</option>
                <option value="1/32">1/32</option>
              </select>
            </label>
            <label className="grid gap-2 text-sm text-white/70">
              Transpose{" "}
              <span>
                {settings.transpose > 0 ? "+" : ""}
                {settings.transpose} semitones
              </span>
              <input
                type="range"
                min="-12"
                max="12"
                value={settings.transpose}
                onChange={(event) =>
                  updateNumber("transpose", Number(event.target.value))
                }
              />
            </label>
            <label className="grid gap-2 text-sm text-white/70">
              Maximum polyphony
              <input
                type="number"
                min="1"
                max="16"
                value={settings.max_polyphony}
                onChange={(event) =>
                  updateNumber("max_polyphony", Number(event.target.value))
                }
                className="rounded-lg border border-white/15 bg-ink p-2.5 text-white"
              />
            </label>
            <label className="flex items-center gap-3 self-end rounded-lg border border-white/10 p-3 text-sm text-white/70">
              <input
                type="checkbox"
                checked={settings.include_drums}
                onChange={(event) =>
                  setSettings((current) => ({
                    ...current,
                    include_drums: event.target.checked,
                  }))
                }
                className="h-4 w-4 accent-lilac"
              />
              Include drums
            </label>
          </div>
        )}
      </section>

      <div className="flex flex-col items-center border-t border-white/10 pt-10 text-center">
        <button
          type="button"
          disabled={!file || busy}
          onClick={upload}
          className="rounded-full bg-lilac px-8 py-3.5 font-semibold text-ink transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy
            ? "Uploading…"
            : file
              ? "Create project"
              : "Choose an audio file first"}
        </button>
        <p
          className={`mt-3 min-h-5 text-sm ${error ? "text-red-300" : "text-white/60"}`}
          role={error ? "alert" : "status"}
          aria-live="polite"
        >
          {message ??
            "Select a file, choose a style, then create your private project."}
        </p>
      </div>

      {projectId && (
        <section
          className="mx-auto mt-10 max-w-2xl rounded-2xl border border-emerald-300/30 bg-emerald-300/[.06] p-6"
          aria-labelledby="ready-title"
        >
          <p className="text-xs font-semibold uppercase tracking-[.2em] text-emerald-300">
            Validated
          </p>
          <h2 id="ready-title" className="mt-2 text-xl font-medium">
            Project created successfully
          </h2>
          <p className="mt-2 text-sm text-white/55">
            Private project <code>{projectId}</code>
          </p>
          <audio
            className="mt-5 w-full"
            controls
            preload="metadata"
            src={`/backend/api/projects/${projectId}/audio`}
          >
            Your browser does not support audio playback.
          </audio>
        </section>
      )}

      <footer className="mx-auto mt-20 max-w-2xl text-center text-xs leading-5 text-white/35">
        Upload only audio you have the right to process. Generated files are for
        your permitted personal or professional use.
      </footer>
    </main>
  );
}

function Range({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="grid gap-2 text-sm text-white/70">
      <span className="flex justify-between">
        <span>{label}</span>
        <output>{value}</output>
      </span>
      <input
        type="range"
        min="0"
        max="100"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="accent-lilac"
      />
    </label>
  );
}
