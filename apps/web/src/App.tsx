import { useEffect, useState, type ReactNode, type CSSProperties } from "react";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const DEMO_DOCUMENT = "demo://architecture_doc.md";
const DEMO_REPOSITORY = "https://github.com/example/driftguard-demo";
const DEMO_PR = `${DEMO_REPOSITORY}/pull/7`;

/* ---------------------------------------------------------------- types (mirror the FastAPI contract) */

type Evidence = {
  id: string;
  source_id: string;
  source_type: string;
  source_uri: string | null;
  source_version: string;
  locator: string;
  heading_path: string[];
  content: string;
};

type Explanation = {
  pm: {
    what_changed: string;
    why_it_matters: string;
    impacts: string[];
    decision_needed: string | null;
  };
  developer: {
    technical_change: string;
    affected_files_and_symbols: string[];
    stale_claim: string;
    verification_needed: string[];
  };
};

type PatchOperation = {
  locator: string;
  original_text: string | null;
  replacement_text: string;
};

type Alert = {
  id: string;
  status: string;
  title: string;
  existing_claim: { statement: string };
  implementation_claim: { statement: string };
  document_evidence: Evidence[];
  implementation_evidence: Evidence[];
  classification: {
    relationship: string;
    severity: string;
    concise_reason: string;
  };
  confidence: number;
  uncertainty: string[];
  explanations: Explanation;
  proposed_canonical_statement: string;
  patch: { operations: PatchOperation[] };
  provenance: {
    mode: string;
    is_demo: boolean;
    label: string;
    inference_mode: string;
  };
};

type ConfigStatus = {
  boot_ready: boolean;
  demo_mode: boolean;
  analysis_ready: boolean;
  mistral_configured: boolean;
  github_authenticated: boolean;
  google_read_ready: boolean;
  missing_requirements: string[];
};

type DecisionItem = {
  title: string;
  statement: string;
  status: "proposed" | "confirmed" | "rejected" | "deferred" | "ambiguous";
  owner: string | null;
  conditions: string[];
  confidence: number;
  evidence_ids: string[];
};

type TranscriptData = {
  provenance: { label: string; is_demo: boolean };
  evidence: Evidence[];
  transcript: { segments: Array<{ speaker: string; start_seconds: number; text: string }> };
  decisions: {
    decisions: DecisionItem[];
    unresolved_questions: DecisionItem[];
    action_items: DecisionItem[];
  };
};

type SourceLink = {
  role: "document" | "repository" | "pull_request" | "transcript";
  mode: "demo_fixture" | "live";
  label: string;
  uri: string;
  source_id: string;
  source_version: string;
  details: string[];
};

type DocumentChange = {
  mode: "demo_local_copy" | "google_docs";
  document_label: string;
  source_uri: string;
  target: string;
  source_version: string;
  before_content: string;
  proposed_content: string;
  applied_content: string | null;
  operations: PatchOperation[];
};

type AnalysisResult = {
  alert: Alert;
  sources: SourceLink[];
  transcript: TranscriptData | null;
  document_change: DocumentChange;
};

type EvaluationReport = {
  provenance: { label: string };
  total_cases: number;
  exact_matches: number;
  relation_accuracy: number;
  actionable_precision: number;
  citation_coverage: number;
  hard_negative_false_positives: number;
  cases: Array<{
    id: string;
    actual_relation: string;
    relation_correct: boolean;
    actionable_correct: boolean;
  }>;
};

function humanize(value: string) {
  return value.replaceAll("_", " ");
}

/* ---------------------------------------------------------------- helpers */

const font = "font-[var(--font-serif)]";

function PillButton({
  children,
  variant = "blue",
  arrow = false,
  onClick,
  disabled,
  type = "button",
}: {
  children: ReactNode;
  variant?: "blue" | "black" | "ghost";
  arrow?: boolean;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  const styles = {
    blue: "bg-lake-blue text-white hover:bg-[#244cb3]",
    black: "bg-off-black text-white hover:bg-black",
    ghost: "border border-off-black text-off-black hover:bg-off-black hover:text-white",
  }[variant];
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-[var(--radius-pill)] px-8 py-3 text-[14px] font-medium uppercase tracking-[-0.02em] transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-40 ${styles} ${font}`}
    >
      {children}
      {arrow && <span aria-hidden>▸</span>}
    </button>
  );
}

function Tag({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "crimson" | "blue" | "mint" }) {
  const tones = {
    neutral: "border-ash bg-parchment text-graphite",
    crimson: "border-crimson/40 bg-crimson/10 text-crimson",
    blue: "border-lake-blue/40 bg-lake-blue/10 text-lake-blue",
    mint: "border-[#4aa87a]/40 bg-mint/25 text-[#2f7a54]",
  }[tone];
  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-[12px] font-medium uppercase tracking-[-0.033em] ${tones} ${font}`}>
      {children}
    </span>
  );
}

function SectionNumber({ n, label }: { n: string; label: string }) {
  return (
    <div className="mb-8 flex items-baseline gap-4">
      <span className={`text-[14px] font-medium tabular-nums text-lake-blue ${font}`}>{n}</span>
      <span className={`text-[12px] font-medium uppercase tracking-[0.08em] text-smoke ${font}`}>{label}</span>
    </div>
  );
}

const reveal = (delay = 0): CSSProperties => ({ animationDelay: `${delay}ms` });

function statusTone(status: string): "neutral" | "crimson" | "blue" | "mint" {
  if (status === "confirmed" || status === "applied") return "mint";
  if (status === "rejected" || status === "ambiguous") return "crimson";
  if (status === "proposed") return "blue";
  return "neutral";
}

/** Wraps the first occurrence of each target substring in a highlight mark, in the order it appears. */
function highlightText(content: string, targets: string[], tone: "removed" | "added"): ReactNode {
  const matches = targets
    .filter((text) => text.length > 0)
    .map((text) => ({ text, index: content.indexOf(text) }))
    .filter((match) => match.index !== -1)
    .sort((a, b) => a.index - b.index);

  if (matches.length === 0) return content;

  const nodes: ReactNode[] = [];
  let cursor = 0;
  matches.forEach((match, i) => {
    if (match.index < cursor) return;
    nodes.push(content.slice(cursor, match.index));
    nodes.push(
      <mark
        key={`${tone}-${i}`}
        className={
          tone === "removed"
            ? "rounded bg-crimson/20 px-0.5 text-off-black line-through decoration-crimson/70"
            : "rounded bg-mint/60 px-0.5 font-bold text-off-black"
        }
      >
        {match.text}
      </mark>,
    );
    cursor = match.index + match.text.length;
  });
  nodes.push(content.slice(cursor));
  return nodes;
}

/* ---------------------------------------------------------------- nav */

function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-ash/60 bg-parchment/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1200px] items-center justify-between px-6">
        <div className={`flex items-center gap-3 text-[16px] font-bold uppercase tracking-[-0.02em] ${font}`}>
          <span className="grid h-6 w-6 place-items-center rounded-full bg-lake-blue text-[12px] text-white">DG</span>
          driftguard
        </div>
        <span className={`hidden text-[12px] font-medium uppercase tracking-[0.06em] text-smoke sm:block ${font}`}>
          Source-backed alignment
        </span>
      </div>
    </header>
  );
}

/* ---------------------------------------------------------------- intro */

function Intro() {
  return (
    <section className="relative overflow-hidden">
      <div
        className="dg-blob pointer-events-none absolute -left-32 -top-10 h-[380px] w-[380px] rounded-full opacity-60 blur-[70px]"
        style={{ background: "radial-gradient(circle,#a0b5eb 0%,#a7fccd 70%,transparent 100%)" }}
      />
      <div
        className="dg-blob pointer-events-none absolute -right-24 top-24 h-[320px] w-[320px] rounded-full opacity-50 blur-[70px]"
        style={{ background: "radial-gradient(circle,#ff9473 0%,#ecda98 70%,transparent 100%)", animationDelay: "-6s" }}
      />
      <div className="relative mx-auto max-w-[1200px] px-6 pb-4 pt-16">
        <Tag tone="blue">◇ DriftGuard · source-backed alignment</Tag>
        <h1 className={`mt-8 max-w-[18ch] text-[40px] font-bold leading-[1.05] tracking-[-0.02em] text-off-black md:text-[64px] ${font}`}>
          Link the document people trust to the code that actually shipped.
        </h1>
        <p className={`mt-6 max-w-[70ch] text-[18px] leading-[1.45] tracking-[-0.02em] text-graphite ${font}`}>
          Connect one architecture document, its GitHub repository and pull request, and an optional
          meeting transcript. DriftGuard shows exactly what it read, what changed, and auto-approves
          and writes the smallest document correction — no human sign-off required, every change
          highlighted in the document view below.
        </p>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- step 1: sources */

function Field({
  label,
  hint,
  value,
  onChange,
  placeholder,
  mono,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  mono?: boolean;
}) {
  return (
    <label className="block">
      <span className={`text-[13px] font-bold uppercase tracking-[-0.01em] text-off-black ${font}`}>{label}</span>
      <span className={`mt-1 block text-[12px] tracking-[-0.02em] text-smoke ${font}`}>{hint}</span>
      <input
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className={`mt-3 w-full rounded-2xl border border-ash bg-parchment px-4 py-3 text-[14px] tracking-[-0.02em] text-off-black outline-none transition-colors placeholder:text-smoke/60 focus:border-lake-blue ${mono ? "font-mono" : font}`}
      />
    </label>
  );
}

function Sources({
  config,
  onBuilding,
  onAnalysis,
  onTranscript,
  onError,
}: {
  config: ConfigStatus | null;
  onBuilding: (busy: boolean) => void;
  onAnalysis: (result: AnalysisResult) => void;
  onTranscript: (result: TranscriptData) => void;
  onError: (message: string | null) => void;
}) {
  const [documentUrl, setDocumentUrl] = useState(DEMO_DOCUMENT);
  const [repositoryUrl, setRepositoryUrl] = useState(DEMO_REPOSITORY);
  const [pullRequestUrl, setPullRequestUrl] = useState(DEMO_PR);
  const [useDemoTranscript, setUseDemoTranscript] = useState(true);
  const [transcriptText, setTranscriptText] = useState("");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const usesLiveDocument = !documentUrl.startsWith("demo://");
  const usesLiveCode = pullRequestUrl !== DEMO_PR;
  const liveAnalysisNeedsMistral = usesLiveDocument || usesLiveCode;
  const ready = Boolean(documentUrl.trim() && repositoryUrl.trim() && pullRequestUrl.trim());

  async function buildAlignment(event?: React.FormEvent) {
    event?.preventDefault();
    setBusy(true);
    onBuilding(true);
    setMessage(null);
    onError(null);
    try {
      const response = await fetch(`${API_URL}/api/analysis/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          document_url: documentUrl.trim(),
          repository_url: repositoryUrl.trim(),
          pull_request_url: pullRequestUrl.trim(),
          transcript_text: useDemoTranscript ? null : transcriptText.trim() || null,
          use_demo_transcript: useDemoTranscript,
        }),
      });
      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string };
        throw new Error(payload.detail ?? "The linked sources could not be analyzed.");
      }
      onAnalysis((await response.json()) as AnalysisResult);
      setMessage("Alignment view built and auto-approved from the linked sources below.");
    } catch (reason: unknown) {
      const text = reason instanceof Error ? reason.message : "Analysis failed.";
      setMessage(text);
      onError(text);
    } finally {
      setBusy(false);
      onBuilding(false);
    }
  }

  async function loadDemo() {
    setDocumentUrl(DEMO_DOCUMENT);
    setRepositoryUrl(DEMO_REPOSITORY);
    setPullRequestUrl(DEMO_PR);
    setUseDemoTranscript(true);
    setTranscriptText("");
    setBusy(true);
    onBuilding(true);
    onError(null);
    try {
      await fetch(`${API_URL}/api/demo/reset`, { method: "POST" });
      const response = await fetch(`${API_URL}/api/analysis/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          document_url: DEMO_DOCUMENT,
          repository_url: DEMO_REPOSITORY,
          pull_request_url: DEMO_PR,
          transcript_text: null,
          use_demo_transcript: true,
        }),
      });
      if (!response.ok) throw new Error("The demo workspace could not be reset.");
      onAnalysis((await response.json()) as AnalysisResult);
      setMessage("Perfect hackathon demo loaded with no credentials.");
    } catch (reason: unknown) {
      const text = reason instanceof Error ? reason.message : "Demo load failed.";
      setMessage(text);
      onError(text);
    } finally {
      setBusy(false);
      onBuilding(false);
    }
  }

  async function transcribeAudio() {
    if (!audioFile) return;
    setBusy(true);
    setMessage(null);
    try {
      const form = new FormData();
      form.append("file", audioFile);
      const response = await fetch(`${API_URL}/api/sources/transcript/audio`, {
        method: "POST",
        body: form,
      });
      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string };
        throw new Error(payload.detail ?? "Audio transcription failed.");
      }
      onTranscript((await response.json()) as TranscriptData);
      setMessage("Voxtral transcript and decisions added to this review.");
    } catch (reason: unknown) {
      setMessage(reason instanceof Error ? reason.message : "Audio upload failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mx-auto max-w-[1200px] px-6 py-16">
      <SectionNumber n="1" label="Link the project sources" />
      <div className="rounded-[var(--radius-card)] border border-ash bg-parchment p-8 md:p-10">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <h2 className={`text-[26px] font-bold tracking-[-0.02em] text-off-black md:text-[32px] ${font}`}>
            Tell DriftGuard which truth sources belong together.
          </h2>
          <PillButton variant="ghost" onClick={loadDemo} disabled={busy}>Load perfect demo</PillButton>
        </div>

        <form onSubmit={buildAlignment}>
          <div className="grid gap-8 md:grid-cols-2">
            <Field label="Architecture document" hint="Google Docs share URL, or the labelled local demo document."
              value={documentUrl} onChange={setDocumentUrl} placeholder="demo://architecture_doc.md" mono />
            <Field label="GitHub repository" hint="Canonical repository URL; read-only for this MVP."
              value={repositoryUrl} onChange={setRepositoryUrl} placeholder="https://github.com/example/driftguard-demo" mono />
            <Field label="GitHub pull request" hint="The behavior-changing PR to compare against the document."
              value={pullRequestUrl} onChange={setPullRequestUrl} placeholder="https://github.com/example/driftguard-demo/pull/7" mono />
            <label className="block">
              <span className={`text-[13px] font-bold uppercase tracking-[-0.01em] text-off-black ${font}`}>Meeting transcript · optional</span>
              <span className={`mt-1 flex items-center gap-2 text-[12px] tracking-[-0.02em] text-smoke ${font}`}>
                <input type="checkbox" checked={useDemoTranscript} onChange={(e) => setUseDemoTranscript(e.target.checked)} className="accent-lake-blue" />
                Use the labelled demo transcript
              </span>
              <textarea
                value={transcriptText}
                onChange={(e) => setTranscriptText(e.target.value)}
                disabled={useDemoTranscript}
                placeholder="[00:00] Priya: We approve asynchronous checkout processing."
                className={`mt-3 min-h-[76px] w-full resize-y rounded-2xl border border-ash bg-parchment px-4 py-3 text-[13px] tracking-[-0.02em] text-off-black outline-none transition-colors placeholder:text-smoke/60 focus:border-lake-blue disabled:bg-ash/20 disabled:text-smoke font-mono`}
              />
              <div className="mt-2 flex items-center gap-3">
                <input
                  type="file"
                  accept="audio/*"
                  onChange={(e) => setAudioFile(e.target.files?.[0] ?? null)}
                  className={`min-w-0 text-[11px] text-smoke ${font}`}
                />
                <button
                  type="button"
                  disabled={busy || !audioFile || !config?.mistral_configured}
                  onClick={transcribeAudio}
                  className={`shrink-0 rounded-[var(--radius-pill)] border border-off-black px-4 py-1.5 text-[11px] font-medium uppercase tracking-[-0.02em] text-off-black transition-colors hover:bg-off-black hover:text-white disabled:cursor-not-allowed disabled:opacity-40 ${font}`}
                >
                  Transcribe with Voxtral
                </button>
              </div>
            </label>
          </div>

          <div className="mt-10 flex flex-wrap items-center justify-between gap-4 border-t border-ash pt-8">
            <div className={`max-w-[560px] text-[12px] uppercase tracking-[-0.02em] text-smoke ${font}`}>
              <strong className="text-graphite">{liveAnalysisNeedsMistral ? "Live setup" : "Demo setup"}</strong>
              {" · "}
              {liveAnalysisNeedsMistral
                ? `Needs ${usesLiveDocument ? "Google service-account access and " : ""}MISTRAL_API_KEY. A public GitHub PR needs no token.`
                : "No credentials required. All local fixtures are visibly labelled."}
            </div>
            <PillButton variant="blue" arrow type="submit" disabled={busy || !ready}>
              {busy ? "Building…" : "Build alignment view"}
            </PillButton>
          </div>
        </form>
        {message && <p className={`mt-4 text-[13px] tracking-[-0.02em] text-graphite ${font}`} role="status">{message}</p>}
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- analyzing */

function Analyzing() {
  const steps = [
    "Reading architecture document · heading-aware chunking",
    "Fetching pull request · resolving changed files",
    "Extracting documented + implementation claims (Mistral)",
    "Classifying drift relation · validating evidence IDs",
    "Auto-approving and writing the minimal document patch",
  ];
  return (
    <section className="mx-auto max-w-[1200px] px-6 py-16">
      <SectionNumber n="··" label="Building alignment view" />
      <div className="relative overflow-hidden rounded-[var(--radius-card)] border border-ash bg-periwinkle-mist/50 p-10">
        <div className="dg-scan pointer-events-none absolute inset-x-0 top-0 h-24"
          style={{ background: "linear-gradient(180deg,transparent,rgba(43,89,209,0.10),transparent)", animation: "dg-scan 1.8s ease-in-out infinite" }} />
        <div className="relative space-y-4">
          {steps.map((s, i) => (
            <div key={s} className="flex items-center gap-4 dg-reveal" style={reveal(i * 260)}>
              <span className="dg-pulse grid h-6 w-6 place-items-center rounded-full bg-lake-blue text-[11px] text-white" style={{ animationDelay: `${i * 260}ms` }}>◐</span>
              <span className={`text-[15px] tracking-[-0.02em] text-off-black ${font}`}>{s}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- step 2: what it read */

function ConnectorCard({ kind, title, url, id, version, extra, delay }: {
  kind: string; title: string; url: string; id: string; version: string; extra: ReactNode; delay: number;
}) {
  return (
    <div className="dg-reveal rounded-[28px] border border-ash bg-parchment p-6" style={reveal(delay)}>
      <Tag>{kind}</Tag>
      <h3 className={`mt-4 text-[18px] font-bold tracking-[-0.02em] text-off-black ${font}`}>{title}</h3>
      {url.startsWith("https://") ? (
        <a href={url} target="_blank" rel="noreferrer" className="mt-1 block truncate text-[12px] text-lake-blue hover:underline font-mono">{url}</a>
      ) : (
        <code className="mt-1 block truncate text-[12px] text-graphite">{url}</code>
      )}
      <dl className="mt-4 space-y-2 text-[12px]">
        <div>
          <dt className={`uppercase tracking-[0.05em] text-smoke ${font}`}>Source ID</dt>
          <dd className="break-all font-mono text-off-black">{id}</dd>
        </div>
        <div>
          <dt className={`uppercase tracking-[0.05em] text-smoke ${font}`}>Version</dt>
          <dd className="break-all font-mono text-graphite">{version}</dd>
        </div>
      </dl>
      <div className={`mt-4 border-t border-ash pt-3 text-[12px] tracking-[-0.02em] text-graphite ${font}`}>{extra}</div>
    </div>
  );
}

function WhatItRead({ sources, alert }: { sources: SourceLink[]; alert: Alert }) {
  return (
    <section className="mx-auto max-w-[1200px] px-6 py-16">
      <SectionNumber n="2" label="What DriftGuard actually read" />
      <h2 className={`mb-8 text-[26px] font-bold tracking-[-0.02em] text-off-black md:text-[32px] ${font}`}>
        Every source, version, file, and write target is explicit.
      </h2>
      <div className="mb-6"><Tag tone={alert.provenance.is_demo ? "neutral" : "mint"}>{alert.provenance.is_demo ? "◆ Labelled demo data" : "● Live connector data"}</Tag></div>
      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
        {sources.map((source, i) => (
          <ConnectorCard
            key={`${source.role}:${source.source_id}`}
            delay={i * 120}
            kind={humanize(source.role)}
            title={source.label}
            url={source.uri}
            id={source.source_id}
            version={source.source_version}
            extra={source.details.length > 0 ? source.details.join(" · ") : "—"}
          />
        ))}
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- step 3: review drift */

function EvidenceBlock({ tag, source, cite, code, children }: {
  tag: string; source: string; cite: string; code?: boolean; children: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-ash bg-parchment p-6">
      <p className={`mb-3 text-[11px] uppercase tracking-[0.06em] text-smoke ${font}`}>{tag}</p>
      {code ? (
        <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-[12px] leading-[1.6] text-off-black">{children}</pre>
      ) : (
        <div className={`text-[15px] leading-[1.5] tracking-[-0.02em] text-off-black ${font}`}>{children}</div>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        <Tag>{source}</Tag>
        <span className="font-mono text-[11px] text-graphite">{cite}</span>
      </div>
    </div>
  );
}

function EvidenceColumn({ title, claim, evidence }: { title: string; claim: string; evidence: Evidence[] }) {
  return (
    <div className="bg-parchment px-8 py-8">
      <p className={`mb-4 text-[12px] font-bold uppercase tracking-[0.05em] text-off-black ${font}`}>{title}</p>
      <p className={`mb-5 text-[15px] leading-[1.5] tracking-[-0.02em] text-off-black ${font}`}>{claim}</p>
      <div className="space-y-4">
        {evidence.map((item) => (
          <EvidenceBlock
            key={item.id}
            tag={`${item.id} · ${item.locator}`}
            source={item.source_type === "github_pr" ? "GitHub PR" : "Architecture document"}
            cite={item.heading_path.join(" / ") || item.source_id}
            code={item.source_type === "github_pr"}
          >
            {item.content}
          </EvidenceBlock>
        ))}
      </div>
    </div>
  );
}

function ReviewDrift({ alert, onRefresh }: { alert: Alert; onRefresh: () => Promise<void> }) {
  const [view, setView] = useState<"product" | "dev">("product");
  const [reviewer, setReviewer] = useState("Demo reviewer");
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [feedbackVerdict, setFeedbackVerdict] = useState<string | null>(null);
  const operation = alert.patch.operations[0];

  useEffect(() => setFeedbackVerdict(null), [alert.id]);

  async function applyNow() {
    setSubmitting(true);
    setActionError(null);
    try {
      const response = await fetch(`${API_URL}/api/alerts/${alert.id}/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor_id: reviewer.trim() || "Demo reviewer" }),
      });
      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string };
        throw new Error(payload.detail ?? "The approved patch could not be applied.");
      }
      await onRefresh();
    } catch (reason: unknown) {
      setActionError(reason instanceof Error ? reason.message : "The patch could not be applied.");
    } finally {
      setSubmitting(false);
    }
  }

  async function submitFeedback(verdict: "correct" | "false_positive" | "needs_evidence") {
    setSubmitting(true);
    setActionError(null);
    try {
      const response = await fetch(`${API_URL}/api/alerts/${alert.id}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor_id: reviewer.trim() || "Demo reviewer", verdict, comment: null }),
      });
      if (!response.ok) throw new Error("Feedback could not be recorded.");
      setFeedbackVerdict(verdict);
    } catch (reason: unknown) {
      setActionError(reason instanceof Error ? reason.message : "Feedback could not be saved.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-[1200px] px-6 py-16">
      <SectionNumber n="3" label="Review the drift" />
      <div className="overflow-hidden rounded-[var(--radius-card)] border border-ash bg-periwinkle-mist">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-ash/70 px-8 py-6">
          <div className="flex flex-wrap items-center gap-3">
            <Tag tone="crimson">▲ {alert.classification.severity} severity</Tag>
            <Tag tone="crimson">{humanize(alert.classification.relationship)}</Tag>
            <Tag tone={alert.provenance.is_demo ? "neutral" : "mint"}>{alert.provenance.is_demo ? "◆ Demo evidence" : "● Live evidence"}</Tag>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-[13px] font-bold text-off-black ${font}`}>{Math.round(alert.confidence * 100)}%</span>
            <span className={`text-[11px] uppercase tracking-[0.05em] text-smoke ${font}`}>confidence</span>
          </div>
        </div>

        <div className="bg-parchment px-8 py-8">
          <h2 className={`text-[24px] font-bold tracking-[-0.02em] text-off-black md:text-[30px] ${font}`}>{alert.title}</h2>
          <p className={`mt-4 max-w-[85ch] text-[16px] leading-[1.55] tracking-[-0.02em] text-graphite ${font}`}>{alert.classification.concise_reason}</p>
        </div>

        <div className="grid gap-px bg-ash/70 md:grid-cols-2">
          <EvidenceColumn title="What the document says" claim={alert.existing_claim.statement} evidence={alert.document_evidence} />
          <EvidenceColumn title="What the implementation does" claim={alert.implementation_claim.statement} evidence={alert.implementation_evidence} />
        </div>

        <div className="border-t border-ash/70 bg-parchment px-8 py-8">
          <div className={`mb-6 inline-flex rounded-full border border-off-black p-1 text-[13px] uppercase tracking-[-0.02em] ${font}`}>
            {(["product", "dev"] as const).map((v) => (
              <button key={v} onClick={() => setView(v)}
                className={`rounded-full px-5 py-1.5 font-medium transition-colors ${view === v ? "bg-off-black text-white" : "text-off-black"}`}>
                {v === "product" ? "Product view" : "Developer view"}
              </button>
            ))}
          </div>

          {view === "product" ? (
            <div className="dg-reveal max-w-[80ch]" style={reveal(0)}>
              <p className={`text-[11px] uppercase tracking-[0.06em] text-smoke ${font}`}>What changed</p>
              <h3 className={`mt-3 text-[18px] font-bold tracking-[-0.02em] text-off-black ${font}`}>{alert.explanations.pm.what_changed}</h3>
              <p className={`mt-3 text-[16px] leading-[1.55] tracking-[-0.02em] text-graphite ${font}`}>{alert.explanations.pm.why_it_matters}</p>
              {alert.explanations.pm.impacts.length > 0 && (
                <ul className={`mt-4 space-y-2 text-[14px] leading-[1.5] tracking-[-0.02em] text-graphite ${font}`}>
                  {alert.explanations.pm.impacts.map((item) => <li key={item}>› {item}</li>)}
                </ul>
              )}
              {alert.explanations.pm.decision_needed && (
                <div className="mt-6 border-l-2 border-gold bg-gold/10 px-4 py-3">
                  <p className={`text-[11px] uppercase tracking-[0.06em] text-smoke ${font}`}>Decision needed</p>
                  <p className={`mt-1 text-[14px] text-off-black ${font}`}>{alert.explanations.pm.decision_needed}</p>
                </div>
              )}
            </div>
          ) : (
            <div className="dg-reveal max-w-[80ch] space-y-4" style={reveal(0)}>
              <p className={`text-[11px] uppercase tracking-[0.06em] text-smoke ${font}`}>Technical change</p>
              <p className={`text-[16px] leading-[1.55] tracking-[-0.02em] text-off-black ${font}`}>{alert.explanations.developer.technical_change}</p>
              <p className={`text-[14px] leading-[1.5] tracking-[-0.02em] text-graphite ${font}`}><strong className="text-off-black">Stale claim:</strong> {alert.explanations.developer.stale_claim}</p>
              <div className="flex flex-wrap gap-2">
                {alert.explanations.developer.affected_files_and_symbols.map((s) => (
                  <span key={s} className="rounded-full border border-ash px-3 py-1 font-mono text-[11px] text-graphite">{s}</span>
                ))}
              </div>
              {alert.explanations.developer.verification_needed.length > 0 && (
                <ul className={`mt-2 space-y-2 text-[14px] leading-[1.5] tracking-[-0.02em] text-graphite ${font}`}>
                  {alert.explanations.developer.verification_needed.map((item) => <li key={item}>› {item}</li>)}
                </ul>
              )}
            </div>
          )}
        </div>

        <div className="border-t border-ash/70 bg-parchment px-8 py-8">
          <p className={`mb-4 text-[12px] font-bold uppercase tracking-[0.05em] text-off-black ${font}`}>Minimal document patch · {operation.locator}</p>
          <div className="space-y-px overflow-hidden rounded-2xl border border-ash font-mono text-[13px] leading-[1.6]">
            <div className="bg-crimson/10 px-4 py-3 text-off-black">
              <span className="mr-2 text-crimson">−</span>{operation.original_text}
            </div>
            <div className="bg-mint/25 px-4 py-3 text-off-black">
              <span className="mr-2 text-[#2f7a54]">+</span>{operation.replacement_text}
            </div>
          </div>
          {alert.uncertainty.length > 0 && (
            <div className={`mt-4 text-[12px] tracking-[-0.02em] text-smoke ${font}`}>
              <strong className="text-graphite">Still unresolved</strong>
              <ul className="mt-1 space-y-1">{alert.uncertainty.map((item) => <li key={item}>› {item}</li>)}</ul>
            </div>
          )}

          <div className="mt-8 flex flex-wrap items-center gap-3">
            {alert.status === "approved" ? (
              <>
                <span className={`grid h-7 w-7 place-items-center rounded-full bg-lake-blue text-white`}>◐</span>
                <span className={`text-[13px] uppercase tracking-[-0.02em] text-off-black ${font}`}>Auto-approved · writing now</span>
                <PillButton variant="blue" onClick={applyNow} disabled={submitting}>
                  {alert.provenance.is_demo ? "Apply to demo copy" : "Apply to Google Docs"}
                </PillButton>
              </>
            ) : (
              <>
                <span className={`grid h-7 w-7 place-items-center rounded-full text-white ${alert.status === "applied" ? "bg-[#2f7a54]" : "bg-off-black"}`}>
                  {alert.status === "applied" ? "✓" : "…"}
                </span>
                <span className={`text-[13px] uppercase tracking-[-0.02em] text-off-black ${font}`}>
                  {alert.status === "applied"
                    ? "Auto-approved & applied · no human review needed · audit recorded"
                    : `${humanize(alert.status)} · audit recorded`}
                </span>
              </>
            )}
            {actionError && <span className="text-[12px] text-crimson">{actionError}</span>}
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-ash pt-6">
            <div className="flex flex-wrap items-center gap-3">
              <span className={`text-[11px] uppercase tracking-[0.05em] text-smoke ${font}`}>Was this alert correctly classified?</span>
              <input
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                placeholder="Reviewer"
                className={`w-40 rounded-full border border-ash bg-parchment px-3 py-1.5 text-[12px] tracking-[-0.02em] outline-none focus:border-lake-blue ${font}`}
              />
            </div>
            {feedbackVerdict ? (
              <span className={`text-[12px] uppercase tracking-[0.05em] text-[#2f7a54] ${font}`}>Feedback recorded: {humanize(feedbackVerdict)}</span>
            ) : (
              <div className="flex flex-wrap gap-2">
                <button disabled={submitting} onClick={() => submitFeedback("correct")} className={`rounded-full border border-ash bg-parchment px-3 py-1.5 text-[11px] text-off-black hover:bg-off-black hover:text-white disabled:opacity-40 ${font}`}>Correct</button>
                <button disabled={submitting} onClick={() => submitFeedback("needs_evidence")} className={`rounded-full border border-ash bg-parchment px-3 py-1.5 text-[11px] text-off-black hover:bg-off-black hover:text-white disabled:opacity-40 ${font}`}>Needs evidence</button>
                <button disabled={submitting} onClick={() => submitFeedback("false_positive")} className={`rounded-full border border-ash bg-parchment px-3 py-1.5 text-[11px] text-off-black hover:bg-off-black hover:text-white disabled:opacity-40 ${font}`}>False positive</button>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- step 4: document change */

function DocChange({ change }: { change: DocumentChange }) {
  const removedTargets = change.operations
    .map((op) => op.original_text)
    .filter((text): text is string => Boolean(text));
  const addedTargets = change.operations.map((op) => op.replacement_text);

  const cols: Array<{ label: string; body: string; tone: string; highlights: string[]; highlightTone: "removed" | "added" }> = [
    { label: "Before · source document", body: change.before_content, tone: "bg-parchment", highlights: removedTargets, highlightTone: "removed" },
    { label: "Auto-approved · proposed document", body: change.proposed_content, tone: "bg-lake-blue/5", highlights: addedTargets, highlightTone: "added" },
    ...(change.applied_content
      ? [{
          label: "Written automatically · applied copy",
          body: change.applied_content,
          tone: "bg-mint/20",
          highlights: addedTargets,
          highlightTone: "added" as const,
        }]
      : []),
  ];

  return (
    <section className="mx-auto max-w-[1200px] px-6 py-16">
      <SectionNumber n="4" label="The actual document change" />
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <h2 className={`text-[26px] font-bold tracking-[-0.02em] text-off-black md:text-[32px] ${font}`}>{change.document_label}</h2>
        <Tag tone={change.applied_content ? "mint" : "blue"}>
          {change.applied_content ? "✓ Applied automatically" : "◐ Auto-approved · writing"}
        </Tag>
      </div>
      <p className={`mb-8 max-w-[90ch] text-[13px] tracking-[-0.02em] text-smoke ${font}`}>
        Reading <span className="font-mono">{change.source_uri}</span> · auto-approved with no human
        review and written to <span className="font-mono">{change.target}</span>
      </p>
      <div className={`grid gap-5 ${cols.length === 3 ? "md:grid-cols-3" : "md:grid-cols-2"}`}>
        {cols.map((c) => (
          <div key={c.label} className={`rounded-[28px] border border-ash p-6 ${c.tone}`}>
            <p className={`mb-4 text-[11px] font-bold uppercase tracking-[0.05em] text-off-black ${font}`}>{c.label}</p>
            <p className={`whitespace-pre-wrap text-[14px] leading-[1.6] tracking-[-0.02em] text-off-black ${font}`}>
              {highlightText(c.body, c.highlights, c.highlightTone)}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- step 5: decisions */

function Decisions({ data }: { data: TranscriptData | null }) {
  if (data === null) {
    return (
      <section className="mx-auto max-w-[1200px] px-6 py-16">
        <SectionNumber n="5" label="Meeting decision log" />
        <h2 className={`text-[26px] font-bold tracking-[-0.02em] text-off-black md:text-[32px] ${font}`}>No transcript linked to this analysis.</h2>
      </section>
    );
  }

  const groups: Array<{ label: string; items: DecisionItem[] }> = [
    { label: "Decisions", items: data.decisions.decisions },
    { label: "Unresolved", items: data.decisions.unresolved_questions },
    { label: "Actions", items: data.decisions.action_items },
  ];

  return (
    <section className="mx-auto max-w-[1200px] px-6 py-16">
      <SectionNumber n="5" label="Meeting decision log" />
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <h2 className={`text-[26px] font-bold tracking-[-0.02em] text-off-black md:text-[32px] ${font}`}>What the team decided — and what remains open.</h2>
        <span className="font-mono text-[11px] text-smoke">{data.provenance.label}</span>
      </div>
      <div className="grid gap-5 md:grid-cols-3">
        {groups.map((group) => (
          <div key={group.label} className="rounded-[28px] border border-ash bg-parchment p-6">
            <div className="mb-4 flex items-center justify-between">
              <span className={`text-[13px] font-bold uppercase tracking-[0.05em] text-off-black ${font}`}>{group.label}</span>
              {group.items.length > 0 && <Tag tone={statusTone(group.items[0].status)}>{group.items[0].status}</Tag>}
            </div>
            {group.items.length === 0 ? (
              <p className={`text-[15px] leading-[1.5] tracking-[-0.02em] text-graphite ${font}`}>None extracted.</p>
            ) : (
              <div className="space-y-4">
                {group.items.map((item) => (
                  <div key={item.title} className="border-t border-ash pt-3 first:border-t-0 first:pt-0">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className={`text-[13px] font-bold text-off-black ${font}`}>{item.title}</span>
                      {group.items.length > 1 && <Tag tone={statusTone(item.status)}>{item.status}</Tag>}
                    </div>
                    <p className={`text-[15px] leading-[1.5] tracking-[-0.02em] text-off-black ${font}`}>{item.statement}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- step 6: evaluation */

function Evaluation({ report }: { report: EvaluationReport | null }) {
  if (report === null) return null;
  const metrics = [
    { v: `${report.exact_matches}/${report.total_cases}`, l: "Exact cases" },
    { v: `${Math.round(report.relation_accuracy * 100)}%`, l: "Relation accuracy" },
    { v: `${Math.round(report.actionable_precision * 100)}%`, l: "Actionable precision" },
    { v: `${Math.round(report.citation_coverage * 100)}%`, l: "Citation coverage" },
  ];
  return (
    <section className="mx-auto max-w-[1200px] px-6 py-16">
      <SectionNumber n="6" label="Seeded evaluation" />
      <h2 className={`mb-8 text-[26px] font-bold tracking-[-0.02em] text-off-black md:text-[32px] ${font}`}>
        Hard negatives stay quiet; actionable drift stays visible.
      </h2>
      <div className="grid gap-5 lg:grid-cols-[auto_1fr]">
        <div className="grid grid-cols-2 gap-4">
          {metrics.map((m) => (
            <div key={m.l} className="rounded-[28px] border border-ash bg-off-black px-8 py-8 text-center">
              <div className={`text-[40px] font-bold tabular-nums text-parchment ${font}`}>{m.v}</div>
              <div className={`mt-2 text-[11px] uppercase tracking-[0.05em] text-parchment/70 ${font}`}>{m.l}</div>
            </div>
          ))}
        </div>
        <div className="rounded-[28px] border border-ash bg-parchment p-6">
          <p className={`mb-4 font-mono text-[11px] uppercase tracking-[0.05em] text-smoke`}>{report.provenance.label}</p>
          <ul className="divide-y divide-ash">
            {report.cases.map((item) => (
              <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <span className="font-mono text-[13px] text-off-black">{item.id}</span>
                <Tag tone={item.relation_correct && item.actionable_correct ? "mint" : "crimson"}>{humanize(item.actual_relation)}</Tag>
              </li>
            ))}
          </ul>
          <p className={`mt-4 text-[12px] uppercase tracking-[0.05em] text-[#2f7a54] ${font}`}>Hard-negative false positives: {report.hard_negative_false_positives}</p>
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- state panel */

function StatePanel({ title, tone, children }: { title: string; tone: "error" | "loading"; children: ReactNode }) {
  return (
    <section className="mx-auto max-w-[1200px] px-6 py-16">
      <div className={`rounded-[var(--radius-card)] border border-ash p-16 text-center ${tone === "error" ? "bg-crimson/5" : "bg-parchment"}`}>
        <span className={`mx-auto mb-4 grid h-5 w-5 place-items-center rounded-full ${tone === "error" ? "bg-crimson" : "dg-pulse bg-lake-blue"}`} />
        <h2 className={`text-[22px] font-bold tracking-[-0.02em] text-off-black ${font}`}>{title}</h2>
        <p className={`mx-auto mt-3 max-w-[60ch] text-[15px] leading-[1.5] text-graphite ${font}`}>{children}</p>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- footer */

function Footer() {
  return (
    <footer className="border-t border-ash">
      <div className={`mx-auto flex max-w-[1200px] flex-col items-center justify-between gap-3 px-6 py-8 text-[12px] uppercase tracking-[0.05em] text-smoke md:flex-row ${font}`}>
        <span>DG driftguard — atlassian hackathon 2026</span>
        <span>Mistral-only · evidence-backed · auto-approved</span>
      </div>
    </footer>
  );
}

/* ---------------------------------------------------------------- app */

export default function App() {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [config, setConfig] = useState<ConfigStatus | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationReport | null>(null);
  const [uploadedTranscript, setUploadedTranscript] = useState<TranscriptData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [building, setBuilding] = useState(false);

  async function loadCurrent() {
    const response = await fetch(`${API_URL}/api/analysis/current`);
    if (!response.ok) throw new Error("The current alignment view could not be loaded.");
    setAnalysis((await response.json()) as AnalysisResult);
  }

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    Promise.all([
      fetch(`${API_URL}/api/analysis/current`, { signal: controller.signal }),
      fetch(`${API_URL}/api/config/status`, { signal: controller.signal }),
      fetch(`${API_URL}/api/evaluations/gold`, { signal: controller.signal }),
    ])
      .then(async ([analysisResponse, configResponse, evaluationResponse]) => {
        if (!analysisResponse.ok || !configResponse.ok) {
          throw new Error("DriftGuard API is unavailable.");
        }
        setAnalysis((await analysisResponse.json()) as AnalysisResult);
        setConfig((await configResponse.json()) as ConfigStatus);
        setEvaluation(evaluationResponse.ok ? ((await evaluationResponse.json()) as EvaluationReport) : null);
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "Unable to load DriftGuard.");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  return (
    <div className="min-h-screen bg-parchment">
      <Nav />
      <Intro />
      <Sources
        config={config}
        onBuilding={setBuilding}
        onAnalysis={(result) => {
          setAnalysis(result);
          setUploadedTranscript(null);
          setError(null);
        }}
        onTranscript={setUploadedTranscript}
        onError={setError}
      />
      {building ? (
        <Analyzing />
      ) : error ? (
        <StatePanel title="The review API is unavailable" tone="error">
          {error} Start the FastAPI service on port 8000, then reload this page.
        </StatePanel>
      ) : loading || analysis === null ? (
        <StatePanel title="Loading the linked workspace" tone="loading">
          Resolving source identity, versions, evidence, and the document patch.
        </StatePanel>
      ) : (
        <div className="dg-reveal" style={reveal(0)}>
          <WhatItRead sources={analysis.sources} alert={analysis.alert} />
          <ReviewDrift alert={analysis.alert} onRefresh={loadCurrent} />
          <DocChange change={analysis.document_change} />
          <Decisions data={uploadedTranscript ?? analysis.transcript} />
          <Evaluation report={evaluation} />
        </div>
      )}
      <Footer />
    </div>
  );
}
