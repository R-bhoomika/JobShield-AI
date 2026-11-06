import { useEffect, useRef, useState } from "react";
import {
  FileText, Globe, Image as ImageIcon, Link2, ClipboardPaste, Upload,
  Rocket, Lightbulb, FileCheck2, ShieldCheck, Camera, Target, X,
} from "lucide-react";
import "./AnalyzeCard.css";

const MAX_MB = 8;

function isValidUrl(value) {
  try {
    const u = new URL(value.startsWith("http") ? value : `https://${value}`);
    return u.hostname.includes(".");
  } catch {
    return false;
  }
}

const TIPS = [
  { icon: FileCheck2, text: "Paste the complete job description." },
  { icon: Link2, text: "Use the official company job URL." },
  { icon: Camera, text: "Upload a screenshot if you don't have text to paste." },
  { icon: Target, text: "Providing more than one source improves accuracy." },
];

function AnalyzeCard({
  text, setText, jobUrl, setJobUrl, image, setImage,
  imagePreview, setImagePreview, analyzeJob, loading,
}) {

  const [dragging, setDragging] = useState(false);
  const [imgError, setImgError] = useState("");
  const fileRef = useRef(null);

  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const urlFilled = jobUrl.trim() !== "";
  const urlOk = !urlFilled || isValidUrl(jobUrl.trim());

  const sources = [
    { label: "Text", on: words > 0 },
    { label: "URL", on: urlFilled && urlOk },
    { label: "Screenshot", on: Boolean(image) },
  ];
  const count = sources.filter((s) => s.on).length;
  const meterText = ["Add at least one source", "Good", "Better", "Best accuracy"][count];

  const takeFile = (file) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) return setImgError("Please choose an image file (PNG, JPG, WEBP).");
    if (file.size > MAX_MB * 1024 * 1024) return setImgError(`Image is too large. Max ${MAX_MB} MB.`);
    setImgError("");
    setImage(file);
    setImagePreview(URL.createObjectURL(file));
  };

  const clearImage = () => {
    setImage(null);
    setImagePreview(null);
    setImgError("");
    if (fileRef.current) fileRef.current.value = "";
  };

  const pasteText = async () => {
    try {
      const t = await navigator.clipboard.readText();
      if (t) setText(t);
    } catch {
      /* clipboard blocked by the browser - ignore */
    }
  };

  // Ctrl+V an image anywhere on the page
  useEffect(() => {
    const onPaste = (e) => {
      const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith("image/"));
      if (item) takeFile(item.getAsFile());
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
    // eslint-disable-next-line
  }, []);

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    takeFile(e.dataTransfer.files?.[0]);
  };

  const canSubmit = !loading && count > 0 && urlOk;

  return (
    <div className="analyze-card az-card">

      <div className="az-header">
        <h2>Analyze <span>Job Posting</span></h2>
        <p>
          Paste a job description, add the job URL, and/or upload a screenshot —
          all in one step. We'll cross-check everything you give us.
        </p>
      </div>

      <div className="az-box">

        <div className="az-cols">

          {/* LEFT */}
          <div className="az-left">
            <div className="az-label">
              <span className="az-ico"><FileText size={15} /></span>
              <b>Job Description</b>
              <button type="button" className="az-paste" onClick={pasteText}>
                <ClipboardPaste size={13} /> Paste
              </button>
            </div>

            <textarea
              placeholder="Paste the complete job description here..."
              value={text}
              onChange={(e) => setText(e.target.value)}
            />

            <small className={`az-tip ${words > 0 && words < 15 ? "warn" : ""}`}>
              {words > 0 && words < 15
                ? "Add a little more text (at least 15 words)."
                : "Tip: the full posting gives the best result"}
            </small>
          </div>

          {/* RIGHT */}
          <div className="az-right">

            <div className="az-label">
              <span className="az-ico blue"><Globe size={15} /></span>
              <b>Job URL</b>
              <em>Optional</em>
            </div>

            <div className={`az-urlbox ${!urlOk ? "invalid" : ""}`}>
              <Link2 size={16} />
              <input
                type="text"
                placeholder="https://company.com/careers/job"
                value={jobUrl}
                onChange={(e) => setJobUrl(e.target.value)}
              />
            </div>
            {!urlOk && <small className="az-tip warn">That doesn't look like a valid link.</small>}

            <div className="az-label" style={{ marginTop: 18 }}>
              <span className="az-ico green"><ImageIcon size={15} /></span>
              <b>Job Screenshot</b>
              <em>Optional</em>
            </div>

            {!imagePreview ? (
              <label
                className={`az-drop ${dragging ? "drag" : ""}`}
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
              >
                <input ref={fileRef} type="file" accept="image/*" hidden onChange={(e) => takeFile(e.target.files?.[0])} />
                <span className="az-drop-ico"><Upload size={22} /></span>
                <b>Click to upload or drag &amp; drop</b>
                <small>PNG, JPG or WEBP · up to {MAX_MB} MB · or press Ctrl+V to paste</small>
              </label>
            ) : (
              <div className="az-preview">
                <img src={imagePreview} alt="Screenshot preview" />
                <div>
                  <b>{image?.name || "Pasted image"}</b>
                  <small>{image ? `${(image.size / 1024).toFixed(0)} KB` : ""}</small>
                </div>
                <button type="button" onClick={clearImage} aria-label="Remove screenshot"><X size={16} /></button>
              </div>
            )}
            {imgError && <small className="az-tip warn">{imgError}</small>}
          </div>

        </div>

        {/* BOTTOM BAR */}
        <div className="az-bar">
          <div>
            <div className="az-chips">
              {sources.map((s) => (
                <span key={s.label} className={`az-chip ${s.on ? "on" : ""}`}>
                  {s.on ? "✔" : "○"} {s.label}
                </span>
              ))}
            </div>
            <div className="az-meter">
              <span className="az-seg">
                {[1, 2, 3].map((n) => <i key={n} className={count >= n ? "on" : ""} />)}
              </span>
              <small>{meterText}</small>
            </div>
          </div>

          <button className="az-btn" onClick={analyzeJob} disabled={!canSubmit}>
            <Rocket size={16} /> {loading ? "Analyzing..." : "Analyze Job"}
          </button>
        </div>

      </div>

      {/* QUICK TIPS */}
      <div className="az-tips">
        <h3><Lightbulb size={16} /> Quick Tips</h3>
        <div className="az-tips-grid">
          {TIPS.map(({ icon: Icon, text }) => (
            <div key={text}>
              <span><Icon size={16} /></span>
              {text}
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}

export default AnalyzeCard;