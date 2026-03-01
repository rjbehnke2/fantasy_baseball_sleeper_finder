import type {
  PlayerDetail,
  PlayerListResponse,
  RankingsResponse,
  RankedPlayer,
  ScoutingReport,
  LeagueSettings,
} from "./types";

const API_BASE = "/api/v1";

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

/**
 * Transform the backend rankings response (nested {rank, player: {...}})
 * into the flat RankedPlayer[] the frontend components expect.
 */
function normalizeRankings(apiResponse: {
  rankings?: { rank: number; player: Record<string, unknown> }[];
  players?: RankedPlayer[];
  total: number;
}): RankingsResponse {
  // If already in the expected format, return as-is
  if (apiResponse.players) {
    return apiResponse as RankingsResponse;
  }

  const players: RankedPlayer[] = (apiResponse.rankings || []).map((entry) => {
    const p = entry.player;
    return {
      player_id: p.id as number,
      full_name: p.full_name as string,
      team: (p.team as string) ?? null,
      position: (p.position as string) ?? null,
      age: (p.age as number) ?? null,
      ai_value_score: (p.ai_value_score as number) ?? null,
      sleeper_score: (p.sleeper_score as number) ?? null,
      bust_score: (p.bust_score as number) ?? null,
      consistency_score: (p.consistency_score as number) ?? null,
      improvement_score: (p.improvement_score as number) ?? null,
      auction_value: (p.auction_value as number) ?? null,
      dynasty_value: (p.dynasty_value as number) ?? null,
      surplus_value: (p.surplus_value as number) ?? null,
    };
  });

  return { players, total: apiResponse.total };
}

// Players
export async function getPlayers(params: {
  page?: number;
  per_page?: number;
  search?: string;
  position?: string;
  team?: string;
  sort_by?: string;
  sort_order?: string;
}): Promise<PlayerListResponse> {
  const query = new URLSearchParams();
  if (params.page) query.set("page", String(params.page));
  if (params.per_page) query.set("per_page", String(params.per_page));
  if (params.search) query.set("search", params.search);
  if (params.position) query.set("position", params.position);
  if (params.team) query.set("team", params.team);
  if (params.sort_by) query.set("sort_by", params.sort_by);
  if (params.sort_order) query.set("sort_order", params.sort_order);
  return fetchJSON(`${API_BASE}/players?${query}`);
}

export async function getPlayer(playerId: number): Promise<PlayerDetail> {
  return fetchJSON(`${API_BASE}/players/${playerId}`);
}

// Rankings
export async function getRankings(params?: {
  limit?: number;
}): Promise<RankingsResponse> {
  const query = new URLSearchParams();
  if (params?.limit) query.set("limit", String(params.limit));
  const raw = await fetchJSON<Record<string, unknown>>(`${API_BASE}/rankings?${query}`);
  return normalizeRankings(raw as Parameters<typeof normalizeRankings>[0]);
}

export async function getSleepers(limit = 50): Promise<RankingsResponse> {
  const raw = await fetchJSON<Record<string, unknown>>(`${API_BASE}/rankings/sleepers?limit=${limit}`);
  return normalizeRankings(raw as Parameters<typeof normalizeRankings>[0]);
}

export async function getBusts(limit = 50): Promise<RankingsResponse> {
  const raw = await fetchJSON<Record<string, unknown>>(`${API_BASE}/rankings/busts?limit=${limit}`);
  return normalizeRankings(raw as Parameters<typeof normalizeRankings>[0]);
}

export async function getDynastyRankings(limit = 50): Promise<RankingsResponse> {
  const raw = await fetchJSON<Record<string, unknown>>(`${API_BASE}/rankings/dynasty?limit=${limit}`);
  return normalizeRankings(raw as Parameters<typeof normalizeRankings>[0]);
}

// Trajectory
export async function getPlayerTrajectory(playerId: number): Promise<{
  player_id: number;
  current_value: number;
  peak_season: number;
  peak_value: number;
  career_value_remaining: number;
  trajectory_grade: string;
  trajectory: {
    season: number;
    projected_value: number;
    upper_bound: number;
    lower_bound: number;
    age: number;
  }[];
}> {
  return fetchJSON(`${API_BASE}/players/${playerId}/trajectory`);
}

// Scouting Reports
export async function getScoutingReport(
  playerId: number,
  reportType = "full"
): Promise<ScoutingReport> {
  return fetchJSON(
    `${API_BASE}/players/${playerId}/scouting-report?report_type=${reportType}`
  );
}

// League Settings
export async function getLeagueSettings(id: number): Promise<LeagueSettings> {
  return fetchJSON(`${API_BASE}/league-settings/${id}`);
}

export async function createLeagueSettings(
  settings: Omit<LeagueSettings, "id">
): Promise<LeagueSettings> {
  const res = await fetch(`${API_BASE}/league-settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
