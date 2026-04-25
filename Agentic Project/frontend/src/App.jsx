import React, { useEffect, useMemo, useState, useRef } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

const phases = ["story", "audio", "video"];
const starterScenes = [
  { scene_id: "scene_1", title: "Discovery beat", mood: "curious", duration_sec: 12 },
  { scene_id: "scene_2", title: "Resolution beat", mood: "uplifting", duration_sec: 12 },
];
const starterEvents = [
  { type: "system", status: "ready", note: "Waiting for your first prompt." },
];

function artifactUrl(path) {
  if (!path) return null;
  const normalized = path.replace(/\\/g, "/");
  const marker = "/data/outputs/";
  const index = normalized.indexOf(marker);
  if (index === -1) return null;
  return `${API_BASE}/artifacts${normalized.slice(index + marker.length - 1)}`;
}

function getEventStyle(event) {
  if (event.type === "error" || event.status === "failed") return "error";
  if (event.status === "completed" || event.status === "success") return "success";
  if (event.type === "tip" || event.type === "warning") return "warning";
  return "info";
}

function getAgentName(type) {
  const map = {
    "system": "System",
    "tip": "Guide",
    "story_agent": "Story Agent",
    "audio_agent": "Audio Agent",
    "video_agent": "Video Agent",
    "error": "Error",
  };
  return map[type] || type || "System";
}

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [project, setProject] = useState(null);
  const [editCommand, setEditCommand] = useState("");
  const [events, setEvents] = useState([]);
  
  // Granular Loading States
  const [isGenerating, setIsGenerating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isUndoing, setIsUndoing] = useState(false);
  const [runningPhase, setRunningPhase] = useState(null);
  
  const [uiError, setUiError] = useState("");
  
  const feedEndRef = useRef(null);

  useEffect(() => {
    if (feedEndRef.current) {
      feedEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [events]);

  useEffect(() => {
    if (!project?.project_id) return undefined;
    const stream = new EventSource(`${API_BASE}/projects/${project.project_id}/events`);
    stream.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setEvents((current) => [...current, payload]);
        refreshProject(project.project_id);
      } catch (error) {
        console.error(error);
      }
    };
    stream.onerror = () => {
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
        if (text) message = text;
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
      console.error(error);
    }
  }

  async function createProject() {
    if (!prompt.trim()) return;
    try {
      setIsGenerating(true);
      setUiError("");
      setEvents([{ type: "system", status: "running", note: "Initializing agents and pipeline..." }]);
      const data = await requestJson(`${API_BASE}/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      setProject(data);
    } catch (error) {
      setUiError(error.message);
      setIsGenerating(false);
    }
  }

  async function rerunPhase(phase) {
    if (!project) return;
    try {
      setRunningPhase(phase);
      setUiError("");
      await requestJson(`${API_BASE}/projects/${project.project_id}/run-phase/${phase}`, { method: "POST" });
      await refreshProject();
    } catch (error) {
      setUiError(error.message);
    } finally {
      setRunningPhase(null);
    }
  }

  async function submitEdit() {
    if (!project || !editCommand.trim()) return;
    try {
      setIsEditing(true);
      setUiError("");
      await requestJson(`${API_BASE}/projects/${project.project_id}/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: editCommand }),
      });
      setEditCommand("");
      await refreshProject();
    } catch (error) {
      setUiError(error.message);
    } finally {
      setIsEditing(false);
    }
  }

  async function undo(versionId = null) {
    if (!project) return;
    try {
      setIsUndoing(true);
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
      setIsUndoing(false);
    }
  }

  const versionCards = useMemo(() => (project?.versions ?? []).slice().reverse(), [project?.versions]);
  const videoUrl = artifactUrl(project?.artifacts?.final_video);
  const activeEvents = events.length ? events : starterEvents;
  const visibleScenes = project?.scenes?.length ? project.scenes : starterScenes;
  const runtimeError = project?.last_error ?? "";
  const combinedError = uiError || runtimeError;
  const isAnyLoading = isGenerating || isEditing || isUndoing || runningPhase !== null;
  const projectStatus = project?.status ?? "idle";

  // Determine which cinematic view to show
  const viewState = useMemo(() => {
    if (isGenerating || projectStatus === "running" || runningPhase !== null) return "running";
    if (projectStatus === "completed" || (projectStatus === "idle" && project?.artifacts?.final_video)) return "completed";
    return "idle";
  }, [isGenerating, projectStatus, runningPhase, project]);

  useEffect(() => {
    if (projectStatus === "completed" || projectStatus === "failed") {
        setIsGenerating(false);
    }
  }, [projectStatus]);


  // Helper Renders
  const renderTerminal = () => (
    <article className="glass-panel agent-terminal">
      <div className="terminal-header">
        <div>
          <p className="micro-label">Activity</p>
          <h3>Agent Output Logs</h3>
        </div>
        {viewState === "running" && <span className="loader loader-lg"></span>}
      </div>
      <div className="terminal-feed">
        {activeEvents.map((ev, i) => (
          <div className={`event-row ${getEventStyle(ev)}`} key={i}>
            <div className="event-agent">[{getAgentName(ev.type)}]</div>
            <div className="event-msg">{ev.note || JSON.stringify(ev)}</div>
          </div>
        ))}
        <div ref={feedEndRef} />
      </div>
    </article>
  );

  return (
    <main className="shell">
      <section className="topbar glass-panel">
        <div className="brand-lockup">
          <span className="brand-mark" />
          <div>
            <h1 className="brand-title">Agentic Shorts Studio</h1>
          </div>
        </div>
        <div>
          <span className={`status-badge status-${projectStatus}`}>
            {projectStatus.charAt(0).toUpperCase() + projectStatus.slice(1)}
          </span>
        </div>
      </section>

      {combinedError && (
        <section className="error-banner">
          <div>
            <strong>Pipeline Error</strong>
            <span>{combinedError}</span>
          </div>
        </section>
      )}

      {/* VIEW: IDLE (Prompt Entry) */}
      {viewState === "idle" && (
        <section className="hero view-container">
          <div className="hero-content">
            <h2 className="hero-title">Create AI shorts effortlessly.</h2>
            <p className="hero-text">
              Provide a prompt and watch specialized agents write the story, generate audio, and render scenes in real-time. Full control with targeted edits and reversible history.
            </p>
          </div>

          <aside className="launch-panel glass-panel">
            <div className="panel-header">
              <p className="micro-label">New Project</p>
              <h3>Launch Film Run</h3>
            </div>
            <textarea
              className="prompt-input"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. A cyberpunk detective exploring neon-lit alleyways..."
              disabled={isGenerating}
            />
            <div className="launch-actions">
              <button className="btn btn-primary" onClick={createProject} disabled={!prompt.trim() || isGenerating}>
                Generate Film
              </button>
            </div>
          </aside>
        </section>
      )}

      {/* VIEW: RUNNING (Cinematic Progress) */}
      {viewState === "running" && (
        <section className="progress-view view-container">
          <div className="progress-header">
            <h2>Agents are working...</h2>
            <p>Phase: {project?.current_phase ? project.current_phase.charAt(0).toUpperCase() + project.current_phase.slice(1) : "Initializing pipeline"}</p>
          </div>
          {renderTerminal()}
        </section>
      )}

      {/* VIEW: COMPLETED (Workspace / Preview) */}
      {viewState === "completed" && (
        <section className="workspace view-container">
          <div>
            <article className="glass-panel preview-surface">
              <div className="panel-header">
                <p className="micro-label">Preview</p>
                <h3>{project?.story?.title ?? "Awaiting Title..."}</h3>
              </div>

              {videoUrl ? (
                <video className="player" controls src={videoUrl} autoPlay loop />
              ) : (
                <div className="empty-player">
                  <div>Video file missing or failed to generate.</div>
                </div>
              )}

              <div className="scene-grid">
                {visibleScenes.map((scene) => (
                  <article className="scene-card" key={scene.scene_id}>
                    <span className="scene-index">{scene.scene_id.replace("_", " ")}</span>
                    <strong>{scene.title}</strong>
                    <p style={{margin: '4px 0 0', color: 'var(--text-soft)', fontSize: '0.9rem'}}>{scene.mood}</p>
                    <span className="scene-time">{scene.duration_sec}s</span>
                  </article>
                ))}
              </div>
            </article>
            
            <div style={{marginTop: '24px'}}>
              {renderTerminal()}
            </div>
          </div>

          <aside className="workspace-rail">
            <div className="glass-panel control-panel">
              <div className="panel-header">
                <p className="micro-label">Revision Agent</p>
                <h3>Targeted Edit</h3>
              </div>
              <input
                className="edit-input"
                value={editCommand}
                onChange={(e) => setEditCommand(e.target.value)}
                placeholder="e.g. Change mood to suspenseful"
                disabled={isAnyLoading || !project}
              />
              <div className="button-group">
                <button className="btn btn-primary" onClick={submitEdit} disabled={isAnyLoading || !project || !editCommand.trim()}>
                  {isEditing ? <><span className="loader"></span></> : "Apply"}
                </button>
                <button className="btn btn-secondary" onClick={() => undo()} disabled={isAnyLoading || !project || versionCards.length <= 1}>
                  {isUndoing ? <span className="loader"></span> : "Undo"}
                </button>
              </div>
            </div>

            <div className="glass-panel control-panel">
              <div className="panel-header">
                <p className="micro-label">Pipeline Control</p>
                <h3>Rerun Phase</h3>
              </div>
              <div style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
                {phases.map((phase) => (
                  <button 
                    key={phase} 
                    className="btn btn-secondary" 
                    onClick={() => rerunPhase(phase)} 
                    disabled={isAnyLoading || !project}
                    style={{justifyContent: 'flex-start'}}
                  >
                    {runningPhase === phase ? <span className="loader"></span> : null}
                    {phase.charAt(0).toUpperCase() + phase.slice(1)} Phase
                  </button>
                ))}
              </div>
            </div>
            
            <article className="glass-panel control-panel">
              <div className="panel-header">
                <p className="micro-label">Artifacts</p>
                <h3>Files</h3>
              </div>
              <div className="artifact-grid">
                <div className={`artifact-item ${project?.artifacts?.story_json ? 'ready' : ''}`}>
                  <span>Story JSON</span>
                  <strong>{project?.artifacts?.story_json ? "Ready" : "Pending"}</strong>
                </div>
                <div className={`artifact-item ${project?.artifacts?.final_audio ? 'ready' : ''}`}>
                  <span>Audio Track</span>
                  <strong>{project?.artifacts?.final_audio ? "Ready" : "Pending"}</strong>
                </div>
                <div className={`artifact-item ${project?.artifacts?.subtitle_file ? 'ready' : ''}`}>
                  <span>Subtitles</span>
                  <strong>{project?.artifacts?.subtitle_file ? "Ready" : "Pending"}</strong>
                </div>
                <div className={`artifact-item ${project?.artifacts?.final_video ? 'ready' : ''}`}>
                  <span>Final MP4</span>
                  <strong>{project?.artifacts?.final_video ? "Ready" : "Pending"}</strong>
                </div>
              </div>
            </article>
            
          </aside>
        </section>
      )}
    </main>
  );
}
