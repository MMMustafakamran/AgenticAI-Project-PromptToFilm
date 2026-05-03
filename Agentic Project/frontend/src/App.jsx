import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  Play, Video, Music, FileText, RefreshCw, Download, 
  History, Undo2, Send, Wand2, CheckCircle2, CircleDashed,
  Sparkles, Layers, TerminalSquare, FileJson, MessageSquare,
  Braces, Volume2, ImagePlay, Activity
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

const PHASES = [
  { id: 'story', title: 'Phase 1: Story & Script', icon: FileText, member: 'Member 1' },
  { id: 'audio', title: 'Phase 2: Audio & TTS', icon: Music, member: 'Member 2' },
  { id: 'video', title: 'Phase 3: Video Compositing', icon: Video, member: 'Member 3' }
];

function artifactUrl(path) {
  if (!path) return null;
  const normalized = path.replace(/\\/g, "/");
  const marker = "/data/outputs/";
  const index = normalized.indexOf(marker);
  if (index === -1) return null;
  return `${API_BASE}/artifacts${normalized.slice(index + marker.length - 1)}`;
}

export default function App() {
  const [appState, setAppState] = useState('idle'); // 'idle' | 'generating' | 'completed' | 'failed'
  const [mainPrompt, setMainPrompt] = useState('');
  const [numScenes, setNumScenes] = useState(2);
  const [editPrompt, setEditPrompt] = useState('');
  
  const [project, setProject] = useState(null);
  const [events, setEvents] = useState([]);
  const [uiError, setUiError] = useState('');
  
  // Progress tracking
  const [progress, setProgress] = useState({ story: 0, audio: 0, video: 0, edit: 0 });
  const [activePhase, setActivePhase] = useState(null);
  
  const videoRef = useRef(null);

  // Derive phase outputs from project state to mimic the inspiration UI
  const phaseOutputs = useMemo(() => {
    if (!project) return { story: null, audio: null, video: null };
    
    let storyOutput = null;
    if (project.artifacts?.story_json) {
      storyOutput = {
        icon: Braces,
        title: "story_schema.json",
        data: `{\n  "title": "${project.story?.title || 'Unknown'}",\n  "scenes": ${project.scenes?.length || 0},\n  "characters": ${project.characters?.length || 0}\n}`
      };
    }
    
    let audioOutput = null;
    if (project.artifacts?.timing_manifest_json) {
      audioOutput = {
        icon: Volume2,
        title: "timing_manifest.json",
        data: `Tracks: ${project.audio?.timing_manifest?.length || 0}\nProvider: ${project.audio?.provider || 'Unknown'}\nTotal Audio Ready`
      };
    }
    
    let videoOutput = null;
    if (project.artifacts?.final_video) {
      videoOutput = {
        icon: ImagePlay,
        title: "render_pipeline.log",
        data: `[${project.video?.image_provider || 'Generator'}] Rendered ${project.scenes?.length || 0} scenes\n[MoviePy] Composited with audio\n[FFmpeg] Final video ready`
      };
    }
    
    return { story: storyOutput, audio: audioOutput, video: videoOutput };
  }, [project]);

  const versions = useMemo(() => {
    return (project?.versions || []).slice().reverse().map(v => ({
      id: v.version_id,
      timestamp: v.created_at ? new Date(v.created_at).toLocaleTimeString() : new Date().toLocaleTimeString(),
      trigger: v.trigger,
      videoUrl: artifactUrl(v.artifact_paths?.find(p => p.endsWith('.mp4')))
    }));
  }, [project]);

  const currentVersionId = project?.current_version;
  const currentVersion = versions.find(v => v.id === currentVersionId);
  const videoUrl = artifactUrl(project?.artifacts?.final_video);

  useEffect(() => {
    if (!project?.project_id) return undefined;
    const stream = new EventSource(`${API_BASE}/projects/${project.project_id}/events`);
    
    stream.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setEvents((current) => [...current, payload]);
        
        if (payload.type === "phase") {
          if (payload.status === "started") {
            setActivePhase(payload.phase);
            setProgress(p => ({ ...p, [payload.phase]: 5 }));
          } else if (payload.status === "completed") {
            setProgress(p => ({ ...p, [payload.phase]: 100 }));
            if (activePhase === payload.phase) setActivePhase(null);
          } else if (payload.status === "failed") {
            setActivePhase(null);
          }
        } else if (payload.type === "progress") {
          setProgress(p => ({ ...p, [payload.phase]: Math.max(p[payload.phase], payload.progress) }));
        } else if (payload.type === 'edit') {
          if (payload.status === 'completed') {
            setProgress(p => ({ ...p, edit: 100 }));
            setActivePhase(null);
            setAppState('completed');
            refreshProject(project.project_id);
          } else if (payload.status === 'failed') {
            setActivePhase(null);
            setAppState('failed');
            setUiError(payload.error || 'Edit failed');
          }
        } else if (payload.type === "status") {
          if (payload.status === "completed") {
            setAppState('completed');
            setProgress({ story: 100, audio: 100, video: 100, edit: 100 });
          } else if (payload.status === "failed") {
            setAppState('failed');
            setUiError(payload.error || "Pipeline failed");
          }
        }
        
        refreshProject(project.project_id);
      } catch (error) {
        console.error(error);
      }
    };
    
    stream.onerror = () => stream.close();
    return () => stream.close();
  }, [project?.project_id]);

  useEffect(() => {
    if (project) {
      if (project.status === "running") {
        setAppState('generating');
      } else if (project.status === "completed") {
        setAppState('completed');
        setProgress({ story: 100, audio: 100, video: 100, edit: 100 });
      } else if (project.status === "failed") {
        setAppState('failed');
        setUiError(project.last_error || "Pipeline failed");
      }
    }
  }, [project?.status]);

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

  const handleInitialSubmit = async (e) => {
    e.preventDefault();
    if (!mainPrompt.trim()) return;
    
    try {
      setAppState('generating');
      setUiError("");
      setProgress({ story: 0, audio: 0, video: 0, edit: 0 });
      setActivePhase('story');
      setEvents([]);
      
      const data = await requestJson(`${API_BASE}/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: mainPrompt, num_scenes: numScenes }),
      });
      setProject(data);
    } catch (error) {
      setUiError(error.message);
      setAppState('failed');
    }
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    if (!editPrompt.trim() || !project) return;

    try {
      setActivePhase('edit');
      setUiError('');
      setAppState('generating');

      // Fire-and-forget: the backend runs async; SSE events drive UI updates
      requestJson(`${API_BASE}/projects/${project.project_id}/edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: editPrompt }),
      }).catch((error) => {
        setUiError(error.message);
        setAppState('failed');
      });

      setEditPrompt('');
    } catch (error) {
      setUiError(error.message);
      setAppState('failed');
    }
  };

  const handleRevert = async (versionId) => {
    if (!project) return;
    try {
      setAppState('generating');
      setUiError("");
      await requestJson(`${API_BASE}/projects/${project.project_id}/undo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version_id: versionId }),
      });
      await refreshProject();
      setAppState('completed');
    } catch (error) {
      setUiError(error.message);
      setAppState('failed');
    }
  };

  const handleRerunPhase = async (phaseId) => {
    if (!project) return;
    try {
      setAppState('generating');
      setActivePhase(phaseId);
      
      let newProg = { ...progress, [phaseId]: 0 };
      if (phaseId === 'story') newProg = { story: 0, audio: 0, video: 0 };
      if (phaseId === 'audio') newProg = { ...newProg, audio: 0, video: 0 };
      setProgress(newProg);
      
      setUiError("");
      await requestJson(`${API_BASE}/projects/${project.project_id}/run-phase/${phaseId}`, { method: "POST" });
      await refreshProject();
    } catch (error) {
      setUiError(error.message);
      setAppState('failed');
    }
  };

  if (appState === 'idle') {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6">
        <div className="max-w-3xl w-full space-y-8">
          <div className="text-center space-y-4">
            <div className="flex justify-center mb-6">
              <div className="bg-indigo-600/20 p-4 rounded-full">
                <Wand2 className="w-12 h-12 text-indigo-400" />
              </div>
            </div>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              Agentic AI Video Studio
            </h1>
            <p className="text-slate-400 text-lg">
              End-to-End Orchestration: Prompt → Script → Voice → Video
            </p>
          </div>

          <form onSubmit={handleInitialSubmit} className="relative mt-10">
            <div className="absolute inset-0 bg-gradient-to-r from-indigo-500 to-cyan-500 rounded-2xl blur opacity-20 transition-opacity duration-500"></div>
            <div className="relative bg-slate-900 border border-slate-800 rounded-2xl p-2 flex flex-col sm:flex-row gap-2 shadow-2xl">
              <textarea 
                value={mainPrompt}
                onChange={(e) => setMainPrompt(e.target.value)}
                placeholder="Describe your short film... e.g. 'A young astronaut discovers a hidden ocean on Mars'"
                className="w-full bg-transparent text-slate-200 placeholder-slate-500 p-4 outline-none resize-none h-24 sm:h-auto font-medium"
                autoFocus
              />
              <div className="flex flex-col gap-2 shrink-0 justify-end">
                <div className="flex items-center justify-between px-2 text-sm text-slate-400 font-medium">
                  <span>Scenes:</span>
                  <select 
                    value={numScenes}
                    onChange={(e) => setNumScenes(parseInt(e.target.value))}
                    className="bg-slate-800 border border-slate-700 rounded-md px-2 py-1 outline-none text-slate-200 cursor-pointer"
                  >
                    {[1, 2, 3, 4].map(n => <option key={n} value={n}>{n}</option>)}
                  </select>
                </div>
                <button 
                  type="submit"
                  disabled={!mainPrompt.trim()}
                  className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-8 py-3 rounded-xl font-semibold flex items-center justify-center gap-2 transition-colors"
                >
                  <Sparkles className="w-5 h-5" />
                  Generate
                </button>
              </div>
            </div>
          </form>
          
          <div className="flex justify-center gap-6 text-sm text-slate-500 font-medium">
            <span className="flex items-center gap-2"><FileText className="w-4 h-4"/> Multi-Agent Scripting</span>
            <span className="flex items-center gap-2"><Music className="w-4 h-4"/> AI Voice & Audio</span>
            <span className="flex items-center gap-2"><Video className="w-4 h-4"/> Auto-Compositing</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 flex flex-col">
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-10 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Layers className="w-6 h-6 text-indigo-400" />
          <h1 className="font-bold text-lg tracking-wide">Agentic Studio</h1>
        </div>
        <div className="flex items-center gap-4 text-sm font-medium">
          {uiError && <span className="text-red-400">Error: {uiError}</span>}
          <span className="text-slate-400 flex items-center gap-2">
            <TerminalSquare className="w-4 h-4"/> Pipeline Active
          </span>
          {appState === 'generating' && (
            <span className="bg-indigo-500/20 text-indigo-300 px-3 py-1 rounded-full flex items-center gap-2 border border-indigo-500/30">
              <RefreshCw className="w-4 h-4 animate-spin" /> Processing {activePhase || '...' }...
            </span>
          )}
        </div>
      </header>
      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 max-w-screen-2xl mx-auto w-full">
        
        <div className="lg:col-span-7 flex flex-col gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col">
            <div className="aspect-video bg-black relative flex items-center justify-center">
              {appState === 'generating' || (!videoUrl && appState !== 'failed') ? (
                <div className="text-center space-y-4">
                  <RefreshCw className="w-12 h-12 text-indigo-500 animate-spin mx-auto" />
                  <p className="text-slate-400 font-medium">Rendering Output...</p>
                </div>
              ) : videoUrl ? (
                <video 
                  ref={videoRef}
                  src={videoUrl} 
                  controls 
                  autoPlay
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="text-slate-500 text-sm">Video not available</div>
              )}
            </div>
            
            <div className="p-4 border-t border-slate-800 flex items-center justify-between bg-slate-900">
              <div>
                <h3 className="font-bold text-white">Final Output</h3>
                <p className="text-sm text-slate-400">Current View: {currentVersionId || 'Pending'}</p>
              </div>
              {videoUrl && (
                <a 
                  href={videoUrl}
                  download
                  target="_blank" rel="noreferrer"
                  className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors border border-slate-700"
                >
                  <Download className="w-4 h-4" /> Download MP4
                </a>
              )}
            </div>
          </div>

          <div className="bg-slate-900 border border-indigo-900/50 rounded-2xl p-5 shadow-xl flex-1 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
              <Wand2 className="w-32 h-32 text-indigo-500" />
            </div>
            
            <h2 className="text-lg font-bold flex items-center gap-2 text-indigo-300 mb-1">
              <MessageSquare className="w-5 h-5" /> Edit Agent
            </h2>
            <p className="text-sm text-slate-400 mb-4">
              Describe changes in natural language. The agent will detect the target and rebuild accordingly.
            </p>

            <form onSubmit={handleEditSubmit} className="flex flex-col gap-3">
              <textarea 
                value={editPrompt}
                onChange={(e) => setEditPrompt(e.target.value)}
                disabled={appState === 'generating'}
                placeholder='e.g., "Change the narrator voice to be deeper", "Make the final scene darker", "Add dramatic background music"'
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-slate-200 placeholder-slate-600 focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 outline-none resize-none h-28 disabled:opacity-50"
              />
              <div className="flex justify-between items-center">
                 <div className="text-xs text-slate-500 flex items-center gap-1">
                    <FileJson className="w-3 h-3"/> JSON Schema synced
                 </div>
                <button 
                  type="submit"
                  disabled={!editPrompt.trim() || appState === 'generating'}
                  className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-6 py-2.5 rounded-lg font-medium flex items-center gap-2 transition-colors"
                >
                  <Send className="w-4 h-4" /> Execute Edit
                </button>
              </div>
            </form>
          </div>
        </div>

        <div className="lg:col-span-5 flex flex-col gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl flex-1 flex flex-col">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
              <TerminalSquare className="w-5 h-5 text-slate-400" /> Pipeline Orchestrator
            </h2>
            
            <div className="space-y-4 overflow-y-auto custom-scrollbar flex-1 pr-2">
              {PHASES.map((phase) => {
                const Icon = phase.icon;
                const progValue = progress[phase.id] || 0;
                const isComplete = progValue === 100;
                const isActive = activePhase === phase.id;
                const phaseOutput = phaseOutputs[phase.id];

                return (
                  <div key={phase.id} className={`p-4 rounded-xl border ${isActive ? 'bg-indigo-950/30 border-indigo-500/50' : 'bg-slate-950 border-slate-800'} transition-all`}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${isComplete ? 'bg-green-500/20 text-green-400' : isActive ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-800 text-slate-500'}`}>
                          <Icon className="w-5 h-5" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-sm">{phase.title}</h3>
                          <p className="text-xs text-slate-500">{phase.member}</p>
                        </div>
                      </div>
                      
                      {appState === 'completed' && (
                         <button 
                            onClick={() => handleRerunPhase(phase.id)}
                            className="text-xs flex items-center gap-1 text-slate-400 hover:text-indigo-400 bg-slate-900 hover:bg-slate-800 px-2 py-1 rounded border border-slate-700 transition-colors"
                         >
                            <RefreshCw className="w-3 h-3" /> Re-run
                         </button>
                      )}
                    </div>
                    
                    <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden flex">
                      <div 
                        className={`h-full transition-all duration-300 ease-out ${isComplete ? 'bg-green-500' : 'bg-indigo-500'} ${isActive && !isComplete ? 'animate-pulse' : ''}`}
                        style={{ width: `${progValue}%` }}
                      ></div>
                    </div>
                    
                    <div className="flex justify-between text-xs mt-2 text-slate-500">
                      <span>{isActive ? 'Processing...' : isComplete ? 'Complete' : 'Pending'}</span>
                      <span>{progValue}%</span>
                    </div>

                    {progValue > 0 && phaseOutput && (
                      <div className="mt-4 bg-black/40 rounded-lg border border-slate-800 p-3 overflow-hidden">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-indigo-400 text-xs font-medium">
                            <phaseOutput.icon className="w-3.5 h-3.5" />
                            {phaseOutput.title}
                          </div>
                          <pre className="text-[11px] text-slate-400 font-mono whitespace-pre-wrap leading-relaxed bg-slate-900/50 p-2 rounded border border-slate-800">
                            {phaseOutput.data}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl max-h-[300px] flex flex-col">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
              <History className="w-5 h-5 text-slate-400" /> Version History
            </h2>
            
            {versions.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-slate-600 text-sm italic">
                Awaiting first generation...
              </div>
            ) : (
              <div className="space-y-3 overflow-y-auto pr-2 custom-scrollbar">
                {versions.map((version) => {
                  const isCurrent = version.id === currentVersionId;

                  return (
                    <div 
                      key={version.id} 
                      className={`p-3 rounded-xl border flex items-center justify-between transition-all ${isCurrent ? 'bg-indigo-900/20 border-indigo-500/50' : 'bg-slate-950 border-slate-800 hover:border-slate-700'}`}
                    >
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-sm font-bold ${isCurrent ? 'text-indigo-400' : 'text-slate-300'}`}>
                            {version.id}
                          </span>
                          {isCurrent && <span className="bg-indigo-500 text-white text-[10px] px-1.5 py-0.5 rounded uppercase font-bold tracking-wider">Active</span>}
                        </div>
                        <p className="text-xs text-slate-400 truncate max-w-[200px]" title={version.trigger}>
                          {version.trigger}
                        </p>
                        <p className="text-[10px] text-slate-500 mt-1">{version.timestamp}</p>
                      </div>
                      
                      {!isCurrent && appState === 'completed' && (
                        <button 
                          onClick={() => handleRevert(version.id)}
                          className="flex flex-col items-center justify-center p-2 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
                          title="Revert to this state"
                        >
                          <Undo2 className="w-4 h-4" />
                          <span className="text-[10px] mt-1">Revert</span>
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        </div>
      </main>
    </div>
  );
}
