import "./Dashboard.css";

const FEATURES = [
  { icon: "🧠", title: "Smart Scam Detection", text: "Machine learning plus scam-pattern rules read every line of the posting." },
  { icon: "🏢", title: "Company Verification", text: "Checks the official website, LinkedIn page and location of the company." },
  { icon: "🔗", title: "Job Link Check", text: "Finds closed, copied or mismatched job links before you apply." },
  { icon: "✨", title: "Generative AI Explanation", text: "A clear, plain-language reason for every score, backed by web evidence." },
];

function Dashboard() {

  const goToAnalyze = () => {
    document.getElementById("analyze")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="db">

      <div className="db-hero">

        <div className="db-copy">
          <span className="db-badge">🛡️ AI-powered job safety</span>

          <h1>Spot fake jobs <span>before</span> they spot you.</h1>

          <p>
            JobShield AI checks a job posting with machine learning, company
            verification, link checks and generative AI — and tells you in
            seconds whether it is safe to apply.
          </p>

          <div className="db-actions">
            <button className="db-btn" onClick={goToAnalyze}>Start Analysis →</button>
            <span className="db-note">Free · No sign-up</span>
          </div>
        </div>

        {/* sample report */}
        <div className="db-sample" aria-hidden="true">
          <div className="db-sample-top">
            <b>Sample report</b>
            <span>Likely Fake</span>
          </div>

          <div className="db-sample-score">
            <div className="db-ring"><b>82</b><small>risk</small></div>
            <ul>
              <li>⚠ Asks for a registration fee</li>
              <li>⚠ Only WhatsApp contact</li>
              <li>⚠ Unrealistic daily income</li>
            </ul>
          </div>

          <div className="db-sample-bar"><i /></div>
          <small>Verdict: Do not apply</small>
        </div>

      </div>

      <div className="db-features">
        {FEATURES.map((f) => (
          <div className="db-feature" key={f.title}>
            <span>{f.icon}</span>
            <h3>{f.title}</h3>
            <p>{f.text}</p>
          </div>
        ))}
      </div>

    </div>
  );
}

export default Dashboard;
