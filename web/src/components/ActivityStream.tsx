import { useEffect, useRef } from "react";
import type { JobEvent } from "../types/events";

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "—";
  }
}

function kindLabel(kind: string): string {
  const map: Record<string, string> = {
    system: "SYS",
    stage: "PIPE",
    agent: "AGENT",
    tool: "TOOL",
  };
  return map[kind] ?? kind.toUpperCase().slice(0, 4);
}

export function ActivityStream({ events }: { events: JobEvent[] }) {
  const tail = useRef<HTMLDivElement>(null);

  useEffect(() => {
    tail.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  return (
    <div className="activity-stream">
      <div className="activity-head">
        <p className="governance-label">Live activity</p>
        <p className="activity-sub">Agent calls, tools, pipeline stages</p>
      </div>
      <div className="activity-table-wrap">
        <table className="activity-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Type</th>
              <th>Event</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {events.length === 0 && (
              <tr>
                <td colSpan={4} className="activity-empty">
                  Waiting for events…
                </td>
              </tr>
            )}
            {events.map((ev, i) => (
              <tr key={`${ev.ts}-${i}`} className={`activity-row activity-${ev.kind}`}>
                <td>{formatTime(ev.ts)}</td>
                <td>
                  <span className="activity-badge">{kindLabel(ev.kind)}</span>
                </td>
                <td>{ev.title}</td>
                <td className="activity-detail">
                  <span>{ev.detail}</span>
                  {ev.data && (
                    <pre className="activity-json">{JSON.stringify(ev.data, null, 2)}</pre>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div ref={tail} />
      </div>
    </div>
  );
}
