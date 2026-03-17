"""Tests for the engagement tracker module."""

import time
from unittest.mock import MagicMock

import numpy as np
import pytest

from src.core.engagement_tracker import EngagementState, EngagementTracker


class TestEngagementTracker:
    """Tests for EngagementTracker state transitions and signal processing."""

    def test_initial_state_is_unknown(self):
        tracker = EngagementTracker()
        assert tracker.state == EngagementState.UNKNOWN

    def test_loud_audio_marks_engaged(self):
        tracker = EngagementTracker(audio_rms_threshold=100.0)
        # Create loud audio (high amplitude)
        loud = np.array([5000] * 1024, dtype=np.int16).tobytes()
        tracker.update_audio(loud)
        assert tracker.state == EngagementState.ENGAGED

    def test_silent_audio_does_not_engage(self):
        tracker = EngagementTracker(audio_rms_threshold=100.0)
        # Create silence (near-zero amplitude)
        silent = np.array([1] * 1024, dtype=np.int16).tobytes()
        tracker.update_audio(silent)
        assert tracker.state == EngagementState.UNKNOWN

    def test_face_detected_marks_engaged(self):
        tracker = EngagementTracker()
        tracker.update_video(face_detected=True)
        assert tracker.state == EngagementState.ENGAGED

    def test_no_face_does_not_engage(self):
        tracker = EngagementTracker()
        tracker.update_video(face_detected=False)
        assert tracker.state == EngagementState.UNKNOWN

    def test_transition_to_disengaged_after_silence(self):
        tracker = EngagementTracker(
            silence_threshold_sec=0.01,
            absence_threshold_sec=0.01,
            audio_rms_threshold=100.0,
        )
        # First engage with audio
        loud = np.array([5000] * 1024, dtype=np.int16).tobytes()
        tracker.update_audio(loud)
        assert tracker.state == EngagementState.ENGAGED

        # Wait past threshold
        time.sleep(0.02)

        # Send silent audio to trigger re-evaluation
        silent = np.array([1] * 1024, dtype=np.int16).tobytes()
        tracker.update_audio(silent)
        assert tracker.state == EngagementState.DISENGAGED

    def test_reengage_after_disengaged(self):
        tracker = EngagementTracker(
            silence_threshold_sec=0.01,
            absence_threshold_sec=0.01,
            audio_rms_threshold=100.0,
        )
        loud = np.array([5000] * 1024, dtype=np.int16).tobytes()
        silent = np.array([1] * 1024, dtype=np.int16).tobytes()

        # Engage -> disengage -> re-engage
        tracker.update_audio(loud)
        time.sleep(0.02)
        tracker.update_audio(silent)
        assert tracker.state == EngagementState.DISENGAGED

        tracker.update_audio(loud)
        assert tracker.state == EngagementState.ENGAGED

    def test_callback_fires_on_transition(self):
        callback = MagicMock()
        tracker = EngagementTracker(
            silence_threshold_sec=0.01,
            absence_threshold_sec=0.01,
            audio_rms_threshold=100.0,
            on_state_change=callback,
        )
        loud = np.array([5000] * 1024, dtype=np.int16).tobytes()
        silent = np.array([1] * 1024, dtype=np.int16).tobytes()

        # First transition (UNKNOWN -> ENGAGED) should NOT fire callback
        tracker.update_audio(loud)
        callback.assert_not_called()

        # Wait and transition to DISENGAGED -- should fire
        time.sleep(0.02)
        tracker.update_audio(silent)
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == EngagementState.ENGAGED
        assert args[1] == EngagementState.DISENGAGED

    def test_video_keeps_engaged_during_silence(self):
        tracker = EngagementTracker(
            silence_threshold_sec=0.01,
            absence_threshold_sec=100.0,
            audio_rms_threshold=100.0,
        )
        loud = np.array([5000] * 1024, dtype=np.int16).tobytes()
        silent = np.array([1] * 1024, dtype=np.int16).tobytes()

        # Engage with both audio and video
        tracker.update_audio(loud)
        tracker.update_video(face_detected=True)

        # Audio goes silent past threshold
        time.sleep(0.02)
        tracker.update_audio(silent)

        # Video still active -- should stay engaged
        assert tracker.state == EngagementState.ENGAGED

    def test_seconds_since_speech(self):
        tracker = EngagementTracker(audio_rms_threshold=100.0)
        assert tracker.seconds_since_speech is None

        loud = np.array([5000] * 1024, dtype=np.int16).tobytes()
        tracker.update_audio(loud)
        assert tracker.seconds_since_speech is not None
        assert tracker.seconds_since_speech < 1.0

    def test_seconds_since_face(self):
        tracker = EngagementTracker()
        assert tracker.seconds_since_face is None

        tracker.update_video(face_detected=True)
        assert tracker.seconds_since_face is not None
        assert tracker.seconds_since_face < 1.0

    def test_empty_audio_data(self):
        tracker = EngagementTracker()
        tracker.update_audio(b"")
        assert tracker.state == EngagementState.UNKNOWN
