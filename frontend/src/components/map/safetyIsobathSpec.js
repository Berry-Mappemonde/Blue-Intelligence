/**
 * S-52 allégée : aplat sur les DEPARE Seascape dont drval1 < seuil.
 * M14 (2026-09-14) : l'attribut existe. Pas un moteur ECDIS.
 */
export const SAFETY_ISOBATH_LAYER_ID = "bi-safety-depare";
export const SAFETY_DEPTHS_M = [2, 5, 10];
export const DEFAULT_SAFETY_M = 2;

export function safetyIsobathLayers(meters = DEFAULT_SAFETY_M) {
  const m = SAFETY_DEPTHS_M.includes(Number(meters)) ? Number(meters) : DEFAULT_SAFETY_M;
  return [
    {
      id: SAFETY_ISOBATH_LAYER_ID,
      type: "fill",
      source: "seascape-vector",
      "source-layer": "depare",
      filter: [
        "all",
        ["has", "drval1"],
        ["<", ["to-number", ["get", "drval1"]], m],
      ],
      paint: {
        "fill-color": "#b45309",
        "fill-opacity": 0.28,
      },
      metadata: { "bi:safety-m": m },
    },
  ];
}
