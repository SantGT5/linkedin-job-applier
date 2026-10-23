import { errorMessage } from "../api/client";
import { useBotStatus } from "../api/useBotStatus";
import BotControls from "../components/BotControls";
import LiveBrowser from "../components/LiveBrowser";
import LogStream from "../components/LogStream";
import NeedsYouBanner from "../components/NeedsYouBanner";

export default function Dashboard() {
  const status = useBotStatus();

  return (
    <div className="mx-auto flex max-w-[1600px] flex-col gap-4">
      <h1 className="sr-only">Dashboard</h1>
      {status.isPending && <div className="panel h-[76px] animate-pulse" role="status" aria-label="Loading bot status" />}
      {status.isError && (
        <p role="alert" className="panel px-5 py-4 text-danger">
          Couldn't load the bot status. {errorMessage(status.error)}
        </p>
      )}
      {status.data && <BotControls status={status.data} />}
      {status.data?.prompt && <NeedsYouBanner prompt={status.data.prompt} />}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <LiveBrowser />
        <LogStream runId={status.data?.run?.id ?? null} />
      </div>
    </div>
  );
}
