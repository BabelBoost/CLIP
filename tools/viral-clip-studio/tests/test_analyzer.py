from viralclip.analyzer import analyze_segments, format_time
from viralclip.models import TranscriptSegment


def sample_segments():
    return [
        TranscriptSegment(0.0, 5.0, "Dzisiaj pokażę zwykły przykład i kilka szczegółów."),
        TranscriptSegment(5.0, 10.0, "Ale potem wydarzyło się coś naprawdę dziwnego."),
        TranscriptSegment(10.0, 15.0, "Nikt nie spodziewał się takiej odpowiedzi!"),
        TranscriptSegment(15.0, 20.0, "Czy naprawdę można było tego uniknąć?"),
        TranscriptSegment(20.0, 25.0, "Właśnie tutaj zaczyna się cały problem."),
        TranscriptSegment(25.0, 30.0, "I to jest puenta tej historii."),
        TranscriptSegment(30.0, 35.0, "Dalej temat robi się już dużo spokojniejszy."),
    ]


def test_format_time():
    assert format_time(65) == "01:05"
    assert format_time(3661) == "01:01:01"


def test_candidates_are_ranked_and_nonempty():
    clips = analyze_segments(sample_segments(), top_n=5, content_mode="general")
    assert clips
    assert clips[0].rank == 1
    assert clips[0].viral_score >= clips[-1].viral_score
    assert 10 <= clips[0].duration <= 64
    assert clips[0].suggested_length in {15, 30, 60}


def test_detailed_scores_are_in_range():
    clip = analyze_segments(sample_segments(), top_n=1, content_mode="general")[0]
    assert 0 <= clip.viral_score <= 100
    assert 0 <= clip.hook_score <= 100
    assert 0 <= clip.emotion_score <= 100
    assert 0 <= clip.comment_potential <= 100
    assert 0 <= clip.retention_score <= 100
    assert 0 <= clip.share_potential <= 100
    assert 0 <= clip.context_dependency <= 100
    assert clip.quality_label in {
        "PUBLIKUJ NAJPIERW",
        "DOBRY MATERIAŁ",
        "POPRAW HOOK LUB SKRÓĆ",
        "ODRZUĆ / PRZEMONTUJ",
    }
    assert clip.hook
    assert clip.screen_text
    assert len(clip.hook_variants) == 3
    assert clip.hook == clip.hook_variants[0]["text"]
    assert clip.selected_hook_score == clip.hook_variants[0]["score"]
    assert clip.hook_score == clip.selected_hook_score
    assert clip.hook_variants[0]["score"] >= clip.hook_variants[-1]["score"]
    assert len({item["text"] for item in clip.hook_variants}) == 3


def test_public_affairs_hook_uses_source_wording():
    segs = [
        TranscriptSegment(0, 8, "Premier powiedział, że ustawa ma wejść w życie w przyszłym roku."),
        TranscriptSegment(8, 16, "Poseł odpowiedział, że to nieprawda i podał inny termin."),
        TranscriptSegment(16, 24, "Spór dotyczy więc konkretnej daty wejścia ustawy w życie."),
    ]
    clips = analyze_segments(segs, top_n=1, content_mode="public_affairs", include_weak=True)
    assert clips
    assert "Tu zaczyna się spór" not in clips[0].hook
    assert len(clips[0].hook_variants) == 3
    assert all("skandal" not in item["text"].lower() for item in clips[0].hook_variants)


def test_weak_candidates_can_be_filtered_or_inspected():
    weak = [
        TranscriptSegment(0.0, 5.0, "Dzisiaj omawiamy zwykły temat bez szczególnych zmian."),
        TranscriptSegment(5.0, 10.0, "Następnie przechodzimy do kolejnego spokojnego punktu rozmowy."),
        TranscriptSegment(10.0, 15.0, "Na końcu pojawia się krótkie podsumowanie całego materiału."),
        TranscriptSegment(15.0, 20.0, "Rozmowa trwa dalej w podobnym spokojnym tempie."),
    ]
    filtered = analyze_segments(weak, top_n=5, content_mode="general", min_viral_score=85)
    inspected = analyze_segments(
        weak,
        top_n=5,
        content_mode="general",
        min_viral_score=85,
        include_weak=True,
    )
    assert filtered == []
    assert inspected
    assert all(0 <= clip.share_potential <= 100 for clip in inspected)
