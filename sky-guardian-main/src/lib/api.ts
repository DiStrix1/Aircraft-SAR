/**
 * Aircraft SAR — API client v3
 * ==============================
 * Real fetch() calls to the FastAPI backend.
 * TypeScript interfaces match the backend's Pydantic models exactly.
 */

// ── Types ──────────────────────────────────────────────────────────────────

export interface AircraftType {
    id: string;
    name: string;
    glide_ratio: number;
    cruise_speed: number;
    category?: string;
    max_altitude_ft?: number;
    max_range_km?: number;
}

export interface Preset {
    id: string;
    name: string;
    aircraft_type: string;
    latitude: number;
    longitude: number;
    heading: number;
    airspeed: number;
    altitude: number;
    time_since_contact: number;
    wind_speed: number;
    wind_direction: number;
    actual_lat?: number;
    actual_lon?: number;
}

export interface SimulationResult {
    centroid: { lat: number; lon: number };
    zones: {
        high: { points: [number, number][]; percentage: number };
        medium: { points: [number, number][]; percentage: number };
        low: { points: [number, number][]; percentage: number };
    };
    impact_points: [number, number][];
    glide_range_km: number;
    search_area_km2: number;
    classification: string;
    severity: string;
    recommended_pattern: string;
    accuracy?: {
        centroid_error_km: number;
        within_50km: boolean;
        within_50km_pct: number;
    };
}

export interface WeatherLayer {
    altitude_ft: number;
    wind_speed_kts: number;
    wind_direction_deg: number;
}

export interface WeatherResult {
    source: string;
    valid_time: string;
    layers: WeatherLayer[];
}

export interface SearchPatternResult {
    pattern: string;
    waypoints: [number, number][];
    center: [number, number];
}

export interface SensitivityEntry {
    parameter: string;
    delta: number;
    centroid_shift_km: number;
    mean_radius_change_pct: number;
}

// ── API base ───────────────────────────────────────────────────────────────

const API_BASE = "/api";

// ── Caching ───────────────────────────────────────────────────────────────

let cachedAircraft: AircraftType[] | null = null;
let cachedPresets: Preset[] | null = null;

// ── Aircraft & Presets ────────────────────────────────────────────────────

export async function fetchAircraftTypes(): Promise<AircraftType[]> {
    if (cachedAircraft) return cachedAircraft;
    const res = await fetch(`${API_BASE}/aircraft`);
    if (!res.ok) throw new Error(`Failed to fetch aircraft: ${res.status}`);
    cachedAircraft = await res.json();
    return cachedAircraft!;
}

export async function fetchPresets(): Promise<Preset[]> {
    if (cachedPresets) return cachedPresets;
    const res = await fetch(`${API_BASE}/presets`);
    if (!res.ok) throw new Error(`Failed to fetch presets: ${res.status}`);
    cachedPresets = await res.json();
    return cachedPresets!;
}

// ── Simulate ───────────────────────────────────────────────────────────────

export async function simulateSearch(params: {
    aircraft_type: string;
    latitude: number;
    longitude: number;
    heading: number;
    airspeed: number;
    altitude: number;
    time_since_contact: number;
    wind_speed: number;
    wind_direction: number;
    iterations?: number;
    heading_spread?: number;
    scatter_min?: number;
    scatter_max?: number;
    descent_rate_override?: number;
    weight_glide?: number;
    weight_spiral?: number;
    weight_dive?: number;
    weight_breakup?: number;
    weight_ditching?: number;
    preset_id?: string;
}): Promise<SimulationResult> {
    const res = await fetch(`${API_BASE}/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Simulation failed: ${res.status}`);
    }
    return res.json();
}

// ── Weather ────────────────────────────────────────────────────────────────

export async function fetchWeatherData(
    lat: number,
    lon: number,
    datetimeUtc?: string,
    surfaceWindSpeed: number = 0,
    surfaceWindDir: number = 0,
): Promise<WeatherResult> {
    const params = new URLSearchParams({
        lat: String(lat),
        lon: String(lon),
        surface_wind_speed: String(surfaceWindSpeed),
        surface_wind_dir: String(surfaceWindDir),
    });
    if (datetimeUtc) params.set("datetime_utc", datetimeUtc);
    const res = await fetch(`${API_BASE}/weather?${params}`);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Weather fetch failed: ${res.status}`);
    }
    return res.json();
}

// ── Search Pattern ─────────────────────────────────────────────────────────

export async function fetchSearchPattern(
    centroidLat: number,
    centroidLon: number,
    areaKm2: number,
    heading: number = 0,
    pattern?: string,
): Promise<SearchPatternResult> {
    const params = new URLSearchParams({
        centroid_lat: String(centroidLat),
        centroid_lon: String(centroidLon),
        area_km2: String(areaKm2),
        heading: String(heading),
    });
    if (pattern) params.set("pattern", pattern);
    const res = await fetch(`${API_BASE}/search-pattern?${params}`);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Search pattern failed: ${res.status}`);
    }
    return res.json();
}

// ── Sensitivity ────────────────────────────────────────────────────────────

export async function fetchSensitivity(params: {
    aircraft_type: string;
    latitude: number;
    longitude: number;
    heading: number;
    airspeed: number;
    altitude: number;
    time_since_contact: number;
    wind_speed: number;
    wind_direction: number;
    iterations?: number;
}): Promise<SensitivityEntry[]> {
    const res = await fetch(`${API_BASE}/sensitivity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Sensitivity failed: ${res.status}`);
    }
    return res.json();
}
