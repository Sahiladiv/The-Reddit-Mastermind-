import { useState } from "react";
import { generateWeeksAndSave } from "../api/api";

export default function MultiWeekGenerator() {
  const [weeks, setWeeks] = useState<number>(1);
  const [loading, setLoading] = useState(false);
  const [files, setFiles] = useState<string[]>([]);

  const handleGenerate = async () => {
    setLoading(true);
    setFiles([]);

    try {
      const res = await generateWeeksAndSave({
        num_weeks: weeks,
        output_dir: "output_weeks",
        max_comments_per_thread: 6,
      });

      setFiles(res.data.files);
    } catch (err: any) {
      alert(err.message || "Error generating weeks");
    }

    setLoading(false);
  };

  return (
    <div className="card">
      <h2>Generate Multiple Weeks</h2>

      <label># of Weeks:</label>
      <input
        type="number"
        min={1}
        max={52}
        value={weeks}
        onChange={(e) => setWeeks(Number(e.target.value))}
      />

      <br />
      <br />

      <button onClick={handleGenerate} disabled={loading}>
        {loading ? "Processing..." : "Generate & Save"}
      </button>

      {files.length > 0 && (
        <div style={{ marginTop: "15px" }}>
          <h4>Saved Files:</h4>
          <ul>
            {files.map((path) => (
              <li key={path}>{path}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
