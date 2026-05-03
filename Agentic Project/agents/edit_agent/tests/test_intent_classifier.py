"""
Unit tests for the Edit Agent intent classifier.
Tests 10+ edit query types using mocked Groq API responses.
Run with: python -m pytest agents/edit_agent/tests/test_intent_classifier.py -v
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.edit_agent.executor import EditExecutor
from agents.edit_agent.planner import rerun_plan_for_target
from shared.schemas.project_state import (
    AudioState,
    CharacterState,
    DialogueLine,
    ProjectState,
    SceneState,
    StoryState,
    VideoState,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_state() -> ProjectState:
    char_a = CharacterState(
        character_id="char_akira",
        name="Akira",
        role="protagonist",
        voice_style="calm, determined female",
        visual_description="female cyber ninja, silver suit",
    )
    char_b = CharacterState(
        character_id="char_viktor",
        name="Viktor",
        role="antagonist",
        voice_style="deep, commanding male",
        visual_description="male cyborg soldier, dark armour",
    )
    scene = SceneState(
        scene_id="scene_1",
        title="Confrontation",
        duration_sec=12,
        narration="They face each other.",
        dialogue=[
            DialogueLine(character_id="char_akira", character_name="Akira", text="You lied."),
            DialogueLine(character_id="char_viktor", character_name="Viktor", text="War requires it."),
        ],
        visual_prompt="Cinematic wide shot, neon alley.",
        mood="tense",
        subtitle_lines=["You lied.", "War requires it."],
    )
    return ProjectState(
        project_id="proj_test",
        prompt="A sci-fi standoff",
        story=StoryState(title="Standoff", logline="...", tone="dark"),
        characters=[char_a, char_b],
        scenes=[scene],
        audio=AudioState(),
        video=VideoState(),
    )


def _mock_groq(intent: str, target: str, details: dict):
    """Helper that patches the Groq API to return a predetermined classification."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps({
            "intent": intent,
            "target": target,
            "details": details,
        })}}]
    }
    mock_response.raise_for_status = MagicMock()
    return mock_response


# ---------------------------------------------------------------------------
# Tests — intent classification (mocked Groq)
# ---------------------------------------------------------------------------

@patch("requests.post")
def test_change_voice_tone(mock_post):
    """Query: change narrator voice deeper → audio / change_voice_tone"""
    mock_post.return_value = _mock_groq(
        "change_voice_tone", "audio",
        {"character_id": "char_viktor", "tone": "deep", "scene_id": None,
         "visual_change": None, "subtitles_enabled": None, "duration_delta": None}
    )
    from agents.edit_agent.intent_classifier import classify_edit
    state = _make_state()
    intent, target, details = classify_edit("Change Viktor's voice to be deeper", state)
    assert target == "audio"
    assert "voice" in intent or "tone" in intent


@patch("requests.post")
def test_make_scene_darker(mock_post):
    """Query: make scene darker → video_frame / adjust_scene_visuals"""
    mock_post.return_value = _mock_groq(
        "adjust_scene_visuals", "video_frame",
        {"scene_id": "scene_1", "visual_change": "darker", "character_id": None,
         "tone": None, "subtitles_enabled": None, "duration_delta": None}
    )
    from agents.edit_agent.intent_classifier import classify_edit
    state = _make_state()
    intent, target, details = classify_edit("Make the first scene darker", state)
    assert target == "video_frame"
    assert details.get("visual_change") == "darker"


@patch("requests.post")
def test_remove_subtitles(mock_post):
    """Query: remove subtitles → video / toggle_subtitles"""
    mock_post.return_value = _mock_groq(
        "toggle_subtitles", "video",
        {"subtitles_enabled": False, "scene_id": None, "character_id": None,
         "tone": None, "visual_change": None, "duration_delta": None}
    )
    from agents.edit_agent.intent_classifier import classify_edit
    state = _make_state()
    intent, target, details = classify_edit("Remove the subtitles", state)
    assert target == "video"
    assert details.get("subtitles_enabled") is False


@patch("requests.post")
def test_regenerate_script(mock_post):
    """Query: regenerate script → script / regenerate_script"""
    mock_post.return_value = _mock_groq(
        "regenerate_script", "script",
        {"scene_id": None, "character_id": None, "tone": None,
         "visual_change": None, "subtitles_enabled": None, "duration_delta": None}
    )
    from agents.edit_agent.intent_classifier import classify_edit
    state = _make_state()
    intent, target, details = classify_edit("Regenerate the script with a darker tone", state)
    assert target == "script"


@patch("requests.post")
def test_change_character_design(mock_post):
    """Query: change character design → video_frame / change_character_design"""
    mock_post.return_value = _mock_groq(
        "change_character_design", "video_frame",
        {"character_id": "char_akira", "visual_change": "red armour instead of silver",
         "scene_id": None, "tone": None, "subtitles_enabled": None, "duration_delta": None}
    )
    from agents.edit_agent.intent_classifier import classify_edit
    state = _make_state()
    intent, target, details = classify_edit("Change Akira's outfit to red armour", state)
    assert target == "video_frame"
    assert "character" in intent or "design" in intent


@patch("requests.post")
def test_speed_up_scene(mock_post):
    """Query: speed up scene → video / adjust_scene_speed"""
    mock_post.return_value = _mock_groq(
        "adjust_scene_speed", "video",
        {"scene_id": "scene_1", "duration_delta": -3, "character_id": None,
         "tone": None, "visual_change": None, "subtitles_enabled": None}
    )
    from agents.edit_agent.intent_classifier import classify_edit
    state = _make_state()
    intent, target, details = classify_edit("Speed up scene 1 by 3 seconds", state)
    assert target == "video"


@patch("requests.post")
def test_lower_bgm_volume(mock_post):
    """Query: lower background music → audio / adjust_bgm_volume"""
    mock_post.return_value = _mock_groq(
        "adjust_bgm_volume", "audio",
        {"scene_id": None, "character_id": None, "tone": "lower",
         "visual_change": None, "subtitles_enabled": None, "duration_delta": None}
    )
    from agents.edit_agent.intent_classifier import classify_edit
    state = _make_state()
    intent, target, details = classify_edit("Lower the background music volume", state)
    assert target == "audio"


@patch("requests.post")
def test_make_scene_brighter(mock_post):
    """Query: make scene brighter → video_frame / adjust_scene_visuals"""
    mock_post.return_value = _mock_groq(
        "adjust_scene_visuals", "video_frame",
        {"scene_id": "scene_1", "visual_change": "brighter", "character_id": None,
         "tone": None, "subtitles_enabled": None, "duration_delta": None}
    )
    from agents.edit_agent.intent_classifier import classify_edit
    state = _make_state()
    intent, target, details = classify_edit("Make scene 1 brighter", state)
    assert target == "video_frame"


@patch("requests.post")
def test_soft_voice_female_character(mock_post):
    """Query: softer voice for female character → audio / change_voice_tone"""
    mock_post.return_value = _mock_groq(
        "change_voice_tone", "audio",
        {"character_id": "char_akira", "tone": "soft", "scene_id": None,
         "visual_change": None, "subtitles_enabled": None, "duration_delta": None}
    )
    from agents.edit_agent.intent_classifier import classify_edit
    state = _make_state()
    intent, target, details = classify_edit("Give Akira a softer voice", state)
    assert target == "audio"
    assert details.get("tone") == "soft"


@patch("requests.post")
def test_add_background_music(mock_post):
    """Query: add background music → audio / adjust_bgm_volume"""
    mock_post.return_value = _mock_groq(
        "adjust_bgm_volume", "audio",
        {"scene_id": None, "character_id": None, "tone": "louder",
         "visual_change": None, "subtitles_enabled": None, "duration_delta": None}
    )
    from agents.edit_agent.intent_classifier import classify_edit
    state = _make_state()
    intent, target, details = classify_edit("Add dramatic background music", state)
    assert target == "audio"


# ---------------------------------------------------------------------------
# Tests — executor
# ---------------------------------------------------------------------------

def test_executor_darken_visual_prompt():
    """Darker edit updates visual_prompt on the scene."""
    state = _make_state()
    executor = EditExecutor()
    result = executor.apply(state, "make it darker", "adjust_scene_visuals", "video_frame",
                            {"scene_id": "scene_1", "visual_change": "darker"})
    assert "darker" in result.scenes[0].visual_prompt.lower()


def test_executor_character_design_clears_image_path():
    """Character design edit clears image_path so VideoAgent re-renders."""
    state = _make_state()
    state.scenes[0].image_path = "/fake/path/scene_1.png"
    state.scenes[0].image_status = "generated"
    executor = EditExecutor()
    result = executor.apply(
        state, "Change Akira to red armour", "change_character_design", "video_frame",
        {"character_id": "char_akira", "visual_change": "red armour"}
    )
    assert result.scenes[0].image_path is None
    assert result.scenes[0].image_status == "pending"


def test_executor_toggle_subtitles():
    """Subtitle toggle sets video.subtitles_enabled correctly."""
    state = _make_state()
    state.video.subtitles_enabled = True
    executor = EditExecutor()
    result = executor.apply(state, "remove subtitles", "toggle_subtitles", "video",
                            {"subtitles_enabled": False})
    assert result.video.subtitles_enabled is False


def test_executor_bgm_volume_lower():
    """BGM volume edit lowers bgm_volume."""
    state = _make_state()
    state.audio.bgm_volume = 0.2
    executor = EditExecutor()
    result = executor.apply(state, "lower the background music", "adjust_bgm_volume", "audio",
                            {"tone": "lower"})
    assert result.audio.bgm_volume < 0.2


def test_executor_voice_tone_change():
    """Voice tone edit updates character voice_style."""
    state = _make_state()
    executor = EditExecutor()
    result = executor.apply(state, "make Viktor sound deep", "change_voice_tone", "audio",
                            {"character_id": "char_viktor", "tone": "deep"})
    viktor = next(c for c in result.characters if c.character_id == "char_viktor")
    assert "deep" in viktor.voice_style.lower() or "bold" in viktor.voice_style.lower()


# ---------------------------------------------------------------------------
# Tests — planner
# ---------------------------------------------------------------------------

def test_planner_script_cascades_all():
    assert rerun_plan_for_target("script") == ["story", "audio", "video"]


def test_planner_audio_includes_video():
    assert rerun_plan_for_target("audio") == ["audio", "video"]


def test_planner_video_frame_filter_is_video_only():
    """Visual filter edits should only re-composite, not re-render image."""
    plan = rerun_plan_for_target("video_frame", intent="adjust_scene_visuals")
    assert plan == ["video"]
    assert "audio" not in plan


def test_planner_character_design_includes_audio():
    """Character design changes may require voice re-gen."""
    plan = rerun_plan_for_target("video_frame", intent="change_character_design")
    assert "audio" in plan
    assert "video" in plan


def test_planner_video_only():
    assert rerun_plan_for_target("video") == ["video"]
