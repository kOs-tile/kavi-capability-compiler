"use client";

import { useEffect, useMemo, useState } from "react";

const EXAMPLES = {
  github: "https://github.com/AvdLee/Swift-Concurrency-Agent-Skill",
  mcp: "https://example.com/mcp",
};

function stateClass(state) {
  return ["SHIP", "FIX", "BLOCKED"].includes(state) ? state.toLowerCase() : "unknown";
}

function normalizeError(payload) {
  if (payload && typeof payload.detail === "object" && payload.detail) {
    return payload.detail.message || "Audit failed.";
  }
  if (payload && typeof payload.detail === "string") return payload.detail;
  return "Audit failed.";
}

export default function Home() {
  const [kind, setKind] = useState("github");
  const [target, setTarget] = useState(EXAMPLES.github);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("idle");
  const [copied, setCopied] = useState(false);

  async function runAudit(nextKind = kind, nextTarget = target) {
    const value = nextTarget.trim();
    if (!value) return;

    setStatus("running");
    setError("");
    setReport(null);
    setCopied(false);

    try {
      const response = await fetch("/api/audit", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ kind: nextKind, target: value }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(normalizeError(payload));
      setReport(payload);
      setStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Audit failed.");
      setStatus("error");
    }
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const qKind = params.get("kind");
    const qTarget = params.get("target");
    const autorun = params.get("run") === "1";
    if ((qKind === "github" || qKind === "mcp") && qTarget) {
      setKind(qKind);
      setTarget(qTarget);
      if (autorun) runAudit(qKind, qTarget);
    }
    // Run only once on page hydration.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const result = report?.report || null;
  const findings = Array.isArray(result?.findings) ? result.findings : [];
  const summary = result?.summary || {};

  const shareAllowed = useMemo(() => {
    if (!report || status !== "done") return false;
    try {
      const url = new URL(target);
      return !url.search && !url.hash;
    } catch {
      return false;
    }
  }, [report, status, target]);

  async function copyShare() {
    if (!shareAllowed) return;
    const url = new URL(window.location.origin);
    url.searchParams.set("kind", kind);
    url.searchParams.set("target", target.trim());
    url.searchParams.set("run", "1");
    await navigator.clipboard.writeText(url.toString());
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="KAVI Plugin Doctor home">
          <span className="mark">K</span>
          <span>KAVI / PLUGIN DOCTOR</span>
        </a>
        <span className="status-pill">V0 · PUBLIC AUDIT</span>
      </header>

      <section className="hero">
        <p className="kicker">PRE-SHIP DIAGNOSTICS FOR AGENT PLUGINS</p>
        <h1>Know what breaks <span>before</span> review.</h1>
        <p className="lede">
          Audit a public Agent Plugin repository or a remote MCP capability surface.
          Plugin Doctor checks structure, authority, metadata, and review-readiness without invoking tools.
        </p>

        <div className="audit-panel">
          <div className="tabs" role="tablist" aria-label="Audit source">
            {["github", "mcp"].map((item) => (
              <button
                key={item}
                type="button"
                className={kind === item ? "tab active" : "tab"}
                onClick={() => {
                  setKind(item);
                  setTarget(EXAMPLES[item]);
                  setReport(null);
                  setError("");
                  setStatus("idle");
                }}
              >
                {item === "github" ? "GitHub repository" : "Remote MCP"}
              </button>
            ))}
          </div>

          <form
            className="audit-form"
            onSubmit={(event) => {
              event.preventDefault();
              runAudit();
            }}
          >
            <input
              value={target}
              onChange={(event) => setTarget(event.target.value)}
              aria-label={kind === "github" ? "GitHub repository URL" : "Remote MCP URL"}
              spellCheck="false"
              autoCapitalize="none"
              autoCorrect="off"
            />
            <button className="primary" disabled={status === "running"} type="submit">
              {status === "running" ? "AUDITING…" : "RUN AUDIT"}
            </button>
          </form>

          <div className="guardline">
            <span>READ-ONLY DISCOVERY</span>
            <span>NO TOOL EXECUTION</span>
            <span>NO CREDENTIAL STORAGE</span>
          </div>
        </div>
      </section>

      {error && (
        <section className="error-card" role="alert">
          <span>AUDIT ERROR</span>
          <p>{error}</p>
        </section>
      )}

      {result && (
        <section className="results">
          <div className="result-head">
            <div>
              <p className="kicker">READINESS RESULT</p>
              <div className={"state " + stateClass(result.state)}>{result.state}</div>
            </div>
            <div className="score">
              <strong>{result.score ?? "—"}</strong>
              <span>/100</span>
            </div>
          </div>

          <div className="metrics">
            {Object.entries(summary)
              .filter(([, value]) => ["string", "number", "boolean"].includes(typeof value))
              .map(([key, value]) => (
                <div className="metric" key={key}>
                  <span>{key.replaceAll("_", " ")}</span>
                  <strong>{String(value)}</strong>
                </div>
              ))}
          </div>

          <div className="result-actions">
            <button type="button" className="secondary" disabled={!shareAllowed} onClick={copyShare}>
              {copied ? "LINK COPIED" : "COPY LIVE REPORT LINK"}
            </button>
            {!shareAllowed && (
              <span className="action-note">
                Share links are disabled for URLs containing query strings or fragments.
              </span>
            )}
          </div>

          <div className="findings">
            <div className="section-label">
              <span>FINDINGS</span>
              <strong>{findings.length}</strong>
            </div>

            {findings.length === 0 ? (
              <div className="clean">No findings in the current V0 rule set.</div>
            ) : (
              findings.map((finding, index) => (
                <article className="finding" key={finding.code + "-" + index}>
                  <div className="finding-meta">
                    <code>{finding.code || "FINDING"}</code>
                    <span className={"severity " + (finding.severity || "medium")}>
                      {finding.severity || "medium"}
                    </span>
                  </div>
                  <h2>{finding.message}</h2>
                  {finding.remediation && <p><b>Fix:</b> {finding.remediation}</p>}
                  {finding.source_url && (
                    <a href={finding.source_url} target="_blank" rel="noreferrer">
                      Official source ↗
                    </a>
                  )}
                </article>
              ))
            )}
          </div>

          <p className="disclaimer">{result.disclaimer}</p>
        </section>
      )}

      <footer>
        <span>KAVI Plugin Doctor</span>
        <span>Powered by KAVI Capability Compiler</span>
      </footer>
    </main>
  );
}
