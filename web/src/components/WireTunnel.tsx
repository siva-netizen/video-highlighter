export function WireTunnel() {
  const horizontals = Array.from({ length: 13 }, (_, i) => {
    const t = i / 12;
    const y = 20 + t * 260;
    const inset = t * 140;
    return (
      <line key={`h-${i}`} x1={40 + inset} y1={y} x2={360 - inset} y2={y} />
    );
  });
  const radials = Array.from({ length: 9 }, (_, i) => {
    const x = 40 + (i / 8) * 320;
    return <line key={`r-${i}`} x1={x} y1={20} x2={200} y2={280} />;
  });
  return (
    <svg className="hero-tunnel" viewBox="0 0 400 300" aria-hidden>
      {horizontals}
      {radials}
      <circle cx="200" cy="150" r="28" fill="#0a0a0a" stroke="#fff" strokeWidth="1" />
    </svg>
  );
}
