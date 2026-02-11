// Player types
export interface PlayerSummary {
  id: number;
  full_name: string;
  team: string | null;
  position: string | null;
  age: number | null;
}

export interface BattingSeason {
  id: number;
  season: number;
  pa: number | null;
  avg: number | null;
  obp: number | null;
  slg: number | null;
  hr: number | null;
  rbi: number | null;
  r: number | null;
  sb: number | null;
  woba: number | null;
  xwoba: number | null;
  wrc_plus: number | null;
  iso: number | null;
  babip: number | null;
  k_pct: number | null;
  bb_pct: number | null;
  barrel_pct: number | null;
  hard_hit_pct: number | null;
  avg_exit_velocity: number | null;
  sprint_speed: number | null;
  war: number | null;
}

export interface PitchingSeason {
  id: number;
  season: number;
  ip: number | null;
  era: number | null;
  whip: number | null;
  fip: number | null;
  xfip: number | null;
  siera: number | null;
  k_pct: number | null;
  bb_pct: number | null;
  k_bb_pct: number | null;
  swstr_pct: number | null;
  csw_pct: number | null;
  war: number | null;
  so: number | null;
  w: number | null;
  sv: number | null;
  stuff_plus: number | null;
}

export interface Projection {
  id: number;
  run_date: string;
  model_version: string;
  sleeper_score: number | null;
  bust_score: number | null;
  regression_direction: number | null;
  regression_magnitude: number | null;
  consistency_score: number | null;
  improvement_score: number | null;
  ai_value_score: number | null;
  confidence: number | null;
  shap_explanations: Record<string, unknown> | null;
  stat_consistency_breakdown: Record<string, unknown> | null;
  stat_improvement_breakdown: Record<string, unknown> | null;
  auction_value: number | null;
  dynasty_value: number | null;
  surplus_value: number | null;
  marcel_projections: Record<string, number> | null;
}

export interface PlayerDetail extends PlayerSummary {
  birth_date: string | null;
  mlb_debut_date: string | null;
  status: string | null;
  prospect_rank: number | null;
  batting_seasons: BattingSeason[];
  pitching_seasons: PitchingSeason[];
  projection: Projection | null;
}

export interface PlayerListResponse {
  players: PlayerSummary[];
  total: number;
  page: number;
  per_page: number;
}

// Rankings
export interface RankedPlayer {
  player_id: number;
  full_name: string;
  team: string | null;
  position: string | null;
  age: number | null;
  ai_value_score: number | null;
  sleeper_score: number | null;
  bust_score: number | null;
  consistency_score: number | null;
  improvement_score: number | null;
  auction_value: number | null;
  dynasty_value: number | null;
  surplus_value: number | null;
}

export interface RankingsResponse {
  players: RankedPlayer[];
  total: number;
}

// Scouting Reports
export interface ScoutingReport {
  id: number;
  player_id: number;
  report_type: string;
  content: string;
  model_scores_snapshot: Record<string, number> | null;
  llm_model_version: string | null;
  generated_at: string;
  stale: boolean;
}

// League Settings
export interface LeagueSettings {
  id: number;
  name: string;
  scoring_type: string;
  league_format: string;
  roster_slots: Record<string, number> | null;
  stat_categories: string[] | null;
  auction_budget: number;
  roster_size: number;
  keeper_rules: Record<string, unknown> | null;
}
