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
    score: "", // optional: use for historical/labeled entries
  });

  const [status, setStatus] = useState("");
  const [pred, setPred] = useState(null);
  const [entries, setEntries] = useState([]);

  function setField(k, v) {
    setForm((p) => ({ ...p, [k]: v }));
  }

  async function refresh() {
    setStatus("");
    const uid = toNumberOrNull(form.user_id);
    if (!uid) return;
    const res = await fetch(`${API}/entries?user_id=${uid}`);
    if (!res.ok) {
      const text = await res.text();
      setStatus(`Fetch entries failed: ${res.status} ${text}`);
      return;
    }
    setEntries(await res.json());
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function buildPayload(includeScore) {
    const payload = {
      user_id: toNumberOrNull(form.user_id),
      test_id: toNumberOrNull(form.test_id),
      confidence: toNumberOrNull(form.confidence),
      stress: toNumberOrNull(form.stress),
      sleep: toNumberOrNull(form.sleep),
      hours_studied: toNumberOrNull(form.hours_studied),
      feeling_text: form.feeling_text || null,
    };
    if (includeScore) payload.score = toNumberOrNull(form.score);
    return payload;
  }

  async function saveEntry(e) {
    e.preventDefault();
    setPred(null);
    setStatus("Saving entry...");

    const payload = buildPayload(true);
    if (!payload.user_id || !payload.test_id) {
      setStatus("user_id and test_id are required.");
      return;
    }

    const res = await fetch(`${API}/entries`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const text = await res.text();
      setStatus(`Save failed: ${res.status} ${text}`);
      return;
    }

    const out = await res.json();
    setStatus(`Saved entry id=${out.id}${out.score != null ? " (labeled)" : ""}`);
    await refresh();
  }

  async function predict(e) {
    e.preventDefault();
    setPred(null);
    setStatus("Checking training status...");

    const payload = buildPayload(false);
    if (!payload.user_id || !payload.test_id) {
      setStatus("user_id and test_id are required.");
      return;
    }

    // 1) Check whether we can/should train
    const statusRes = await fetch(
      `${API}/train/status?user_id=${payload.user_id}&test_id=${payload.test_id}`
    );
    if (!statusRes.ok) {
      const text = await statusRes.text();
      setStatus(`Train status failed: ${statusRes.status} ${text}`);
      return;
    }

    const s = await statusRes.json();

    // 2) If model doesn't exist but we can train, train now
    if (!s.model_exists || s.needs_retrain) {
      if (!s.can_train) {
        const need = s.min_required - s.labeled_count;
        setStatus(
          `Model not trained yet. Add ${need} more labeled entries (with score) to train.`
        );
        return;
      }

      setStatus(`Training model (${s.labeled_count} labeled rows)...`);
      const trainRes = await fetch(`${API}/train`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: payload.user_id, test_id: payload.test_id }),
      });

      if (!trainRes.ok) {
        const text = await trainRes.text();
        setStatus(`Train failed: ${trainRes.status} ${text}`);
        return;
      }

      const tr = await trainRes.json();
      setStatus(`Trained! train_mae=${tr.train_mae.toFixed(2)}. Predicting...`);
    } else {
      setStatus("Model exists. Predicting...");
    }

    // 3) Predict (and backend stores prediction as an entry)
    const predRes = await fetch(`${API}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!predRes.ok) {
      const text = await predRes.text();
      setStatus(`Predict failed: ${predRes.status} ${text}`);
      return;
    }

    const out = await predRes.json();
    setPred(out.predicted_score);
    setStatus(`Predicted ${out.predicted_score.toFixed(2)} (saved as entry_id=${out.entry_id})`);
    await refresh();
  }

  return (
    <main style={{ maxWidth: 900, margin: "40px auto", fontFamily: "system-ui" }}>
      <h1>Test Predictor</h1>
      <p style={{ color: "#666" }}>
        Save entries anytime. Add labeled entries (with <code>score</code>) to train. Predict trains automatically once you have enough labeled data.
      </p>

      <form style={{ border: "1px solid #ddd", borderRadius: 12, padding: 16 }}>
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

          <label>
            Score (optional, for training)
            <input value={form.score} onChange={(e) => setField("score", e.target.value)} style={{ width: "100%", padding: 8 }} placeholder="Use this for past tests" />
          </label>
        </div>

        <label style={{ display: "block", marginTop: 12 }}>
          How do you feel? (text)
          <textarea value={form.feeling_text} onChange={(e) => setField("feeling_text", e.target.value)} style={{ width: "100%", padding: 8, height: 90 }} />
        </label>

        <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 12 }}>
          <button onClick={saveEntry} style={{ padding: "10px 14px", cursor: "pointer" }}>
            Save Entry
          </button>
          <button onClick={predict} style={{ padding: "10px 14px", cursor: "pointer" }}>
            Predict
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
            <div key={e.id} style={{ border: "1px solid #eee", borderRadius: 12, padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <b>#{e.id}</b>
                <span style={{ color: "#666", fontSize: 12 }}>{e.created_at}</span>
              </div>
              <div style={{ marginTop: 6 }}>
                test_id={e.test_id} | predicted={e.predicted_score ?? "—"} | actual={e.score ?? "—"}
              </div>
              {e.feeling_text ? <div style={{ marginTop: 6 }}><i>{e.feeling_text}</i></div> : null}
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
