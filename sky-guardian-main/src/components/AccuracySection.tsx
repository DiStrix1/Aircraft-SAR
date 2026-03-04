import { useEffect, useRef, useState } from "react";

const AnimatedValue = ({ target, suffix = "" }: { target: number; suffix?: string }) => {
  const [val, setVal] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const started = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !started.current) {
        started.current = true;
        const start = performance.now();
        const animate = (now: number) => {
          const p = Math.min((now - start) / 1500, 1);
          setVal(Math.round(p * target * 10) / 10);
          if (p < 1) requestAnimationFrame(animate);
        };
        requestAnimationFrame(animate);
      }
    });
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [target]);

  return <span ref={ref}>{val}{suffix}</span>;
};

const validations = [
  {
    name: "Air France 447",
    year: 2009,
    description: "Mid-Atlantic oceanic crash. Aircraft lost in deep water with minimal radar coverage.",
    error_km: 22.6,
    coverage: 76,
  },
  {
    name: "Germanwings 9525",
    year: 2015,
    description: "Controlled descent into terrain in the French Alps. Mountainous terrain challenge.",
    error_km: 11.1,
    coverage: 96,
  },
  {
    name: "EgyptAir 804",
    year: 2016,
    description: "Mediterranean disappearance during cruise phase. Over-water search scenario.",
    error_km: 35.0,
    coverage: 70,
  },
  {
    name: "AirAsia QZ8501",
    year: 2014,
    description: "Java Sea incident during climb phase. Tropical weather conditions.",
    error_km: 24.9,
    coverage: 89,
  },
];

const AccuracySection = () => {
  return (
    <section id="accuracy" className="py-24 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <span className="section-tag mb-4 block w-fit mx-auto">VALIDATED</span>
          <h2 className="text-3xl sm:text-4xl font-extrabold">Proven Accuracy</h2>
        </div>

        <div className="grid sm:grid-cols-2 gap-6">
          {validations.map((v) => (
            <div key={v.name} className="glass-strong p-6 hover:scale-[1.02] transition-transform duration-300">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="font-bold text-lg text-foreground">{v.name}</h3>
                  <span className="font-mono text-xs text-muted-foreground">{v.year}</span>
                </div>
                <span className="pass-badge">✓ PASS</span>
              </div>
              <p className="text-sm text-muted-foreground mb-4 leading-relaxed">{v.description}</p>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-muted/50 rounded-lg p-3 text-center">
                  <div className="font-mono font-bold text-xl text-cyan">
                    <AnimatedValue target={v.error_km} suffix=" km" />
                  </div>
                  <div className="text-xs text-muted-foreground font-mono mt-1">Centroid Error</div>
                </div>
                <div className="bg-muted/50 rounded-lg p-3 text-center">
                  <div className="font-mono font-bold text-xl text-cyan">
                    <AnimatedValue target={v.coverage} suffix="%" />
                  </div>
                  <div className="text-xs text-muted-foreground font-mono mt-1">Coverage</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default AccuracySection;
