import time
from dataclasses import dataclass


@dataclass
class ProgressPrediction:
    current_progress: int
    predicted_completion_time: float | None
    estimated_total_duration: float | None
    confidence: float  # 0.0 to 1.0
    smoothed_progress: int  # Smoothed progress value


class ProgressPredictor:
    """Predicts and smooths progress updates for better UX"""

    def __init__(self):
        self._agent_histories: dict[str, list[tuple[float, int]]] = {}
        self._demo_baselines: dict[str, float] = {
            "online": 45.0,  # seconds
            "offline": 25.0,  # seconds
            "continuous": 120.0,  # seconds
        }
        self._smoothing_factor = 0.3  # For exponential smoothing

    def update_progress(
        self, agent_id: str, progress: int, demo_type: str
    ) -> ProgressPrediction:
        """Update progress and return prediction"""
        now = time.time()

        # Initialize history if needed
        if agent_id not in self._agent_histories:
            self._agent_histories[agent_id] = []

        history = self._agent_histories[agent_id]
        history.append((now, progress))

        # Keep only recent history (last 10 points)
        if len(history) > 10:
            history.pop(0)

        # Calculate smoothed progress
        smoothed_progress = self._calculate_smoothed_progress(agent_id, progress)

        # Calculate prediction
        prediction = self._calculate_prediction(history, demo_type, smoothed_progress)
        prediction.smoothed_progress = smoothed_progress

        return prediction

    def _calculate_smoothed_progress(self, agent_id: str, current_progress: int) -> int:
        """Calculate exponentially smoothed progress"""
        history = self._agent_histories.get(agent_id, [])

        if not history:
            return current_progress

        # Get previous smoothed value
        prev_smoothed = history[-1][1] if len(history) > 0 else current_progress

        # Apply exponential smoothing
        smoothed = int(
            prev_smoothed + self._smoothing_factor * (current_progress - prev_smoothed)
        )

        return max(0, min(100, smoothed))  # Clamp to 0-100

    def _calculate_prediction(
        self, history: list[tuple[float, int]], demo_type: str, current_progress: int
    ) -> ProgressPrediction:
        """Calculate progress prediction based on history"""
        if len(history) < 2:
            baseline = self._demo_baselines.get(demo_type, 60.0)
            remaining_time = baseline * (100 - current_progress) / 100
            return ProgressPrediction(
                current_progress=current_progress,
                predicted_completion_time=time.time() + remaining_time,
                estimated_total_duration=baseline,
                confidence=0.3,
                smoothed_progress=current_progress,
            )

        # Calculate velocity (progress per second)
        time_diff = history[-1][0] - history[0][0]
        progress_diff = history[-1][1] - history[0][1]

        if time_diff > 0 and progress_diff > 0:
            velocity = progress_diff / time_diff  # progress per second
            remaining_progress = 100 - current_progress
            estimated_remaining_time = remaining_progress / velocity

            confidence = min(
                len(history) / 10.0, 0.9
            )  # More history = higher confidence

            return ProgressPrediction(
                current_progress=current_progress,
                predicted_completion_time=time.time() + estimated_remaining_time,
                estimated_total_duration=time_diff + estimated_remaining_time,
                confidence=confidence,
                smoothed_progress=current_progress,
            )

        # Fallback to baseline
        baseline = self._demo_baselines.get(demo_type, 60.0)
        return ProgressPrediction(
            current_progress=current_progress,
            predicted_completion_time=time.time()
            + baseline * (100 - current_progress) / 100,
            estimated_total_duration=baseline,
            confidence=0.2,
            smoothed_progress=current_progress,
        )

    def get_estimated_completion_time(
        self, agent_id: str, demo_type: str
    ) -> str | None:
        """Get estimated completion time as formatted string"""
        prediction = self.update_progress(
            agent_id, 0, demo_type
        )  # Get current prediction

        if prediction.predicted_completion_time:
            remaining_seconds = prediction.predicted_completion_time - time.time()
            if remaining_seconds > 0:
                minutes = int(remaining_seconds // 60)
                seconds = int(remaining_seconds % 60)
                if minutes > 0:
                    return f"{minutes}m {seconds}s"
                else:
                    return f"{seconds}s"

        return None


# Global predictor instance
progress_predictor = ProgressPredictor()
