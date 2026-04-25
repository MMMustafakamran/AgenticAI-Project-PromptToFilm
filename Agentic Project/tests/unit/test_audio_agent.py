from agents.audio_agent.agent import AudioAgent
from shared.schemas.project_state import CharacterState, DialogueLine, ProjectState, SceneState


def _sample_state() -> ProjectState:
    return ProjectState(
        project_id="proj_audio_test",
        prompt="A mechanic repairs a singing bridge.",
        characters=[
            CharacterState(
                character_id="char_1",
                name="Aanya",
                role="lead",
                voice_style="warm, reflective, youthful",
                visual_description="silver jacket",
            ),
            CharacterState(
                character_id="char_2",
                name="Rafi",
                role="partner",
                voice_style="calm, grounded, reassuring",
                visual_description="earth-toned coat",
            ),
        ],
        scenes=[
            SceneState(
                scene_id="scene_1",
                title="Start",
                duration_sec=12,
                narration="Intro",
                dialogue=[DialogueLine(character_id="char_1", character_name="Aanya", text="Hello there.")],
                visual_prompt="Bridge at dawn",
                mood="curious",
                subtitle_lines=["Hello there."],
            ),
            SceneState(
                scene_id="scene_2",
                title="Finish",
                duration_sec=12,
                narration="Outro",
                dialogue=[DialogueLine(character_id="char_2", character_name="Rafi", text="We fixed it.")],
                visual_prompt="Bridge at sunset",
                mood="uplifting",
                subtitle_lines=["We fixed it."],
            ),
        ],
    )


def test_audio_agent_builds_timing_manifest(monkeypatch):
    state = _sample_state()

    def fake_generate(self, text, voice_style, character_name, output_base, voice_seed, preferred_voice_name=None):
        if character_name == "Aanya":
            return "edge-tts", str(output_base.with_suffix(".mp3")), 1200, preferred_voice_name or "en-US-JennyNeural"
        return "elevenlabs", str(output_base.with_suffix(".mp3")), 1500, preferred_voice_name or "en-US-GuyNeural"

    def fake_stitch_audio(timing_manifest, bgm_track, output_path, bgm_volume=0.2):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake wav")
        return str(output_path)

    monkeypatch.setattr("agents.audio_agent.agent.stitch_audio", fake_stitch_audio)
    monkeypatch.setattr("agents.audio_agent.agent.TTSGenerator.generate", fake_generate)

    updated = AudioAgent().run(state)

    assert updated.audio.final_audio_path
    assert len(updated.audio.dialogue_tracks) == len(updated.audio.timing_manifest) == 2
    assert updated.audio.providers_used == ["edge-tts", "elevenlabs"]
    assert updated.audio.dialogue_tracks[0].voice_name == "en-US-JennyNeural"
    assert updated.characters[0].voice_name == "en-US-JennyNeural"
    assert all(entry.end_ms > entry.start_ms for entry in updated.audio.timing_manifest)
