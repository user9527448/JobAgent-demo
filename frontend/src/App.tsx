import { useCallback, useEffect, useState } from "react";

import { AppShell } from "./components/app-shell";
import { MorningBriefing } from "./components/morning-briefing";
import {
  DashboardRequestError,
  getBriefing,
  getHealth,
  type BriefingResponse,
  type HealthSnapshot,
} from "./lib/api";

const initialHealth: HealthSnapshot = {
  live: "unreachable",
  ready: "unreachable",
};

export function App() {
  const [data, setData] = useState<BriefingResponse | null>(null);
  const [health, setHealth] = useState<HealthSnapshot>(initialHealth);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [requestId, setRequestId] = useState(0);

  const retry = useCallback(() => {
    setLoading(true);
    setError(null);
    setRequestId((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void getHealth(controller.signal).then(setHealth);
    void getBriefing(controller.signal)
      .then((response) => {
        setData(response);
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError")
          return;
        setError(
          reason instanceof DashboardRequestError
            ? reason.message
            : "暂时无法读取简报证据，请稍后重试。",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [requestId]);

  return (
    <AppShell health={health} timezone={data?.timezone}>
      <MorningBriefing
        data={data}
        error={error}
        loading={loading}
        onRetry={retry}
      />
    </AppShell>
  );
}
