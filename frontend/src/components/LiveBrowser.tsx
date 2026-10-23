import Icon from "./Icon";

export const NOVNC_URL = "/novnc/vnc.html?autoconnect=1&resize=scale&reconnect=1&path=novnc/websockify";

export default function LiveBrowser() {
  return (
    <section aria-label="Live browser" className="panel flex min-w-0 flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-line px-4 py-2">
        <h2 className="text-sm font-semibold">Live browser</h2>
        <a href={NOVNC_URL} target="_blank" rel="noreferrer" className="btn-ghost min-h-[32px] text-sm">
          Open full screen
          <Icon name="external" className="h-4 w-4" />
        </a>
      </div>
      <div className="aspect-video w-full bg-ink focus-within:outline focus-within:outline-2 focus-within:-outline-offset-2 focus-within:outline-signal">
        <iframe title="Live browser" src={NOVNC_URL} className="h-full w-full border-0" />
      </div>
      <p className="px-4 py-2 text-[13px] text-muted">Click inside to control Chrome: solve a captcha, finish 2FA or answer a question.</p>
    </section>
  );
}
