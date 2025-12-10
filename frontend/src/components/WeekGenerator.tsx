import { useState } from "react";
import { generateWeek, CalendarEntry } from "../api/api";
import JsonViewer from "./JsonViewer";

export default function WeekGenerator() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CalendarEntry[] | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setResult(null);

    try {
      const res = await generateWeek({
        max_comments_per_thread: 6,
      });
      setResult(res.data);
    } catch (err: any) {
      alert(err.message || "Error generating week");
    }

    setLoading(false);
  };

  return (
    <div className="card">
      <h2>Generate One Week</h2>

      <button onClick={handleGenerate} disabled={loading}>
        {loading ? "Generating..." : "Generate Week"}
      </button>

      {result && <JsonViewer data={result} />}
    </div>
  );
}
