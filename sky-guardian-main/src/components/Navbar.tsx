import { useEffect, useState } from "react";

const navLinks = [
  { label: "Home", href: "#home" },
  { label: "Problem", href: "#problem" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Accuracy", href: "#accuracy" },
  { label: "Mission Control", href: "#mission-control" },
];

/* ── SPECTRA Radar Logo
 *  Three probability-zone sectors (red/amber/green) inside a radar disk,
 *  with a top-view aircraft silhouette and centroid blip.
 * ─────────────────────────────────────────────────────── */
const SpectraLogo = () => (
  <svg width="36" height="36" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <radialGradient id="sBg" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stopColor="#0d1f2d" />
        <stop offset="100%" stopColor="#060f18" />
      </radialGradient>
      <linearGradient id="sPlane" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#00e5ff" />
        <stop offset="100%" stopColor="#0094b3" />
      </linearGradient>
    </defs>

    {/* Disk background */}
    <circle cx="32" cy="32" r="30" fill="url(#sBg)" stroke="#00B4D8" strokeWidth="1.5" strokeOpacity="0.65" />

    {/* Probability zone sectors — RED (high), AMBER (medium), GREEN (low) */}
    <path d="M32 32 L56 32 A24 24 0 0 0 32 8 Z" fill="#ef4444" fillOpacity="0.25" />
    <path d="M32 32 L8  32 A24 24 0 0 1 32 8 Z" fill="#f97316" fillOpacity="0.2" />
    <path d="M32 32 L8  32 A24 24 0 0 0 32 56 L56 32 A24 24 0 0 0 32 32 Z" fill="#22c55e" fillOpacity="0.15" />

    {/* Radar rings */}
    <circle cx="32" cy="32" r="24" fill="none" stroke="#00B4D8" strokeWidth="0.5" strokeOpacity="0.3" />
    <circle cx="32" cy="32" r="15" fill="none" stroke="#00B4D8" strokeWidth="0.5" strokeOpacity="0.22" />

    {/* Crosshairs */}
    <line x1="32" y1="8" x2="32" y2="56" stroke="#00B4D8" strokeWidth="0.45" strokeOpacity="0.22" />
    <line x1="8" y1="32" x2="56" y2="32" stroke="#00B4D8" strokeWidth="0.45" strokeOpacity="0.22" />

    {/* Aircraft top-view — angled 45° NE (direction of travel) */}
    <g transform="rotate(-45 32 32)">
      {/* Fuselage */}
      <ellipse cx="32" cy="32" rx="2.4" ry="9" fill="url(#sPlane)" />
      {/* Wings */}
      <path d="M32 29 L10 40 L18 40 L32 33 L46 40 L54 40 Z" fill="url(#sPlane)" />
      {/* Tail stab */}
      <path d="M32 46 L24 52 L27 52 L32 48 L37 52 L40 52 Z" fill="url(#sPlane)" fillOpacity="0.8" />
    </g>

    {/* Centroid blip (predicted impact point) */}
    <circle cx="40" cy="24" r="2.2" fill="#00ffcc" fillOpacity="0.95" />
  </svg>
);

const Navbar = () => {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? "glass-strong shadow-lg" : "glass"
        }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
        <a href="#home" className="flex items-center gap-2.5 font-bold text-xl text-foreground">
          <SpectraLogo />
          <span
            className="tracking-widest font-black"
            style={{
              background: "linear-gradient(90deg, #00e5ff 0%, #60a5fa 50%, #a78bfa 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            SPECTRA
          </span>
        </a>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-1">
          {navLinks.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-muted/50"
            >
              {l.label}
            </a>
          ))}
        </div>

        {/* Mobile toggle */}
        <button
          className="md:hidden p-2 rounded-lg hover:bg-muted/50"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle menu"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {mobileOpen ? (
              <path d="M6 6l12 12M6 18L18 6" />
            ) : (
              <path d="M3 12h18M3 6h18M3 18h18" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden glass-strong border-t border-border px-4 pb-4">
          {navLinks.map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setMobileOpen(false)}
              className="block py-3 text-sm font-medium text-muted-foreground hover:text-foreground"
            >
              {l.label}
            </a>
          ))}
        </div>
      )}
    </nav>
  );
};

export default Navbar;
