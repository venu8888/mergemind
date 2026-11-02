import React, { useState } from 'react';
import {
  Search,
  FileCode,
  RotateCw,
  Terminal,
  PlusCircle,
  Copy,
  Check,
  ShieldCheck,
  Wrench,
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
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950/60 text-rose-400 border border-rose-800/60">
            TEST FAILURE
          </span>
        );
      case 'LINT_ERROR':
        return (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950/60 text-amber-400 border border-amber-800/60">
            LINT ERROR
          </span>
        );
      case 'SECURITY_VIOLATION':
        return (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950/80 text-rose-300 border border-rose-700">
            SECURITY
          </span>
        );
      default:
        return (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-ink-850 text-zinc-400 border border-white/[0.06]">
            {category || 'BUILD ERROR'}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-ink-900 border border-white/[0.08] px-5 py-3.5 rounded-panel">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-control bg-ink-800 border border-white/[0.08] flex items-center justify-center text-zinc-200">
            <Terminal className="w-3.5 h-3.5" strokeWidth={1.5} />
          </div>
          <div>
            <h2 className="text-xs font-semibold text-white">CI/CD Failure Intelligence</h2>
            <p className="text-[11px] text-zinc-500">
              Deterministic log parsing, credential scrubbing, and stack-frame localization
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowIngestModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-ink-850 hover:bg-ink-800 text-zinc-200 text-xs font-mono border border-white/[0.08] transition-colors"
          >
            <PlusCircle className="w-3 h-3 text-zinc-400" strokeWidth={1.5} />
            <span>Ingest Failure Log</span>
          </button>

          <button
            onClick={onRefresh}
            className="p-1.5 rounded-control bg-ink-850 hover:bg-ink-800 text-zinc-400 hover:text-white transition-colors border border-white/[0.08]"
            title="Refresh Failures"
          >
            <RotateCw className="w-3.5 h-3.5" strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-ink-900 border border-white/[0.08] p-3 rounded-panel font-mono text-xs">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Search className="w-3.5 h-3.5 text-zinc-500 shrink-0 ml-1" strokeWidth={1.5} />
          <input
            type="text"
            placeholder="Search commits, workflows, or error messages..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-transparent text-zinc-200 placeholder:text-zinc-600 focus:outline-none w-full sm:w-80 text-xs"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="bg-ink-950 border border-white/[0.08] text-zinc-300 text-xs px-2.5 py-1 rounded-control focus:outline-none"
          >
            <option value="ALL">All Categories</option>
            <option value="TEST_FAILURE">Test Failure</option>
            <option value="LINT_ERROR">Lint / Style</option>
            <option value="SECURITY_VIOLATION">Security</option>
          </select>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-ink-950 border border-white/[0.08] text-zinc-300 text-xs px-2.5 py-1 rounded-control focus:outline-none"
          >
            <option value="ALL">All Statuses</option>
            <option value="ANALYZED">Analyzed</option>
            <option value="REMEDIATION_PROPOSED">Remediation Proposed</option>
          </select>
        </div>
      </div>

      {/* Two-Column Explorer Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Failure List */}
        <div className="lg:col-span-5 space-y-2.5">
          <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500 px-1">
            Recorded Failures ({filteredFailures.length})
          </div>

          <div className="space-y-2 max-h-[720px] overflow-y-auto pr-1">
            {filteredFailures.length > 0 ? (
              filteredFailures.map((failure) => {
                const isSelected = failure.id === selectedFailure?.id;
                const cat = failure.classification || failure.failure_category;
                const summary = failure.error_summary || failure.error_message || failure.log_excerpt;
                return (
                  <div
                    key={failure.id}
                    onClick={() => setSelectedFailureId(failure.id)}
                    className={`p-3.5 rounded-panel cursor-pointer transition-colors border ${
                      isSelected
                        ? 'bg-ink-800 border-white/[0.15]'
                        : 'bg-ink-900 border-white/[0.08] hover:border-zinc-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <div className="text-xs font-semibold text-white truncate font-mono">
                        {failure.workflow_name || 'Workflow Run'}
                      </div>
                      {getCategoryBadge(cat)}
                    </div>

                    <p className="text-xs text-zinc-400 font-sans line-clamp-2 mb-2 leading-relaxed">
                      {summary || 'No summary parsed'}
                    </p>

                    <div className="flex items-center justify-between text-[11px] text-zinc-500 font-mono">
                      <span>Commit: {failure.commit_sha ? failure.commit_sha.substring(0, 7) : '—'}</span>
                      <span>{new Date(failure.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-8 text-center bg-ink-900 border border-white/[0.08] rounded-panel text-zinc-500 text-xs font-mono">
                No CI failures match the current filter criteria.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Deep-Dive Panel */}
        <div className="lg:col-span-7">
          {selectedFailure ? (
            <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-5 space-y-5">
              {/* Detail Header */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-white/[0.08]">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white font-mono">
                      {selectedFailure.workflow_name || 'Workflow Run'}
                    </span>
                    {getCategoryBadge(selectedFailure.classification || selectedFailure.failure_category)}
                  </div>
                  <div className="text-xs text-zinc-500 font-mono">
                    ID: {selectedFailure.id.substring(0, 8)} • Commit: {selectedFailure.commit_sha?.substring(0, 7)}
                  </div>
                </div>

                <button
                  onClick={() => handleCreateProposal(selectedFailure.id)}
                  disabled={isProposing}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-ink-800 hover:bg-ink-700 disabled:bg-ink-800 text-zinc-100 text-xs font-mono font-medium border border-white/[0.08] transition-colors shrink-0"
                >
                  {isProposing ? (
                    <>
                      <RotateCw className="w-3 h-3 animate-spin text-zinc-400" strokeWidth={1.5} />
                      <span>Synthesizing...</span>
                    </>
                  ) : (
                    <>
                      <Wrench className="w-3 h-3 text-zinc-300" strokeWidth={1.5} />
                      <span>Fix with AI</span>
                    </>
                  )}
                </button>
              </div>

              {/* Error Summary Box */}
              <div className="p-3.5 rounded-control bg-ink-950 border border-white/[0.06] space-y-1.5 font-mono text-xs">
                <div className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">
                  Primary Error Signature
                </div>
                <div className="text-rose-300 font-medium">
                  {selectedFailure.error_summary || selectedFailure.error_message || 'Assertion failed'}
                </div>
              </div>

              {/* Localized Root Cause Files */}
              <div className="space-y-2">
                <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">
                  Localized Root Cause Files ({selectedFailure.localized_files?.length || 0})
                </div>

                {selectedFailure.localized_files && selectedFailure.localized_files.length > 0 ? (
                  <div className="space-y-1.5">
                    {selectedFailure.localized_files.map((loc: any, idx: number) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded-control bg-ink-950 border border-white/[0.06] flex items-center justify-between font-mono text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <FileCode className="w-3.5 h-3.5 text-zinc-400" strokeWidth={1.5} />
                          <span className="text-zinc-200">{loc.file_path}</span>
                          {loc.line_number && <span className="text-zinc-500">:{loc.line_number}</span>}
                        </div>
                        <span className="text-[11px] text-zinc-500">
                          {Math.round((loc.confidence || 0.85) * 100)}% conf
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-3 bg-ink-950 rounded-control border border-white/[0.06] text-zinc-500 text-xs font-mono">
                    No files localized from stack frames.
                  </div>
                )}
              </div>

              {/* Raw Sanitized Log Console */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs font-mono text-zinc-500">
                  <div className="flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" strokeWidth={1.5} />
                    <span>Sanitized CI Log (Secrets Scrubbed)</span>
                  </div>
                  <button
                    onClick={() => handleCopyLog(selectedFailure.log_excerpt || '')}
                    className="inline-flex items-center gap-1 hover:text-zinc-300 transition-colors"
                  >
                    {copiedLog ? (
                      <Check className="w-3 h-3 text-emerald-400" strokeWidth={1.5} />
                    ) : (
                      <Copy className="w-3 h-3 text-zinc-500" strokeWidth={1.5} />
                    )}
                    <span>{copiedLog ? 'Copied' : 'Copy Log'}</span>
                  </button>
                </div>

                <div className="p-3.5 rounded-control bg-ink-950 border border-white/[0.08] font-mono text-xs text-zinc-300 max-h-[300px] overflow-y-auto leading-relaxed select-text whitespace-pre-wrap">
                  {selectedFailure.log_excerpt || 'No log excerpt available.'}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center p-12 bg-ink-900 border border-white/[0.08] rounded-panel text-zinc-500 text-xs font-mono">
              Select a CI Failure record to view sanitized logs and root-cause localization.
            </div>
          )}
        </div>
      </div>

      {/* Ingestion Modal */}
      {showIngestModal && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-ink-900 border border-white/[0.1] rounded-panel max-w-xl w-full p-6 space-y-4 font-mono text-xs shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
              <span className="text-sm font-semibold text-white">Ingest CI Failure Log</span>
              <button onClick={() => setShowIngestModal(false)} className="text-zinc-500 hover:text-zinc-200">
                Cancel
              </button>
            </div>

            <form onSubmit={handleIngest} className="space-y-4 font-sans text-xs">
              <div>
                <label className="block text-zinc-400 font-mono text-[11px] mb-1">Workflow Name</label>
                <input
                  type="text"
                  value={formWorkflowName}
                  onChange={(e) => setFormWorkflowName(e.target.value)}
                  className="w-full bg-ink-950 border border-white/[0.08] rounded-control px-3 py-1.5 text-zinc-200 font-mono focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-zinc-400 font-mono text-[11px] mb-1">Target Commit SHA</label>
                <input
                  type="text"
                  value={formCommitSha}
                  onChange={(e) => setFormCommitSha(e.target.value)}
                  className="w-full bg-ink-950 border border-white/[0.08] rounded-control px-3 py-1.5 text-zinc-200 font-mono focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-zinc-400 font-mono text-[11px] mb-1">Raw Log Excerpt</label>
                <textarea
                  rows={6}
                  value={formRawLog}
                  onChange={(e) => setFormRawLog(e.target.value)}
                  className="w-full bg-ink-950 border border-white/[0.08] rounded-control p-3 text-zinc-300 font-mono text-xs leading-relaxed focus:outline-none"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowIngestModal(false)}
                  className="px-3 py-1.5 rounded-control bg-ink-800 text-zinc-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isIngesting}
                  className="px-4 py-1.5 rounded-control bg-emerald-600 hover:bg-emerald-500 disabled:bg-ink-800 text-white font-mono font-medium transition-colors"
                >
                  {isIngesting ? 'Ingesting...' : 'Ingest & Classify'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
