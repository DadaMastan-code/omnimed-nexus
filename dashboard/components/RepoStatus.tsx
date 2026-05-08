"use client";

import { useEffect, useState } from "react";
import { GitBranch, Star, AlertCircle } from "lucide-react";
import clsx from "clsx";

interface RepoInfo {
  repo: string;
  stars: number;
  open_issues: number;
  open_prs: number;
  last_push: string;
  language: string;
  error?: string;
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const REPOS = [
  { slug: "DadaMastan-code/codesense-ai", label: "codesense-ai", color: "violet" },
  { slug: "DadaMastan-code/MedFusion-Leuk", label: "MedFusion-Leuk", color: "sky" },
  { slug: "DadaMastan-code/medbrain-ai", label: "medbrain-ai", color: "emerald" },
];

export default function RepoStatus() {
  const [statuses, setStatuses] = useState<Record<string, RepoInfo>>({});

  useEffect(() => {
    const fetchAll = async () => {
      const results = await Promise.all(
        REPOS.map(async (r) => {
          try {
            const res = await fetch(`${API}/query`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ query: `get_repo_status ${r.slug}` }),
            });
            const data = await res.json();
            return [r.slug, data] as const;
          } catch {
            return [r.slug, { error: "unreachable" }] as const;
          }
        })
      );
      setStatuses(Object.fromEntries(results));
    };

    fetchAll();
    const id = setInterval(fetchAll, 60_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {REPOS.map((r) => {
        const s = statuses[r.slug];
        return (
          <div
            key={r.slug}
            className={clsx(
              "rounded-xl border p-5 space-y-3",
              r.color === "violet" && "border-violet-800 bg-violet-950/30",
              r.color === "sky" && "border-sky-800 bg-sky-950/30",
              r.color === "emerald" && "border-emerald-800 bg-emerald-950/30",
            )}
          >
            <div className="flex items-center justify-between">
              <span className={clsx(
                "font-semibold text-sm",
                r.color === "violet" && "text-violet-300",
                r.color === "sky" && "text-sky-300",
                r.color === "emerald" && "text-emerald-300",
              )}>
                {r.label}
              </span>
              {s && !s.error && (
                <span className="flex items-center gap-1 text-xs text-yellow-400">
                  <Star size={12} /> {s.stars}
                </span>
              )}
            </div>

            {s ? (
              s.error ? (
                <p className="text-red-400 text-xs">Unreachable</p>
              ) : (
                <div className="space-y-1 text-xs text-gray-400">
                  <div className="flex items-center gap-2">
                    <AlertCircle size={12} className="text-orange-400" />
                    <span>{s.open_issues} open issues</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <GitBranch size={12} className="text-blue-400" />
                    <span>{s.open_prs} open PRs</span>
                  </div>
                  {s.last_push && (
                    <p className="text-gray-600 truncate">
                      Last push: {new Date(s.last_push).toLocaleDateString()}
                    </p>
                  )}
                </div>
              )
            ) : (
              <div className="h-12 animate-pulse bg-gray-800 rounded" />
            )}
          </div>
        );
      })}
    </div>
  );
}
