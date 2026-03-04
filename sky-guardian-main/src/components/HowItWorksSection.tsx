const pipelineCards = [
  {
    icon: (
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="hsl(193,100%,42%)" strokeWidth="1.5">
        <circle cx="12" cy="12" r="10" />
        <path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10A15.3 15.3 0 0112 2z" />
      </svg>
    ),
    title: "Flight Physics",
    description: "Haversine geodesics, glide ratio modeling, and multi-layer wind drift calculations.",
    tags: ["Haversine", "Glide L/D", "Wind Drift"],
  },
  {
    icon: (
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="hsl(193,100%,42%)" strokeWidth="1.5">
        <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" />
        <circle cx="12" cy="12" r="4" />
      </svg>
    ),
    title: "Monte Carlo Simulation",
    description: "3,000 randomized trajectory iterations across 4 descent archetypes with KDE analysis.",
    tags: ["3,000 Iterations", "4 Archetypes", "KDE Zoning"],
  },
  {
    icon: (
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="hsl(193,100%,42%)" strokeWidth="1.5">
        <path d="M3 3h18v18H3zM9 3v18M3 9h18M3 15h18M15 3v18" />
      </svg>
    ),
    title: "Zone Classification",
    description: "Kernel density estimation produces HIGH, MEDIUM, and LOW probability search zones.",
    tags: ["KDE Analysis", "Convex Hulls", "3 Zones"],
  },
];

const archetypes = [
  { emoji: "✈️", name: "Best Glide", rate: "700–3,000 fpm", desc: "Controlled descent at optimal L/D ratio" },
  { emoji: "🌀", name: "Spiral / Spin", rate: "5,000–15,000 fpm", desc: "Uncontrolled rotation with altitude loss" },
  { emoji: "⚡", name: "High-Speed Dive", rate: "10,000–30,000 fpm", desc: "Steep nose-down trajectory" },
  { emoji: "💥", name: "In-Flight Breakup", rate: "2,000–30,000 fpm", desc: "Structural failure with debris scatter" },
];

const HowItWorksSection = () => {
  return (
    <section id="how-it-works" className="py-24 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <span className="section-tag mb-4 block w-fit mx-auto">THE ENGINE</span>
          <h2 className="text-3xl sm:text-4xl font-extrabold">How It Works</h2>
        </div>

        {/* Pipeline */}
        <div className="flex flex-col lg:flex-row items-stretch gap-4 mb-20">
          {pipelineCards.map((card, i) => (
            <div key={card.title} className="contents">
              <div className="glass-strong p-6 flex-1 flex flex-col items-center text-center">
                <div className="mb-4">{card.icon}</div>
                <h3 className="text-lg font-bold mb-2 text-foreground">{card.title}</h3>
                <p className="text-sm text-muted-foreground mb-4 leading-relaxed">{card.description}</p>
                <div className="flex flex-wrap gap-2 justify-center mt-auto">
                  {card.tags.map((t) => (
                    <span key={t} className="text-xs font-mono px-2.5 py-1 rounded-full bg-muted text-muted-foreground">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
              {i < pipelineCards.length - 1 && (
                <div className="pipeline-arrow">→</div>
              )}
            </div>
          ))}
        </div>

        {/* Descent Archetypes */}
        <div className="text-center mb-10">
          <h3 className="text-2xl font-bold text-foreground">Four Descent Archetypes</h3>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {archetypes.map((a) => (
            <div key={a.name} className="glass p-6 text-center hover:scale-[1.03] transition-transform duration-300">
              <div className="text-4xl mb-3">{a.emoji}</div>
              <h4 className="font-bold text-foreground mb-1">{a.name}</h4>
              <p className="font-mono text-xs text-cyan mb-2">{a.rate}</p>
              <p className="text-sm text-muted-foreground">{a.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default HowItWorksSection;
