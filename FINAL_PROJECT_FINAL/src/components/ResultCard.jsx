import { useMemo, useState } from "react";
import "./ResultCard.css";

const STEPS = {
  danger: [
    "Do not pay any registration, training or security fee.",
    "Do not share Aadhaar, PAN, bank or OTP details.",
    "Check the company on its official website and LinkedIn.",
    "Report the posting on the platform where you found it.",
  ],
  caution: [
    "Verify the recruiter on LinkedIn before replying.",
    "Apply only through the official company website.",
    "Never pay money to get a job or an interview.",
    "Ask for an official offer letter on company email.",
  ],
  safe: [
    "Apply through the official company website.",
    "Verify the recruiter on LinkedIn.",
    "Keep a copy of the job description.",
    "Attend interviews only through official channels.",
  ],
};

const TONE = {
  danger:  { icon: "🚨", title: "High risk — likely a fake job",  sub: "Several scam signs were found in this posting.", rec: "Do Not Apply" },
  caution: { icon: "⚠️", title: "Be careful — some concerns",     sub: "Nothing is certain, but check a few things first.", rec: "Verify First" },
  safe:    { icon: "✅", title: "Looks safe",                      sub: "No serious scam signs were found.", rec: "Safe to Apply" },
};

function ResultCard({ result, jobUrl }) {

  const isFake = result.prediction === "FAKE JOB";
  const confidence = Number(result.ai_confidence) || 0;

  // risk: smart analyzer first, otherwise derive from the ML confidence
  const risk = typeof result.gemini_analysis?.risk_score === "number"
    ? Math.round(result.gemini_analysis.risk_score)
    : Math.round(isFake ? confidence : 100 - confidence);

  const tone = isFake || risk >= 65 ? "danger" : risk >= 35 ? "caution" : "safe";
  const safety = Math.max(0, Math.min(100, 100 - risk));
  const t = TONE[tone];

  const [done, setDone] = useState({});
  const reportId = useMemo(() => `JS-${String(Date.now()).slice(-6)}`, []);

  const company = result.company_verification;
  const trust = typeof company?.trust_score === "number" ? company.trust_score : null;
  const verified = Boolean(company?.website || company?.linkedin);

  const checks = [
    { ok: true, label: "Job description analysed" },
    { ok: verified, label: verified ? "Company found online" : "Company not found online" },
    { ok: !result.fraud_signals?.fraud_reports_found, label: result.fraud_signals?.fraud_reports_found ? "Negative reports found" : "No scam reports found" },
  ];
  if (jobUrl?.trim()) {
    const closed = result.job_status?.status === "closed";
    checks.push({ ok: !closed, label: closed ? "Job link is closed" : "Job link checked" });
    if (result.consistency_check) {
      checks.push({ ok: !result.consistency_check.mismatch, label: result.consistency_check.mismatch ? "Company differs from link" : "Company matches link" });
    }
  }

  const indicators = result.indicators || [];
  const ring = { background: `conic-gradient(var(--rc) ${safety * 3.6}deg, rgba(255,255,255,.08) 0)` };

  return (
    <div className={`rc rc-${tone}`}>

      {/* ---------- top banner ---------- */}
      <div className="rc-top">
        <div className="rc-ring" style={ring}>
          <div><b>{safety}</b><small>safety</small></div>
        </div>

        <div className="rc-top-text">
          <span className="rc-eyebrow">JobShield AI Security Report</span>
          <h2>{t.icon} {t.title}</h2>
          <p>{t.sub}</p>
          <div className="rc-meta">
            <span>📅 {new Date().toLocaleDateString("en-GB")}</span>
            <span>🆔 {reportId}</span>
            <span className="rc-pill">{result.prediction}</span>
          </div>
        </div>

        <div className="rc-rec">
          <small>Recommendation</small>
          <b>{t.rec}</b>
        </div>
      </div>

      {/* ---------- stats ---------- */}
      <div className="rc-stats">
        <div className="rc-stat">
          <small>AI Confidence</small>
          <b>{confidence}%</b>
          <div className="rc-bar"><i style={{ width: `${confidence}%` }} /></div>
        </div>
        <div className="rc-stat">
          <small>Risk Score</small>
          <b>{risk}%</b>
          <div className="rc-bar"><i style={{ width: `${risk}%` }} /></div>
        </div>
        <div className="rc-stat">
          <small>Company Trust</small>
          <b>{trust === null ? "N/A" : `${trust}%`}</b>
          <div className="rc-bar"><i style={{ width: `${trust ?? 0}%` }} /></div>
        </div>
        <div className="rc-stat">
          <small>Red Flags</small>
          <b>{indicators.length}</b>
          <span>{indicators.length ? "found in the text" : "none found"}</span>
        </div>
      </div>

      {/* ---------- two columns ---------- */}
      <div className="rc-cols">

        <div className="rc-panel">
          <h3>📋 Suggested Next Steps</h3>
          <p className="rc-hint">Tap a step to tick it off.</p>
          <ul className="rc-steps">
            {STEPS[tone].map((s, i) => (
              <li key={i}>
                <button
                  type="button"
                  className={done[i] ? "done" : ""}
                  onClick={() => setDone((d) => ({ ...d, [i]: !d[i] }))}
                >
                  <span>{done[i] ? "✔" : ""}</span>
                  {s}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="rc-panel">
          <h3>🔎 What We Checked</h3>
          <ul className="rc-checks">
            {checks.map((c, i) => (
              <li key={i} className={c.ok ? "ok" : "bad"}>
                <span>{c.ok ? "✔" : "✖"}</span>{c.label}
              </li>
            ))}
          </ul>

          {result.recommendation && <p className="rc-note">{result.recommendation}</p>}
        </div>

      </div>

      {/* ---------- indicators ---------- */}
      <div className="rc-panel rc-ind">
        <h3>🚩 Suspicious Indicators</h3>
        <div className="rc-ind-grid">
          {indicators.length ? (
            indicators.map((item, i) => <div key={i} className="rc-ind-item">{item}</div>)
          ) : (
            <div className="rc-ind-item good">✅ No suspicious indicators detected.</div>
          )}
        </div>
      </div>

    </div>
  );
}

export default ResultCard;
