import { useEffect, useRef, useState, useCallback } from "react";

const stats = [
  { value: 5, label: "Descent Archetypes" },
  { value: 10, label: "Wind Layers" },
  { value: 3000, label: "Simulations/Run" },
  { value: 18, label: "Aircraft Types" },
];

const AnimatedCounter = ({ target, duration = 2000 }: { target: number; duration?: number }) => {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const started = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !started.current) {
        started.current = true;
        const start = performance.now();
        const animate = (now: number) => {
          const progress = Math.min((now - start) / duration, 1);
          setCount(Math.floor(progress * target));
          if (progress < 1) requestAnimationFrame(animate);
        };
        requestAnimationFrame(animate);
      }
    });
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [target, duration]);

  return <span ref={ref}>{count.toLocaleString()}</span>;
};

const TypewriterText = ({ text }: { text: string }) => {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    let i = 0;
    const interval = setInterval(() => {
      setDisplayed(text.slice(0, i + 1));
      i++;
      if (i >= text.length) {
        clearInterval(interval);
        setDone(true);
      }
    }, 45);
    return () => clearInterval(interval);
  }, [text]);

  return (
    <span>
      {displayed}
      {!done && <span className="animate-blink text-cyan">|</span>}
    </span>
  );
};

/* ── Cityscape SVG ── */
const CityscapeSilhouette = () => (
  <svg
    viewBox="0 0 1920 320"
    preserveAspectRatio="none"
    className="w-full h-full"
    xmlns="http://www.w3.org/2000/svg"
  >
    <defs>
      <linearGradient id="cityGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="hsl(218,47%,20%)" stopOpacity="0.08" />
        <stop offset="100%" stopColor="hsl(218,47%,20%)" stopOpacity="0.18" />
      </linearGradient>
    </defs>
    <path
      fill="url(#cityGrad)"
      d={`
        M0 320 L0 260 L40 260 L40 220 L60 220 L60 180 L80 180 L80 220 L100 220 L100 200 L120 200 L120 160 L130 160 L130 140 L140 140 L140 160 L160 160 L160 200 L180 200 L180 240 L220 240 L220 190 L240 190 L240 150 L250 150 L250 120 L260 120 L260 150 L280 150 L280 190 L300 190 L300 230 L340 230 L340 180 L360 180 L360 140 L380 140 L380 100 L390 100 L390 80 L400 80 L400 100 L420 100 L420 140 L440 140 L440 200 L480 200 L480 170 L500 170 L500 130 L520 130 L520 170 L540 170 L540 210 L580 210 L580 160 L600 160 L600 120 L610 120 L610 90 L620 90 L620 70 L630 70 L630 90 L640 90 L640 120 L660 120 L660 160 L680 160 L680 200 L720 200 L720 230 L760 230 L760 190 L780 190 L780 150 L800 150 L800 110 L810 110 L810 80 L820 80 L820 60 L830 60 L830 80 L840 80 L840 110 L860 110 L860 150 L880 150 L880 190 L920 190 L920 220 L960 220 L960 180 L980 180 L980 140 L1000 140 L1000 100 L1010 100 L1010 70 L1020 70 L1020 100 L1040 100 L1040 140 L1060 140 L1060 180 L1100 180 L1100 210 L1140 210 L1140 170 L1160 170 L1160 130 L1180 130 L1180 90 L1190 90 L1190 60 L1200 60 L1200 90 L1220 90 L1220 130 L1240 130 L1240 170 L1280 170 L1280 200 L1320 200 L1320 240 L1360 240 L1360 200 L1380 200 L1380 160 L1400 160 L1400 120 L1410 120 L1410 90 L1420 90 L1420 120 L1440 120 L1440 160 L1460 160 L1460 200 L1500 200 L1500 230 L1540 230 L1540 190 L1560 190 L1560 150 L1580 150 L1580 190 L1620 190 L1620 220 L1660 220 L1660 250 L1700 250 L1700 210 L1720 210 L1720 180 L1740 180 L1740 210 L1780 210 L1780 240 L1820 240 L1820 260 L1860 260 L1860 230 L1880 230 L1880 250 L1920 250 L1920 320 Z
      `}
    />
    {/* Window dots */}
    {[400, 620, 825, 1015, 1195, 1415].map((x) => (
      <g key={x} opacity="0.12">
        {[0, 12, 24].map((dy) => (
          <rect key={dy} x={x - 3} y={85 + dy} width="6" height="6" rx="1" fill="hsl(193,100%,42%)" />
        ))}
      </g>
    ))}
  </svg>
);

/* ── Animated Plane with contrail (rAF-driven) ── */
const usePlaneAnim = (startX: number, startPhase: number, yBase: string) => {
  const planeRef = useRef<HTMLDivElement>(null);
  const animRef = useRef<number>(0);

  const state = useRef({
    x: startX,
    phase: startPhase,
    speedPhase: Math.random() * Math.PI * 2,
    bankPhase: Math.random() * Math.PI * 2,
  });

  const animate = useCallback((time: number) => {
    const el = planeRef.current;
    if (!el) return;

    const s = state.current;
    const t = time * 0.001;

    const speed = 48 + 10 * Math.sin(t * 0.25 + s.speedPhase);
    const dt = speed / 60;
    s.x += dt;

    const container = el.parentElement;
    const containerW = container ? container.offsetWidth : 1920;
    if (s.x > containerW + 120) {
      s.x = -120;
      s.phase += 0.8 + Math.random() * 0.5;
      s.speedPhase += 0.6 + Math.random() * 0.7;
      s.bankPhase += 0.4 + Math.random() * 0.5;
    }

    const yDrift =
      10 * Math.sin(t * 0.35 + s.phase) +
      5 * Math.sin(t * 0.8 + s.phase * 1.6);

    const bankAngle =
      4 * Math.sin(t * 0.3 + s.bankPhase) +
      2 * Math.sin(t * 0.75 + s.bankPhase * 1.9);

    el.style.transform = `translate3d(${Math.round(s.x)}px, ${Math.round(yDrift)}px, 0) rotate(${bankAngle.toFixed(2)}deg)`;

    animRef.current = requestAnimationFrame(animate);
  }, []);

  useEffect(() => {
    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, [animate]);

  return { planeRef, yBase };
};

const PlaneWithContrail = ({
  startX,
  startPhase,
  top,
  scale = 1,
  opacity = 0.5,
}: {
  startX: number;
  startPhase: number;
  top: string;
  scale?: number;
  opacity?: number;
}) => {
  const { planeRef } = usePlaneAnim(startX, startPhase, top);

  return (
    <div
      ref={planeRef}
      className="absolute will-change-transform"
      style={{ top, left: 0, opacity }}
    >
      {/* Contrail — gradient line behind the plane */}
      <svg
        width={180 * scale}
        height={28 * scale}
        viewBox="0 0 180 28"
        xmlns="http://www.w3.org/2000/svg"
        style={{ position: "absolute", right: "100%", top: "50%", transform: "translateY(-50%)" }}
      >
        <defs>
          <linearGradient id={`contrail-${startPhase}`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="hsl(193,100%,42%)" stopOpacity="0" />
            <stop offset="80%" stopColor="hsl(193,100%,42%)" stopOpacity="0.25" />
            <stop offset="100%" stopColor="hsl(193,100%,42%)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* Upper trail */}
        <line x1="0" y1="10" x2="180" y2="10" stroke={`url(#contrail-${startPhase})`} strokeWidth="2" />
        {/* Lower trail */}
        <line x1="0" y1="18" x2="180" y2="18" stroke={`url(#contrail-${startPhase})`} strokeWidth="2" />
      </svg>

      {/* Glow halo */}
      <svg
        width={16 * scale}
        height={16 * scale}
        viewBox="0 0 16 16"
        xmlns="http://www.w3.org/2000/svg"
        style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", filter: "blur(4px)" }}
      >
        <circle cx="8" cy="8" r="8" fill="hsl(193,100%,60%)" fillOpacity="0.35" />
      </svg>

      {/* Plane SVG — detailed top-view silhouette */}
      <svg
        width={64 * scale}
        height={64 * scale}
        viewBox="0 0 64 64"
        xmlns="http://www.w3.org/2000/svg"
        style={{ transform: "rotate(90deg)" }}
      >
        <defs>
          <linearGradient id={`planeGrad-${startPhase}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00e5ff" />
            <stop offset="100%" stopColor="#007bbf" />
          </linearGradient>
        </defs>
        {/* Fuselage */}
        <ellipse cx="32" cy="32" rx="3.5" ry="20" fill={`url(#planeGrad-${startPhase})`} />
        {/* Main wings */}
        <path d="M32 30 L8 44 L18 44 L32 34 L46 44 L56 44 Z" fill={`url(#planeGrad-${startPhase})`} />
        {/* Horizontal stabilizers */}
        <path d="M32 50 L22 56 L26 56 L32 52 L38 56 L42 56 Z" fill={`url(#planeGrad-${startPhase})`} fillOpacity="0.85" />
        {/* Engine nacelles */}
        <ellipse cx="20" cy="38" rx="2.5" ry="5" fill={`url(#planeGrad-${startPhase})`} fillOpacity="0.7" />
        <ellipse cx="44" cy="38" rx="2.5" ry="5" fill={`url(#planeGrad-${startPhase})`} fillOpacity="0.7" />
        {/* Cockpit glint */}
        <ellipse cx="32" cy="16" rx="2" ry="3" fill="white" fillOpacity="0.25" />
      </svg>
    </div>
  );
};

const AnimatedPlane = () => (
  <>
    {/* Main foreground plane */}
    <PlaneWithContrail
      startX={-120}
      startPhase={0}
      top="28%"
      scale={1.0}
      opacity={0.52}
    />
    {/* Second plane — higher altitude, smaller, delayed */}
    <PlaneWithContrail
      startX={-600}
      startPhase={2.4}
      top="18%"
      scale={0.65}
      opacity={0.32}
    />
  </>
);


/* ── Hero Section ── */
const HeroSection = () => {
  const cityscapeRef = useRef<HTMLDivElement>(null);

  // Parallax: cityscape moves at 0.3× scroll speed
  useEffect(() => {
    const handleScroll = () => {
      if (cityscapeRef.current) {
        const scrollY = window.scrollY;
        cityscapeRef.current.style.transform = `translate3d(0, ${scrollY * 0.3}px, 0)`;
      }
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <section id="home" className="relative min-h-screen flex flex-col items-center justify-center px-4 overflow-hidden">
      {/* Layer 1: Background gradient (inherited from body) */}

      {/* Layer 2: Radar rings (very faint) */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-[0.05]">
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="absolute rounded-full border border-cyan"
            style={{
              width: `${i * 200}px`,
              height: `${i * 200}px`,
              animation: `pulse-ring ${3 + i * 0.5}s ease-out infinite`,
              animationDelay: `${i * 0.6}s`,
            }}
          />
        ))}
      </div>

      {/* Layer 3: Cityscape silhouette with parallax */}
      <div
        ref={cityscapeRef}
        className="absolute bottom-0 left-0 right-0 pointer-events-none will-change-transform"
        style={{ height: "35%" }}
      >
        <CityscapeSilhouette />
      </div>

      {/* Layer 4: Animated plane */}
      <div className="absolute inset-0 pointer-events-none">
        <AnimatedPlane />
      </div>

      {/* Layer 5: UI content */}
      <div className="relative z-10 text-center max-w-4xl mx-auto">
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-tight mb-6 tracking-tight">
          <TypewriterText text="SPECTRA" />
        </h1>
        <p className="text-base sm:text-lg text-cyan font-mono uppercase tracking-widest mb-3">
          SAR Predictive Engine for Crash Trajectory &amp; Risk Analysis
        </p>
        <p className="text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed">
          Predicting aircraft crash zones in real-time using Monte Carlo simulation, multi-layer wind physics, and probability spectrum mapping.
        </p>
        <div className="flex flex-wrap gap-4 justify-center mb-16">
          <a href="#mission-control" className="btn-primary-solid">
            Launch Mission Control
          </a>
          <a href="#problem" className="btn-ghost">
            Learn More ↓
          </a>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto">
          {stats.map((s) => (
            <div key={s.label} className="metric-card">
              <div className="metric-value">
                <AnimatedCounter target={s.value} />
              </div>
              <div className="metric-label">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Scroll hint */}
      <div className="absolute bottom-8 flex flex-col items-center gap-2 text-muted-foreground text-sm font-mono z-10">
        <span>Scroll to explore</span>
        <svg className="w-5 h-5 animate-bounce-slow" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
      </div>
    </section>
  );
};

export default HeroSection;
