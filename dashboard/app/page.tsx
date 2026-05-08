import RepoStatus from "@/components/RepoStatus";
import ActivityFeed from "@/components/ActivityFeed";
import { Suspense } from "react";

export default function Home() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">
          OmniMed-Nexus <span className="text-emerald-400">Command Center</span>
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          Unified orchestration for codesense-ai · MedFusion-Leuk · medbrain-ai
        </p>
      </div>

      {/* Repo health cards */}
      <section>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Repository Health
        </h2>
        <Suspense fallback={<div className="h-32 animate-pulse bg-gray-800 rounded-xl" />}>
          <RepoStatus />
        </Suspense>
      </section>

      {/* System architecture overview */}
      <section className="rounded-xl border border-gray-800 bg-gray-900/50 p-6">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
          System Architecture
        </h2>
        <pre className="text-xs text-gray-400 leading-relaxed overflow-auto">
{`
  ┌─────────────────────────────────────────────────────────────┐
  │                     OmniMed-Nexus Hub                       │
  │                                                             │
  │  GitHub Webhooks ──► Webhook Server ──► Meta-Agent          │
  │                                          │                  │
  │                           ┌─────────────┼──────────────┐   │
  │                           ▼             ▼              ▼   │
  │                     codesense-ai  MedFusion-Leuk  medbrain  │
  │                     (code review) (diagnosis)    (reasoning)│
  │                           │             │              │    │
  │                           └─────────────┴──────────────┘   │
  │                                         │                   │
  │                              Qdrant · Neo4j · MLflow        │
  └─────────────────────────────────────────────────────────────┘
`}
        </pre>
      </section>

      {/* Activity feed */}
      <section>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Live Findings
        </h2>
        <Suspense fallback={<div className="h-48 animate-pulse bg-gray-800 rounded-xl" />}>
          <ActivityFeed />
        </Suspense>
      </section>
    </div>
  );
}
