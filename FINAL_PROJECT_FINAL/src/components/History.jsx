import "./History.css";

function History({ history, setHistory }) {

  if (!history || history.length === 0) return null;

  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem("jobHistory");
  };

  return (
    <div className="history-card">

      <div className="history-header">

        <h2>🕒 Analysis History</h2>

        <button
          className="clear-btn"
          onClick={clearHistory}
        >
          Clear History
        </button>

      </div>

      {history.map((item, index) => {

        const risk =
          item.risk_score ??
          item.risk ??
          0;

        const confidence =
          item.ai_confidence ??
          0;

        return (

          <div
            key={index}
            className="history-item"
          >

            <div className="history-left">

              <span
                className={`status-badge ${
                  item.prediction === "FAKE JOB"
                    ? "fake"
                    : "legit"
                }`}
              >
                {item.prediction}
              </span>

              <div className="history-info">

                <p>

                  <strong>Risk Score</strong>

                </p>

                <div className="progress">

                  <div
                    className={`progress-fill ${
                      item.prediction === "FAKE JOB"
                        ? "red"
                        : "green"
                    }`}
                    style={{
                      width: `${risk}%`,
                    }}
                  ></div>

                </div>

                <span>{risk}%</span>

              </div>

              <div className="history-info">

                <p>

                  <strong>AI Confidence</strong>

                </p>

                <span>{confidence}%</span>

              </div>

            </div>

            <div className="history-right">

              <small>{item.time}</small>

            </div>

          </div>

        );

      })}

    </div>

  );

}

export default History;