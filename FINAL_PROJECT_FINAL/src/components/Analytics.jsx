import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Legend, ReferenceLine, CartesianGrid,
} from "recharts";

import "./Analytics.css";

// risk score of one scan (smart analyzer first, ML confidence as fallback)
function riskOf(item) {
  const r = item.gemini_analysis?.risk_score;
  if (typeof r === "number") return Math.round(r);
  const c = Number(item.ai_confidence) || 0;
  return Math.round(item.prediction === "FAKE JOB" ? c : 100 - c);
}

const tip = {
  borderRadius: "12px",
  border: "none",
  boxShadow: "0 8px 20px rgba(0,0,0,.25)",
};

function Analytics({ history }) {

  if (!history || history.length === 0) return null;

  const fakeJobs = history.filter((i) => i.prediction === "FAKE JOB").length;
  const legitJobs = history.length - fakeJobs;

  const avgConfidence = (
    history.reduce((s, i) => s + (Number(i.ai_confidence) || 0), 0) / history.length
  ).toFixed(1);

  const latest = history[0]; // newest first
  const latestRisk = riskOf(latest);

  const pieData = [
    { name: "Fake", value: fakeJobs },
    { name: "Legitimate", value: legitJobs },
  ];

  // oldest -> newest, last 12 scans
  const barData = [...history].slice(0, 12).reverse().map((item, i) => ({
    name: `#${i + 1}`,
    risk: riskOf(item),
  }));

  const riskColor = (r) => (r >= 65 ? "#ef4444" : r >= 35 ? "#f59e0b" : "#22c55e");

  const recent = history.slice(0, 6);

  return (
    <div className="analytics-container">

      <div className="analytics-header">
        <div className="analytics-title">
          <h1>📊 Analytics Overview</h1>
          <p>AI Powered Fake Job Detection Insights</p>
        </div>
        <div className="analytics-update">
          <span>Last Scan</span>
          <h3>{latest.time || "Today"}</h3>
        </div>
      </div>

      <div className="analytics-stats-grid">
        <div className="stat-box total-card">
          <div className="stat-icon">📄</div>
          <h3>Total Jobs</h3>
          <h1>{history.length}</h1>
          <p>Jobs Analyzed</p>
        </div>
        <div className="stat-box fake-card">
          <div className="stat-icon">❌</div>
          <h3>Fake Jobs</h3>
          <h1>{fakeJobs}</h1>
          <p>Detected by AI</p>
        </div>
        <div className="stat-box legit-card">
          <div className="stat-icon">✅</div>
          <h3>Legitimate Jobs</h3>
          <h1>{legitJobs}</h1>
          <p>Verified Safe</p>
        </div>
        <div className="stat-box confidence-card">
          <div className="stat-icon">🤖</div>
          <h3>AI Confidence</h3>
          <h1>{avgConfidence}%</h1>
          <p>Average Accuracy</p>
        </div>
      </div>

      <div className="analytics-overview">

        <div className="analytics-card">
          <h3>Fake vs Legitimate Jobs</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                   innerRadius={70} outerRadius={100} paddingAngle={6} label animationDuration={1200}>
                <Cell fill="#ef4444" />
                <Cell fill="#22c55e" />
              </Pie>
              <Legend verticalAlign="bottom" height={36} />
              <Tooltip contentStyle={tip} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="analytics-card">
          <h3>Risk Score per Scan</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={barData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,.2)" />
              <XAxis dataKey="name" />
              <YAxis domain={[0, 100]} />
              <Tooltip contentStyle={tip} formatter={(v) => [`${v}%`, "Risk"]} />
              <ReferenceLine y={65} stroke="#ef4444" strokeDasharray="4 4" label={{ value: "Likely fake", fill: "#ef4444", fontSize: 11, position: "insideTopRight" }} />
              <ReferenceLine y={35} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: "Suspicious", fill: "#f59e0b", fontSize: 11, position: "insideTopRight" }} />
              <Bar dataKey="risk" radius={[10, 10, 0, 0]} animationDuration={1200}>
                {barData.map((d, i) => <Cell key={i} fill={riskColor(d.risk)} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="analytics-card">
          <h3>Latest Scan</h3>
          <br />
          <div className="latest-item">
            <span>Prediction</span>
            <h4>{latest.prediction}</h4>
          </div>
          <div className="latest-item">
            <span>AI Confidence</span>
            <h4>{latest.ai_confidence}%</h4>
          </div>
          <div className="latest-item">
            <span>Risk Score</span>
            <h4 style={{ color: riskColor(latestRisk) }}>{latestRisk}%</h4>
          </div>
        </div>

      </div>

      {/* Recent scans */}
      <div className="analytics-card an2-recent">
        <h3>Recent Scans</h3>
        <div className="an2-table-wrap">
          <table className="an2-table">
            <thead>
              <tr><th>Company</th><th>Result</th><th>Risk</th><th>Confidence</th><th>Time</th></tr>
            </thead>
            <tbody>
              {recent.map((item, i) => {
                const r = riskOf(item);
                return (
                  <tr key={i}>
                    <td>{item.company_verification?.company || "—"}</td>
                    <td>
                      <span className={`an2-tag ${item.prediction === "FAKE JOB" ? "bad" : "ok"}`}>
                        {item.prediction === "FAKE JOB" ? "Fake" : "Legit"}
                      </span>
                    </td>
                    <td style={{ color: riskColor(r), fontWeight: 700 }}>{r}%</td>
                    <td>{item.ai_confidence}%</td>
                    <td>{item.time || ""}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}

export default Analytics;
