"""Tests for Marcel baseline projection system."""

import pytest

from backend.ml.models.marcel_baseline import project_batter, project_pitcher


class TestMarcelBatter:
    def test_single_season_projects_with_regression(self):
        """A single season should regress heavily toward league average."""
        seasons = [{"pa": 600, "avg": 0.300, "hr": 30, "rbi": 100, "r": 90, "sb": 15,
                     "obp": 0.370, "slg": 0.520, "iso": 0.220, "woba": 0.370,
                     "babip": 0.310, "k_pct": 0.200, "bb_pct": 0.100,
                     "barrel_pct": 0.120, "hard_hit_pct": 0.450}]
        proj = project_batter(seasons, age=27)

        assert proj is not None
        # Should regress toward league average (.248)
        assert proj["avg"] < 0.300
        assert proj["avg"] > 0.248  # But not all the way
        assert proj["pa"] > 0

    def test_three_seasons_weights_recent_more(self):
        """Most recent season should have highest weight."""
        # Player improving: .240 -> .260 -> .280
        seasons = [
            {"pa": 600, "avg": 0.280, "obp": 0.350, "slg": 0.450, "woba": 0.340,
             "iso": 0.170, "babip": 0.300, "k_pct": 0.200, "bb_pct": 0.090,
             "barrel_pct": 0.080, "hard_hit_pct": 0.400, "hr": 25, "rbi": 80, "r": 85, "sb": 10},
            {"pa": 600, "avg": 0.260, "obp": 0.330, "slg": 0.420, "woba": 0.320,
             "iso": 0.160, "babip": 0.290, "k_pct": 0.210, "bb_pct": 0.085,
             "barrel_pct": 0.070, "hard_hit_pct": 0.380, "hr": 20, "rbi": 70, "r": 75, "sb": 8},
            {"pa": 600, "avg": 0.240, "obp": 0.310, "slg": 0.390, "woba": 0.300,
             "iso": 0.150, "babip": 0.280, "k_pct": 0.220, "bb_pct": 0.080,
             "barrel_pct": 0.060, "hard_hit_pct": 0.360, "hr": 15, "rbi": 60, "r": 65, "sb": 5},
        ]
        proj = project_batter(seasons, age=27)

        # Weighted avg should be closer to .280 than to .240
        assert proj["avg"] > 0.255

    def test_age_adjustment_pre_peak(self):
        """Young player should get a slight boost."""
        seasons = [{"pa": 500, "avg": 0.260, "obp": 0.330, "slg": 0.420, "woba": 0.320,
                     "iso": 0.160, "babip": 0.290, "k_pct": 0.200, "bb_pct": 0.085,
                     "barrel_pct": 0.070, "hard_hit_pct": 0.380, "hr": 20, "rbi": 70, "r": 75, "sb": 10}]
        proj_young = project_batter(seasons, age=24)
        proj_peak = project_batter(seasons, age=27)
        proj_old = project_batter(seasons, age=33)

        # Young player should project higher than peak, peak higher than old
        assert proj_young["avg"] > proj_peak["avg"]
        assert proj_peak["avg"] > proj_old["avg"]

    def test_empty_seasons_returns_empty(self):
        """No seasons = no projection."""
        assert project_batter([], age=27) == {}

    def test_playing_time_declines_with_age(self):
        """Older players should project fewer PA."""
        seasons = [{"pa": 600, "avg": 0.260, "hr": 20, "rbi": 70, "r": 75, "sb": 10}]
        proj_young = project_batter(seasons, age=25)
        proj_old = project_batter(seasons, age=35)
        assert proj_young["pa"] > proj_old["pa"]


class TestMarcelPitcher:
    def test_single_season_pitcher(self):
        """Basic pitcher projection with regression."""
        seasons = [{"ip": 180, "era": 3.00, "whip": 1.10, "fip": 3.20,
                     "k_pct": 0.280, "bb_pct": 0.060, "k_bb_pct": 0.220,
                     "babip": 0.280, "barrel_pct_against": 0.050,
                     "hard_hit_pct_against": 0.330, "hr_fb_pct": 0.100,
                     "so": 180, "w": 12, "g": 32, "gs": 32, "sv": 0}]
        proj = project_pitcher(seasons, age=26)

        assert proj is not None
        # ERA should regress toward league average (4.15)
        assert proj["era"] > 3.00
        assert proj["era"] < 4.15
        assert proj["ip"] > 0
        assert proj["so"] > 0

    def test_aging_makes_era_worse(self):
        """Older pitchers should project higher ERA."""
        seasons = [{"ip": 180, "era": 3.50, "whip": 1.20, "fip": 3.40,
                     "k_pct": 0.250, "bb_pct": 0.070, "k_bb_pct": 0.180,
                     "babip": 0.290, "barrel_pct_against": 0.060,
                     "hard_hit_pct_against": 0.350, "hr_fb_pct": 0.120,
                     "so": 150, "w": 10, "g": 30, "gs": 30, "sv": 0}]
        proj_young = project_pitcher(seasons, age=24)
        proj_old = project_pitcher(seasons, age=34)
        assert proj_young["era"] < proj_old["era"]

    def test_reliever_saves_projection(self):
        """Closer should project saves."""
        seasons = [{"ip": 65, "era": 2.50, "whip": 1.00, "fip": 2.80,
                     "k_pct": 0.300, "bb_pct": 0.070, "k_bb_pct": 0.230,
                     "babip": 0.270, "barrel_pct_against": 0.040,
                     "hard_hit_pct_against": 0.300, "hr_fb_pct": 0.090,
                     "so": 75, "w": 4, "g": 65, "gs": 0, "sv": 35}]
        proj = project_pitcher(seasons, age=28)
        assert proj.get("sv", 0) > 0
