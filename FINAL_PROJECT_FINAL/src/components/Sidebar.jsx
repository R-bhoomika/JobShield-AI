import { useCallback, useEffect, useState } from "react";
import {
  Home,
  Search,
  ShieldCheck,
  Bot,
  BarChart3,
  Lock,
  Lightbulb,
  Shield,
} from "lucide-react";

import "./Sidebar.css";

// Sections of the page, in the same order as they appear on screen.
// "needsResult" sections only exist after a job has been analyzed.
const ITEMS = [
  { id: "home",         label: "Dashboard",    short: "Home",    icon: Home },
  { id: "analyze",      label: "Analyze",      short: "Analyze", icon: Search },
  { id: "verification", label: "Verification", short: "Verify",  icon: ShieldCheck, needsResult: true },
  { id: "ai-analysis",  label: "AI Analysis",  short: "AI",      icon: Bot,         needsResult: true },
  { id: "analytics",    label: "Analytics",    short: "Stats",   icon: BarChart3 },
];

function Sidebar() {

  const [active, setActive] = useState("home");
  const [ready, setReady] = useState({});

  const scrollToSection = (id) => {
    document.getElementById(id)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };

  // Works out (1) which section is on screen and (2) which sections exist.
  const update = useCallback(() => {
    const exists = {};
    let current = "home";

    ITEMS.forEach((item) => {
      const el = document.getElementById(item.id);
      exists[item.id] = Boolean(el);

      if (el && el.getBoundingClientRect().top <= window.innerHeight * 0.35) {
        current = item.id;
      }
    });

    // at the very bottom of the page -> highlight the last section
    const atBottom =
      window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 6;

    if (atBottom && window.scrollY > 0) {
      const last = [...ITEMS].reverse().find((item) => exists[item.id]);
      if (last) current = last.id;
    }

    setActive(current);
    setReady((prev) =>
      JSON.stringify(prev) === JSON.stringify(exists) ? prev : exists
    );
  }, []);

  useEffect(() => {
    let frame = 0;
    const schedule = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(update);
    };

    update();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);

    // sections appear / disappear when a result is loaded
    const observer = new MutationObserver(schedule);
    observer.observe(document.body, { childList: true, subtree: true });

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      observer.disconnect();
    };
  }, [update]);

  const handleClick = (item) => {
    // locked section -> take the user to the place where they can unlock it
    scrollToSection(ready[item.id] === false ? "analyze" : item.id);
  };

  return (

    <aside className="sidebar">

      {/* ---------- Logo ---------- */}

      <button className="sidebar-logo" onClick={() => scrollToSection("home")}>
        <span className="sidebar-logo-icon">
          <Shield size={24} strokeWidth={2.4} />
        </span>

        <span className="sidebar-logo-text">
          <b>JobShield</b>
          <small>Fake job detector</small>
        </span>
      </button>

      {/* ---------- Menu ---------- */}

      <nav className="sidebar-menu" aria-label="Main navigation">

        <span className="sidebar-label">Menu</span>

        {ITEMS.map((item) => {
          const Icon = item.icon;
          const locked = item.needsResult && ready[item.id] === false;
          const isActive = active === item.id && !locked;

          return (
            <button
              key={item.id}
              className={`sidebar-item ${isActive ? "active" : ""} ${locked ? "locked" : ""}`}
              onClick={() => handleClick(item)}
              title={locked ? "Analyze a job to unlock this" : item.label}
              aria-current={isActive ? "page" : undefined}
            >
              <span className="sidebar-item-icon">
                <Icon size={19} />
              </span>

              <span className="sidebar-item-text">
                <span className="full">{item.label}</span>
                <span className="short">{item.short}</span>
              </span>

              {locked && <Lock size={14} className="sidebar-lock" />}
            </button>
          );
        })}

      </nav>

      {/* ---------- Footer ---------- */}

      <div className="sidebar-footer">

        <div className="sidebar-tip">
          <span className="sidebar-tip-icon"><Lightbulb size={16} /></span>
          <p>Real employers never ask you to pay a fee to get a job.</p>
        </div>

        <div className="sidebar-version">JobShield AI v1.0</div>

      </div>

    </aside>

  );

}

export default Sidebar;
