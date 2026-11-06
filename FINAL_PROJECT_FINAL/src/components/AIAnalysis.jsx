import { useState } from "react";
import "./AIAnalysis.css";

function flagIcon(text = "") {
  const t = text.toLowerCase();
  if (/fee|deposit|payment|\bpay\b|money|₹|\brs\b/.test(t)) return "💸";
  if (/whatsapp|telegram|messag/.test(t)) return "💬";
  if (/email|gmail|yahoo|domain/.test(t)) return "✉️";
  if (/link|url|bit\.ly/.test(t)) return "🔗";
  if (/aadhaar|pan|bank|otp|password|sensitive/.test(t)) return "🔐";
  if (/interview/.test(t)) return "🎤";
  if (/urgent|hurry|limited|immediate/.test(t)) return "⏰";
  return "⚠️";
}

function AIAnalysis({ analysis }) {

  const [more, setMore] = useState(false);

  if (!analysis) return null;

  // unavailable state
  if (analysis.unavailable || typeof analysis.risk_score !== "number") {
    return (
      <div className="aia">
        <div className="aia-unavail">
          <span>🤖</span>
          <h2>AI Analysis unavailable</h2>
          <p>{analysis.explanation || "The analysis could not be completed. The result above is still valid."}</p>
        </div>
      </div>
    );
  }

  const risk = Math.max(0, Math.min(100, Math.round(analysis.risk_score)));
  const verdict = analysis.verdict || "";
  const tone = /fake/i.test(verdict) ? "danger" : /suspicious/i.test(verdict) ? "caution" : "safe";

  const flags = analysis.red_flags || [];
  const positives = analysis.positives || [];
  const breakdown = analysis.score_breakdown || [];
  const comps = analysis.components || {};
  const web = analysis.web_evidence;

  const explanation = analysis.explanation || "";
  const sentences = explanation.split(/(?<=[.!?])\s+/);
  const key = sentences[0] || explanation;
  const rest = sentences.slice(1).join(" ");

  const by = analysis.explanation_by ? `✨ ${analysis.explanation_by}` : "by JobShield AI";

  // half-circle gauge: 0..100 -> 0..180deg
  const angle = (risk / 100) * 180;

  return (
    <div className={`aia aia-${tone}`}>

      <div className="aia-head">
        <div>
          <h1>🤖 AI Analysis</h1>
          <p>Scam rules, our ML model and web evidence — explained in plain words.</p>
        </div>
        <span className="aia-badge">{verdict}</span>
      </div>

      {/* gauge + key finding */}
      <div className="aia-top">

        <div className="aia-gauge-card">
          <div className="aia-gauge">
            <div className="aia-gauge-fill" style={{ transform: `rotate(${angle}deg)` }} />
            <div className="aia-gauge-mask" />
            <div className="aia-gauge-num"><b>{risk}</b><small>/ 100 risk</small></div>
          </div>
          <div className="aia-scale"><span>Safe</span><span>Risky</span></div>
        </div>

        <div className="aia-key">
          <div className="aia-key-top">
            <h3>Key finding</h3>
            <span className="aia-by">{by}</span>
          </div>
          <p>{key}</p>
          {rest && (
            <>
              {more && <p className="aia-rest">{rest}</p>}
              <button className="aia-more" onClick={() => setMore((m) => !m)}>
                {more ? "Show less ▲" : "Read more ▼"}
              </button>
            </>
          )}
        </div>

      </div>

      {/* red flags */}
      <div className="aia-panel">
        <h2>🚩 Red Flags {flags.length > 0 && <em>{flags.length}</em>}</h2>

        {flags.length ? (
          <div className="aia-flags">
            {flags.map((f, i) => (
              <div className="aia-flag" key={i}>
                <span className="aia-num">{i + 1}</span>
                <span className="aia-ico">{flagIcon(f)}</span>
                <p>{f}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="aia-good">✅ No suspicious indicators detected.</div>
        )}

        {positives.length > 0 && (
          <div className="aia-pos">
            <h4>👍 Good signs</h4>
            <ul>{positives.map((p, i) => <li key={i}>✔ {p}</li>)}</ul>
          </div>
        )}
      </div>

      {/* how the score was calculated */}
      <div className="aia-panel">
        <h2>🧮 How the Score Was Calculated</h2>

        {(comps.rules != null || comps.ml != null) && (
          <div className="aia-comps">
            {comps.rules != null && (
              <div><small>Scam rules</small><b>{Math.round(comps.rules)}</b></div>
            )}
            {comps.ml != null && (
              <div><small>ML model</small><b>{Math.round(comps.ml)}</b></div>
            )}
            <div><small>Final score</small><b>{risk}</b></div>
          </div>
        )}

        {breakdown.length > 0 && (
          <ul className="aia-break">
            {breakdown.map((b, i) => {
              const label = typeof b === "string" ? b : b.label || b.name || "";
              const pts = typeof b === "object" ? b.points ?? b.score : null;
              return (
                <li key={i}>
                  <span>{label}</span>
                  {pts != null && <b>{pts > 0 ? `+${pts}` : pts}</b>}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* web evidence */}
      {web && (web.summary || web.sources?.length > 0) && (
        <div className="aia-panel">
          <h2>🌐 Web Evidence</h2>
          {web.summary && <p className="aia-web">{web.summary}</p>}

          {web.sources?.length > 0 && (
            <div className="aia-sources">
              {web.sources.map((s, i) => (
                <a key={i} href={s.url} target="_blank" rel="noreferrer">
                  <b>{s.title || s.url}</b>
                  <small>{(s.url || "").replace(/^https?:\/\/(www\.)?/, "").split("/")[0]}</small>
                </a>
              ))}
            </div>
          )}
        </div>
      )}

    </div>
  );
}

export default AIAnalysis;
