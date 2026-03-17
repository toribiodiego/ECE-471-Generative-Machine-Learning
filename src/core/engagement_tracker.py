"""Engagement tracking for real-time user interaction.

Monitors audio activity (speech detection via RMS energy) and video
activity (face/person presence) to determine if a user is engaged
or disengaged. Emits state changes that the media loop can use to
trigger re-engagement strategies.
"""

import time
from enum import Enum
from typing import Callable, Optional

import numpy as np


class EngagementState(Enum):
    """Possible engagement states."""
    ENGAGED = "engaged"
    DISENGAGED = "disengaged"
    UNKNOWN = "unknown"


class EngagementTracker:
    """Tracks user engagement from audio and video signals.

    Monitors two signals:
    - Audio RMS energy (is the user speaking?)
    - Face presence in video (is someone in frame?)

    When both signals are absent for longer than their respective
    thresholds, the state transitions to DISENGAGED. When either
    signal reappears, the state transitions back to ENGAGED.

    Attributes:
        state: Current engagement state.
        on_state_change: Optional callback fired on state transitions.
    """

    def __init__(
        self,
        silence_threshold_sec: float = 10.0,
        absence_threshold_sec: float = 15.0,
        audio_rms_threshold: float = 500.0,
        on_state_change: Optional[Callable] = None,
    ):
        """Initialize the engagement tracker.

        Args:
            silence_threshold_sec: Seconds of silence before marking
                audio as inactive.
            absence_threshold_sec: Seconds without a face before marking
                video as inactive.
            audio_rms_threshold: RMS energy level above which audio is
                considered speech (not silence/noise).
            on_state_change: Optional callback called with
                (old_state, new_state, timestamp) on transitions.
        """
        self.silence_threshold_sec = silence_threshold_sec
        self.absence_threshold_sec = absence_threshold_sec
        self.audio_rms_threshold = audio_rms_threshold
        self.on_state_change = on_state_change

        self.state = EngagementState.UNKNOWN
        self._last_speech_time: Optional[float] = None
        self._last_face_time: Optional[float] = None
        self._audio_active = False
        self._video_active = False

    def update_audio(self, audio_data: bytes) -> None:
        """Update engagement state with new audio data.

        Computes RMS energy from raw PCM audio bytes and updates
        the last-speech timestamp if energy exceeds threshold.

        Args:
            audio_data: Raw PCM audio bytes (16-bit signed integers).
        """
        samples = np.frombuffer(audio_data, dtype=np.int16)
        if len(samples) == 0:
            return

        rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2))
        now = time.monotonic()

        if rms > self.audio_rms_threshold:
            self._last_speech_time = now
            self._audio_active = True
        else:
            if self._last_speech_time is not None:
                elapsed = now - self._last_speech_time
                self._audio_active = elapsed < self.silence_threshold_sec

        self._evaluate_state()

    def update_video(self, face_detected: bool) -> None:
        """Update engagement state with face detection result.

        Args:
            face_detected: Whether a face was detected in the current frame.
        """
        now = time.monotonic()

        if face_detected:
            self._last_face_time = now
            self._video_active = True
        else:
            if self._last_face_time is not None:
                elapsed = now - self._last_face_time
                self._video_active = elapsed < self.absence_threshold_sec

        self._evaluate_state()

    def _evaluate_state(self) -> None:
        """Evaluate engagement based on current audio and video activity.

        Transitions to DISENGAGED when both audio and video are inactive.
        Transitions to ENGAGED when either becomes active.
        """
        if self._audio_active or self._video_active:
            new_state = EngagementState.ENGAGED
        elif self._last_speech_time is not None or self._last_face_time is not None:
            new_state = EngagementState.DISENGAGED
        else:
            new_state = EngagementState.UNKNOWN

        if new_state != self.state:
            old_state = self.state
            self.state = new_state
            if self.on_state_change and old_state != EngagementState.UNKNOWN:
                self.on_state_change(old_state, new_state, time.monotonic())

    @property
    def seconds_since_speech(self) -> Optional[float]:
        """Seconds elapsed since last detected speech, or None."""
        if self._last_speech_time is None:
            return None
        return time.monotonic() - self._last_speech_time

    @property
    def seconds_since_face(self) -> Optional[float]:
        """Seconds elapsed since last detected face, or None."""
        if self._last_face_time is None:
            return None
        return time.monotonic() - self._last_face_time
