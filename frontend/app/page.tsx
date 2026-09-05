"use client";

import { ChangeEvent, DragEvent, useId, useState } from "react";

const styles = [
  ["◌", "Original", "Keep the song's musical shape"],
  ["✦", "Music Box", "Bright, delicate and mechanical"],
  ["♬", "Solo Piano", "Expressive two-hand voicings"],
  ["▦", "8-Bit", "Bold leads and compact voices"],
  ["☾", "Lullaby", "Soft, sparse and unhurried"],
] as const;

export default function Home() {
  const inputId = useId();
  const [file, setFile] = useState<File | null>(null);
  const [selectedStyle, setSelectedStyle] = useState("Music Box");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const choose = (candidate?: File) => {
    if (candidate) setFile(candidate);
  };
  const drop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    choose(event.dataTransfer.files.item(0) ?? undefined);
  };
  const change = (event: ChangeEvent<HTMLInputElement>) =>
    choose(event.target.files?.[0]);

  const upload = async () => {
    if (!file || busy) return;
    setBusy(true);
    setMessage("Creating your private project…");
    const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const style = selectedStyle
      .toLowerCase()
      .replaceAll(" ", "_")
      .replace("8-bit", "eight_bit");
    try {
      const created = await fetch(`${api}/api/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ style }),
      });
      if (!created.ok) throw new Error("Unable to create the project.");
      const project = (await created.json()) as { id: string };
      setMessage("Uploading and validating audio…");
      const form = new FormData();
      form.append("audio", file);
      const response = await fetch(`${api}/api/projects/${project.id}/audio`, {
        method: "POST",
        body: form,
      });
      if (!response.ok) {
        const problem = (await response.json()) as { detail?: string };
        throw new Error(problem.detail ?? "The audio could not be uploaded.");
      }
      setMessage(
        "Audio validated. Your project is ready for analysis in the next phase.",
      );
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Unexpected upload error.",
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
          Milestone 02
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
          <h2 id="upload-title" className="text-xl font-medium">
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
            Choose file
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
          <button className="text-sm text-white/50 underline decoration-white/20 underline-offset-4">
            Advanced settings
          </button>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {styles.map(([icon, title, description]) => {
            const selected = title === selectedStyle;
            return (
              <button
                key={title}
                aria-pressed={selected}
                onClick={() => setSelectedStyle(title)}
                className={`min-h-44 rounded-2xl border p-5 text-left transition ${selected ? "border-lilac bg-lilac/10" : "border-white/10 bg-white/[.025] hover:border-white/30"}`}
              >
                <span aria-hidden="true" className="text-2xl text-lilac">
                  {icon}
                </span>
                <strong className="mt-8 block font-medium">{title}</strong>
                <span className="mt-2 block text-sm leading-5 text-white/45">
                  {description}
                </span>
              </button>
            );
          })}
        </div>
      </section>

      <div className="flex flex-col items-center border-t border-white/10 pt-10 text-center">
        <button
          disabled={!file || busy}
          onClick={upload}
          className="rounded-full bg-lilac px-8 py-3.5 font-semibold text-ink transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? "Uploading…" : "Create project"}
        </button>
        <p
          className="mt-3 min-h-5 text-xs text-white/50"
          role="status"
          aria-live="polite"
        >
          {message ?? "Audio is streamed to a private UUID-isolated project."}
        </p>
      </div>
      <footer className="mx-auto mt-20 max-w-2xl text-center text-xs leading-5 text-white/35">
        Upload only audio you have the right to process. Generated files are for
        your permitted personal or professional use.
      </footer>
    </main>
  );
}
