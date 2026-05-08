"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle, Code, Brain, Microscope } from "lucide-react";
import clsx from "clsx";

interface Finding {
  repo: string;
  type: string;
  description: string;
  severity: string;
  timestamp: string;
  resolved: boolean;
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "text-red-400 border-red-800",
  high: "text-orange-400 border-orange-800",
  medium: "text-yellow-400 border-yellow-800",
  low: "text-green-400 border-green-800",
};

const TYPE_ICON: Record<string, React.ReactNode> = {
  code_issue: <Code size={14} />,
  model_drift: <Brain size={14} />,
  clinical_flag: <Microscope size={14} />,
  config_change: <CheckCircle size={14} />,
};

export default function ActivityFeed() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch_ = async () => {
      try {
        const res = await fetch(`${API}/findings`);
        const data: Finding[] = await res.json();
        setFindings(data.slice(0, 20));
      } catch {
        /* API not yet running */
      } finally {
        setLoading(false);
      }
    };
    fetch_();
    const id = setInterval(fetch_, 30_000);
    return () => clearInterval(id);
  }, []);

  if (loading) return <div className="h-48 animate-pulse bg-gray-800 rounded-xl" />;

  if (!findings.length) {
    return (
      <div className="rounded-xl border border-gray-800 p-8 text-center text-gray-500">
        No open findings. All systems nominal.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {findings.map((f, i) => (
        <div
          key={i}
          className={clsx(
            "rounded-lg border px-4 py-3 flex items-start gap-3 text-sm",
            SEVERITY_COLOR[f.severity] ?? "text-gray-400 border-gray-800",
          )}
        >
          <span className="mt-0.5 shrink-0">
            {TYPE_ICON[f.type] ?? <AlertTriangle size={14} />}
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold capitalize">{f.type.replace("_", " ")}</span>
              <span className="text-gray-500 text-xs">{f.repo.split("/")[1]}</span>
              <span className="text-gray-600 text-xs ml-auto">
                {new Date(f.timestamp).toLocaleString()}
              </span>
            </div>
            <p className="text-gray-300 text-xs mt-1 line-clamp-2">{f.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
