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
  GitBranch,
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
  const tabs = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'explorer', label: 'Codebase Explorer', icon: FolderGit2 },
    { id: 'intelligence', label: 'Repository Intelligence', icon: Cpu },
    { id: 'quality-security', label: 'Quality & Security', icon: ShieldCheck },
    { id: 'pull-requests', label: 'Pull Requests', icon: GitPullRequest },
    { id: 'ci-intelligence', label: 'CI/CD Intelligence', icon: Terminal },
    { id: 'remediation', label: 'AI Remediation', icon: Wrench },
  ] as const;

  return (
    <header className="bg-ink-950 border-b border-white/[0.08] sticky top-0 z-40 backdrop-blur-sm">
      <div className="max-w-[1440px] mx-auto px-6">
        {/* Top Bar: Brand, Repo Context & Refresh */}
        <div className="flex items-center justify-between h-14">
          {/* Product Title */}
          <div className="flex items-baseline gap-3">
            <span className="font-bold text-lg sm:text-xl tracking-tight text-white">
              MergeMind
            </span>
            <span className="text-zinc-600 hidden sm:inline text-xs font-mono">•</span>
            <span className="text-xs text-zinc-400 hidden sm:inline font-normal">
              Repository Verification & Automated Remediation
            </span>
          </div>

          {/* Repository Selector & Status */}
          <div className="flex items-center gap-3">
            {repositories.length > 0 && (
              <div className="flex items-center gap-2 bg-ink-900 border border-white/[0.08] px-2.5 py-1 rounded-control">
                <GitBranch className="w-3.5 h-3.5 text-zinc-400 shrink-0" strokeWidth={1.5} />
                <select
                  value={selectedRepoId}
                  onChange={(e) => onSelectRepo(e.target.value)}
                  className="bg-transparent text-zinc-200 text-xs font-mono focus:outline-none cursor-pointer pr-1"
                >
                  {repositories.map((repo) => (
                    <option key={repo.id} value={repo.id} className="bg-ink-900 text-zinc-200">
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
                className="p-1.5 rounded-control bg-ink-900 hover:bg-ink-800 text-zinc-400 hover:text-zinc-200 transition-colors border border-white/[0.08] disabled:opacity-50"
                title="Refresh Active View"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} strokeWidth={1.5} />
              </button>
            )}
          </div>
        </div>

        {/* 7-Section Navigation Tabs */}
        <nav className="flex space-x-1 -mb-px overflow-x-auto no-scrollbar">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onSelectTab(tab.id as TabType)}
                className={`flex items-center gap-2 px-3 py-2 text-xs font-medium border-b-2 transition-colors shrink-0 ${
                  isActive
                    ? 'border-zinc-200 text-zinc-100'
                    : 'border-transparent text-zinc-400 hover:text-zinc-200 hover:border-zinc-700'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-zinc-100' : 'text-zinc-500'}`} strokeWidth={1.5} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
