/** Vue de dessus : proue vers le haut (nord carte). `rotate(cap)` aligne la proue. */
export function catamaranTransform(bearing) {
  const deg = ((Number(bearing) || 0) % 360 + 360) % 360;
  return `rotate(${deg}deg)`;
}

function hullPath(cx) {
  const left = cx - 6.2;
  const right = cx + 6.2;
  return [
    `M ${cx} 5.5`,
    `C ${cx + 3.2} 6.2, ${right} 11, ${right} 16`,
    `L ${right - 0.4} 50`,
    `C ${right} 54.5, ${cx + 3.4} 57.2, ${cx} 58`,
    `C ${cx - 3.4} 57.2, ${left} 54.5, ${left + 0.4} 50`,
    `L ${left} 16`,
    `C ${left} 11, ${cx - 3.2} 6.2, ${cx} 5.5`,
    "Z",
  ].join(" ");
}

/** Catamaran lisible à l’échelle carte : deux coques, trampoline, roof, mât. Proue = haut. */
export function catamaranSvg(bearing, { size = 64 } = {}) {
  const deg = ((Number(bearing) || 0) % 360 + 360) % 360;
  const transform = catamaranTransform(deg);
  const port = hullPath(19);
  const starboard = hullPath(45);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 64 64" aria-label="catamaran" data-bow="north" data-heading="${deg}" style="display:block;transform:${transform};transform-origin:50% 50%;transition:transform 0.35s ease;">
  <ellipse cx="32" cy="34" rx="20" ry="22" fill="#0f172a" opacity="0.18"/>
  <path d="M24 14 L40 14 L41 48 L23 48 Z" fill="#0e7490" opacity="0.38"/>
  <path d="M25 10 L39 10 L40 18 L24 18 Z" fill="#67e8f9" opacity="0.28"/>
  <rect x="22" y="19" width="20" height="2.4" rx="1.1" fill="#cbd5e1"/>
  <rect x="22" y="43.5" width="20" height="2.4" rx="1.1" fill="#cbd5e1"/>
  <rect x="25.5" y="26" width="13" height="13" rx="2.6" fill="#155e75" stroke="#22d3ee" stroke-width="0.9"/>
  <rect x="27.5" y="28.2" width="4.2" height="4.6" rx="0.7" fill="#67e8f9" opacity="0.55"/>
  <rect x="32.4" y="28.2" width="4.2" height="4.6" rx="0.7" fill="#67e8f9" opacity="0.35"/>
  <circle cx="32" cy="24.2" r="2.15" fill="#f8fafc" stroke="#0f172a" stroke-width="0.7"/>
  <path d="${port}" fill="#f8fafc" stroke="#0f172a" stroke-width="1.15" stroke-linejoin="round"/>
  <path d="${starboard}" fill="#f8fafc" stroke="#0f172a" stroke-width="1.15" stroke-linejoin="round"/>
  <path d="M18.2 13 L19.8 13 L20.4 49 L17.6 49 Z" fill="#22d3ee" opacity="0.55"/>
  <path d="M44.2 13 L45.8 13 L46.4 49 L43.6 49 Z" fill="#22d3ee" opacity="0.55"/>
  <path d="M32 3.2 L36.4 11.6 L27.6 11.6 Z" fill="#22d3ee" stroke="#0f172a" stroke-width="0.7" stroke-linejoin="round"/>
  <circle cx="32" cy="55.4" r="1.15" fill="#64748b"/>
</svg>`;
}
