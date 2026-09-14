import { useState } from "react";

/**
 * Blocking site-entry dialog.
 * The nautical banner then stays at the bottom of the map.
 */
export default function NotForNavModal({ t, open, onAccept }) {
  const [acked, setAcked] = useState(false);
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-[2000] flex items-center justify-center bg-abyss/80 px-4"
      data-testid="not-for-nav-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="not-for-nav-title"
    >
      <div className="max-w-md w-full bg-surface border border-amber-400/50 rounded-sm shadow-xl p-5">
        <h2
          id="not-for-nav-title"
          className="font-heading font-bold text-base text-amber-200"
        >
          {t("notForNavTitle")}
        </h2>
        <p className="mt-3 text-[13px] leading-relaxed text-slate-300">
          {t("notForNavBody")}
        </p>
        <p className="mt-2 font-mono text-[10px] text-slate-500 leading-relaxed">
          {t("notForNavModalHint")}
        </p>
        <label className="mt-4 flex items-start gap-2 text-[12px] text-slate-200">
          <input
            type="checkbox"
            data-testid="not-for-nav-ack"
            className="mt-0.5 accent-amber-400"
            checked={acked}
            onChange={(e) => setAcked(e.target.checked)}
          />
          <span>{t("notForNavAck")}</span>
        </label>
        <div className="mt-4">
          <button
            type="button"
            data-testid="not-for-nav-accept"
            className="w-full px-3 py-2 font-mono text-[11px] uppercase tracking-wide border border-amber-400/60 bg-amber-400/15 text-amber-100 hover:bg-amber-400/25 rounded-sm disabled:opacity-40"
            disabled={!acked}
            onClick={() => { if (acked) onAccept(); }}
          >
            {t("notForNavAccept")}
          </button>
        </div>
      </div>
    </div>
  );
}
