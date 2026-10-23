import { useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type { BotStatus } from "./types";

export function useBotStatus() {
  return useQuery({ queryKey: ["bot-status"], queryFn: () => api<BotStatus>("/api/bot/status"), refetchInterval: 2000 });
}
