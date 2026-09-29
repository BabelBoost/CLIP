from downloader.smartclip import CandidateClip
from downloader.speech import SpeechSegment
from downloader.viral import (
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


def test_pace_score_prefers_dynamic_but_readable_speech():
    assert pace_score(3.0) > pace_score(0.5)
    assert pace_score(3.0) > pace_score(6.5)


def test_words_in_window_counts_only_overlapping_segments():
    segments = [
        SpeechSegment(0, 3, "To jest pierwszy fragment"),
        SpeechSegment(10, 12, "Drugi fragment tutaj"),
    ]
    assert words_in_window(segments, 0, 5) == 4


def test_viral_score_rewards_strong_opening_and_dense_speech():
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
    assert score.total > 0.65
    assert score.hook > 0.5
    assert score.words_per_second > 1.5


def test_rerank_candidates_prefers_stronger_transcript():
    candidates = [
        CandidateClip(0, 10, 0.7, 0.7, 0.6, 0.3, 0.5, 0.9),
        CandidateClip(20, 30, 0.7, 0.7, 0.6, 0.3, 0.5, 0.9),
    ]
    segments = [
        SpeechSegment(0, 10, "Spokojny zwykły opis bez specjalnego początku"),
        SpeechSegment(20, 24, "Dlaczego 5 błędów niszczy twój wynik?"),
        SpeechSegment(24, 30, "Większość ludzi tego nie zauważa, ale to naprawdę ważne."),
    ]
    ranked = rerank_candidates(candidates, segments, 2)
    assert ranked[0][1].start == 20
    assert ranked[0][0] > ranked[1][0]
