from app.local_video_engine import render_attempt_profiles, _valid_frames


def test_frame_counts_match_cogvideox_temporal_scale():
    assert _valid_frames(17) == 17
    assert _valid_frames(13) == 13
    assert _valid_frames(9) == 9
    assert _valid_frames(16) == 13
    assert _valid_frames(1) == 9


def test_t4_profiles_shrink_without_duplicates():
    assert render_attempt_profiles(17, 8) == [(17, 8), (13, 6), (9, 4)]
    assert render_attempt_profiles(9, 4) == [(9, 4)]
    assert render_attempt_profiles(13, 6) == [(13, 6), (9, 4)]
