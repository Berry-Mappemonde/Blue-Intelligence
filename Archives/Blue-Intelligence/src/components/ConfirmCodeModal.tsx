import { useState } from "react";
import { Lock } from "lucide-react";

interface ConfirmCodeModalProps {
  open: boolean;
  title: string;
  error: string;
  onClose: () => void;
  onConfirm: (code: string) => Promise<void>;
  onError: (msg: string) => void;
  isDark: boolean;
  t: Record<string, string>;
}

export function ConfirmCodeModal({
  open,
  title,
  error,
  onClose,
  onConfirm,
  onError,
  isDark,
  t,
}: ConfirmCodeModalProps) {
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);

  /** Normalise le code (Unicode, caractères invisibles) pour éviter les faux négatifs */
  const normalizeCode = (s: string) =>
    s
      .trim()
      .replace(/\r\n?|\n/g, "")
      .replace(/\uFEFF/g, "")
      .replace(/\u200B|\u200C|\u200D|\u2060/g, "")
      .normalize("NFC");

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const normalized = normalizeCode(code);
    if (!normalized) return;
    setLoading(true);
    try {
      await onConfirm(normalized);
      setCode("");
      onError("");
      onClose();
    } catch (err: any) {
      setCode("");
      onError(err?.message === "invalid" || err?.message === "required" ? (t.invalidConfirmCode || "Invalid code.") : String(err?.message || "Error"));
    } finally {
      setLoading(false);
    }
  };

  const bg = isDark ? "bg-slate-900 border-slate-700" : "bg-white border-slate-200";
  const inputBg = isDark ? "bg-slate-800 border-slate-600 text-white" : "bg-slate-50 border-slate-300 text-slate-900";

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50">
      <div className={`${bg} border rounded-xl shadow-xl p-6 max-w-sm w-full mx-4`}>
        <div className="flex items-center gap-3 mb-4">
          <Lock className="w-6 h-6 text-amber-500" />
          <h3 className="text-lg font-bold">{title}</h3>
        </div>
        <p className={`text-sm mb-4 ${isDark ? "text-slate-400" : "text-slate-600"}`}>
          {t.confirmCodeDesc || "Enter the confirmation code to proceed."}
        </p>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder={t.confirmCodePlaceholder || "Code"}
            className={`w-full px-4 py-2 rounded-lg border ${inputBg} placeholder-slate-500 focus:ring-2 focus:ring-amber-500/50 focus:outline-none`}
            autoFocus
            autoComplete="off"
          />
          {error && (
            <p className="mt-2 text-sm text-red-500">{error}</p>
          )}
          <div className="flex gap-2 mt-4">
            <button
              type="button"
              onClick={onClose}
              className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium ${isDark ? "bg-slate-700 hover:bg-slate-600 text-slate-300" : "bg-slate-200 hover:bg-slate-300 text-slate-700"}`}
            >
              {t.cancel || "Cancel"}
            </button>
            <button
              type="submit"
              disabled={!code.trim() || loading}
              className="flex-1 px-4 py-2 rounded-lg text-sm font-medium bg-amber-500 hover:bg-amber-600 text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "..." : (t.confirm || "Confirm")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
