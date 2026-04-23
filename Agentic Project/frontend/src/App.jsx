import React, { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

const phases = ["story", "audio", "video"];

function artifactUrl(path) {
  if (!path) return null;
  const normalized = path.replace(/\\/g, "/");
  const marker = "/data/outputs/";
  const index = normalized.indexOf(marker);
  if (index === -1) return null;
  return `${API_BASE}/artifacts${normalized.slice(index + marker.length - 1)}`;
}

export default function App() {
  const [prompt, setPrompt] = useState("A young inventor finds a hidden garden inside an abandoned observatory.");
  const [project, setProject] = useState(null);
  const [editCommand, setEditCommand] = useState("Make scene darker");
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!project?.project_id) return undefined;
    const stream = new EventSource(`${API_BASE}/projects/${project.project_id}/events`);
    stream.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setEvents((current) => [payload, ...current].slice(0, 12));
        refreshProject(project.project_id);
      } catch (error) {
        console.error(error);
      }
    };
    return () => stream.close();
  }, [project?.project_id]);

  async function refreshProject(projectId = project?.project_id) {
    if (!projectId) return;
    const response = await fetch(`${API_BASE}/projects/${projectId}`);
    if (!response.ok) return;
    const data = await response.json();
    setProject(data);
  }

  async function createProject() {
    setLoading(true);
    const response = await fetch(`${API_BASE}/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const data = await response.json();
    setProject(data);
    setEvents([]);
    setLoading(false);
  }

  async function rerunPhase(phase) {
    if (!project) return;
    setLoading(true);
    await fetch(`${API_BASE}/projects/${project.project_id}/run-phase/${phase}`, { method: "POST" });
    await refreshProject();
    setLoading(false);
  }

  async function submitEdit() {
    if (!project) return;
    setLoading(true);
    await fetch(`${API_BASE}/projects/${project.project_id}/edit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: editCommand }),
    });
    await refreshProject();
    setLoading(false);
  }

  async function undo(versionId = null) {
    if (!project) return;
    setLoading(true);
    await fetch(`${API_BASE}/projects/${project.project_id}/undo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(versionId ? { version_id: versionId } : {}),
    });
    await refreshProject();
    setLoading(false);
  }

  const versionCards = useMemo(() => (project?.versions ?? []).slice().reverse(), [project?.versions]);
  const videoUrl = artifactUrl(project?.artifacts?.final_video);

  return (
    <main className="studio-shell">
      <section className="hero-panel">
        <p className="eyebrow">Agentic Shorts Studio</p>
        <h1>Prompt to polished micro-film, with edits and undo built in.</h1>
        <p className="lede">
          Local-first orchestration, cloud-ready providers, and a workflow tuned for a final project demo instead of a fragile lab prototype.
        </p>

        <div className="composer">
          <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />
          <button onClick={createProject} disabled={loading}>
            {loading ? "Working..." : "Generate film"}
          </button>
        </div>
      </section>

      <section className="dashboard-grid">
        <article className="panel">
          <div className="panel-head">
            <h2>Pipeline</h2>
            <span className={`status-chip status-${project?.status ?? "idle"}`}>{project?.status ?? "idle"}</span>
          </div>
          <div className="phase-list">
            {phases.map((phase) => (
              <div className="phase-card" key={phase}>
                <div>
                  <strong>{phase}</strong>
                  <p>{project?.current_phase === phase ? "Running now" : "Ready to rerun"}</p>
                </div>
                <button onClick={() => rerunPhase(phase)} disabled={!project || loading}>
                  Rerun
                </button>
              </div>
            ))}
          </div>

          <div className="events">
            <h3>Live events</h3>
            {(events.length ? events : [{ type: "status", status: "Awaiting run" }]).map((event, index) => (
              <div className="event-row" key={`${event.type}-${index}`}>
                <span>{event.type}</span>
                <code>{JSON.stringify(event)}</code>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-head">
            <h2>Edit Agent</h2>
            <span className="subtle">Targeted reruns</span>
          </div>
          <div className="edit-box">
            <input value={editCommand} onChange={(event) => setEditCommand(event.target.value)} placeholder="Make scene darker" />
            <button onClick={submitEdit} disabled={!project || loading}>
              Apply edit
            </button>
          </div>
          <button className="ghost-button" onClick={() => undo()} disabled={!project || loading}>
            Undo latest
          </button>

          <div className="versions">
            <h3>Version history</h3>
            {versionCards.map((version) => (
              <div className="version-card" key={version.version_id}>
                <div>
                  <strong>{version.version_id}</strong>
                  <p>{version.trigger}</p>
                </div>
                <button onClick={() => undo(version.version_id)} disabled={loading}>
                  Restore
                </button>
              </div>
            ))}
          </div>
        </article>

        <article className="panel wide">
          <div className="panel-head">
            <h2>Output</h2>
            <span className="subtle">{project?.story?.title ?? "No film yet"}</span>
          </div>
          {videoUrl ? (
            <video className="player" controls src={videoUrl} />
          ) : (
            <div className="empty-player">Your film preview appears here after the video phase finishes.</div>
          )}
          <div className="story-strip">
            {(project?.scenes ?? []).map((scene) => (
              <div className="scene-pill" key={scene.scene_id}>
                <strong>{scene.title}</strong>
                <span>{scene.duration_sec}s</span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </main>
  );
}
