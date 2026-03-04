import { useEffect, useRef, useState } from "react";

const AnimatedCounter = ({ target, suffix = "", prefix = "" }: { target: number; suffix?: string; prefix?: string }) => {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const started = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !started.current) {
        started.current = true;
        const start = performance.now();
        const animate = (now: number) => {
          const progress = Math.min((now - start) / 2000, 1);
          setCount(Math.floor(progress * target));
          if (progress < 1) requestAnimationFrame(animate);
        };
        requestAnimationFrame(animate);
      }
    });
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [target]);

  return (
    <span ref={ref}>
      {prefix}{count.toLocaleString()}{suffix}
    </span>
  );
};

const RadarScreen = () => {
  const [blipVisible, setBlipVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setBlipVisible(false), 3000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="relative w-64 h-64 sm:w-80 sm:h-80 mx-auto">
      {/* Radar background */}
      <div className="absolute inset-0 rounded-full border-2 border-cyan/20 bg-navy/10">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="absolute rounded-full border border-cyan/10"
            style={{
              inset: `${i * 20}%`,
            }}
          />
        ))}
        {/* Crosshairs */}
        <div className="absolute top-0 bottom-0 left-1/2 w-px bg-cyan/10" />
        <div className="absolute left-0 right-0 top-1/2 h-px bg-cyan/10" />
        {/* Sweep line */}
        <div className="absolute top-1/2 left-1/2 w-1/2 h-0.5 origin-left bg-gradient-to-r from-cyan/60 to-transparent animate-radar-sweep" />
      </div>
      {/* Blip */}
      <div
        className={`absolute top-[35%] left-[55%] w-3 h-3 rounded-full bg-cyan shadow-[0_0_12px_hsl(193,100%,42%)] transition-opacity duration-1000 ${
          blipVisible ? "opacity-100" : "opacity-0"
        }`}
      />
      {blipVisible && (
        <div className="absolute top-[35%] left-[55%] w-3 h-3 rounded-full bg-cyan/50 animate-ping" />
      )}
      {!blipVisible && (
        <div className="absolute top-[35%] left-[55%] font-mono text-[10px] text-destructive font-bold tracking-wider">
          SIGNAL LOST
        </div>
      )}
    </div>
  );
};

const statCards = [
  { value: 72, suffix: " hrs", label: "Average time to locate wreckage" },
  { value: 500000, suffix: " km²", label: "AF447 initial search area" },
  { value: 22, suffix: " km", label: "Our centroid accuracy on AF447" },
];

const ProblemSection = () => {
  return (
    <section id="problem" className="py-24 px-4">
      <div className="max-w-6xl mx-auto grid lg:grid-cols-2 gap-16 items-center">
        {/* Left — Radar */}
        <div className="flex justify-center">
          <RadarScreen />
        </div>

        {/* Right — Content */}
        <div>
          <span className="section-tag mb-4 block w-fit">THE CHALLENGE</span>
          <h2 className="text-3xl sm:text-4xl font-extrabold mb-6 leading-tight">When an Aircraft Vanishes</h2>
          <p className="text-muted-foreground leading-relaxed mb-4">
            When an aircraft disappears from radar, search teams face an enormous challenge: locating wreckage in potentially vast, remote areas with limited information. Traditional search methods rely on expanding grid patterns that can take days or weeks.
          </p>
          <p className="text-muted-foreground leading-relaxed mb-8">
            Our system transforms last-known flight data into probabilistic crash zone predictions within seconds, dramatically reducing search areas and saving critical time in the golden hours after an incident.
          </p>

          {/* Stat cards */}
          <div className="space-y-3">
            {statCards.map((s) => (
              <div key={s.label} className="glass p-4 flex items-center gap-4">
                <span className="metric-value text-2xl min-w-[120px]">
                  <AnimatedCounter target={s.value} suffix={s.suffix} />
                </span>
                <span className="text-sm text-muted-foreground font-medium">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default ProblemSection;
