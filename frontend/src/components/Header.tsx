import React from 'react';
import { GitPullRequest, ShieldCheck, Terminal } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <GitPullRequest className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              MergeMind
              <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800/50">
                Phase 1 Shell
              </span>
            </span>
            <p className="text-xs text-slate-400 hidden sm:block">
              Intelligent Pull Request Analysis & Verification Framework
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-1.5 text-xs text-slate-400 bg-slate-800/50 px-3 py-1.5 rounded-md border border-slate-700/50">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Evidence-Backed Engine</span>
          </div>
          <div className="flex items-center space-x-1.5 text-xs font-mono text-slate-400 bg-slate-800/50 px-3 py-1.5 rounded-md border border-slate-700/50">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span>v0.1.0</span>
          </div>
        </div>
      </div>
    </header>
  );
};
