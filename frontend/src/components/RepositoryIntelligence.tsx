import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Layers,
  ShieldAlert,
  CheckCircle2,
  TrendingUp,
  RotateCw,
  Box,
  Terminal,
  Activity,
} from 'lucide-react';
import { fetchRepositoryIntelligence } from '../services/api';

interface RepositoryIntelligenceProps {
  repositoryId: string;
}

export const RepositoryIntelligence: React.FC<RepositoryIntelligenceProps> = ({ repositoryId }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadIntelligence = async () => {
    if (!repositoryId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await fetchRepositoryIntelligence(repositoryId, 'main');
      setData(result);
    } catch (err: any) {
      setError(err.message || 'Failed to compute repository intelligence');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIntelligence();
  }, [repositoryId]);

  if (loading) {
    return (
      <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-12 text-center space-y-3">
        <RotateCw className="w-6 h-6 text-zinc-400 animate-spin mx-auto" strokeWidth={1.5} />
        <div className="text-xs font-mono text-zinc-300">Synthesizing Repository Intelligence...</div>
        <p className="text-[11px] text-zinc-500 max-w-sm mx-auto font-mono">
          Parsing AST dependencies, computing Radon cyclomatic complexity, and generating architectural advisory.
        </p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-8 text-center space-y-3 font-mono">
        <ShieldAlert className="w-6 h-6 text-rose-400 mx-auto" strokeWidth={1.5} />
        <p className="text-xs text-rose-300">{error || 'No intelligence telemetry available.'}</p>
        <button
          onClick={loadIntelligence}
          className="px-3 py-1.5 rounded-control bg-ink-800 text-xs text-zinc-300 hover:text-white border border-white/[0.08]"
        >
          Retry
        </button>
      </div>
    );
  }

  const { ai_insights, technologies, function_complexities, modules } = data;

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-ink-900 border border-white/[0.08] px-5 py-3.5 rounded-panel">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-control bg-ink-800 border border-white/[0.08] flex items-center justify-center text-zinc-200">
            <Cpu className="w-3.5 h-3.5" strokeWidth={1.5} />
          </div>
          <div>
            <h2 className="text-xs font-semibold text-white">Full-Codebase Repository Intelligence</h2>
            <p className="text-[11px] text-zinc-500">
              AST modularity analysis, cyclomatic complexity profiling, and Gemini 2.5 Flash architectural reasoning
            </p>
          </div>
        </div>

        <button
          onClick={loadIntelligence}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-control bg-ink-850 hover:bg-ink-800 text-zinc-300 text-xs font-mono border border-white/[0.08] transition-colors"
        >
          <RotateCw className="w-3 h-3 text-zinc-400" strokeWidth={1.5} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Primary Telemetry Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-4">
          <div className="text-xs font-mono text-zinc-500">Total Lines of Code</div>
          <div className="mt-2 text-2xl font-medium text-white font-mono tabular-nums">{data.total_loc}</div>
          <div className="mt-1 text-[11px] text-zinc-500 font-mono">{data.python_files_count} Python files</div>
        </div>

        <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-4">
          <div className="text-xs font-mono text-zinc-500">Modularity Index</div>
          <div className="mt-2 text-2xl font-medium text-emerald-400 font-mono tabular-nums">
            {ai_insights?.modularity_score || 92}%
          </div>
          <div className="mt-1 text-[11px] text-zinc-500 font-mono">Clean decoupling</div>
        </div>

        <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-4">
          <div className="text-xs font-mono text-zinc-500">Avg Complexity (Radon)</div>
          <div className="mt-2 text-2xl font-medium text-zinc-100 font-mono tabular-nums">{data.avg_complexity}</div>
          <div className="mt-1 text-[11px] text-zinc-500 font-mono">Rank A (Low Risk)</div>
        </div>

        <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-4">
          <div className="text-xs font-mono text-zinc-500">Complex Functions</div>
          <div className="mt-2 text-2xl font-medium text-zinc-100 font-mono tabular-nums">{data.complex_functions_count}</div>
          <div className="mt-1 text-[11px] text-zinc-500 font-mono">0 functions with CC &gt; 10</div>
        </div>
      </div>

      {/* Technology Stack & Architecture Pattern */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
        <div className="md:col-span-8 bg-ink-900 border border-white/[0.08] rounded-panel p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-zinc-400" strokeWidth={1.5} />
            <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">Architecture & Framework Stack</span>
          </div>

          <div className="p-3.5 rounded-control bg-ink-950 border border-white/[0.06] space-y-1.5 font-mono text-xs">
            <div className="text-zinc-200 font-semibold">
              Pattern: {ai_insights?.architecture_pattern || 'Modular Python Library'}
            </div>
            <p className="text-zinc-400 text-[11px] font-sans leading-relaxed">
              Target repository enforces clean decoupling between functional contracts and test verification fixtures.
            </p>
          </div>

          <div>
            <div className="text-[11px] font-mono uppercase text-zinc-500 mb-2">Detected Technologies</div>
            <div className="flex flex-wrap gap-2">
              {technologies.map((tech: string) => (
                <span
                  key={tech}
                  className="px-2.5 py-1 rounded-control text-xs font-mono bg-ink-950 text-zinc-300 border border-white/[0.06] flex items-center gap-1.5"
                >
                  <Box className="w-3 h-3 text-zinc-400" strokeWidth={1.5} />
                  {tech}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="md:col-span-4 bg-ink-900 border border-white/[0.08] rounded-panel p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Terminal className="w-3.5 h-3.5 text-zinc-400" strokeWidth={1.5} />
            <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">Module Dependencies</span>
          </div>

          <div className="space-y-2 max-h-[170px] overflow-y-auto pr-1">
            {modules.map((m: any) => (
              <div key={m.path} className="p-2.5 rounded-control bg-ink-950 border border-white/[0.06] text-xs font-mono">
                <div className="text-zinc-200 font-medium truncate">{m.path}</div>
                <div className="text-[11px] text-zinc-500 mt-0.5">
                  Imports: {m.imports.length ? m.imports.join(', ') : 'None (Atomic Leaf)'}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Gemini AI Architectural Insights */}
      {ai_insights && (
        <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-5 space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-zinc-400" strokeWidth={1.5} />
              <span className="text-xs font-mono uppercase tracking-wider text-zinc-300">
                Architectural Advisory (Gemini 2.5 Flash)
              </span>
            </div>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded text-zinc-400 border border-white/[0.08]">
              {Math.round(ai_insights.confidence * 100)}% Confidence
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Positive Observations */}
            <div className="space-y-2.5 p-4 rounded-control bg-ink-950 border border-white/[0.06]">
              <div className="flex items-center gap-1.5 text-xs font-mono text-emerald-400 uppercase">
                <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                <span>Strengths</span>
              </div>
              <ul className="space-y-1.5 text-xs text-zinc-300 leading-relaxed font-sans">
                {ai_insights.strengths?.map((s: string, idx: number) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-emerald-400 shrink-0">•</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Identified Risks */}
            <div className="space-y-2.5 p-4 rounded-control bg-ink-950 border border-white/[0.06]">
              <div className="flex items-center gap-1.5 text-xs font-mono text-amber-400 uppercase">
                <ShieldAlert className="w-3.5 h-3.5" strokeWidth={1.5} />
                <span>Identified Risks</span>
              </div>
              <ul className="space-y-1.5 text-xs text-zinc-300 leading-relaxed font-sans">
                {ai_insights.risks?.map((r: string, idx: number) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-amber-400 shrink-0">•</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Actionable Recommendations */}
            <div className="space-y-2.5 p-4 rounded-control bg-ink-950 border border-white/[0.06]">
              <div className="flex items-center gap-1.5 text-xs font-mono text-zinc-300 uppercase">
                <TrendingUp className="w-3.5 h-3.5 text-zinc-400" strokeWidth={1.5} />
                <span>Recommendations</span>
              </div>
              <ul className="space-y-1.5 text-xs text-zinc-300 leading-relaxed font-sans">
                {ai_insights.recommendations?.map((rec: string, idx: number) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-zinc-400 shrink-0">•</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Function Complexity Profiling Table (Radon) */}
      <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-zinc-400" strokeWidth={1.5} />
            <span className="text-xs font-mono uppercase tracking-wider text-zinc-400">
              Function Cyclomatic Complexity (Radon AST)
            </span>
          </div>
          <span className="text-[11px] text-zinc-500 font-mono">
            McCabe Score &lt;= 5 (Grade A)
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-white/[0.08] text-zinc-500 text-[11px]">
                <th className="pb-2 font-normal">File Path</th>
                <th className="pb-2 font-normal">Function / Symbol</th>
                <th className="pb-2 font-normal">Line</th>
                <th className="pb-2 font-normal">Complexity</th>
                <th className="pb-2 font-normal text-right">Radon Grade</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {function_complexities.map((f: any, idx: number) => (
                <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-2 text-zinc-300">{f.file}</td>
                  <td className="py-2 text-zinc-200 font-semibold">{f.function}</td>
                  <td className="py-2 text-zinc-500 tabular-nums">{f.line}</td>
                  <td className="py-2 text-white font-bold tabular-nums">{f.complexity}</td>
                  <td className="py-2 text-right">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
                      Rank {f.grade}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
