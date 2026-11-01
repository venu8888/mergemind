import React, { useEffect, useState, useCallback } from 'react';
import { Header, type TabType } from './components/Header';
import { DashboardOverview } from './components/DashboardOverview';
import { HealthView } from './components/HealthView';
import { CIFailureExplorer } from './components/CIFailureExplorer';
import { RemediationCenter } from './components/RemediationCenter';
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
  const [activeTab, setActiveTab] = useState<TabType>('dashboard');
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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
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
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {error && (
          <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => initApp()}
              className="text-xs text-rose-300 hover:text-white underline font-medium"
            >
              Retry
            </button>
          </div>
        )}

        {/* Tab Views */}
        {activeTab === 'dashboard' && (
          <DashboardOverview
            dashboard={dashboard}
            onNavigateToTab={(tab: TabType) => setActiveTab(tab)}
            onProposeForFailure={() => setActiveTab('remediation')}
          />
        )}

        {activeTab === 'health' && (
          <HealthView
            repositoryId={selectedRepoId}
            dashboard={dashboard}
            onRefresh={loadRepositoryData}
          />
        )}

        {activeTab === 'ci-failures' && (
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
      <footer className="border-t border-slate-900 bg-slate-950/80 py-6 mt-12 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-400">MergeMind v4.2.0</span>
            <span>•</span>
            <span>Intelligent Repository Health & Automated Remediation Platform</span>
          </div>
          <div className="flex items-center gap-4">
            <a
              href="http://localhost:8000/api/v1/docs"
              target="_blank"
              rel="noreferrer"
              className="hover:text-indigo-400 transition-colors"
            >
              Interactive OpenAPI Docs
            </a>
            <span>•</span>
            <span className="text-slate-600">PostgreSQL 18 + Docker Sandbox Isolation</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
