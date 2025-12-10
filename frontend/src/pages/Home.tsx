import React, { useState } from "react";
import "./Home.css";

export default function Home() {
  const [weekResult, setWeekResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const generateWeek = async () => {
    setLoading(true);
    const res = await fetch("https://the-reddit-mastermind.onrender.com/generate-week", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const data = await res.json();
    setWeekResult(data);
    setLoading(false);
  };

  return (
    <div className="page">
      <h1 className="title">The Reddit Mastermind </h1>

      <div className="card">
        <h2>Generate</h2>
        <button className="generate-btn" onClick={generateWeek} disabled={loading}>
          {loading ? "Generating..." : "Generate Posts and Comments"}
        </button>
      </div>

      {weekResult && (
        <div className="output-container">
          <pre className="json-output">
            {JSON.stringify(weekResult, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
