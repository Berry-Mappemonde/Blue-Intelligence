/** Symboles GRIB façon carte météo / climatologie. Pas un rectangle. */

export function beaufortColor(knots) {
  const k = Number(knots) || 0;
  if (k < 1) return "#94a3b8";
  if (k < 7) return "#7dd3fc";
  if (k < 16) return "#38bdf8";
  if (k < 27) return "#2dd4bf";
  if (k < 34) return "#fbbf24";
  if (k < 48) return "#f97316";
  return "#ef4444";
}

/** Hs comme les disques climatologie (moyenne). */
export function waveHsColor(hs) {
  const h = Number(hs) || 0;
  if (h >= 3) return "#155e75";
  if (h >= 1.5) return "#0d9488";
  return "#5eead4";
}

/** Barbules OMM : 50 kn = fanion, 10 kn = longue, 5 kn = courte. */
export function wmoBarbMarks(knots) {
  let k = Math.max(0, Math.round((Number(knots) || 0) / 5) * 5);
  const pennants = Math.floor(k / 50);
  k -= pennants * 50;
  const longs = Math.floor(k / 10);
  k -= longs * 10;
  const shorts = k >= 5 ? 1 : 0;
  return {
    pennants,
    longs,
    shorts,
    calm: pennants + longs + shorts === 0,
  };
}

export function pickGribSlice(samples, whenIso, limit = 24) {
  const byKey = new Map();
  const target = whenIso ? Date.parse(whenIso) : NaN;
  for (const s of samples || []) {
    if (s.lat == null || s.lon == null) continue;
    if (s.windKnots == null && s.hs == null) continue;
    const key = `${Number(s.lat).toFixed(2)},${Number(s.lon).toFixed(2)}`;
    const prev = byKey.get(key);
    if (!prev) {
      byKey.set(key, s);
      continue;
    }
    if (!Number.isFinite(target)) continue;
    const dt = Math.abs(Date.parse(s.t) - target);
    const prevDt = Math.abs(Date.parse(prev.t) - target);
    if (dt < prevDt) byKey.set(key, s);
  }
  return [...byKey.values()].slice(0, limit);
}

export function worldCopyLngs(lon) {
  const x = Number(lon);
  if (!Number.isFinite(x)) return [];
  return [x, x + 360, x - 360];
}

/**
 * Hampe OMM : pointe vers d’où vient le vent (dirFromDeg).
 * Disque central teinté Beaufort, comme le centre des roses climatologie.
 */
export function gribBarbSvg(sample) {
  const kn = Number(sample?.windKnots) || 0;
  const from = Number(sample?.dirFromDeg) || 0;
  const color = beaufortColor(kn);
  const { pennants, longs, shorts, calm } = wmoBarbMarks(kn);
  if (calm) {
    return `<svg width="28" height="28" viewBox="0 0 28 28" xmlns="http://www.w3.org/2000/svg">
      <circle cx="14" cy="14" r="5" fill="none" stroke="${color}" stroke-width="1.6"/>
      <circle cx="14" cy="14" r="2.4" fill="${color}"/>
    </svg>`;
  }
  const feathers = [];
  let y = 5;
  for (let i = 0; i < pennants; i++) {
    feathers.push(`<polygon points="14,${y} 22,${y + 3.2} 14,${y + 6.4}" fill="${color}"/>`);
    y += 6.2;
  }
  for (let i = 0; i < longs; i++) {
    feathers.push(`<line x1="14" y1="${y}" x2="23" y2="${y - 3.4}" stroke="${color}" stroke-width="1.5"/>`);
    y += 3.6;
  }
  if (shorts) {
    feathers.push(`<line x1="14" y1="${y}" x2="19.5" y2="${y - 2.2}" stroke="${color}" stroke-width="1.5"/>`);
  }
  return `<svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <g transform="rotate(${from} 16 16)">
      <line x1="16" y1="26" x2="16" y2="5" stroke="${color}" stroke-width="1.6"/>
      ${feathers.join("")}
    </g>
    <circle cx="16" cy="16" r="3.1" fill="${color}"/>
  </svg>`;
}
