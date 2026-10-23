type Listener = (event: MessageEvent) => void;

/** Minimal EventSource stand-in for jsdom; tests push events with `emit`. */
export class FakeEventSource {
  static instances: FakeEventSource[] = [];
  url: string;
  closed = false;
  onmessage: Listener | null = null;
  onerror: ((event: Event) => void) | null = null;
  private listeners: Record<string, Listener[]> = {};

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }
  addEventListener(type: string, listener: Listener) {
    (this.listeners[type] ??= []).push(listener);
  }
  removeEventListener(type: string, listener: Listener) {
    this.listeners[type] = (this.listeners[type] ?? []).filter((l) => l !== listener);
  }
  close() {
    this.closed = true;
  }
  emit(data: string, type = "message", lastEventId = "") {
    const event = new MessageEvent(type, { data, lastEventId });
    if (type === "message") this.onmessage?.(event);
    (this.listeners[type] ?? []).forEach((l) => l(event));
  }
}
