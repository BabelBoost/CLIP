from downloader.smartclip import CandidateClip
from downloader.speech import SpeechSegment
from downloader.viral import (
    comment_potential_score,
    context_dependency_score,
    emotion_score,
    hook_score,
    pace_score,
    rerank_candidates,
    viral_score_for_window,
    words_in_window,
)


def test_hook_score_rewards_question_and_number():
    score, reasons = hook_score("Dlaczego 3 rzeczy zmienią twój wynik?")
    assert score > 0.5
    assert "pytanie na początku" in reasons
    assert "konkret/liczba" in reasons


def test_emotion_score_rewards_emotional_language():
    strong, reasons = emotion_score("To jest absurd! Nie wierzę, że naprawdę to powiedział!")
    calm, _ = emotion_score("To jest zwykły opis wydarzenia.")
    assert strong > calm
    assert strong >= 0.4
    assert reasons


def test_comment_potential_rewards_question_and_strong_claim():
    strong, reasons = comment_potential_score(
        "Czy naprawdę każdy powinien za to płacić? Co o tym myślisz?",
        emotion=0.5,
        punch=0.5,
    )
    calm, _ = comment_potential_score("Dzisiaj omówimy kolejną część raportu.")
    assert strong > calm
    assert strong >= 0.5
    assert reasons


def test_context_dependency_penalizes_reference_to_earlier_discussion():
    dependent, reasons = context_dependency_score(
        "I dlatego, jak mówiłem wcześniej, on zrobił właśnie to."
    )
    standalone, _ = context_dependency_score(
        "Dlaczego 3 firmy podniosły ceny w tym tygodniu?"
    )
    assert dependent > standalone
    assert dependent >= 0.5
    assert reasons


def test_pace_score_prefers_dynamic_but_readable_speech():
    assert pace_score(3.0) > pace_score(0.5)
    assert pace_score(3.0) > pace_score(6.5)


def test_words_in_window_counts_only_overlapping_segments():
    segments = [
        SpeechSegment(0, 3, "To jest pierwszy fragment"),
        SpeechSegment(10, 12, "Drugi fragment tutaj"),
    ]
    assert words_in_window(segments, 0, 5) == 4


def test_viral_score_exposes_new_quality_scores():
    segments = [
        SpeechSegment(0, 4, "Dlaczego 3 proste błędy kosztują cię pieniądze?"),
        SpeechSegment(4, 10, "Większość ludzi robi to zawsze, ale rozwiązanie jest bardzo proste."),
    ]
    score = viral_score_for_window(
        segments,
        0,
        10,
        speech_ratio=0.95,
        face_ratio=0.8,
        motion_score=0.7,
        scene_score=0.4,
    )
    assert score.total > 0.6
    assert score.hook > 0.5
    assert score.comment_potential > 0.4
    assert score.context_dependency < 0.5
    assert score.words_per_second > 1.5
    assert score.eligible is True


def test_rerank_candidates_filters_weak_clip_before_display():
    candidates = [
        CandidateClip(0, 10, 0.7, 0.7, 0.6, 0.3, 0.5, 0.9),
        CandidateClip(20, 30, 0.7, 0.7, 0.6, 0.3, 0.5, 0.9),
    ]
    segments = [
        SpeechSegment(0, 10, "Spokojny zwykły opis bez specjalnego początku i bez wyraźnej puenty."),
        SpeechSegment(20, 24, "Dlaczego 5 błędów niszczy twój wynik?"),
        SpeechSegment(24, 30, "Większość ludzi tego nie zauważa, ale to naprawdę ważne."),
    ]
    ranked = rerank_candidates(candidates, segments, 2)
    assert ranked
    assert ranked[0][1].start == 20
    assert all(item[2].eligible for item in ranked)


def test_rerank_can_keep_weak_candidates_when_filter_disabled():
    candidates = [CandidateClip(0, 10, 0.4, 0.2, 0.1, 0.1, 0.5, 0.3)]
    segments = [SpeechSegment(0, 10, "I wtedy on powiedział to i poszedł dalej.")]
    filtered = rerank_candidates(candidates, segments, 1)
    unfiltered = rerank_candidates(candidates, segments, 1, filter_weak=False)
    assert filtered == []
    assert len(unfiltered) == 1
    assert unfiltered[0][2].eligible is False
