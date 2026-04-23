"""Unit tests for pi0buzzer.core.music.MusicBuzzer."""

import time

from pi0buzzer.notes import BUILTIN_SONGS, EMOTION_SOUNDS, NOTES, get_emotion_names, get_song_names


class TestMusicBuzzerPlayNote:
    """Test play_note() method."""

    def test_play_note_valid(self, music_buzzer):
        music_buzzer.play_note("C4", 0.1)
        time.sleep(0.3)
        music_buzzer.pi.set_PWM_frequency.assert_called_with(17, 262)

    def test_play_note_case_insensitive(self, music_buzzer):
        music_buzzer.play_note("c4", 0.1)
        time.sleep(0.3)
        music_buzzer.pi.set_PWM_frequency.assert_called_with(17, 262)

    def test_play_note_unknown(self, music_buzzer):
        # Should not raise, just log warning
        music_buzzer.play_note("Z9", 0.1)


class TestMusicBuzzerPlaySong:
    """Test play_song() method."""

    def test_play_song_queues_notes(self, music_buzzer):
        song = [("C4", 0.05), ("E4", 0.05), ("G4", 0.05)]
        music_buzzer.play_song(song)
        # Give worker time to process
        time.sleep(0.5)
        assert music_buzzer.pi.set_PWM_frequency.call_count >= 3

    def test_play_song_handles_pauses(self, music_buzzer):
        song = [("C4", 0.05), ("pause", 0.05), ("E4", 0.05)]
        music_buzzer.play_song(song)
        time.sleep(0.5)
        # Should have played 2 notes (C4 and E4), skipping pause
        assert music_buzzer.pi.set_PWM_frequency.call_count >= 2

    def test_play_song_is_nonblocking(self, music_buzzer):
        """play_song should return immediately."""
        song = [("C4", 1.0)] * 5  # 5 seconds of music
        start = time.time()
        music_buzzer.play_song(song)
        elapsed = time.time() - start
        assert elapsed < 0.5  # Should return in under 0.5s


class TestMusicBuzzerPlayEmotion:
    """Test play_emotion() method."""

    def test_play_emotion_happy(self, music_buzzer):
        music_buzzer.play_emotion("happy")
        time.sleep(1.0)
        assert music_buzzer.pi.set_PWM_frequency.call_count >= 1

    def test_play_emotion_unknown(self, music_buzzer):
        # Should not raise
        music_buzzer.play_emotion("nonexistent")

    def test_all_emotions_are_valid(self):
        """Verify all emotion sounds use valid note names."""
        for name, melody in EMOTION_SOUNDS.items():
            for note, dur in melody:
                if note != "pause":
                    assert note in NOTES, (
                        f"Emotion '{name}' uses unknown note: {note}"
                    )
                assert dur > 0, (
                    f"Emotion '{name}' has non-positive duration: {dur}"
                )


class TestMusicBuzzerPlayDemo:
    """Test play_demo() method."""

    def test_play_demo(self, music_buzzer):
        music_buzzer.play_demo()
        time.sleep(0.5)
        assert music_buzzer.pi.set_PWM_frequency.call_count >= 1


class TestMusicBuzzerPlayNamedSong:
    """Test play_named_song() method."""

    def test_play_named_song(self, music_buzzer):
        music_buzzer.play_named_song("jingle_bells")
        time.sleep(1.0)
        assert music_buzzer.pi.set_PWM_frequency.call_count >= 1

    def test_play_named_song_unknown(self, music_buzzer):
        music_buzzer.play_named_song("nonexistent_song")
        time.sleep(0.1)
        assert music_buzzer.pi.set_PWM_frequency.call_count == 0


class TestNotesModule:
    """Test the notes.py constants."""

    def test_notes_not_empty(self):
        assert len(NOTES) > 0

    def test_notes_contains_a4(self):
        assert NOTES["A4"] == 440

    def test_get_emotion_names(self):
        names = get_emotion_names()
        assert "happy" in names
        assert "sad" in names
        assert len(names) == 14

    def test_emotion_names_sorted(self):
        names = get_emotion_names()
        assert names == sorted(names)

    def test_all_builtin_songs_are_valid(self):
        for name, melody in BUILTIN_SONGS.items():
            for note, duration in melody:
                if note != "pause":
                    assert note in NOTES, f"Song '{name}' uses unknown note: {note}"
                assert duration > 0, f"Song '{name}' has non-positive duration: {duration}"

    def test_get_song_names(self):
        names = get_song_names()
        assert "happy_birthday" in names
        assert "jingle_bells" in names
        assert "twinkle_twinkle_little_star" in names
        assert "head_shoulders_knees_and_toes" in names
        assert names == sorted(names)
