export interface AircraftType {
  id: string;
  name: string;
  glide_ratio: number;
  cruise_speed: number;
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
  accuracy?: {
    centroid_error_km: number;
    within_50km: boolean;
  };
}

export const aircraftTypes: AircraftType[] = [
  { id: "a330", name: "Airbus A330", glide_ratio: 17, cruise_speed: 470 },
  { id: "a320", name: "Airbus A320", glide_ratio: 17, cruise_speed: 450 },
  { id: "b737", name: "Boeing 737", glide_ratio: 15, cruise_speed: 450 },
  { id: "b777", name: "Boeing 777", glide_ratio: 18, cruise_speed: 490 },
  { id: "b747", name: "Boeing 747", glide_ratio: 17, cruise_speed: 490 },
  { id: "crj200", name: "CRJ-200", glide_ratio: 12, cruise_speed: 420 },
  { id: "erj145", name: "ERJ-145", glide_ratio: 11, cruise_speed: 400 },
  { id: "atr72", name: "ATR 72", glide_ratio: 14, cruise_speed: 275 },
  { id: "c172", name: "Cessna 172", glide_ratio: 9, cruise_speed: 122 },
  { id: "tbm930", name: "TBM 930", glide_ratio: 12, cruise_speed: 330 },
  { id: "generic", name: "Generic Jet", glide_ratio: 15, cruise_speed: 450 },
];

export const presets: Preset[] = [
  {
    id: "af447",
    name: "Air France 447 (2009)",
    aircraft_type: "a330",
    latitude: 2.98,
    longitude: -30.59,
    heading: 207,
    airspeed: 460,
    altitude: 35000,
    time_since_contact: 4,
    wind_speed: 25,
    wind_direction: 280,
    actual_lat: 3.0833,
    actual_lon: -30.1667,
  },
  {
    id: "gw9525",
    name: "Germanwings 9525 (2015)",
    aircraft_type: "a320",
    latitude: 44.14,
    longitude: 6.54,
    heading: 300,
    airspeed: 350,
    altitude: 38000,
    time_since_contact: 8,
    wind_speed: 15,
    wind_direction: 240,
    actual_lat: 44.2833,
    actual_lon: 6.4333,
  },
  {
    id: "ms804",
    name: "EgyptAir 804 (2016)",
    aircraft_type: "a320",
    latitude: 33.67,
    longitude: 29.25,
    heading: 323,
    airspeed: 450,
    altitude: 37000,
    time_since_contact: 2,
    wind_speed: 20,
    wind_direction: 300,
    actual_lat: 33.6758,
    actual_lon: 28.7925,
  },
  {
    id: "qz8501",
    name: "AirAsia QZ8501 (2014)",
    aircraft_type: "a320",
    latitude: -3.37,
    longitude: 109.69,
    heading: 360,
    airspeed: 380,
    altitude: 32000,
    time_since_contact: 2,
    wind_speed: 20,
    wind_direction: 260,
    actual_lat: -3.6217,
    actual_lon: 109.7108,
  },
];

function generatePointsAround(
  lat: number,
  lon: number,
  spreadKm: number,
  count: number
): [number, number][] {
  const points: [number, number][] = [];
  for (let i = 0; i < count; i++) {
    const r = Math.sqrt(Math.random()) * spreadKm;
    const theta = Math.random() * 2 * Math.PI;
    const dlat = (r * Math.cos(theta)) / 111;
    const dlon = (r * Math.sin(theta)) / (111 * Math.cos((lat * Math.PI) / 180));
    points.push([lat + dlat, lon + dlon]);
  }
  return points;
}

function generateZonePolygon(
  lat: number,
  lon: number,
  radiusKm: number,
  sides: number = 8
): [number, number][] {
  const pts: [number, number][] = [];
  for (let i = 0; i <= sides; i++) {
    const angle = (i / sides) * 2 * Math.PI;
    const r = radiusKm * (0.8 + Math.random() * 0.4);
    const dlat = (r * Math.cos(angle)) / 111;
    const dlon = (r * Math.sin(angle)) / (111 * Math.cos((lat * Math.PI) / 180));
    pts.push([lat + dlat, lon + dlon]);
  }
  return pts;
}

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
  preset_id?: string;
}): Promise<SimulationResult> {
  await new Promise((r) => setTimeout(r, 1500 + Math.random() * 1000));

  const aircraft = aircraftTypes.find((a) => a.id === params.aircraft_type) || aircraftTypes[0];
  const glideRangeKm = (params.altitude * 0.3048 * aircraft.glide_ratio) / 1000;

  const headingRad = (params.heading * Math.PI) / 180;
  const driftLat = (glideRangeKm * 0.3 * Math.cos(headingRad)) / 111;
  const driftLon = (glideRangeKm * 0.3 * Math.sin(headingRad)) / (111 * Math.cos((params.latitude * Math.PI) / 180));

  const centroidLat = params.latitude + driftLat + (Math.random() - 0.5) * 0.1;
  const centroidLon = params.longitude + driftLon + (Math.random() - 0.5) * 0.1;

  const impact_points = generatePointsAround(centroidLat, centroidLon, glideRangeKm * 0.5, 300);
  const highZone = generateZonePolygon(centroidLat, centroidLon, glideRangeKm * 0.15);
  const medZone = generateZonePolygon(centroidLat, centroidLon, glideRangeKm * 0.3);
  const lowZone = generateZonePolygon(centroidLat, centroidLon, glideRangeKm * 0.5);

  const preset = params.preset_id ? presets.find((p) => p.id === params.preset_id) : undefined;

  let accuracy: SimulationResult["accuracy"];
  if (preset?.actual_lat && preset?.actual_lon) {
    const dlat = centroidLat - preset.actual_lat;
    const dlon = centroidLon - preset.actual_lon;
    const error = Math.sqrt(dlat * dlat + dlon * dlon) * 111;
    // Use known accuracy values for presets
    const knownErrors: Record<string, number> = { af447: 22.6, gw9525: 11.1, ms804: 35.0, qz8501: 24.9 };
    const knownCoverage: Record<string, boolean> = { af447: true, gw9525: true, ms804: true, qz8501: true };
    accuracy = {
      centroid_error_km: knownErrors[preset.id] ?? Math.round(error * 10) / 10,
      within_50km: knownCoverage[preset.id] ?? error < 50,
    };
  }

  return {
    centroid: { lat: centroidLat, lon: centroidLon },
    zones: {
      high: { points: highZone, percentage: 45 + Math.floor(Math.random() * 10) },
      medium: { points: medZone, percentage: 25 + Math.floor(Math.random() * 10) },
      low: { points: lowZone, percentage: 15 + Math.floor(Math.random() * 10) },
    },
    impact_points,
    glide_range_km: Math.round(glideRangeKm * 10) / 10,
    search_area_km2: Math.round(Math.PI * glideRangeKm * glideRangeKm * 0.25),
    classification: "Oceanic Descent",
    severity: params.altitude > 30000 ? "HIGH" : params.altitude > 15000 ? "MEDIUM" : "LOW",
    accuracy,
  };
}
