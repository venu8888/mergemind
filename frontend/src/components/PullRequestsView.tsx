import React, { useState, useEffect } from 'react';
import {
  GitPullRequest,
  CheckCircle2,
  Play,
  ExternalLink,
  RotateCw,
  FileDiff,
  FileCode,
  Check,
  Copy,
  User,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import {
  fetchGitHubPullRequests,
  fetchGitHubPullRequestDetail,
  reviewPullRequestWithAI,
  verifyPullRequestInSandbox,
} from '../services/api';

interface PullRequestsViewProps {
  repositoryId: string;
}

export const PullRequestsView: React.FC<PullRequestsViewProps> = ({ repositoryId }) => {
  const [prs, setPrs] = useState<any[]>([]);
  const [filterState, setFilterState] = useState<'all' | 'open' | 'closed'>('all');
  const [selectedPrNumber, setSelectedPrNumber] = useState<number | null>(null);
  const [prDetail, setPrDetail] = useState<any | null>(null);
  const [loadingList, setLoadingList] = useState<boolean>(true);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);
  const [isReviewing, setIsReviewing] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [reviewResult, setReviewResult] = useState<any | null>(null);
  const [verificationResult, setVerificationResult] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<'diff' | 'files' | 'review'>('diff');
  const [copiedDiff, setCopiedDiff] = useState<boolean>(false);

  // Load PR list
  const loadPrList = async () => {
    if (!repositoryId) return;
    setLoadingList(true);
    try {
      const list = await fetchGitHubPullRequests(repositoryId, filterState);
      setPrs(list);
      if (list.length > 0 && !selectedPrNumber) {
        setSelectedPrNumber(list[0].number);
      }
    } catch (err) {
      console.error('Failed to load GitHub PRs:', err);
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    loadPrList();
  }, [repositoryId, filterState]);

  // Load PR detail when selected
  useEffect(() => {
    if (!repositoryId || !selectedPrNumber) return;
    const loadDetail = async () => {
      setLoadingDetail(true);
      setReviewResult(null);
      setVerificationResult(null);
      try {
        const detail = await fetchGitHubPullRequestDetail(repositoryId, selectedPrNumber);
        setPrDetail(detail);
      } catch (err) {
        console.error('Failed to load PR detail:', err);
      } finally {
        setLoadingDetail(false);
      }
    };
    loadDetail();
  }, [repositoryId, selectedPrNumber]);

  // AI PR Review action
  const handleRunAIReview = async () => {
    if (!repositoryId || !selectedPrNumber) return;
    setIsReviewing(true);
    try {
      const review = await reviewPullRequestWithAI(repositoryId, selectedPrNumber);
      setReviewResult(review);
      setActiveTab('review');
    } catch (err: any) {
      alert('AI PR Review failed: ' + (err.message || 'Error communicating with Gemini'));
    } finally {
      setIsReviewing(false);
    }
  };

  // Sandbox Verification action
  const handleVerifySandbox = async () => {
    if (!repositoryId || !selectedPrNumber) return;
    setIsVerifying(true);
    try {
      const result = await verifyPullRequestInSandbox(repositoryId, selectedPrNumber);
      setVerificationResult(result);
    } catch (err: any) {
      alert('Sandbox verification failed: ' + (err.message || 'Error running pytest sandbox'));
    } finally {
      setIsVerifying(false);
    }
  };

  const handleCopyDiff = (diffText: string) => {
    navigator.clipboard.writeText(diffText);
    setCopiedDiff(true);
    setTimeout(() => setCopiedDiff(false), 2000);
  };

  const renderUnifiedDiff = (diffText: string) => {
    if (!diffText || !diffText.trim()) {
      return (
        <div className="p-8 text-center text-zinc-500 font-mono text-xs">
          No diff changes recorded for this Pull Request.
        </div>
      );
    }
    const lines = diffText.split('\n');
    return (
      <div className="font-mono text-xs overflow-x-auto p-4 bg-ink-950 rounded-control border border-white/[0.08] max-h-[500px] leading-relaxed select-text">
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

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-ink-900 border border-white/[0.08] px-5 py-3.5 rounded-panel">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-control bg-ink-800 border border-white/[0.08] flex items-center justify-center text-zinc-200">
            <GitPullRequest className="w-3.5 h-3.5" strokeWidth={1.5} />
          </div>
          <div>
            <h2 className="text-xs font-semibold text-white">Pull Request Intelligence & Review</h2>
            <p className="text-[11px] text-zinc-500">
              GitHub PR tracking, deterministic sandbox quality gates, and automated code review
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* State Filter */}
          <div className="flex items-center bg-ink-950 p-0.5 rounded-control text-xs font-mono border border-white/[0.08]">
            {(['all', 'open', 'closed'] as const).map((st) => (
              <button
                key={st}
                onClick={() => setFilterState(st)}
                className={`px-2.5 py-1 rounded-control capitalize transition-colors ${
                  filterState === st ? 'bg-ink-800 text-zinc-100 font-medium' : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          <button
            onClick={loadPrList}
            className="p-1.5 rounded-control bg-ink-850 hover:bg-ink-800 text-zinc-400 hover:text-white transition-colors border border-white/[0.08]"
            title="Refresh Pull Requests"
          >
            <RotateCw className={`w-3.5 h-3.5 ${loadingList ? 'animate-spin' : ''}`} strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: PR Listing */}
        <div className="lg:col-span-4 space-y-2.5">
          <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500 px-1">
            Pull Requests ({prs.length})
          </div>

          <div className="space-y-2 max-h-[720px] overflow-y-auto pr-1">
            {prs.length > 0 ? (
              prs.map((pr) => {
                const isSelected = pr.number === selectedPrNumber;
                return (
                  <div
                    key={pr.number}
                    onClick={() => setSelectedPrNumber(pr.number)}
                    className={`p-3.5 rounded-panel cursor-pointer transition-colors border ${
                      isSelected
                        ? 'bg-ink-800 border-white/[0.15]'
                        : 'bg-ink-900 border-white/[0.08] hover:border-zinc-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <div className="text-xs font-semibold text-white truncate font-mono">
                        #{pr.number} {pr.title}
                      </div>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                          pr.state === 'open'
                            ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60'
                            : 'bg-zinc-800 text-zinc-400 border border-zinc-700'
                        }`}
                      >
                        {pr.draft ? 'DRAFT' : pr.state}
                      </span>
                    </div>

                    <div className="text-[11px] font-mono text-zinc-400 flex items-center gap-1.5 mb-2">
                      <span className="text-zinc-300">{pr.head_branch}</span>
                      <ArrowRight className="w-3 h-3 text-zinc-600" />
                      <span className="text-zinc-500">{pr.base_branch}</span>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-zinc-500 font-mono">
                      <div className="flex items-center gap-1.5">
                        {pr.author_avatar ? (
                          <img src={pr.author_avatar} alt="" className="w-3.5 h-3.5 rounded-full" />
                        ) : (
                          <User className="w-3 h-3" strokeWidth={1.5} />
                        )}
                        <span>{pr.author}</span>
                      </div>
                      <span>{new Date(pr.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-8 text-center bg-ink-900 border border-white/[0.08] rounded-panel text-zinc-500 text-xs font-mono">
                No pull requests match filter '{filterState}'.
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Detailed PR Console */}
        <div className="lg:col-span-8">
          {loadingDetail ? (
            <div className="h-full min-h-[400px] flex items-center justify-center p-12 bg-ink-900 border border-white/[0.08] rounded-panel text-zinc-500 text-xs font-mono gap-2">
              <RotateCw className="w-3.5 h-3.5 animate-spin text-zinc-400" strokeWidth={1.5} />
              <span>Fetching Pull Request details and diff from GitHub...</span>
            </div>
          ) : prDetail ? (
            <div className="bg-ink-900 border border-white/[0.08] rounded-panel p-5 space-y-5">
              {/* PR Header & Actions */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-4 border-b border-white/[0.08]">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white font-mono">
                      #{prDetail.number} {prDetail.title}
                    </span>
                    <a
                      href={prDetail.html_url}
                      target="_blank"
                      rel="noreferrer"
                      className="p-1 rounded-control hover:bg-ink-800 text-zinc-500 hover:text-zinc-200 transition-colors"
                      title="Open on GitHub"
                    >
                      <ExternalLink className="w-3.5 h-3.5" strokeWidth={1.5} />
                    </a>
                  </div>
                  <div className="text-xs font-mono text-zinc-400 flex items-center gap-2">
                    <span>Author: {prDetail.author}</span>
                    <span>•</span>
                    <span>Branch: {prDetail.head_branch} &rarr; {prDetail.base_branch}</span>
                    <span>•</span>
                    <span className="text-emerald-400">+{prDetail.additions}</span>
                    <span className="text-rose-400">-{prDetail.deletions}</span>
                  </div>
                </div>

                {/* Verification & AI Review Triggers */}
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={handleVerifySandbox}
                    disabled={isVerifying}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-emerald-600 hover:bg-emerald-500 disabled:bg-ink-800 text-white text-xs font-mono font-medium transition-colors"
                  >
                    {isVerifying ? (
                      <>
                        <RotateCw className="w-3 h-3 animate-spin" strokeWidth={1.5} />
                        <span>Verifying...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3 h-3 fill-current" />
                        <span>Verify in Sandbox</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={handleRunAIReview}
                    disabled={isReviewing}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-ink-800 hover:bg-ink-700 disabled:bg-ink-800 text-zinc-100 text-xs font-mono border border-white/[0.08] transition-colors"
                  >
                    {isReviewing ? (
                      <>
                        <RotateCw className="w-3 h-3 animate-spin text-zinc-400" strokeWidth={1.5} />
                        <span>Reviewing...</span>
                      </>
                    ) : (
                      <>
                        <ShieldCheck className="w-3 h-3 text-zinc-300" strokeWidth={1.5} />
                        <span>Run AI Review</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Sandbox Verification Result Banner */}
              {verificationResult && (
                <div className="p-3.5 rounded-control bg-ink-950 border border-emerald-800/60 text-xs font-mono space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                      <span>Sandbox Gate: {verificationResult.quality_gate}</span>
                    </div>
                    <span className="text-zinc-500 tabular-nums">{verificationResult.duration_ms}ms</span>
                  </div>
                  <p className="text-zinc-300 font-sans">{verificationResult.summary}</p>
                </div>
              )}

              {/* Sub-Tabs */}
              <div className="flex items-center space-x-1 border-b border-white/[0.08]">
                <button
                  onClick={() => setActiveTab('diff')}
                  className={`flex items-center gap-1.5 px-3.5 py-2 text-xs font-mono border-b-2 transition-colors ${
                    activeTab === 'diff'
                      ? 'border-zinc-200 text-zinc-100 font-medium'
                      : 'border-transparent text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  <FileDiff className="w-3.5 h-3.5" strokeWidth={1.5} />
                  <span>Unified Patch Diff</span>
                </button>

                <button
                  onClick={() => setActiveTab('files')}
                  className={`flex items-center gap-1.5 px-3.5 py-2 text-xs font-mono border-b-2 transition-colors ${
                    activeTab === 'files'
                      ? 'border-zinc-200 text-zinc-100 font-medium'
                      : 'border-transparent text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  <FileCode className="w-3.5 h-3.5" strokeWidth={1.5} />
                  <span>Changed Files ({prDetail.changed_files.length})</span>
                </button>

                <button
                  onClick={() => setActiveTab('review')}
                  className={`flex items-center gap-1.5 px-3.5 py-2 text-xs font-mono border-b-2 transition-colors ${
                    activeTab === 'review'
                      ? 'border-zinc-200 text-zinc-100 font-medium'
                      : 'border-transparent text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  <ShieldCheck className="w-3.5 h-3.5" strokeWidth={1.5} />
                  <span>AI Review Verdict {reviewResult && `(${reviewResult.verdict})`}</span>
                </button>
              </div>

              {/* Tab 1: Diff Viewer */}
              {activeTab === 'diff' && (
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between text-xs text-zinc-500 font-mono px-1">
                    <span>Git Diff Output</span>
                    <button
                      onClick={() => handleCopyDiff(prDetail.diff)}
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
                  {renderUnifiedDiff(prDetail.diff)}
                </div>
              )}

              {/* Tab 2: Changed Files */}
              {activeTab === 'files' && (
                <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                  {prDetail.changed_files.map((f: any) => (
                    <div
                      key={f.filename}
                      className="p-3 rounded-control bg-ink-950 border border-white/[0.06] text-xs font-mono flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <FileCode className="w-3.5 h-3.5 text-zinc-400" strokeWidth={1.5} />
                        <span className="text-zinc-200 font-medium">{f.filename}</span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] uppercase font-bold bg-ink-850 text-zinc-400 border border-white/[0.06]">
                          {f.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs tabular-nums">
                        <span className="text-emerald-400">+{f.additions}</span>
                        <span className="text-rose-400">-{f.deletions}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Tab 3: Gemini AI Review Results */}
              {activeTab === 'review' && (
                <div className="space-y-4">
                  {reviewResult ? (
                    <div className="space-y-4">
                      {/* Summary Banner */}
                      <div className="p-4 rounded-control bg-ink-950 border border-white/[0.06] space-y-2.5">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 font-mono">
                            <span
                              className={`px-2 py-0.5 rounded text-xs font-bold uppercase border ${
                                reviewResult.verdict === 'APPROVE'
                                  ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60'
                                  : 'bg-amber-950/60 text-amber-400 border-amber-800/60'
                              }`}
                            >
                              {reviewResult.verdict}
                            </span>
                            <span className="text-xs text-zinc-500">
                              Gate: {reviewResult.quality_gate} • Risk: {reviewResult.risk_level}
                            </span>
                          </div>
                          <span className="text-[11px] font-mono text-zinc-500">
                            Provider: {reviewResult.provider}
                          </span>
                        </div>

                        <p className="text-xs text-zinc-300 leading-relaxed font-sans">{reviewResult.summary}</p>
                      </div>

                      {/* Findings List */}
                      {reviewResult.findings?.length > 0 && (
                        <div className="space-y-2">
                          <div className="text-[11px] font-mono uppercase text-zinc-500">Review Findings</div>
                          {reviewResult.findings.map((f: any, idx: number) => (
                            <div
                              key={idx}
                              className="p-3 rounded-control bg-ink-950 border border-white/[0.06] text-xs space-y-1 font-mono"
                            >
                              <div className="flex items-center justify-between">
                                <span className="text-zinc-200 font-semibold">
                                  {f.file}:{f.line}
                                </span>
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-950/60 text-amber-400 border border-amber-800/60">
                                  {f.category}
                                </span>
                              </div>
                              <p className="text-zinc-300 font-sans">{f.message}</p>
                              {f.recommendation && (
                                <p className="text-zinc-500 font-sans text-[11px]">
                                  <span className="text-zinc-400">Fix:</span> {f.recommendation}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Positive Observations */}
                      {reviewResult.positive_observations?.length > 0 && (
                        <div className="p-3.5 rounded-control bg-ink-950 border border-white/[0.06] text-xs space-y-1.5 font-mono">
                          <div className="font-semibold text-emerald-400 flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={1.5} />
                            <span>Positive Observations</span>
                          </div>
                          <ul className="space-y-1 text-zinc-300 font-sans">
                            {reviewResult.positive_observations.map((obs: string, idx: number) => (
                              <li key={idx} className="flex items-start gap-1.5">
                                <span className="text-emerald-400">•</span>
                                <span>{obs}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-8 text-center bg-ink-950 rounded-control border border-white/[0.06] space-y-3 font-mono">
                      <div className="text-xs text-zinc-400 max-w-sm mx-auto">
                        Trigger automated code review for this pull request's diff and code changes.
                      </div>
                      <button
                        onClick={handleRunAIReview}
                        disabled={isReviewing}
                        className="px-3.5 py-1.5 rounded-control bg-ink-800 text-zinc-200 text-xs font-mono hover:bg-ink-700 border border-white/[0.08] transition-colors"
                      >
                        Run Code Review
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center p-12 bg-ink-900 border border-white/[0.08] rounded-panel text-zinc-500 text-xs font-mono">
              Select a Pull Request to view its files, diff, and verification console.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
