import React, { useState } from 'react';
import {
  AlertOctagon,
  Search,
  FileCode,
  RotateCw,
  Terminal,
  Sparkles,
  PlusCircle,
  Copy,
  Check,
} from 'lucide-react';
import type { CIFailure } from '../types';
import { ingestCIFailure, generateRemediationProposal } from '../services/api';

interface CIFailureExplorerProps {
  repositoryId: string;
  failures: CIFailure[];
  onRefresh: () => Promise<void>;
  onNavigateToRemediation: (proposalId?: string) => void;
}

export const CIFailureExplorer: React.FC<CIFailureExplorerProps> = ({
  repositoryId,
  failures,
  onRefresh,
  onNavigateToRemediation,
}) => {
  const [selectedFailureId, setSelectedFailureId] = useState<string | null>(
    failures.length > 0 ? failures[0].id : null
  );
  const [filterCategory, setFilterCategory] = useState<string>('ALL');
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isIngesting, setIsIngesting] = useState<boolean>(false);
  const [showIngestModal, setShowIngestModal] = useState<boolean>(false);
  const [isProposing, setIsProposing] = useState<boolean>(false);
  const [copiedLog, setCopiedLog] = useState<boolean>(false);

  // Ingestion form state
  const [formWorkflowName, setFormWorkflowName] = useState('CI / Pull Request Verification');
  const [formCommitSha, setFormCommitSha] = useState('e82a91f37b12d4a');
  const [formRawLog, setFormRawLog] = useState(
    `FAILED tests/test_payment.py::test_calculate_tax - AssertionError: assert 12.0 == 10.0\n` +
    `  + where 12.0 = calculate_tax(100.0, 0.12)\n` +
    `  File "/workspace/src/payment/calculator.py", line 42, in calculate_tax\n` +
    `    return amount * rate\n` +
    `GITHUB_TOKEN=ghp_secretTokenExample1234567890abcdef`
  );

  const selectedFailure =
    failures.find((f) => f.id === selectedFailureId) || (failures.length > 0 ? failures[0] : null);

  const filteredFailures = failures.filter((f) => {
    const cat = f.classification || f.failure_category;
    if (filterCategory !== 'ALL' && cat !== filterCategory) return false;
    if (filterStatus !== 'ALL' && f.status !== filterStatus) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchCommit = f.commit_sha?.toLowerCase().includes(q);
      const matchWf = f.workflow_name?.toLowerCase().includes(q);
      const matchSummary = (f.error_summary || f.error_message)?.toLowerCase().includes(q);
      if (!matchCommit && !matchWf && !matchSummary) return false;
    }
    return true;
  });

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsIngesting(true);
    try {
      await ingestCIFailure({
        repository_id: repositoryId,
        workflow_name: formWorkflowName,
        commit_sha: formCommitSha,
        raw_log: formRawLog,
      });
      setShowIngestModal(false);
      await onRefresh();
    } catch (err: any) {
      alert('Ingestion failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsIngesting(false);
    }
  };

  const handleCreateProposal = async (failureId: string) => {
    setIsProposing(true);
    try {
      const proposal = await generateRemediationProposal(failureId);
      await onRefresh();
      onNavigateToRemediation(proposal.id);
    } catch (err: any) {
      alert('Proposal generation failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsProposing(false);
    }
  };

  const handleCopyLog = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedLog(true);
    setTimeout(() => setCopiedLog(false), 2000);
  };

  const getCategoryBadge = (category?: string) => {
    switch (category) {
      case 'TEST_FAILURE':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-950/70 text-rose-300 border border-rose-800">
            TEST FAILURE
          </span>
        );
      case 'LINT_ERROR':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-950/70 text-amber-300 border border-amber-800">
            LINT / STYLE ERROR
          </span>
        );
      case 'SECURITY_VIOLATION':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-red-950/90 text-red-200 border border-red-700">
            SECURITY VIOLATION
          </span>
        );
      case 'DEPENDENCY_CONFLICT':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-purple-950/70 text-purple-300 border border-purple-800">
            DEPENDENCY CONFLICT
          </span>
        );
      case 'TIMEOUT':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-yellow-950/70 text-yellow-300 border border-yellow-800">
            TIMEOUT
          </span>
        );
      case 'INFRASTRUCTURE_FAILURE':
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            INFRASTRUCTURE
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            {category || 'UNANALYZED'}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-xl">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400">
            <AlertOctagon className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">CI/CD Failure Intelligence Explorer</h2>
            <p className="text-sm text-slate-400">
              Deterministic log classification, secret sanitization, stack localization, and root-cause hypothesis.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowIngestModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors shadow-lg shadow-indigo-900/20"
          >
            <PlusCircle className="w-4 h-4" />
            Ingest CI Log
          </button>
          <button
            onClick={onRefresh}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700"
            title="Refresh Failures"
          >
            <RotateCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center gap-3 bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by commit SHA, workflow, or summary..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-slate-800/80 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-medium">Category:</span>
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg text-xs text-white py-1.5 px-2.5 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Categories</option>
            <option value="TEST_FAILURE">Test Failure</option>
            <option value="LINT_ERROR">Lint Error</option>
            <option value="SECURITY_VIOLATION">Security Violation</option>
            <option value="DEPENDENCY_CONFLICT">Dependency Conflict</option>
            <option value="TIMEOUT">Timeout</option>
            <option value="INFRASTRUCTURE_FAILURE">Infrastructure Failure</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-medium">Status:</span>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg text-xs text-white py-1.5 px-2.5 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="UNANALYZED">Unanalyzed</option>
            <option value="ANALYZED">Analyzed</option>
            <option value="REMEDIATING">Remediating</option>
            <option value="RESOLVED">Resolved</option>
          </select>
        </div>
      </div>

      {/* Two-Column Explorer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Failure List */}
        <div className="lg:col-span-5 space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">
            Recorded Failures ({filteredFailures.length})
          </div>

          <div className="space-y-2.5 max-h-[750px] overflow-y-auto pr-1">
            {filteredFailures.length > 0 ? (
              filteredFailures.map((failure) => {
                const isSelected = failure.id === selectedFailure?.id;
                const cat = failure.classification || failure.failure_category;
                const summary = failure.error_summary || failure.error_message || failure.log_excerpt;
                return (
                  <div
                    key={failure.id}
                    onClick={() => setSelectedFailureId(failure.id)}
                    className={`p-4 rounded-xl cursor-pointer transition-all border ${
                      isSelected
                        ? 'bg-slate-800/90 border-indigo-500 shadow-md shadow-indigo-950/30'
                        : 'bg-slate-900/80 border-slate-800 hover:border-slate-700 hover:bg-slate-850'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="text-sm font-semibold text-white truncate">
                        {failure.workflow_name || 'Workflow Run'}
                      </div>
                      {getCategoryBadge(cat)}
                    </div>

                    <p className="text-xs text-slate-400 line-clamp-2 mb-3">
                      {summary || 'No summary parsed'}
                    </p>

                    <div className="flex items-center justify-between text-xs text-slate-500 font-mono">
                      <span>SHA: {failure.commit_sha ? failure.commit_sha.substring(0, 7) : '—'}</span>
                      <span>{new Date(failure.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-8 text-center bg-slate-900/40 border border-slate-800 rounded-xl text-slate-500 text-sm">
                No CI failures match the current filter criteria.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Deep-Dive Panel */}
        <div className="lg:col-span-7">
          {selectedFailure ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
              {/* Detail Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg font-bold text-white">
                      {selectedFailure.workflow_name || 'Workflow Run'}
                    </span>
                    {getCategoryBadge(selectedFailure.classification || selectedFailure.failure_category)}
                  </div>
                  <div className="text-xs text-slate-400 font-mono">
                    ID: {selectedFailure.id} • Commit: {selectedFailure.commit_sha}
                  </div>
                </div>

                <button
                  onClick={() => handleCreateProposal(selectedFailure.id)}
                  disabled={isProposing}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white font-medium text-xs transition-colors shrink-0 shadow-lg shadow-indigo-900/20"
                >
                  {isProposing ? (
                    <>
                      <RotateCw className="w-3.5 h-3.5 animate-spin" />
                      Generating Proposal...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" />
                      Generate Remediation
                    </>
                  )}
                </button>
              </div>

              {/* Classification & Confidence */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-slate-800/50 p-3.5 rounded-lg border border-slate-700/60">
                  <div className="text-xs text-slate-400 mb-1">Classification Status</div>
                  <div className="text-sm font-semibold text-white flex items-center gap-2">
                    <span>{selectedFailure.classification || selectedFailure.failure_category || 'UNANALYZED'}</span>
                    <span className="text-xs text-slate-400">
                      ({Math.round((selectedFailure.confidence || 0.95) * 100)}% confidence)
                    </span>
                  </div>
                </div>

                <div className="bg-slate-800/50 p-3.5 rounded-lg border border-slate-700/60">
                  <div className="text-xs text-slate-400 mb-1">Failure Status</div>
                  <div className="text-sm font-semibold text-white">
                    {selectedFailure.status}
                  </div>
                </div>
              </div>

              {/* Advisory Root-Cause Hypothesis */}
              {(selectedFailure.root_cause_hypothesis || selectedFailure.ai_advisory_hypothesis) && (
                <div className="bg-indigo-950/30 border border-indigo-800/40 p-4 rounded-xl space-y-2">
                  <div className="flex items-center gap-2 text-indigo-300 text-xs font-semibold uppercase tracking-wider">
                    <Sparkles className="w-4 h-4 text-indigo-400" />
                    Advisory Root-Cause Hypothesis
                  </div>
                  <p className="text-sm text-slate-200">
                    {selectedFailure.root_cause_hypothesis || selectedFailure.ai_advisory_hypothesis}
                  </p>
                  <p className="text-xs text-indigo-300/70 italic">
                    Note: Hypotheses are informational and advisory. All corrective code must pass deterministic sandbox verification before pull request creation.
                  </p>
                </div>
              )}

              {/* Localized Files and Stack Locations */}
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-slate-400" />
                  Localized Stack Locations
                </div>
                {((selectedFailure.stack_locations && selectedFailure.stack_locations.length > 0) ||
                  (selectedFailure.localized_files && selectedFailure.localized_files.length > 0)) ? (
                  <div className="space-y-1.5">
                    {(selectedFailure.stack_locations || selectedFailure.localized_files || []).map((loc: any, idx: number) => (
                      <div
                        key={idx}
                        className="bg-slate-800/70 border border-slate-700/70 px-3 py-2 rounded text-xs font-mono text-slate-300 flex items-center justify-between"
                      >
                        <span className="text-indigo-300">
                          {typeof loc === 'string' ? loc : `${loc.file || loc.file_path || loc.path}:${loc.line || loc.line_number || '?'}`}
                        </span>
                        {loc.function && <span className="text-slate-500">in {loc.function}()</span>}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-slate-500 bg-slate-800/40 p-3 rounded border border-slate-800">
                    No explicit source file locations localized from build log.
                  </div>
                )}
              </div>

              {/* Sanitized Log Viewer */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-slate-400" />
                    Sanitized Log Output
                  </div>
                  <button
                    onClick={() => handleCopyLog(selectedFailure.sanitized_log || selectedFailure.raw_log || selectedFailure.log_excerpt || '')}
                    className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
                  >
                    {copiedLog ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    {copiedLog ? 'Copied' : 'Copy Log'}
                  </button>
                </div>

                <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 font-mono text-xs text-slate-300 max-h-[300px] overflow-y-auto whitespace-pre-wrap leading-relaxed">
                  {selectedFailure.sanitized_log || selectedFailure.raw_log || selectedFailure.log_excerpt || 'No log data recorded.'}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center p-12 bg-slate-900 border border-slate-800 rounded-xl text-slate-500 text-sm">
              Select a CI failure to inspect detailed analysis and logs.
            </div>
          )}
        </div>
      </div>

      {/* Manual Ingestion Modal */}
      {showIngestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <PlusCircle className="w-5 h-5 text-indigo-400" />
              Ingest CI Build Log
            </h3>
            <p className="text-xs text-slate-400">
              Paste raw build failure logs. MergeMind will automatically sanitize credentials, match failure patterns, and localize impacted source code.
            </p>

            <form onSubmit={handleIngest} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Workflow Name</label>
                <input
                  type="text"
                  value={formWorkflowName}
                  onChange={(e) => setFormWorkflowName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Commit SHA</label>
                <input
                  type="text"
                  value={formCommitSha}
                  onChange={(e) => setFormCommitSha(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white font-mono focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Raw CI Log</label>
                <textarea
                  rows={6}
                  value={formRawLog}
                  onChange={(e) => setFormRawLog(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowIngestModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isIngesting}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white text-sm font-medium transition-colors"
                >
                  {isIngesting ? <RotateCw className="w-4 h-4 animate-spin" /> : null}
                  Ingest and Analyze
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
