from app.tutor.prompt import HISTORY_TURNS, LearnerContext, build_messages, build_profile, greeting

CTX = LearnerContext(
    level="A2",
    skill_levels={"grammar": "A2", "reading": "B1"},
    course_title="English A2 — Elementary",
    facts=["Works as a nurse", "Has a daughter called Mira"],
    recurring_mistakes=[("I go yesterday", "I went yesterday"), ("he have", "he has")],
)


def test_profile_includes_level_course_facts_and_mistakes() -> None:
    profile = build_profile(CTX)

    assert "- Level: A2" in profile
    assert "grammar A2, reading B1" in profile
    assert "English A2 — Elementary" in profile
    assert "Works as a nurse; Has a daughter called Mira" in profile
    assert '"I go yesterday" -> "I went yesterday"' in profile


def test_profile_for_a_new_learner() -> None:
    assert "What you remember: nothing yet" in build_profile(LearnerContext(level="A1"))


def test_messages_open_with_a_user_turn_and_alternate() -> None:
    history = [("tutor", "Hi! Tell me about yourself."), ("learner", "I am nurse.")]

    system, messages = build_messages(CTX, history)

    assert [m.role for m in messages] == ["user", "model", "user"]
    assert messages[0].text == "(The learner opens the chat.)"
    assert messages[-1].text == "I am nurse."
    assert "Speak at the learner's level (A2)" in system


def test_consecutive_learner_messages_are_merged() -> None:
    history = [("tutor", "Hi!"), ("learner", "Hello"), ("learner", "Are you there?")]

    _, messages = build_messages(CTX, history)

    assert [m.role for m in messages] == ["user", "model", "user"]
    assert messages[-1].text == "Hello\nAre you there?"


def test_only_recent_history_is_sent() -> None:
    history = [("learner" if i % 2 else "tutor", f"message {i}") for i in range(50)]

    _, messages = build_messages(CTX, history)

    assert messages[-1].text == "message 49"
    assert len(messages) <= HISTORY_TURNS + 1  # + the synthetic opener


def test_greetings() -> None:
    assert "get to know you" in greeting(CTX, first_conversation=True)
    assert "Welcome back" in greeting(CTX, first_conversation=False)
