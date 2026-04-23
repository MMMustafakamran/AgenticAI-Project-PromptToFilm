import React, { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

const phases = ["story", "audio", "video"];
const starterScenes = [
  { scene_id: "scene_1", title: "Discovery beat", mood: "curious", duration_sec: 12 },
  { scene_id: "scene_2", title: "Resolution beat", mood: "uplifting", duration_sec: 12 },
];
const starterEvents = [
  { type: "system", status: "ready", note: "Waiting for your first prompt." },
  { type: "tip", status: "guide", note: "Try a simple 2-scene story prompt to validate the full pipeline." },
];

function artifactUrl(path) {
  if (!path) return null;
  const normalized = path.replace(/\\/g, "/");
  const marker = "/data/outputs/";
  const index = normalized.indexOf(marker);
  if (index === -1) return null;
  return `${API_BASE}/artifacts${normalized.slice(index + marker.length - 1)}`;
}

function prettyStatus(status) {
  if (!status) return "Idle";
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export default function App() {
  const [prompt, setPrompt] = useState("A young inventor finds a hidden garden inside an abandoned observatory.");
  const [project, setProject] = useState(null);
  const [editCommand, setEditCommand] = useState("Make scene darker");
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uiError, setUiError] = useState("");

  useEffect(() => {
    if (!project?.project_id) return undefined;
    const stream = new EventSource(`${API_BASE}/projects/${project.project_id}/events`);
    stream.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setEvents((current) => [payload, ...current].slice(0, 10));
        refreshProject(project.project_id);
      } catch (error) {
        console.error(error);
        setUiError(`Could not read live event payload: ${error.message}`);
      }
    };
    stream.onerror = () => {
      setUiError("Live event stream disconnected. Refresh the page or rerun a phase.");
      stream.close();
    };
    return () => stream.close();
  }, [project?.project_id]);

  async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
      let message = `Request failed with status ${response.status}`;
      try {
        const payload = await response.json();
        message = payload.detail ?? payload.error ?? message;
      } catch {
        const text = await response.text();
        if (text) {
          message = text;
        }
      }
      throw new Error(message);
    }
    return response.json();
  }

  async function refreshProject(projectId = project?.project_id) {
    if (!projectId) return;
    try {
      const data = await requestJson(`${API_BASE}/projects/${projectId}`);
      setProject(data);
      setUiError("");
    } catch (error) {
      setUiError(error.message);
    }
  }

  async function createProject() {
    try {
      setLoading(true);
      setUiError("");
      const data = await requestJson(`${API_BASE}/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      setProject(data);
      setEvents([]);
    } catch (error) {
      setUiError(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function rerunPhase(phase) {
    if (!project) return;
    try {
      setLoading(true);
      setUiError("");
      await requestJson(`${API_BASE}/projects/${project.project_id}/run-phase/${phase}`, { method: "POST" });
      await refreshProject();
    } catch (error) {
      setUiError(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function submitEdit() {
    if (!project) return;
    try {
      setLoading(true);
      setUiError("");
      await requestJson(`${API_BASE}/projects/${project.project_id}/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: editCommand }),
      });
      await refreshProject();
    } catch (error) {
      setUiError(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function undo(versionId = null) {
    if (!project) return;
    try {
      setLoading(true);
      setUiError("");
      await requestJson(`${API_BASE}/projects/${project.project_id}/undo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(versionId ? { version_id: versionId } : {}),
      });
      await refreshProject();
    } catch (error) {
      setUiError(error.message);
    } finally {
      setLoading(false);
    }
  }

  const versionCards = useMemo(() => (project?.versions ?? []).slice().reverse(), [project?.versions]);
  const videoUrl = artifactUrl(project?.artifacts?.final_video);
  const sceneCount = project?.scenes?.length ?? 0;
  const duration = (project?.scenes ?? []).reduce((sum, scene) => sum + scene.duration_sec, 0);
  const activeEvents = events.length ? events : starterEvents;
  const visibleScenes = project?.scenes?.length ? project.scenes : starterScenes;
  const runtimeError = project?.last_error ?? "";
  const combinedError = uiError || runtimeError;

  return (
    <main className="shell">
      <section className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark" />
          <div>
            <p className="micro-label">Agentic AI Final Project</p>
            <h1 className="brand-title">Agentic Shorts Studio</h1>
          </div>
        </div>
        <div className="topbar-meta">
          <span className={`status-badge status-${project?.status ?? "idle"}`}>{prettyStatus(project?.status ?? "idle")}</span>
          <span className="muted-chip">{project?.current_version ?? "No version yet"}</span>
        </div>
      </section>

      <section className="hero">
        <div className="hero-copy">
          <p className="section-kicker">Prompt-to-film workspace</p>
          <h2 className="hero-title">A minimal control surface for story, voice, visuals, edits, and reversible runs.</h2>
          <p className="hero-text">
            Designed for demo day: clean enough to feel credible, structured enough to show the full agentic pipeline without visual noise.
          </p>

          <div className="metric-row">
            <article className="metric-card">
              <span className="metric-label">Scenes</span>
              <strong>{sceneCount || "02"}</strong>
            </article>
            <article className="metric-card">
              <span className="metric-label">Runtime</span>
              <strong>{duration ? `${duration}s` : "24s"}</strong>
            </article>
            <article className="metric-card">
              <span className="metric-label">Current phase</span>
              <strong>{project?.current_phase ?? "idle"}</strong>
            </article>
          </div>
        </div>

        <aside className="launch-panel">
          <div className="panel-header compact">
            <div>
              <p className="micro-label">Launch input</p>
              <h3>Create a film run</h3>
            </div>
            <span className="soft-pill">Local-first</span>
          </div>

          <textarea
            className="prompt-input"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Describe the short film you want to generate"
          />

          <div className="launch-actions">
            <button className="primary-button" onClick={createProject} disabled={loading}>
              {loading ? "Generating..." : "Generate film"}
            </button>
            <p className="helper-copy">Cloud providers are optional. The fallback pipeline still runs locally for demos.</p>
          </div>
        </aside>
      </section>

      {combinedError ? (
        <section className="error-banner">
          <div>
            <p className="micro-label">Pipeline error</p>
            <strong>Something failed during a request or phase run.</strong>
            <p>{combinedError}</p>
          </div>
        </section>
      ) : null}

      <section className="workspace">
        <article className="surface preview-surface">
          <div className="panel-header">
            <div>
              <p className="micro-label">Output preview</p>
              <h3>{project?.story?.title ?? "No film generated yet"}</h3>
            </div>
            <span className="soft-pill">{project?.project_id ?? "Project pending"}</span>
          </div>

          {videoUrl ? (
            <video className="player" controls src={videoUrl} />
          ) : (
            <div className="empty-player">
              <div>
                <strong>The preview canvas is ready.</strong>
                <p>Your generated film, subtitles, and scene snapshots will appear here after the video phase completes.</p>
              </div>
            </div>
          )}

          <div className="scene-grid">
            {visibleScenes.map((scene) => (
              <article className="scene-card" key={scene.scene_id}>
                <span className="scene-index">{scene.scene_id.replace("_", " ")}</span>
                <strong>{scene.title}</strong>
                <p>{scene.mood}</p>
                <span className="scene-time">{scene.duration_sec}s</span>
              </article>
            ))}
          </div>
        </article>

        <aside className="workspace-rail">
          <article className="surface dark-surface">
            <div className="panel-header">
              <div>
                <p className="micro-label">Pipeline</p>
                <h3>Phase controls</h3>
              </div>
            </div>
            <div className="phase-stack">
              {phases.map((phase) => (
                <div className="phase-tile" key={phase}>
                  <div>
                    <strong>{phase}</strong>
                    <p>{project?.current_phase === phase ? "Running now" : "Available for rerun"}</p>
                  </div>
                  <button className="secondary-button" onClick={() => rerunPhase(phase)} disabled={!project || loading}>
                    Rerun
                  </button>
                </div>
              ))}
            </div>
          </article>

          <article className="surface dark-surface">
            <div className="panel-header">
              <div>
                <p className="micro-label">Edit agent</p>
                <h3>Targeted revision</h3>
              </div>
              <span className="soft-pill">Undo ready</span>
            </div>

            <div className="edit-stack">
              <input
                className="inline-input"
                value={editCommand}
                onChange={(event) => setEditCommand(event.target.value)}
                placeholder="Make scene darker"
              />
              <div className="button-row">
                <button className="primary-button" onClick={submitEdit} disabled={!project || loading}>
                  Apply edit
                </button>
                <button className="ghost-button" onClick={() => undo()} disabled={!project || loading}>
                  Undo latest
                </button>
              </div>
            </div>

            <div className="version-list">
              {versionCards.length ? (
                versionCards.map((version) => (
                  <div className="version-item" key={version.version_id}>
                    <div>
                      <strong>{version.version_id}</strong>
                      <p>{version.trigger}</p>
                    </div>
                    <button className="text-button" onClick={() => undo(version.version_id)} disabled={loading}>
                      Restore
                    </button>
                  </div>
                ))
              ) : (
                <p className="empty-copy">Versions appear after the first successful phase run.</p>
              )}
            </div>
          </article>
        </aside>
      </section>

      <section className="bottom-grid">
        <article className="surface">
          <div className="panel-header">
            <div>
              <p className="micro-label">Activity</p>
              <h3>Live events</h3>
            </div>
          </div>
          <div className="event-stack">
            {activeEvents.map((event, index) => (
              <div className="event-item" key={`${event.type}-${index}`}>
                <span className="event-type">{event.type}</span>
                <code>{event.note ?? JSON.stringify(event)}</code>
              </div>
            ))}
          </div>
        </article>

        <article className="surface">
          <div className="panel-header">
            <div>
              <p className="micro-label">Artifacts</p>
              <h3>Generated outputs</h3>
            </div>
          </div>
          <div className="artifact-grid">
            <div className="artifact-card">
              <span>Story JSON</span>
              <strong>{project?.artifacts?.story_json ? "Ready" : "Pending"}</strong>
            </div>
            <div className="artifact-card">
              <span>Audio track</span>
              <strong>{project?.artifacts?.final_audio ? "Ready" : "Pending"}</strong>
            </div>
            <div className="artifact-card">
              <span>Subtitle file</span>
              <strong>{project?.artifacts?.subtitle_file ? "Ready" : "Pending"}</strong>
            </div>
            <div className="artifact-card">
              <span>Final MP4</span>
              <strong>{project?.artifacts?.final_video ? "Ready" : "Pending"}</strong>
            </div>
          </div>
        </article>
      </section>
    </main>
  );
}
