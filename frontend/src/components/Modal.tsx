import { useEffect, useRef, type ReactNode } from "react";

/** Modal dialog: traps Tab, closes on Escape, returns focus to the opener. */
export default function Modal({ title, onClose, children, role = "dialog", width = "max-w-2xl" }: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  role?: "dialog" | "alertdialog";
  width?: string;
}) {
  const box = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    const focusables = () =>
      Array.from(box.current?.querySelectorAll<HTMLElement>("button, a[href], input, select, textarea, [tabindex]:not([tabindex='-1'])") ?? []);
    focusables()[0]?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.stopPropagation();
        onCloseRef.current();
      } else if (event.key === "Tab") {
        const items = focusables();
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      opener?.focus?.();
    };
  }, []);

  const headingId = `modal-${title.replace(/\W+/g, "-")}`;
  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-[rgba(28,35,33,0.45)] px-4 py-10" onMouseDown={(e) => {
        if (e.target !== e.currentTarget) return;
        e.preventDefault(); // keep the browser from moving focus to <body> after we close
        onClose();
      }}>
      <div ref={box} role={role} aria-modal="true" aria-labelledby={headingId} className={`panel w-full ${width} shadow-xl`}>
        <h2 id={headingId} className="sr-only">
          {title}
        </h2>
        {children}
      </div>
    </div>
  );
}
