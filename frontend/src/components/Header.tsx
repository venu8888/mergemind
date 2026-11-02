import React from 'react';
import {
  ShieldCheck,
  Activity,
  Terminal,
  Wrench,
  RefreshCw,
  FolderGit2,
  Cpu,
  GitPullRequest,
} from 'lucide-react';
import type { Repository } from '../types';

export type TabType =
  | 'overview'
  | 'explorer'
  | 'intelligence'
  | 'quality-security'
  | 'pull-requests'
  | 'ci-intelligence'
  | 'remediation';

interface HeaderProps {
  repositories: Repository[];
  selectedRepoId: string;
  onSelectRepo: (id: string) => void;
  activeTab: TabType;
  onSelectTab: (tab: TabType) => void;
  isRefreshing?: boolean;
  onRefresh?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  repositories,
  selectedRepoId,
  onSelectRepo,
  activeTab,
  onSelectTab,
  isRefreshing,
  onRefresh,
}) => {
  return (
    <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Platform Title */}
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-600/30">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg text-white tracking-tight">MergeMind</span>
                <span className="px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded bg-indigo-950 text-indigo-400 border border-indigo-800/60">
                  Platform v4.2
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                AI-Powered GitHub Repository Management & Intelligence Platform
              </p>
            </div>
          </div>

          {/* Repository Selector & Refresh */}
          <div className="flex items-center space-x-3">
            {repositories.length > 0 && (
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-400 font-medium hidden md:inline">Repository:</span>
                <select
                  value={selectedRepoId}
                  onChange={(e) => onSelectRepo(e.target.value)}
                  className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500 font-mono"
                >
                  {repositories.map((repo) => (
                    <option key={repo.id} value={repo.id}>
                      {repo.full_name || repo.name || repo.id}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={isRefreshing}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition border border-slate-700 disabled:opacity-50"
                title="Refresh Active View"
              >
                <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              </button>
            )}
          </div>
        </div>

        {/* 7-Section Navigation Tabs */}
        <nav className="flex space-x-1 -mb-px overflow-x-auto no-scrollbar">
          <button
            onClick={() => onSelectTab('overview')}
            className={`flex items-center space-x-2 px-3 py-2.5 text-xs font-semibold border-b-2 transition shrink-0 ${
              activeTab === 'overview'
                ? 'border-indigo-500 text-indigo-400 bg-slate-850/40'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Overview</span>
          </button>

          <button
            onClick={() => onSelectTab('explorer')}
            className={`flex items-center space-x-2 px-3 py-2.5 text-xs font-semibold border-b-2 transition shrink-0 ${
              activeTab === 'explorer'
                ? 'border-indigo-500 text-indigo-400 bg-slate-850/40'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <FolderGit2 className="w-3.5 h-3.5" />
            <span>Codebase Explorer</span>
          </button>

          <button
            onClick={() => onSelectTab('intelligence')}
            className={`flex items-center space-x-2 px-3 py-2.5 text-xs font-semibold border-b-2 transition shrink-0 ${
              activeTab === 'intelligence'
                ? 'border-indigo-500 text-indigo-400 bg-slate-850/40'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>Repository Intelligence</span>
          </button>

          <button
            onClick={() => onSelectTab('quality-security')}
            className={`flex items-center space-x-2 px-3 py-2.5 text-xs font-semibold border-b-2 transition shrink-0 ${
              activeTab === 'quality-security'
                ? 'border-indigo-500 text-indigo-400 bg-slate-850/40'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Quality & Security</span>
          </button>

          <button
            onClick={() => onSelectTab('pull-requests')}
            className={`flex items-center space-x-2 px-3 py-2.5 text-xs font-semibold border-b-2 transition shrink-0 ${
              activeTab === 'pull-requests'
                ? 'border-indigo-500 text-indigo-400 bg-slate-850/40'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <GitPullRequest className="w-3.5 h-3.5" />
            <span>Pull Requests</span>
          </button>

          <button
            onClick={() => onSelectTab('ci-intelligence')}
            className={`flex items-center space-x-2 px-3 py-2.5 text-xs font-semibold border-b-2 transition shrink-0 ${
              activeTab === 'ci-intelligence'
                ? 'border-indigo-500 text-indigo-400 bg-slate-850/40'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>CI/CD Intelligence</span>
          </button>

          <button
            onClick={() => onSelectTab('remediation')}
            className={`flex items-center space-x-2 px-3 py-2.5 text-xs font-semibold border-b-2 transition shrink-0 ${
              activeTab === 'remediation'
                ? 'border-indigo-500 text-indigo-400 bg-slate-850/40'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            <Wrench className="w-3.5 h-3.5" />
            <span>AI Remediation</span>
          </button>
        </nav>
      </div>
    </header>
  );
};
