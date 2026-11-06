import { useEffect, useState } from "react";
import "./LoadingCard.css";

const STEPS = [
  { icon: "📄", title: "Reading Job Description",   desc: "Reading and cleaning the job text" },
  { icon: "🔍", title: "Detecting Scam Patterns",   desc: "Looking for fees, pressure and scam wording" },
  { icon: "🏢", title: "Verifying Company Details", desc: "Checking website, LinkedIn and location" },
  { icon: "🧠", title: "AI Security Analysis",      desc: "Generative AI is writing the explanation" },
  { icon: "📊", title: "Generating Final Report",   desc: "Putting everything into your report" },
];

// how long each of the first 4 steps stays active (ms).
// The last step stays active until the real result arrives.
const STEP_TIME = [1200, 1800, 2600, 3200];

const TIPS = [
  "Real companies never ask for a registration or security fee.",
  "Be careful if the recruiter only uses WhatsApp or Telegram.",
  "Check that the company website matches the email domain.",
  "\"Earn daily from home\" promises are a common scam sign.",
  "Search the company name with the word \"scam\" before you apply.",
];

function LoadingCard() {

  const [step, setStep] = useState(0);
  const [progress, setProgress] = useState(2);
  const [seconds, setSeconds] = useState(0);
  const [tip, setTip] = useState(0);

  // move through the steps (last step waits for the real result)
  useEffect(() => {
    if (step >= STEPS.length - 1) return;
    const t = setTimeout(() => setStep((s) => s + 1), STEP_TIME[step]);
    return () => clearTimeout(t);
  }, [step]);

  // smooth progress: glides towards the current step's target, never hits 100%
  useEffect(() => {
    const target = Math.min(95, (step + 1) * 19);
    const t = setInterval(() => {
      setProgress((p) => (p < target ? Math.min(target, p + Math.max(0.4, (target - p) * 0.06)) : p));
    }, 120);
    return () => clearInterval(t);
  }, [step]);

  // timer + rotating tips
  useEffect(() => {
    const a = setInterval(() => setSeconds((s) => s + 1), 1000);
    const b = setInterval(() => setTip((i) => (i + 1) % TIPS.length), 4500);
    return () => { clearInterval(a); clearInterval(b); };
  }, []);

  return (
    <div className="ld-card" role="status" aria-live="polite">

      <div className="ld-glow ld-glow-1" />
      <div className="ld-glow ld-glow-2" />

      {/* radar / shield */}
      <div className="ld-radar">
        <span className="ld-ring r1" />
        <span className="ld-ring r2" />
        <span className="ld-ring r3" />
        <span className="ld-sweep" />
        <div className="ld-shield">🛡️</div>
      </div>

      <h2 className="ld-title">
        JobShield <span>AI</span>
      </h2>

      <p className="ld-sub" key={step}>
        {STEPS[step].desc}
        <span className="ld-dots"><i>.</i><i>.</i><i>.</i></span>
      </p>

      {/* progress */}
      <div className="ld-progress">
        <div className="ld-track">
          <div className="ld-fill" style={{ width: `${progress}%` }} />
        </div>
        <b>{Math.round(progress)}%</b>
      </div>

      {/* steps timeline */}
      <ol className="ld-steps">
        {STEPS.map((s, i) => {
          const state = i < step ? "done" : i === step ? "active" : "todo";
          return (
            <li className={`ld-step ${state}`} key={s.title}>
              <span className="ld-dot">
                {state === "done" ? "✓" : state === "active" ? <em className="ld-mini-spin" /> : i + 1}
              </span>
              <span className="ld-step-emoji">{s.icon}</span>
              <span className="ld-step-text">{s.title}</span>
              <span className="ld-step-status">
                {state === "done" ? "Done" : state === "active" ? "Working" : "Waiting"}
              </span>
            </li>
          );
        })}
      </ol>

      {/* footer */}
      <div className="ld-foot">
        <div className="ld-tip" key={tip}>
          <span>💡</span> {TIPS[tip]}
        </div>
        <div className="ld-time">⏱ {seconds}s</div>
      </div>

    </div>
  );
}

export default LoadingCard;
