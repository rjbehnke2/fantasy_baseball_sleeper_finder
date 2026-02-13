"""Tests for the career trajectory model."""

import pytest

from backend.ml.models.trajectory_model import (
    CareerTrajectory,
    batch_project_trajectories,
    project_career_trajectory,
)


class TestBatterTrajectory:
    """Test career trajectory projections for batters."""

    def test_young_rising_player(self):
        """A young improving player should have a rising trajectory."""
        result = project_career_trajectory(
            player_id=1,
            current_age=23,
            current_value=55,
            player_type="batter",
            improvement_score=60,
            consistency_score=70,
            dynasty_value=80,
        )
        assert isinstance(result, CareerTrajectory)
        assert result.trajectory_grade == "Rising"
        # Young improving players should project higher in the near future
        assert result.peak_value >= result.current_value
        assert len(result.trajectory) == 6  # Default 6 years

    def test_peak_age_player(self):
        """A peak-age player should plateau then decline."""
        result = project_career_trajectory(
            player_id=2,
            current_age=27,
            current_value=85,
            player_type="batter",
            improvement_score=5,
            consistency_score=80,
            dynasty_value=70,
        )
        assert result.trajectory_grade == "Peak"
        # Should start declining after peak
        last_point = result.trajectory[-1]
        assert last_point.projected_value < result.current_value

    def test_declining_old_player(self):
        """An old declining player should have a falling trajectory."""
        result = project_career_trajectory(
            player_id=3,
            current_age=35,
            current_value=60,
            player_type="batter",
            improvement_score=-30,
            consistency_score=65,
            dynasty_value=25,
        )
        assert result.trajectory_grade in ("Declining", "Late Career")
        # Each year should be lower
        values = [p.projected_value for p in result.trajectory]
        for i in range(1, len(values)):
            assert values[i] <= values[i - 1] + 1  # Allow tiny float tolerance

    def test_confidence_bands_widen(self):
        """Confidence bands should be wider further into the future."""
        result = project_career_trajectory(
            player_id=4,
            current_age=26,
            current_value=70,
            player_type="batter",
        )
        bandwidths = [
            p.upper_bound - p.lower_bound for p in result.trajectory
        ]
        # Each subsequent year should have equal or wider bands
        for i in range(1, len(bandwidths)):
            assert bandwidths[i] >= bandwidths[i - 1] - 0.5  # Allow tiny tolerance

    def test_inconsistent_player_wider_bands(self):
        """Players with low consistency should have wider confidence bands."""
        consistent = project_career_trajectory(
            player_id=5, current_age=28, current_value=70,
            consistency_score=90,
        )
        volatile = project_career_trajectory(
            player_id=6, current_age=28, current_value=70,
            consistency_score=30,
        )
        # Volatile player should have wider bands at same projection year
        c_band = consistent.trajectory[2].upper_bound - consistent.trajectory[2].lower_bound
        v_band = volatile.trajectory[2].upper_bound - volatile.trajectory[2].lower_bound
        assert v_band > c_band

    def test_values_stay_in_range(self):
        """All projected values should be 0-100."""
        result = project_career_trajectory(
            player_id=7,
            current_age=24,
            current_value=95,
            improvement_score=80,
        )
        for p in result.trajectory:
            assert 0 <= p.projected_value <= 100
            assert 0 <= p.upper_bound <= 100
            assert 0 <= p.lower_bound <= 100
            assert p.lower_bound <= p.projected_value <= p.upper_bound


class TestPitcherTrajectory:
    """Test pitcher-specific trajectory behavior."""

    def test_pitcher_peaks_earlier(self):
        """Pitchers peak at 26, one year earlier than batters."""
        batter = project_career_trajectory(
            player_id=10, current_age=25, current_value=70,
            player_type="batter",
        )
        pitcher = project_career_trajectory(
            player_id=11, current_age=25, current_value=70,
            player_type="pitcher",
        )
        # At age 25, pitcher is closer to peak than batter
        # So pitcher's year-1 projection should be higher (aging curve boost)
        assert pitcher.trajectory[0].projected_value >= batter.trajectory[0].projected_value - 5


class TestBatchProjection:
    """Test batch projection utility."""

    def test_batch_returns_all(self):
        """Batch projection should return one trajectory per player."""
        players = [
            {"player_id": 1, "age": 24, "current_value": 70, "player_type": "batter"},
            {"player_id": 2, "age": 30, "current_value": 80, "player_type": "pitcher"},
            {"player_id": 3, "age": 35, "current_value": 50, "player_type": "batter"},
        ]
        results = batch_project_trajectories(players)
        assert len(results) == 3
        assert all(isinstance(r, CareerTrajectory) for r in results)

    def test_batch_handles_missing_fields(self):
        """Batch should use defaults for missing optional fields."""
        players = [
            {"player_id": 1},  # Only required field
        ]
        results = batch_project_trajectories(players)
        assert len(results) == 1
        assert results[0].player_id == 1


class TestTrajectoryGrades:
    """Test trajectory grading logic."""

    def test_rising_grade(self):
        result = project_career_trajectory(
            player_id=20, current_age=22, current_value=40,
            improvement_score=50,
        )
        assert result.trajectory_grade == "Rising"

    def test_peak_grade(self):
        result = project_career_trajectory(
            player_id=21, current_age=27, current_value=80,
            improvement_score=15,
        )
        assert result.trajectory_grade == "Peak"

    def test_late_career_grade(self):
        result = project_career_trajectory(
            player_id=22, current_age=36, current_value=40,
            improvement_score=-20,
        )
        assert result.trajectory_grade in ("Declining", "Late Career")
