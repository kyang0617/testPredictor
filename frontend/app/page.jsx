"use client";

import { useEffect, useState} from "react";
const API_BASE = "/api"

function toNumberOrNull(v) {
  if (v === "" || v === null || v === undefined) {
    return null;
  }

  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export default function Page() {
  const [form, setForm] = useState({
    user_id: "1",
    test_id: "1",
    score: "",
    confidence: "",
    stress: "",
    sleep: "",
    hours_studied: "",
    feeling_text: "",
  });

  const [status, setStatus] = useState("");
  const [entries, setEntries] = useState([]);
  const [loadingEntries, setLoadingEntries] = useState(false);

  const userIdNum = toNumberOrNull(form.user_id);

  async function fetchEntries() {
    if (!userIdNum) return;
    setLoadingEntries(true);
    setStatus("");
    try {
      const res = await fetch(`${API_BASE}/entries?user_id=${userIdNum}`);
      if (!res.ok) throw new Error(`GET /entries failed: ${res.status}`);

      const data = await res.json();
      setEntries(data);

    } catch(e) {
      setStatus(String(e.message || e));
    } finally {
      setLoadingEntries(false);
    }
  }


  useEffect(() => {
    fetchEntries();
  }, []);

  function updateField(key, value) {
    setForm((prev) => ({...prev, [key]: value}));
  }

  async function onSubmit(e) {
    e.preventDefault();
    setStatus("submitting...")

    const payload = {
      user_id: toNumberOrNull(form.user_id),
      test_id: toNumberOrNull(form.test_id),
      score: toNumberOrNull(form.score),
      confidence: toNumberOrNull(form.confidence),
      stress: toNumberOrNull(form.stress),
      sleep: toNumberOrNull(form.sleep),
      hours_studied: toNumberOrNull(form.hours_studied),
      feeling_text: form.feeling_text || null,
    }


    if (!payload.user_id || !payload.test_id) {
      setStatus("user_id and test_id are required");
      return;

    }

    try {
      const res = await fetch(`${API_BASE}/entries`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`POST /entries failed: ${res.status} ${text}`);
      }

      const created = await res.json();

      setStatus(`Saved entry id=${created.id}`);
      await fetchEntries();

    } catch (e) {
      setStatus(String(e.message || e));
    }
  }
  return (
    <main style={{ maxWidth: 860, margin: "40px auto", fontFamily: "system-ui" }}>
      <h1 style={{ marginBottom: 8 }}>Test Predictor – Data Entry</h1>
      <p style={{ marginTop: 0, color: "#666" }}>
        Submits to <code>{API_BASE}/entries</code> and reads from <code>{API_BASE}/entries</code>.
      </p>

      <form onSubmit={onSubmit} style={{ border: "1px solid #ddd", borderRadius: 12, padding: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <label>
            User ID (required)
            <input
              value={form.user_id}
              onChange={(e) => updateField("user_id", e.target.value)}
              style={{ width: "100%", padding: 8 }}
            />
          </label>

          <label>
            Test ID (required)
            <input
              value={form.test_id}
              onChange={(e) => updateField("test_id", e.target.value)}
              style={{ width: "100%", padding: 8 }}
            />
          </label>

          <label>
            Score
            <input
              value={form.score}
              onChange={(e) => updateField("score", e.target.value)}
              placeholder="e.g. 87"
              style={{ width: "100%", padding: 8 }}
            />
          </label>

          <label>
            Hours studied
            <input
              value={form.hours_studied}
              onChange={(e) => updateField("hours_studied", e.target.value)}
              placeholder="e.g. 6"
              style={{ width: "100%", padding: 8 }}
            />
          </label>

          <label>
            Confidence (1–7)
            <input
              value={form.confidence}
              onChange={(e) => updateField("confidence", e.target.value)}
              placeholder="e.g. 5"
              style={{ width: "100%", padding: 8 }}
            />
          </label>

          <label>
            Stress (1–7)
            <input
              value={form.stress}
              onChange={(e) => updateField("stress", e.target.value)}
              placeholder="e.g. 4"
              style={{ width: "100%", padding: 8 }}
            />
          </label>

          <label>
            Sleep (1–7)
            <input
              value={form.sleep}
              onChange={(e) => updateField("sleep", e.target.value)}
              placeholder="e.g. 6"
              style={{ width: "100%", padding: 8 }}
            />
          </label>
        </div>

        <label style={{ display: "block", marginTop: 12 }}>
          How do you feel? (optional text)
          <textarea
            value={form.feeling_text}
            onChange={(e) => updateField("feeling_text", e.target.value)}
            style={{ width: "100%", padding: 8, height: 90 }}
            placeholder="e.g. I feel okay but nervous about the time limit..."
          />
        </label>

        <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 12 }}>
          <button type="submit" style={{ padding: "10px 14px", cursor: "pointer" }}>
            Submit
          </button>

          <button
            type="button"
            onClick={fetchEntries}
            style={{ padding: "10px 14px", cursor: "pointer" }}
            disabled={!userIdNum || loadingEntries}
          >
            Refresh entries
          </button>

          <span style={{ color: status.includes("failed") ? "crimson" : "#333" }}>{status}</span>
        </div>
      </form>

      <h2 style={{ marginTop: 24 }}>Recent Entries (user_id={form.user_id || "?"})</h2>

      {loadingEntries ? (
        <p>Loading…</p>
      ) : entries.length === 0 ? (
        <p style={{ color: "#666" }}>No entries yet.</p>
      ) : (
        <div style={{ display: "grid", gap: 10 }}>
          {entries.map((e) => (
            <div key={e.id} style={{ border: "1px solid #eee", borderRadius: 12, padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <div>
                  <b>Entry #{e.id}</b> — test_id={e.test_id}
                </div>
                <div style={{ color: "#666", fontSize: 12 }}>{e.created_at}</div>
              </div>

              <div style={{ marginTop: 6, color: "#333" }}>
                score={String(e.score ?? "—")}, hours={String(e.hours_studied ?? "—")}, conf=
                {String(e.confidence ?? "—")}, stress={String(e.stress ?? "—")}, sleep=
                {String(e.sleep ?? "—")}
              </div>

              {e.feeling_text ? (
                <div style={{ marginTop: 6, color: "#444" }}>
                  <i>{e.feeling_text}</i>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
