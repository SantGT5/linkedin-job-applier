import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

type Tone = "success" | "error";
interface ToastItem {
  id: number;
  text: string;
  tone: Tone;
}

const ToastContext = createContext<(text: string, tone?: Tone) => void>(() => {});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);
  const show = useCallback((text: string, tone: Tone = "success") => {
    const id = nextId.current++;
    setItems((current) => [...current, { id, text, tone }]);
  }, []);
  return (
    <ToastContext.Provider value={show}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {items.map((item) => (
          <Toast key={item.id} item={item} onDone={() => setItems((current) => current.filter((t) => t.id !== item.id))} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function Toast({ item, onDone }: { item: ToastItem; onDone: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDone, item.tone === "error" ? 6000 : 4000);
    return () => clearTimeout(timer);
  }, [item, onDone]);
  return (
    <div
      role={item.tone === "error" ? "alert" : "status"}
      className={`pointer-events-auto max-w-sm rounded border px-4 py-3 text-sm shadow-lg ${
        item.tone === "error" ? "border-danger bg-danger-soft text-danger" : "border-pine bg-surface text-ink"
      }`}
    >
      {item.text}
    </div>
  );
}
