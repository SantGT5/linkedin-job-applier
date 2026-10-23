from modules.ai.glmConnections import glm_thinking_params


def test_effort_enables_thinking_at_that_depth():
    # GLM-5.3 models reject disabled thinking; depth is set by reasoning_effort.
    assert glm_thinking_params("high") == {
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
    }


def test_none_disables_thinking_for_older_models():
    assert glm_thinking_params("none") == {"thinking": {"type": "disabled"}}
    assert glm_thinking_params("") == {"thinking": {"type": "disabled"}}
