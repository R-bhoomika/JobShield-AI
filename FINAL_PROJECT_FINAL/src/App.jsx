import { useState, useEffect } from "react";
import axios from "axios";

import Sidebar from "./components/Sidebar";
import AnalyzeCard from "./components/AnalyzeCard";
import ResultCard from "./components/ResultCard";
import AIAnalysis from "./components/AIAnalysis";
import CompanyCard from "./components/CompanyCard";
import Analytics from "./components/Analytics";
import LoadingCard from "./components/LoadingCard";
import Dashboard from "./components/Dashboard/Dashboard";
import AlertBanner from "./components/AlertBanner";

import "./App.css";

const API_BASE = "http://127.0.0.1:8000";

function App() {

  const [text, setText] = useState("");
  const [jobUrl, setJobUrl] = useState("");
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);

  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("jobHistory");

    if (saved) {
      setHistory(JSON.parse(saved));
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(
      "jobHistory",
      JSON.stringify(history)
    );
  }, [history]);

  const analyzeJob = async () => {

    // Validation
    if (text.trim() === "" && jobUrl.trim() === "" && !image) {
      alert("Please enter a job description, a job URL, or upload a screenshot.");
      return;
    }

    if (text.trim() !== "") {
      const words = text.trim().split(/\s+/);

      if (words.length < 15) {
        alert("Please paste a complete job description.");
        return;
      }
    }

    setLoading(true);
    setResult(null);

    const startTime = Date.now();

    try {

      // ==========================
      // ALL-IN-ONE ANALYSIS
      // Sends JD text, job URL, and/or screenshot together in a single
      // request so nothing needs to be analyzed sequentially.
      // ==========================

      const formData = new FormData();
      formData.append("text", text);
      formData.append("job_url", jobUrl);

      if (image) {
        formData.append("image", image);
      }

      const response = await axios.post(
        `${API_BASE}/analyze`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        }
      );

      if (response.data?.error) {

        // Feature: a closed/unavailable job link is shown immediately as
        // a clear "not available" banner, right at the start of the
        // results — not as a generic browser alert popup, and without
        // waiting on (or running) the rest of the analysis pipeline.
        if (response.data?.job_status?.status === "closed") {

          setResult(response.data);

          setTimeout(() => {

            document
              .getElementById("verification")
              ?.scrollIntoView({
                behavior: "smooth",
                block: "start",
              });

          }, 300);

          return;
        }

        alert(
          response.data.error +
          (response.data.ocr_error
            ? "\n\nImage reading problem: " + response.data.ocr_error
            : "")
        );
        return;
      }

      setResult(response.data);

      setHistory((prev) => [
        {
          ...response.data,
          time: new Date().toLocaleString(),
        },
        ...prev,
      ]);

      // Scroll to results
      setTimeout(() => {

        document
          .getElementById("verification")
          ?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });

      }, 300);

    } catch (error) {

      console.error(error);

      if (error.response?.data?.error) {

        alert(error.response.data.error);

      } else {

        alert("Unable to analyze the job.");

      }

    } finally {

      const elapsed = Date.now() - startTime;

      const minimumLoading = 1200;

      if (elapsed < minimumLoading) {

        await new Promise((resolve) =>
          setTimeout(resolve, minimumLoading - elapsed)
        );

      }

      setLoading(false);

    }

  };

  return (
    <>
      <Sidebar />

      <div className="main-content">

        {/* Dashboard */}

        <section id="home">
          <Dashboard />
        </section>

        {/* Analyze */}

        <section id="analyze">

          <AnalyzeCard
            text={text}
            setText={setText}
            jobUrl={jobUrl}
            setJobUrl={setJobUrl}
            image={image}
            setImage={setImage}
            imagePreview={imagePreview}
            setImagePreview={setImagePreview}
            analyzeJob={analyzeJob}
            loading={loading}
          />

        </section>

        {loading && <LoadingCard />}

        {result && (
          <>

            {/* Verification */}

            <section id="verification">

              {/* Feature: immediate warning banner for a likely-fake posting */}
              {result.fake_warning?.flagged && (
                <AlertBanner
                  tone="danger"
                  icon="🚨"
                  title={result.fake_warning.headline}
                  reasons={result.fake_warning.reasons}
                />
              )}

              {/* Feature: job availability notice */}
              {result.job_status?.status === "closed" && (
                <AlertBanner
                  tone="warning"
                  icon="⏳"
                  title="Job is no longer available"
                  message={result.job_status.reason}
                />
              )}

              {/* Feature: JD vs URL company mismatch */}
              {result.consistency_check?.mismatch && (
                <AlertBanner
                  tone="warning"
                  icon="🔀"
                  title="Company Mismatch Detected"
                  message={result.consistency_check.message}
                />
              )}

              {result.prediction && (
                <>
                  <ResultCard
                    result={result}
                    jobUrl={jobUrl}
                  />

                  <CompanyCard
                    result={result}
                  />
                </>
              )}

            </section>

            {/* AI Analysis */}

            {result.gemini_analysis && (
              <section id="ai-analysis">

                <AIAnalysis
                  analysis={result.gemini_analysis}
                />

              </section>
            )}

          </>
        )}

        {/* Analytics */}

        <section id="analytics">

          <Analytics
            history={history}
          />

        </section>

      </div>

    </>
  );
}

export default App;
