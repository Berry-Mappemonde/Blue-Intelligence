/**
 * Presentation of the header toggles whose "on" state changes what the map shows.
 * "Show review" filters every dataset down to certified (Gold) items: when it is on
 * by accident the lists look empty, so its pressed state must be unmistakable.
 */

export function reviewToggleClass(pressed) {
  const base = "nav-tab rounded-md border";
  return pressed
    ? `${base} border-m-accent text-m-accent-fg bg-m-accent/10 hover:text-m-accent-fg`
    : `${base} border-line`;
}

/** The label is always visible while the toggle is on; otherwise only on wide screens. */
export function reviewToggleLabelClass(pressed) {
  return pressed ? "inline" : "hidden 2xl:inline";
}
