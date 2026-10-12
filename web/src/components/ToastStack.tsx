import { useEffect, type Dispatch, type SetStateAction } from "react";

export type ToastItem = {
  id: string;
  message: string;
  variant?: "error" | "info";
};

export function ToastStack({
  toasts,
  onDismiss,
}: {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}) {
  return (
    <div className="toast-stack" aria-live="assertive">
      {toasts.map((t) => (
        <Toast key={t.id} item={t} onDismiss={() => onDismiss(t.id)} />
      ))}
    </div>
  );
}

function Toast({ item, onDismiss }: { item: ToastItem; onDismiss: () => void }) {
  useEffect(() => {
    const id = setTimeout(onDismiss, 8000);
    return () => clearTimeout(id);
  }, [onDismiss]);

  return (
    <div className={`toast toast-${item.variant ?? "info"}`} role="alert">
      <span>{item.message}</span>
      <button type="button" className="toast-close" onClick={onDismiss} aria-label="Dismiss">
        ×
      </button>
    </div>
  );
}

export function pushToast(
  setToasts: Dispatch<SetStateAction<ToastItem[]>>,
  message: string,
  variant: "error" | "info" = "info",
) {
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
  setToasts((prev) => [...prev, { id, message, variant }]);
}
