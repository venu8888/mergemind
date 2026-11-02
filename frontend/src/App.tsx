import React, { useEffect, useState, useCallback } from 'react';
import { Header, type TabType } from './components/Header';
import { DashboardOverview } from './components/DashboardOverview';
import { HealthView } from './components/HealthView';
import { CIFailureExplorer } from './components/CIFailureExplorer';
import { RemediationCenter } from './components/RemediationCenter';
import { CodebaseExplorer } from './components/CodebaseExplorer';
import { RepositoryIntelligence } from './components/RepositoryIntelligence';
import { PullRequestsView } from './components/PullRequestsView';
import {
  fetchRepositories,
  fetchRepositoryDashboard,
  fetchCIFailures,
  fetchRemediationProposals,
} from './services/api';
import type {
  Repository,
  RepositoryDashboard,
  CIFailure,
  RemediationProposal,
} from './types';
import { AlertCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>('');
  const [dashboard, setDashboard] = useState<RepositoryDashboard | null>(null);
  const [failures, setFailures] = useState<CIFailure[]>([]);
  const [proposals, setProposals] = useState<RemediationProposal[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [initialProposalId, setInitialProposalId] = useState<string | null>(null);

  // Initial load: repositories
  const initApp = async () => {
    setError(null);
    try {
      const repos = await fetchRepositories();
      if (repos.length > 0) {
        setRepositories(repos);
        setSelectedRepoId(repos[0].id);
      } else {
        const defaultRepoId = '00000000-0000-0000-0000-000000000001';
        setSelectedRepoId(defaultRepoId);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to initialize dashboard');
    }
  };

  useEffect(() => {
    initApp();
  }, []);

  // Fetch repository-specific dashboard, failures, and proposals
  const loadRepositoryData = useCallback(async () => {
    if (!selectedRepoId) return;
    try {
      const [dashRes, failRes, propRes] = await Promise.allSettled([
        fetchRepositoryDashboard(selectedRepoId),
        fetchCIFailures(selectedRepoId),
        fetchRemediationProposals(selectedRepoId),
      ]);

      if (dashRes.status === 'fulfilled') {
        setDashboard(dashRes.value);
      }
      if (failRes.status === 'fulfilled') {
        setFailures(failRes.value);
      }
      if (propRes.status === 'fulfilled') {
        setProposals(propRes.value);
      }
    } catch (err: any) {
      console.error('Failed to load repo data:', err);
    }
  }, [selectedRepoId]);

  useEffect(() => {
    if (selectedRepoId) {
      loadRepositoryData();
    }
  }, [selectedRepoId, loadRepositoryData]);

  const handleNavigateToRemediation = (proposalId?: string) => {
    if (proposalId) {
      setInitialProposalId(proposalId);
    }
    setActiveTab('remediation');
  };

  return (
    <div className="min-h-screen bg-ink-950 text-zinc-100 flex flex-col font-sans selection:bg-zinc-700 selection:text-white">
      {/* Top Application Header */}
      <Header
        activeTab={activeTab}
        onSelectTab={(tab: TabType) => setActiveTab(tab)}
        repositories={repositories}
        selectedRepoId={selectedRepoId}
        onSelectRepo={(id: string) => setSelectedRepoId(id)}
        onRefresh={loadRepositoryData}
      />

      {/* Main View Container */}
      <main className="flex-1 max-w-[1440px] w-full mx-auto px-6 py-6 space-y-6">
        {error && (
          <div className="p-3.5 rounded-control bg-ink-950 border border-rose-800/60 text-rose-300 text-xs font-mono flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" strokeWidth={1.5} />
              <span>{error}</span>
            </div>
            <button
              onClick={() => initApp()}
              className="text-[11px] text-rose-300 hover:text-white underline font-medium"
            >
              Retry
            </button>
          </div>
        )}

        {/* 7-Section Tab Views */}
        {activeTab === 'overview' && (
          <DashboardOverview
            dashboard={dashboard}
            onNavigateToTab={(tab: any) => {
              if (tab === 'health') setActiveTab('quality-security');
              else if (tab === 'ci-failures') setActiveTab('ci-intelligence');
              else if (tab === 'remediation') setActiveTab('remediation');
              else setActiveTab(tab);
            }}
          />
        )}

        {activeTab === 'explorer' && (
          <CodebaseExplorer repositoryId={selectedRepoId} />
        )}

        {activeTab === 'intelligence' && (
          <RepositoryIntelligence repositoryId={selectedRepoId} />
        )}

        {activeTab === 'quality-security' && (
          <HealthView
            repositoryId={selectedRepoId}
            dashboard={dashboard}
            onRefresh={loadRepositoryData}
          />
        )}

        {activeTab === 'pull-requests' && (
          <PullRequestsView repositoryId={selectedRepoId} />
        )}

        {activeTab === 'ci-intelligence' && (
          <CIFailureExplorer
            repositoryId={selectedRepoId}
            failures={failures}
            onRefresh={loadRepositoryData}
            onNavigateToRemediation={handleNavigateToRemediation}
          />
        )}

        {activeTab === 'remediation' && (
          <RemediationCenter
            repositoryId={selectedRepoId}
            proposals={proposals}
            initialSelectedProposalId={initialProposalId}
            onRefresh={loadRepositoryData}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-white/[0.08] bg-ink-950 py-5 mt-10 text-xs text-zinc-500 font-mono">
        <div className="max-w-[1440px] mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-zinc-300">MergeMind v4.2.0</span>
            <span>•</span>
            <span className="text-zinc-500 font-sans">Repository Health & Automated Remediation Platform</span>
          </div>
          <div className="flex items-center gap-3 text-[11px]">
            <a
              href="http://localhost:8000/api/v1/docs"
              target="_blank"
              rel="noreferrer"
              className="hover:text-zinc-300 transition-colors"
            >
              Interactive API
            </a>
            <span>•</span>
            <span>PostgreSQL 16 + Docker Sandbox Engine</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
