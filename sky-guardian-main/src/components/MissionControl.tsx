import { useState, useEffect, useRef, useCallback } from "react";
import L from "leaflet";
import {
  fetchAircraftTypes,
  fetchPresets,
  simulateSearch,
  fetchWeatherData,
  fetchSearchPattern,
  type AircraftType,
  type Preset,
  type SimulationResult,
  type SearchPatternResult,
} from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────

interface HistoryEntry {
  timestamp: string;
  centroid: { lat: number; lon: number };
  classification: string;
  severity: string;
  result: SimulationResult;
  params: typeof DEFAULT_PARAMS;
}

const DEFAULT_PARAMS = {
  aircraft_type: "",
  latitude: 0,
  longitude: 0,
  heading: 0,
  airspeed: 450,
  altitude: 35000,
  time_since_contact: 5,
  wind_speed: 15,
  wind_direction: 270,
  iterations: 3000,
  heading_spread: 15,
  scatter_min: 0.5,
  scatter_max: 1.5,
  descent_rate_override: 0,
  weight_glide: 25,
  weight_spiral: 25,
  weight_dive: 25,
  weight_breakup: 25,
  weight_ditching: 0,
};

// ── Shared sub-components (defined OUTSIDE MissionControl to be stable across renders) ──

/**
 * Number input that allows free-form typing.
 * Keeps a local string while the user types; commits the parsed number on blur.
 * Syncs from parent `value` when it changes externally (e.g. preset load).
 */
const InputField = ({
  label,
  paramKey,
  step,
  value,
  onChange,
}: {
  label: string;
  paramKey: string;
  step?: number;
  value: number;
  onChange: (key: string, val: number) => void;
}) => {
  const [local, setLocal] = useState(String(value));

  // Sync when parent value changes (preset applied, history restored, etc.)
  useEffect(() => {
    setLocal(String(value));
  }, [value]);

  return (
    <div>
      <label className="block text-xs font-mono text-muted-foreground mb-1">{label}</label>
      <input
        type="text"
        inputMode="decimal"
        step={step}
        value={local}
        onChange={(e) => setLocal(e.target.value)}
        onBlur={() => {
          const parsed = parseFloat(local);
          if (!isNaN(parsed)) {
            onChange(paramKey, parsed);
            setLocal(String(parsed));
          } else {
            // Revert to last valid value on invalid input
            setLocal(String(value));
          }
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") (e.target as HTMLInputElement).blur();
        }}
        className="w-full px-3 py-2 rounded-lg text-sm font-mono bg-muted/50 border border-border focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors"
      />
    </div>
  );
};

/**
 * Range slider that commits changes when the drag ends (mouseup/touchend)
 * to avoid flooding setParams during dragging.
 * Shows live value while dragging via local state.
 */
const SliderField = ({
  label,
  paramKey,
  value,
  onChange,
}: {
  label: string;
  paramKey: string;
  value: number;
  onChange: (key: string, val: number) => void;
}) => {
  const [draft, setDraft] = useState(value);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  return (
    <div>
      <div className="flex justify-between text-xs font-mono text-muted-foreground mb-1">
        <span>{label}</span>
        <span>{draft}%</span>
      </div>
      <input
        type="range"
        min={0}
        max={100}
        value={draft}
        onChange={(e) => setDraft(parseInt(e.target.value))}
        onMouseUp={(e) => onChange(paramKey, parseInt((e.target as HTMLInputElement).value))}
        onTouchEnd={(e) => onChange(paramKey, parseInt((e.target as HTMLInputElement).value))}
        className="w-full accent-cyan cursor-pointer"
        style={{ touchAction: "none" }}
      />
    </div>
  );
};

// ── Component ─────────────────────────────────────────────────────────────

const MissionControl = () => {
  const [aircraftTypes, setAircraftTypes] = useState<AircraftType[]>([]);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [params, setParams] = useState(DEFAULT_PARAMS);
  const [selectedPreset, setSelectedPreset] = useState("");
  const [loading, setLoading] = useState(false);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [weatherStatus, setWeatherStatus] = useState<string>("");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showPattern, setShowPattern] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [patternData, setPatternData] = useState<SearchPatternResult | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [activeTab, setActiveTab] = useState<"results" | "history">("results");

  const mapRef = useRef<L.Map | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);
  const patternLayerRef = useRef<L.LayerGroup | null>(null);
  const sectionRef = useRef<HTMLDivElement>(null);

  // ── Data loading ────────────────────────────────────────────────────────
  useEffect(() => {
    fetchAircraftTypes().then((types) => {
      setAircraftTypes(types);
      if (types.length > 0) setParams((p) => ({ ...p, aircraft_type: types[0].id }));
    });
    fetchPresets().then(setPresets);
  }, []);

  // ── Map init ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;
    const map = L.map(mapContainerRef.current, {
      center: [20, 0],
      zoom: 3,
      zoomControl: false,
    });
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: "&copy; <a href=\"https://carto.com\">CARTO</a>",
    }).addTo(map);
    mapRef.current = map;
    layerGroupRef.current = L.layerGroup().addTo(map);
    patternLayerRef.current = L.layerGroup().addTo(map);

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // ── Resize observer ───────────────────────────────────────────────────────
  useEffect(() => {
    const ref = sectionRef.current;
    if (!ref) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) mapRef.current?.invalidateSize(); },
      { threshold: 0.1 }
    );
    obs.observe(ref);
    return () => obs.disconnect();
  }, []);

  // ── Param helpers ─────────────────────────────────────────────────────────
  const updateParam = (key: string, value: number | string) => {
    setParams((p) => ({ ...p, [key]: value }));
  };

  const applyPreset = (presetId: string) => {
    setSelectedPreset(presetId);
    const preset = presets.find((p) => p.id === presetId);
    if (preset) {
      setParams((p) => ({
        ...p,
        aircraft_type: preset.aircraft_type,
        latitude: preset.latitude,
        longitude: preset.longitude,
        heading: preset.heading,
        airspeed: preset.airspeed,
        altitude: preset.altitude,
        time_since_contact: preset.time_since_contact,
        wind_speed: preset.wind_speed,
        wind_direction: preset.wind_direction,
      }));
      mapRef.current?.flyTo([preset.latitude, preset.longitude], 6, { duration: 1.5 });
    }
  };

  // ── Fetch Real Wind ───────────────────────────────────────────────────────
  const fetchRealWind = useCallback(async () => {
    if (!params.latitude || !params.longitude) {
      setWeatherStatus("⚠ Set lat/lon first");
      return;
    }
    setWeatherLoading(true);
    setWeatherStatus("");
    try {
      const data = await fetchWeatherData(
        params.latitude,
        params.longitude,
        undefined,
        params.wind_speed,
        params.wind_direction,
      );
      // Use the lowest layer (surface) for wind inputs
      if (data.layers.length > 0) {
        const surface = data.layers[0];
        setParams((p) => ({
          ...p,
          wind_speed: Math.round(surface.wind_speed_kts * 10) / 10,
          wind_direction: Math.round(surface.wind_direction_deg),
        }));
        setWeatherStatus(`✓ ${data.source}`);
      } else {
        setWeatherStatus("⚠ No layers returned");
      }
    } catch (e: any) {
      setWeatherStatus(`⚠ ${e.message}`);
    } finally {
      setWeatherLoading(false);
    }
  }, [params.latitude, params.longitude, params.wind_speed, params.wind_direction]);

  // ── Draw results on map ───────────────────────────────────────────────────
  const drawResults = useCallback((res: SimulationResult) => {
    const lg = layerGroupRef.current;
    if (!lg) return;
    lg.clearLayers();

    // Probability zones
    L.polygon(res.zones.low.points, { color: "#22c55e", fillOpacity: 0.15, weight: 1 }).addTo(lg);
    L.polygon(res.zones.medium.points, { color: "#f97316", fillOpacity: 0.2, weight: 1 }).addTo(lg);
    L.polygon(res.zones.high.points, { color: "#ef4444", fillOpacity: 0.3, weight: 1 }).addTo(lg);

    // Glide range circle
    L.circle([params.latitude, params.longitude], {
      radius: res.glide_range_km * 1000,
      color: "#00B4D8",
      fillOpacity: 0.05,
      weight: 1,
      dashArray: "8 4",
    }).addTo(lg);

    // Path line to centroid
    L.polyline(
      [[params.latitude, params.longitude], [res.centroid.lat, res.centroid.lon]],
      { color: "#00B4D8", weight: 2, dashArray: "6 4" }
    ).addTo(lg);

    // Impact scatter points
    res.impact_points.slice(0, 100).forEach((pt) => {
      L.circleMarker(pt as [number, number], {
        radius: 2, color: "#00B4D8", fillOpacity: 0.4, weight: 0, fillColor: "#00B4D8",
      }).addTo(lg);
    });

    // LKP marker
    const lkpIcon = L.divIcon({
      html: `<div style="width:12px;height:12px;background:#00B4D8;border:2px solid white;border-radius:50%;box-shadow:0 0 8px #00B4D8"></div>`,
      className: "", iconSize: [12, 12], iconAnchor: [6, 6],
    });
    L.marker([params.latitude, params.longitude], { icon: lkpIcon })
      .bindPopup("Last Known Position").addTo(lg);

    // Centroid marker
    const centIcon = L.divIcon({
      html: `<div style="width:16px;height:16px;background:#FF6B35;border:2px solid white;border-radius:50%;box-shadow:0 0 12px #FF6B35"></div>`,
      className: "", iconSize: [16, 16], iconAnchor: [8, 8],
    });
    L.marker([res.centroid.lat, res.centroid.lon], { icon: centIcon })
      .bindPopup(`Predicted Centroid<br>Pattern: ${res.recommended_pattern}`).addTo(lg);
  }, [params.latitude, params.longitude]);

  // ── Draw search pattern ───────────────────────────────────────────────────
  const drawSearchPattern = useCallback((pd: SearchPatternResult) => {
    const pl = patternLayerRef.current;
    if (!pl) return;
    pl.clearLayers();
    if (!pd.waypoints || pd.waypoints.length < 2) return;

    L.polyline(pd.waypoints as [number, number][], {
      color: "#FFD700",
      weight: 2,
      dashArray: "6 3",
      opacity: 0.85,
    }).addTo(pl);

    pd.waypoints.forEach((wp, i) => {
      if (i === 0 || i === pd.waypoints.length - 1) return;
      L.circleMarker(wp as [number, number], {
        radius: 3, color: "#FFD700", fillOpacity: 0.8, weight: 1,
      }).addTo(pl);
    });
  }, []);

  const clearSearchPattern = useCallback(() => {
    patternLayerRef.current?.clearLayers();
    setPatternData(null);
    setShowPattern(false);
  }, []);

  // ── Toggle search pattern overlay ─────────────────────────────────────────
  const togglePattern = useCallback(async () => {
    if (showPattern) {
      clearSearchPattern();
      return;
    }
    if (!result) return;
    try {
      const pd = await fetchSearchPattern(
        result.centroid.lat,
        result.centroid.lon,
        result.search_area_km2,
        params.heading,
        result.recommended_pattern,
      );
      setPatternData(pd);
      drawSearchPattern(pd);
      setShowPattern(true);
    } catch (e: any) {
      console.error("Search pattern error:", e);
    }
  }, [showPattern, result, params.heading, drawSearchPattern, clearSearchPattern]);

  // ── Run simulation ────────────────────────────────────────────────────────
  const runSimulation = useCallback(async () => {
    setLoading(true);
    clearSearchPattern();
    try {
      const res = await simulateSearch({
        ...params,
        preset_id: selectedPreset || undefined,
      });
      setResult(res);
      drawResults(res);
      mapRef.current?.flyTo([res.centroid.lat, res.centroid.lon], 7, { duration: 1.5 });

      // Append to history (keep last 5)
      setHistory((prev) => [
        {
          timestamp: new Date().toLocaleTimeString(),
          centroid: res.centroid,
          classification: res.classification,
          severity: res.severity,
          result: res,
          params: { ...params },
        },
        ...prev.slice(0, 4),
      ]);
      setActiveTab("results");
    } finally {
      setLoading(false);
    }
  }, [params, selectedPreset, drawResults, clearSearchPattern]);

  // ── CSV export ────────────────────────────────────────────────────────────
  const exportCSV = useCallback(() => {
    if (!result) return;
    const rows = [
      ["type", "lat", "lon", "note"],
      [
        "centroid",
        result.centroid.lat.toFixed(6),
        result.centroid.lon.toFixed(6),
        `${result.classification} / ${result.severity}`,
      ],
      ...result.impact_points.map((pt, i) => [
        `impact_${i + 1}`,
        pt[0].toFixed(6),
        pt[1].toFixed(6),
        "",
      ]),
    ];
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sar_results_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [result]);

  // ── Restore history entry ─────────────────────────────────────────────────
  const restoreHistory = (entry: HistoryEntry) => {
    setResult(entry.result);
    setParams(entry.params);
    drawResults(entry.result);
    mapRef.current?.flyTo([entry.result.centroid.lat, entry.result.centroid.lon], 7, { duration: 1.5 });
    setActiveTab("results");
  };

  const SeverityBadge = ({ severity }: { severity: string }) => {
    const color = severity === "CRITICAL" ? "#ef4444" : severity === "HIGH" ? "#f97316" : "#eab308";
    return (
      <span style={{ color }} className="font-bold font-mono">
        {severity}
      </span>
    );
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <section id="mission-control" ref={sectionRef} className="min-h-screen py-8 px-4">
      <div className="max-w-[1400px] mx-auto">
        {/* Header */}
        <div className="glass-strong p-4 mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-cyan text-xl">◉</span>
            <h2 className="text-xl font-bold text-foreground">Mission Control</h2>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${loading ? "bg-orange animate-pulse" : result ? "bg-green-500" : "bg-muted-foreground"}`} />
            <span className="text-xs font-mono text-muted-foreground">
              {loading ? "COMPUTING" : result ? "COMPLETE" : "STANDBY"}
            </span>
          </div>
        </div>

        <div className="grid lg:grid-cols-[300px_1fr_340px] gap-4">
          {/* ── LEFT — Parameters ─────────────────────────────────────────── */}
          <div className="glass p-4 space-y-4 max-h-[calc(100vh-140px)] overflow-y-auto">
            <h3 className="font-bold text-sm text-foreground">Parameters</h3>

            {/* Quick Preset */}
            <div>
              <label className="block text-xs font-mono text-muted-foreground mb-1">Quick Preset</label>
              <select
                value={selectedPreset}
                onChange={(e) => applyPreset(e.target.value)}
                className="w-full px-3 py-2 rounded-lg text-sm font-mono bg-muted/50 border border-border focus:border-primary outline-none"
              >
                <option value="">Custom Parameters</option>
                {presets.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>

            {/* Aircraft Type */}
            <div>
              <label className="block text-xs font-mono text-muted-foreground mb-1">Aircraft Type</label>
              <select
                value={params.aircraft_type}
                onChange={(e) => updateParam("aircraft_type", e.target.value)}
                className="w-full px-3 py-2 rounded-lg text-sm font-mono bg-muted/50 border border-border focus:border-primary outline-none"
              >
                {aircraftTypes.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}{a.category ? ` (${a.category})` : ""}</option>
                ))}
              </select>
            </div>

            {/* Coordinates & Navigation */}
            <div className="grid grid-cols-2 gap-3">
              <InputField label="Latitude" paramKey="latitude" step={0.01} value={params.latitude} onChange={updateParam} />
              <InputField label="Longitude" paramKey="longitude" step={0.01} value={params.longitude} onChange={updateParam} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <InputField label="Heading (°)" paramKey="heading" value={params.heading} onChange={updateParam} />
              <InputField label="Airspeed (kts)" paramKey="airspeed" value={params.airspeed} onChange={updateParam} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <InputField label="Altitude (ft)" paramKey="altitude" value={params.altitude} onChange={updateParam} />
              <InputField label="Time Lost (min)" paramKey="time_since_contact" value={params.time_since_contact} onChange={updateParam} />
            </div>

            {/* Wind with Fetch button */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-mono text-muted-foreground">Wind</label>
                <button
                  id="fetch-wind-btn"
                  onClick={fetchRealWind}
                  disabled={weatherLoading}
                  title="Fetch real wind data from Open-Meteo"
                  className="text-xs font-mono px-2 py-0.5 rounded border border-cyan/40 text-cyan hover:bg-cyan/10 disabled:opacity-50 transition-colors flex items-center gap-1"
                >
                  {weatherLoading ? (
                    <span className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
                  ) : "⇣"}
                  Fetch Wind
                </button>
              </div>
              {weatherStatus && (
                <p className="text-xs font-mono text-muted-foreground mb-1 truncate">{weatherStatus}</p>
              )}
              <div className="grid grid-cols-2 gap-3">
                <InputField label="Speed (kts)" paramKey="wind_speed" value={params.wind_speed} onChange={updateParam} />
                <InputField label="Direction (°)" paramKey="wind_direction" value={params.wind_direction} onChange={updateParam} />
              </div>
            </div>

            {/* Advanced Parameters toggle */}
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full text-xs font-mono text-muted-foreground hover:text-foreground flex items-center gap-2 py-2"
            >
              <span>{showAdvanced ? "▼" : "▶"}</span> Advanced Parameters
            </button>
            {showAdvanced && (
              <div className="space-y-3 border-t border-border pt-3">
                <InputField label="Iterations" paramKey="iterations" value={params.iterations} onChange={updateParam} />
                <InputField label="Heading Spread (°)" paramKey="heading_spread" value={params.heading_spread} onChange={updateParam} />
                <div className="grid grid-cols-2 gap-3">
                  <InputField label="Scatter Min" paramKey="scatter_min" step={0.1} value={params.scatter_min} onChange={updateParam} />
                  <InputField label="Scatter Max" paramKey="scatter_max" step={0.1} value={params.scatter_max} onChange={updateParam} />
                </div>
                <InputField label="Descent Override (fpm)" paramKey="descent_rate_override" value={params.descent_rate_override} onChange={updateParam} />
                {/* Scenario weights */}
                <div className="space-y-2 pt-2">
                  <span className="text-xs font-mono font-semibold text-foreground">Scenario Weights</span>
                  <SliderField label="Best Glide" paramKey="weight_glide" value={params.weight_glide} onChange={updateParam} />
                  <SliderField label="Spiral" paramKey="weight_spiral" value={params.weight_spiral} onChange={updateParam} />
                  <SliderField label="Dive" paramKey="weight_dive" value={params.weight_dive} onChange={updateParam} />
                  <SliderField label="Breakup" paramKey="weight_breakup" value={params.weight_breakup} onChange={updateParam} />
                  <SliderField label="Ditching" paramKey="weight_ditching" value={params.weight_ditching} onChange={updateParam} />
                </div>
              </div>
            )}

            {/* Run button */}
            <button
              id="run-simulation-btn"
              onClick={runSimulation}
              disabled={loading}
              className="w-full btn-primary-solid text-center disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Running...
                </>
              ) : (
                "▶ Run Simulation"
              )}
            </button>
          </div>

          {/* ── CENTER — Map ──────────────────────────────────────────────── */}
          <div className="glass overflow-hidden min-h-[500px] lg:min-h-0 relative">
            <div ref={mapContainerRef} className="w-full h-full min-h-[500px]" />
            {!result && !loading && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-[1000]">
                <div className="glass-strong p-6 text-center">
                  <p className="text-sm font-mono text-muted-foreground">
                    Configure parameters and click Run Simulation
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* ── RIGHT — Results / History ─────────────────────────────────── */}
          <div className="glass p-4 space-y-3 max-h-[calc(100vh-140px)] overflow-y-auto">
            {/* Tab bar */}
            <div className="flex gap-2 border-b border-border pb-2">
              {(["results", "history"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`text-xs font-mono px-3 py-1 rounded-md transition-colors capitalize ${activeTab === tab
                    ? "bg-cyan/20 text-cyan"
                    : "text-muted-foreground hover:text-foreground"
                    }`}
                >
                  {tab}
                  {tab === "history" && history.length > 0 && (
                    <span className="ml-1 bg-muted px-1 rounded">{history.length}</span>
                  )}
                </button>
              ))}
            </div>

            {/* ── Results tab ─────────────────────────────────── */}
            {activeTab === "results" && (
              <>
                {!result ? (
                  <div className="text-center py-12 text-sm font-mono text-muted-foreground">
                    Awaiting simulation…
                  </div>
                ) : (
                  <>
                    {/* Scenario Assessment */}
                    <div className="glass-subtle p-4 space-y-2">
                      <h4 className="text-xs font-mono font-semibold text-foreground uppercase tracking-wider">Scenario Assessment</h4>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-muted-foreground font-mono">Classification</span>
                          <p className="font-semibold text-foreground">{result.classification}</p>
                        </div>
                        <div>
                          <span className="text-muted-foreground font-mono">Severity</span>
                          <p><SeverityBadge severity={result.severity} /></p>
                        </div>
                        <div>
                          <span className="text-muted-foreground font-mono">Search Area</span>
                          <p className="font-semibold font-mono text-foreground">{result.search_area_km2.toLocaleString()} km²</p>
                        </div>
                        <div>
                          <span className="text-muted-foreground font-mono">Glide Range</span>
                          <p className="font-semibold font-mono text-foreground">{result.glide_range_km} km</p>
                        </div>
                      </div>
                    </div>

                    {/* Zone Distribution */}
                    <div className="glass-subtle p-4 space-y-3">
                      <h4 className="text-xs font-mono font-semibold text-foreground uppercase tracking-wider">Zone Distribution</h4>
                      {[
                        { label: "HIGH", pct: result.zones.high.percentage, color: "#ef4444" },
                        { label: "MEDIUM", pct: result.zones.medium.percentage, color: "#f97316" },
                        { label: "LOW", pct: result.zones.low.percentage, color: "#22c55e" },
                      ].map((z) => (
                        <div key={z.label}>
                          <div className="flex justify-between text-xs font-mono mb-1">
                            <span className="text-muted-foreground">{z.label}</span>
                            <span className="text-foreground">{z.pct}%</span>
                          </div>
                          <div className="h-2 bg-muted rounded-full overflow-hidden">
                            <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${z.pct}%`, background: z.color }} />
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Accuracy check */}
                    {result.accuracy && (
                      <div className="glass-subtle p-4 space-y-2">
                        <h4 className="text-xs font-mono font-semibold text-foreground uppercase tracking-wider">Accuracy Check</h4>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <span className="text-muted-foreground font-mono">Centroid Error</span>
                            <p className="font-mono font-bold text-cyan text-lg">{result.accuracy.centroid_error_km} km</p>
                          </div>
                          <div>
                            <span className="text-muted-foreground font-mono">50km Coverage</span>
                            <p className={`font-mono font-bold text-lg ${result.accuracy.within_50km ? "text-green-500" : "text-destructive"}`}>
                              {result.accuracy.within_50km ? "✓" : "✗"} {result.accuracy.within_50km_pct}%
                            </p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Centroid + pattern */}
                    <div className="glass-subtle p-4">
                      <h4 className="text-xs font-mono font-semibold text-foreground uppercase tracking-wider mb-2">Centroid Position</h4>
                      <div className="font-mono text-sm text-foreground space-y-1 mb-3">
                        <div>Lat: <span className="text-cyan">{result.centroid.lat.toFixed(4)}</span></div>
                        <div>Lon: <span className="text-cyan">{result.centroid.lon.toFixed(4)}</span></div>
                      </div>
                      {result.recommended_pattern && (
                        <div className="text-xs font-mono text-muted-foreground mb-3">
                          Recommended: <span className="text-foreground">{result.recommended_pattern}</span>
                        </div>
                      )}

                      {/* Action buttons */}
                      <div className="flex flex-col gap-2">
                        <button
                          id="toggle-pattern-btn"
                          onClick={togglePattern}
                          className={`w-full text-xs font-mono py-2 rounded-lg border transition-colors ${showPattern
                            ? "border-yellow-500/60 text-yellow-400 bg-yellow-500/10"
                            : "border-border text-muted-foreground hover:border-yellow-500/40 hover:text-yellow-400"
                            }`}
                        >
                          {showPattern ? "✕ Hide Search Pattern" : "◈ Show Search Pattern"}
                        </button>
                        <button
                          id="export-csv-btn"
                          onClick={exportCSV}
                          className="w-full text-xs font-mono py-2 rounded-lg border border-border text-muted-foreground hover:border-cyan/40 hover:text-cyan transition-colors"
                        >
                          ↓ Export CSV
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </>
            )}

            {/* ── History tab ─────────────────────────────────── */}
            {activeTab === "history" && (
              <div className="space-y-2">
                {history.length === 0 ? (
                  <div className="text-center py-12 text-sm font-mono text-muted-foreground">
                    No runs yet
                  </div>
                ) : (
                  history.map((entry, i) => (
                    <button
                      key={i}
                      onClick={() => restoreHistory(entry)}
                      className="w-full text-left glass-subtle p-3 rounded-lg hover:border-cyan/30 border border-transparent transition-colors"
                    >
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs font-mono text-muted-foreground">{entry.timestamp}</span>
                        <SeverityBadge severity={entry.severity} />
                      </div>
                      <div className="text-xs font-mono text-foreground">{entry.classification}</div>
                      <div className="text-xs font-mono text-muted-foreground mt-0.5">
                        {entry.centroid.lat.toFixed(3)}, {entry.centroid.lon.toFixed(3)}
                      </div>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default MissionControl;
