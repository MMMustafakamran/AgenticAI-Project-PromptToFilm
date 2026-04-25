from agents.edit_agent.agent import EditAgent
from agents.edit_agent.intent_classifier import classify_edit
from agents.edit_agent.planner import rerun_plan_for_target
from shared.schemas.project_state import CharacterState, DialogueLine, ProjectState, SceneState


def _state() -> ProjectState:
    return ProjectState(
        project_id="proj_edit_test",
        prompt="A glowing city mystery.",
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
                title="One",
                duration_sec=12,
                narration="Intro",
                dialogue=[DialogueLine(character_id="char_1", character_name="Aanya", text="Hello")],
                visual_prompt="Bright alley",
                mood="curious",
                subtitle_lines=["Hello"],
            ),
            SceneState(
                scene_id="scene_2",
                title="Two",
                duration_sec=12,
                narration="Outro",
                dialogue=[DialogueLine(character_id="char_2", character_name="Rafi", text="Goodbye")],
                visual_prompt="Warm rooftop",
                mood="uplifting",
                subtitle_lines=["Goodbye"],
            ),
        ],
    )


def test_edit_classifier_routes_known_commands():
    state = _state()
    assert classify_edit("Change Aanya voice to softer", state)[1] == "audio"
    assert classify_edit("Make scene 2 darker", state)[1] == "video_frame"
    assert classify_edit("Remove subtitles", state)[1] == "video"


def test_edit_agent_targets_only_selected_scene():
    state = _state()

    updated, phases, intent, target = EditAgent().prepare(state, "Make scene 2 darker")

    assert target == "video_frame"
    assert phases == ["video"]
    assert "darker mood" not in updated.scenes[0].visual_prompt
    assert "darker mood" in updated.scenes[1].visual_prompt
    assert intent == "adjust_scene_visuals"


def test_edit_agent_targets_only_selected_character_voice():
    state = _state()

    updated, phases, _, target = EditAgent().prepare(state, "Change Aanya voice to softer")

    assert target == "audio"
    assert phases == ["audio", "video"]
    assert "soft and gentle" in updated.characters[0].voice_style
    assert "soft and gentle" not in updated.characters[1].voice_style


def test_rerun_plan_targets_correct_phases():
    assert rerun_plan_for_target("script") == ["story", "audio", "video"]
    assert rerun_plan_for_target("audio") == ["audio", "video"]
    assert rerun_plan_for_target("video") == ["video"]
