from agents.edit_agent.intent_classifier import classify_edit
from agents.edit_agent.planner import rerun_plan_for_target


def test_edit_classifier_routes_known_commands():
    assert classify_edit("Change voice tone")[1] == "audio"
    assert classify_edit("Make scene darker")[1] == "video_frame"
    assert classify_edit("Remove subtitles")[1] == "video"


def test_rerun_plan_targets_correct_phases():
    assert rerun_plan_for_target("script") == ["story", "audio", "video"]
    assert rerun_plan_for_target("audio") == ["audio", "video"]
    assert rerun_plan_for_target("video") == ["video"]
