import "./CompanyCard.css";

const searchUrl = (q) => `https://www.google.com/search?q=${encodeURIComponent(q)}`;

function CompanyCard({ result }) {

  if (!result) return null;

  const c = result.company_verification || {};
  const name = c.company || "Company not identified";
  const hasName = Boolean(c.company) && !/not available|unknown|not identified/i.test(c.company);

  const website = c.website || "";
  const linkedin = c.linkedin || "";
  const location = c.location || "";
  const fraud = result.fraud_signals;

  const reported = Boolean(fraud?.checked && fraud.fraud_reports_found);
  const impersonation = Boolean(fraud?.checked && fraud.impersonation_risk);
  const found = Boolean(website || linkedin);

  // four statuses
  let status = "unverified";
  if (reported) status = "risk";
  else if (website && linkedin) status = "verified";
  else if (found) status = "partial";

  const STATUS = {
    verified:   { label: "Verified",       text: "Website and LinkedIn page were both found." },
    partial:    { label: "Partly verified", text: "Only one official source was found." },
    unverified: { label: "Not verified",   text: "No official website or LinkedIn page was found." },
    risk:       { label: "Warning",        text: "Negative reports were found about this company." },
  }[status];

  const trust = typeof c.trust_score === "number" ? c.trust_score : null;
  const ring = {
    background: `conic-gradient(var(--cv) ${(trust ?? 0) * 3.6}deg, rgba(255,255,255,.08) 0)`,
  };

  const checks = [
    { ok: Boolean(website),  label: "Official website found" },
    { ok: Boolean(linkedin), label: "LinkedIn page found" },
    { ok: Boolean(location), label: "Location identified" },
    { ok: !reported,         label: "No scam reports found" },
  ];

  return (
    <div className={`cv cv-${status}`}>

      <div className="cv-head">
        <div>
          <h2>🏢 Company Verification</h2>
          <p>Is this company real, and does it have an official online presence?</p>
        </div>
        <span className="cv-status">{STATUS.label}</span>
      </div>

      {reported && (
        <div className="cv-alert danger">
          🚩 {fraud.reasons?.[0] || "This company has negative online feedback."}
        </div>
      )}
      {!reported && impersonation && (
        <div className="cv-alert warn">
          ⚠️ Pages pretending to be this company were reported. Use only the official website below.
        </div>
      )}

      <div className="cv-body">

        {/* profile */}
        <div className="cv-profile">
          <div className="cv-avatar">{hasName ? name.trim()[0].toUpperCase() : "?"}</div>
          <div>
            <h3>{name}</h3>
            <span>📍 {location || "Location unavailable"}</span>
            <small>{STATUS.text}</small>
          </div>
        </div>

        {/* trust ring */}
        <div className="cv-trust">
          <div className="cv-ring" style={ring}>
            <div><b>{trust === null ? "N/A" : `${trust}%`}</b></div>
          </div>
          <small>Trust score</small>
        </div>

        {/* checklist */}
        <ul className="cv-checks">
          {checks.map((k) => (
            <li key={k.label} className={k.ok ? "ok" : "bad"}>
              <span>{k.ok ? "✔" : "✖"}</span>{k.label}
            </li>
          ))}
        </ul>

      </div>

      {/* links */}
      <div className="cv-links">

        <div className="cv-link">
          <span>🌐 Official Website</span>
          {website ? (
            <a href={website} target="_blank" rel="noreferrer">{website.replace(/^https?:\/\//, "")}</a>
          ) : (
            <>
              <em>Not found</em>
              {hasName && <a className="cv-search" href={searchUrl(`${name} official website`)} target="_blank" rel="noreferrer">Search it ↗</a>}
            </>
          )}
        </div>

        <div className="cv-link">
          <span>💼 LinkedIn</span>
          {linkedin ? (
            <a href={linkedin} target="_blank" rel="noreferrer">{linkedin.replace(/^https?:\/\/(www\.)?/, "")}</a>
          ) : (
            <>
              <em>Not found</em>
              {hasName && <a className="cv-search" href={searchUrl(`${name} LinkedIn company page`)} target="_blank" rel="noreferrer">Search it ↗</a>}
            </>
          )}
        </div>

      </div>

      {result.company_ai && result.company_ai !== "Temporarily Disabled" && (
        <p className="cv-ai">🤖 {result.company_ai}</p>
      )}

    </div>
  );
}

export default CompanyCard;
