import React, { useState } from 'react';
import {
  GitPullRequest,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  FileDiff,
  Play,
  ExternalLink,
  Copy,
  Check,
  Wrench,
} from 'lucide-react';
import type {
  RemediationProposal,
} from '../types';
import {
  verifyRemediationProposal,
  createRemediationPullRequest,
} from '../services/api';

interface RemediationCenterProps {
  repositoryId?: string;
  proposals: RemediationProposal[];
  initialSelectedProposalId?: string | null;
  onRefresh: () => Promise<void>;
}

export const RemediationCenter: React.FC<RemediationCenterProps> = ({
  proposals,
  initialSelectedProposalId,
  onRefresh,
}) => {
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(
    initialSelectedProposalId || (proposals.length > 0 ? proposals[0].id : null)
  );
  const [isVerifying, setIsVerifying] = useState(false);
  const [isCreatingPR, setIsCreatingPR] = useState(false);
  const [copiedDiff, setCopiedDiff] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const selectedProposal =
    proposals.find((p) => p.id === selectedProposalId) || (proposals.length > 0 ? proposals[0] : null);

  const handleVerify = async (proposalId: string) => {
    setIsVerifying(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const verification = await verifyRemediationProposal(proposalId);
      const isVerified = verification.verification_status === 'VERIFIED' || verification.is_verified;
      setActionSuccess(
        `Dual-run verification completed: ${verification.verification_status}. ${
          isVerified
            ? 'Candidate patch confirmed to resolve failure without regressions.'
            : 'Candidate patch failed sandbox verification.'
        }`
      );
      await onRefresh();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || err.message || 'Verification failed');
    } finally {
      setIsVerifying(false);
    }
  };

  const handleCreatePR = async (proposalId: string) => {
    setIsCreatingPR(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const pr = await createRemediationPullRequest(proposalId);
      setActionSuccess(
        `Draft pull request created on GitHub: Branch ${pr.branch_name}. PR #${pr.github_pr_number || pr.pr_number || ''}`
      );
      await onRefresh();
    } catch (err: any) {
      setActionError(err.response?.data?.detail || err.message || 'Draft PR creation failed');
    } finally {
      setIsCreatingPR(false);
    }
  };

  const handleCopyDiff = (diffText: string) => {
    navigator.clipboard.writeText(diffText);
    setCopiedDiff(true);
    setTimeout(() => setCopiedDiff(false), 2000);
  };

  const getProviderInfo = (provider?: string | null, model?: string | null) => {
    const isGemini =
      provider === 'llm' ||
      provider === 'gemini-llm' ||
      provider?.includes('gemini') ||
      model?.includes('gemini');
    if (isGemini) {
      return {
        label: 'Gemini 2.5 Flash',
        badgeClass: 'bg-ink-800 text-zinc-200 border-white/[0.1]',
      };
    }
    return {
      label: 'Deterministic Engine',
      badgeClass: 'bg-ink-850 text-zinc-400 border-white/[0.06]',
    };
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'VERIFIED':
        return (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
            VERIFIED
          </span>
        );
      case 'PR_CREATED':
        return (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-950/60 text-sky-400 border border-sky-800/60">
            PR CREATED
          </span>
        );
      case 'PROPOSED':
        return (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950/60 text-amber-400 border border-amber-800/60">
            PROPOSED
          </span>
        );
      default:
        return (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-ink-850 text-zinc-400 border border-white/[0.06]">
            {status}
          </span>
        );
    }
  };

  const renderUnifiedDiff = (diffText: string) => {
    const lines = diffText.split('\n');
    return (
      <div className="font-mono text-xs overflow-x-auto p-4 bg-ink-950 rounded-control border border-white/[0.08] max-h-[400px] leading-relaxed select-text">
        {lines.map((line, idx) => {
          let lineClass = 'text-zinc-300';
          if (line.startsWith('+') && !line.startsWith('+++')) {
            lineClass = 'bg-emerald-950/40 text-emerald-300 font-medium px-1';
          } else if (line.startsWith('-') && !line.startsWith('---')) {
            lineClass = 'bg-rose-950/40 text-rose-300 font-medium px-1';
          } else if (line.startsWith('@@')) {
            lineClass = 'text-sky-400 font-semibold my-1';
          } else if (line.startsWith('diff --git') || line.startsWith('index ')) {
            lineClass = 'text-zinc-500 font-bold';
          }

          return (
            <div key={idx} className={`${lineClass} whitespace-pre`}>
              {line || ' '}
            </div>
          );
        })}
      </div>
    );
  };

  const activePR = selectedProposal?.pull_request || selectedProposal?.remediation_pr;

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-ink-900 border border-white/[0.08] px-5 py-3.5 rounded-panel">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-control bg-ink-800 border border-white/[0.08] flex items-center justify-center text-zinc-200">
            <Wrench className="w-3.5 h-3.5" strokeWidth={1.5} />
          </div>
          <div>
            <h2 className="text-xs font-semibold text-white">AI Remediation Center</h2>
            <p className="text-[11px] text-zinc-500">
              Deterministic patch synthesis, isolated dual-sandbox verification, and automated GitHub Draft PR lifecycle
            </p>
          </div>
        </div>

        <button
          onClick={onRefresh}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-control bg-ink-850 hover:bg-ink-800 text-zinc-300 text-xs font-mono border border-white/[0.08] transition-colors"
        >
          <RotateCw className="w-3 h-3 text-zinc-400" strokeWidth={1.5} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Action Banners */}
      {actionSuccess && (
        <div className="p-3 rounded-control bg-ink-950 border border-emerald-800/60 text-emerald-300 text-xs font-mono flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" strokeWidth={1.5} />
            <span>{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-[11px] text-zinc-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {actionError && (
        <div className="p-3 rounded-control bg-ink-950 border border-rose-800/60 text-rose-300 text-xs font-mono flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" strokeWidth={1.5} />
            <span>{actionError}</span>
          </div>
          <button onClick={() => setActionError(null)} className="text-[11px] text-zinc-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Proposals List */}
        <div className="lg:col-span-4 space-y-2.5">
          <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500 px-1">
            Remediation Proposals ({proposals.length})
          </div>

          <div className="space-y-2 max-h-[720px] overflow-y-auto pr-1">
            {proposals.length > 0 ? (
              proposals.map((proposal) => {
                const isSelected = proposal.id === selectedProposal?.id;
                const explanation = proposal.explanation || proposal.description || proposal.rationale || proposal.title;
                const pInfo = getProviderInfo(proposal.provider_name, proposal.model_identifier);
                return (
                  <div
                    key={proposal.id}
                    onClick={() => setSelectedProposalId(proposal.id)}
                    className={`p-3.5 rounded-panel cursor-pointer transition-colors border ${
                      isSelected
                        ? 'bg-ink-800 border-white/[0.15]'
                        : 'bg-ink-900 border-white/[0.08] hover:border-zinc-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <div className="text-xs font-semibold text-white truncate font-mono">
                        Proposal #{proposal.id.substring(0, 7)}
                      </div>
                      {getStatusBadge(proposal.status)}
                    </div>

                    <p className="text-xs text-zinc-400 font-sans line-clamp-2 mb-2.5 leading-relaxed">
                      {explanation || 'No description provided.'}
                    </p>

                    <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500 pt-2 border-t border-white/[0.06]">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] border ${pInfo.badgeClass}`}>
                        {pInfo.label}
                      </span>
                      <span className="tabular-nums">
                        {Math.round(proposal.confidence_score * 100)}% conf
                      </span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-8 text-center bg-ink-900 border border-white/[0.08] rounded-panel text-zinc-500 text-xs font-mono">
                No remediation proposals available.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Proposal Deep-Dive Console */}
        <div className="lg:col-span-8">
          {selectedProposal ? (
            <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-5 space-y-5">
              {/* Proposal Header */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-white/[0.08]">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white font-mono">
                      Remediation #{selectedProposal.id.substring(0, 7)}
                    </span>
                    {getStatusBadge(selectedProposal.status)}
                  </div>
                  <div className="text-xs text-zinc-500 font-mono flex items-center gap-2">
                    <span>Target Failure: {selectedProposal.ci_failure_id ? selectedProposal.ci_failure_id.substring(0, 7) : '—'}</span>
                    <span>•</span>
                    <span className="text-zinc-300">
                      {getProviderInfo(selectedProposal.provider_name, selectedProposal.model_identifier).label}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {/* Verify Action */}
                  <button
                    onClick={() => handleVerify(selectedProposal.id)}
                    disabled={isVerifying || selectedProposal.status === 'VERIFIED' || selectedProposal.status === 'PR_CREATED'}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-emerald-600 hover:bg-emerald-500 disabled:bg-ink-800 disabled:text-zinc-600 text-white font-mono text-xs font-medium transition-colors"
                  >
                    {isVerifying ? (
                      <>
                        <RotateCw className="w-3 h-3 animate-spin" strokeWidth={1.5} />
                        <span>Verifying in Sandbox...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3 h-3 fill-current" />
                        <span>Verify in Sandbox</span>
                      </>
                    )}
                  </button>

                  {/* Create Draft PR Action */}
                  <button
                    onClick={() => handleCreatePR(selectedProposal.id)}
                    disabled={
                      isCreatingPR ||
                      selectedProposal.status !== 'VERIFIED' ||
                      Boolean(activePR)
                    }
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-ink-800 hover:bg-ink-700 disabled:bg-ink-800 disabled:text-zinc-600 text-zinc-100 font-mono text-xs border border-white/[0.08] transition-colors"
                  >
                    {isCreatingPR ? (
                      <>
                        <RotateCw className="w-3 h-3 animate-spin text-zinc-400" strokeWidth={1.5} />
                        <span>Creating PR...</span>
                      </>
                    ) : (
                      <>
                        <GitPullRequest className="w-3 h-3 text-zinc-300" strokeWidth={1.5} />
                        <span>Create Draft PR</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Active PR Link Box (if created) */}
              {activePR && (
                <div className="p-3.5 rounded-control bg-ink-950 border border-sky-800/60 flex items-center justify-between font-mono text-xs">
                  <div className="flex items-center gap-2">
                    <GitPullRequest className="w-3.5 h-3.5 text-sky-400" strokeWidth={1.5} />
                    <span className="text-zinc-300">Draft Pull Request:</span>
                    <span className="text-white font-semibold">#{activePR.pr_number || activePR.github_pr_number}</span>
                    <span className="text-zinc-500">({activePR.branch_name})</span>
                  </div>
                  <a
                    href={activePR.pr_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-sky-400 hover:text-sky-300 transition-colors"
                  >
                    <span>View on GitHub</span>
                    <ExternalLink className="w-3 h-3" strokeWidth={1.5} />
                  </a>
                </div>
              )}

              {/* Rationale and Strategy */}
              <div className="p-3.5 rounded-control bg-ink-950 border border-white/[0.06] space-y-1.5 text-xs">
                <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500 font-semibold">
                  Remediation Rationale
                </div>
                <p className="text-zinc-300 leading-relaxed font-sans">
                  {selectedProposal.rationale || selectedProposal.description || selectedProposal.explanation || 'No rationale provided.'}
                </p>
              </div>

              {/* Unified Diff Preview */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs font-mono text-zinc-500 px-1">
                  <div className="flex items-center gap-1.5">
                    <FileDiff className="w-3.5 h-3.5 text-zinc-400" strokeWidth={1.5} />
                    <span>Candidate Patch Diff</span>
                  </div>
                  <button
                    onClick={() => handleCopyDiff(selectedProposal.patch_diff)}
                    className="inline-flex items-center gap-1 hover:text-zinc-300 transition-colors"
                  >
                    {copiedDiff ? (
                      <Check className="w-3 h-3 text-emerald-400" strokeWidth={1.5} />
                    ) : (
                      <Copy className="w-3 h-3 text-zinc-500" strokeWidth={1.5} />
                    )}
                    <span>{copiedDiff ? 'Copied' : 'Copy Diff'}</span>
                  </button>
                </div>

                {renderUnifiedDiff(selectedProposal.patch_diff)}
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center p-12 bg-ink-900 border border-white/[0.08] rounded-panel text-zinc-500 text-xs font-mono">
              Select a remediation proposal to inspect its candidate diff and verification console.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
