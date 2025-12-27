"use client";

import { useEffect, useState } from "react";

const API = "http://localhost:8000";

function toNumberOrNull(v) {
  if (v === "" || v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export default function Page() {
  const [form, setForm] = useState({
    user_id: "1",
    test_id: "1",
    confidence: "",
    stress: "",
    sleep: "",
    hours_studied: "",
    feeling_text: "",
  });

  const [pred, setPred] = useState(null);
  const [status, setStatus] = useState("");
  const [entries, setEntries] = useState([]);

  async function refresh() {
    setStatus("");
    const uid = toNumberOrNull(form.user_id);
    if (!uid) return;
    const res = await fetch(`${API}/entries?user_id=${uid}`);
    const data = await res.json();
    setEntries(data);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function setField(k, v) {
    setForm((p) => ({ ...p, [k]: v }));
  }

  async function predictAndSave(e) {
    e.preventDefault();
    setStatus("Predicting...");
    setPred(null);

    const payload = {
      user_id: toNumberOrNull(form.user_id),
      test_id: toNumberOrNull(form.test_id),
      confidence: toNumberOrNull(form.confidence),
      stress: toNumberOrNull(form.stress),
      sleep: toNumberOrNull(form.sleep),
      hours_studied: toNumberOrNull(form.hours_studied),
      feeling_text: form.feeling_text || null,
    };

    if (!payload.user_id || !payload.test_id) {
      setStatus("user_id and test_id are required.");
      return;
    }

    const res = await fetch(`${API}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const text = await res.text();
      setStatus(`Predict failed: ${res.status} ${text}`);
      return;
    }

    const out = await res.json();
    setPred(out.predicted_score);
    setStatus(`Saved prediction as entry_id=${out.entry_id}`);
    await refresh();
  }

  async function labelEntry(entryId, scoreVal) {
    const score = toNumberOrNull(scoreVal);
    if (score === null) return;

    setStatus(`Labeling entry ${entryId}...`);
    const res = await fetch(`${API}/entries/${entryId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ score }),
    });

    if (!res.ok) {
      const text = await res.text();
      setStatus(`Label failed: ${res.status} ${text}`);
      return;
    }

    setStatus(`Labeled entry ${entryId} with score=${score}`);
    await refresh();
  }

  return (
    <main style={{ maxWidth: 900, margin: "40px auto", fontFamily: "system-ui" }}>
      <h1>Test Predictor (MVP)</h1>
      <p style={{ color: "#666" }}>
        Submit pre-test info → backend predicts + stores entry → later you label actual score.
      </p>

      <form onSubmit={predictAndSave} style={{ border: "1px solid #ddd", borderRadius: 12, padding: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <label>
            User ID
            <input value={form.user_id} onChange={(e) => setField("user_id", e.target.value)} style={{ width: "100%", padding: 8 }} />
          </label>

          <label>
            Test/Class ID
            <input value={form.test_id} onChange={(e) => setField("test_id", e.target.value)} style={{ width: "100%", padding: 8 }} />
          </label>

          <label>
            Hours studied
            <input value={form.hours_studied} onChange={(e) => setField("hours_studied", e.target.value)} style={{ width: "100%", padding: 8 }} />
          </label>

          <label>
            Confidence (1–7)
            <input value={form.confidence} onChange={(e) => setField("confidence", e.target.value)} style={{ width: "100%", padding: 8 }} />
          </label>

          <label>
            Stress (1–7)
            <input value={form.stress} onChange={(e) => setField("stress", e.target.value)} style={{ width: "100%", padding: 8 }} />
          </label>

          <label>
            Sleep (1–7)
            <input value={form.sleep} onChange={(e) => setField("sleep", e.target.value)} style={{ width: "100%", padding: 8 }} />
          </label>
        </div>

        <label style={{ display: "block", marginTop: 12 }}>
          How do you feel? (text)
          <textarea value={form.feeling_text} onChange={(e) => setField("feeling_text", e.target.value)} style={{ width: "100%", padding: 8, height: 90 }} />
        </label>

        <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 12 }}>
          <button type="submit" style={{ padding: "10px 14px", cursor: "pointer" }}>
            Predict + Save
          </button>
          <button type="button" onClick={refresh} style={{ padding: "10px 14px", cursor: "pointer" }}>
            Refresh
          </button>
          <span>{status}</span>
        </div>

        {pred !== null && (
          <p style={{ marginTop: 12 }}>
            <b>Predicted score:</b> {pred.toFixed(2)}
          </p>
        )}
      </form>

      <h2 style={{ marginTop: 24 }}>Recent Entries</h2>
      {entries.length === 0 ? (
        <p style={{ color: "#666" }}>No entries yet.</p>
      ) : (
        <div style={{ display: "grid", gap: 10 }}>
          {entries.map((e) => (
            <EntryCard key={e.id} entry={e} onLabel={labelEntry} />
          ))}
        </div>
      )}
    </main>
  );
}

function EntryCard({ entry, onLabel }) {
  const [score, setScore] = useState("");

  return (
    <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div>
          <b>#{entry.id}</b> test_id={entry.test_id}
        </div>
        <div style={{ color: "#666", fontSize: 12 }}>{entry.created_at}</div>
      </div>

      <div style={{ marginTop: 6 }}>
        predicted={entry.predicted_score ?? "—"} | actual={entry.score ?? "—"} | hours={entry.hours_studied ?? "—"} | conf={entry.confidence ?? "—"} | stress={entry.stress ?? "—"} | sleep={entry.sleep ?? "—"}
      </div>

      {entry.feeling_text ? <div style={{ marginTop: 6, color: "#444" }}><i>{entry.feeling_text}</i></div> : null}

      <div style={{ display: "flex", gap: 8, marginTop: 10, alignItems: "center" }}>
        <input
          placeholder="Actual score"
          value={score}
          onChange={(e) => setScore(e.target.value)}
          style={{ padding: 8, width: 140 }}
        />
        <button onClick={() => onLabel(entry.id, score)} style={{ padding: "8px 12px", cursor: "pointer" }}>
          Label
        </button>
      </div>
    </div>
  );
}
