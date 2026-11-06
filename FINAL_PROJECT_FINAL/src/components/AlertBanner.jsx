import "./AlertBanner.css";

// tone: "danger" | "warning" | "info"
function AlertBanner({ tone = "danger", icon, title, message, reasons }) {
  return (
    <div className={`alert-banner alert-${tone}`}>
      <div className="alert-icon">{icon}</div>

      <div className="alert-body">
        <h3>{title}</h3>

        {message && <p>{message}</p>}

        {reasons && reasons.length > 0 && (
          <ul>
            {reasons.map((reason, index) => (
              <li key={index}>{reason}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default AlertBanner;
