import { useState } from "react";

/**
 * Blocking site-entry dialog.
 * The nautical banner then stays at the bottom of the map.
 * Presentation: Meridian modal (scrim, 12 px radius, hairline, Inter); the
 * checkbox + enter behaviour and the storage logic (App.js) are unchanged.
 */
export default function NotForNavModal({ t, open, onAccept }) {
  const [acked, setAcked] = useState(false);
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/60 px-4 font-ui"
      data-testid="not-for-nav-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="not-for-nav-title"
    >
      <div
        className="m-enter max-w-md w-full bg-m-overlay border border-m-line-strong rounded-xl p-5 text-m-fg"
        style={{ boxShadow: "var(--m-shadow-float)" }}
      >
        <h2
          id="not-for-nav-title"
          className="text-[15px] leading-5 font-medium text-m-fg"
        >
          {t("notForNavTitle")}
        </h2>
        <p className="mt-3 text-[13px] leading-[18px] text-m-fg2">
          {t("notForNavBody")}
        </p>
        <p className="mt-2 text-[12px] leading-4 text-m-fg3">
          {t("notForNavModalHint")}
        </p>
        <label className="mt-4 flex items-start gap-2 text-[13px] leading-[18px] text-m-fg">
          <input
            type="checkbox"
            data-testid="not-for-nav-ack"
            autoFocus
            className="mt-0.5 accent-m-accent"
            checked={acked}
            onChange={(e) => setAcked(e.target.checked)}
          />
          <span>{t("notForNavAck")}</span>
        </label>
        <div className="mt-4">
          <button
            type="button"
            data-testid="not-for-nav-accept"
            className="m-btn m-btn-primary w-full"
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
