import React, { useState, useEffect } from 'react';
import {
  Folder,
  FileCode,
  FileText,
  File,
  ChevronRight,
  ChevronDown,
  GitBranch,
  Copy,
  Check,
  RotateCw,
  Code2,
} from 'lucide-react';
import { fetchRepositoryTree, fetchRepositoryBlob, fetchRepositoryBranches } from '../services/api';

interface CodebaseExplorerProps {
  repositoryId: string;
}

interface TreeItem {
  path: string;
  type: string;
  size?: number;
  sha: string;
}

export const CodebaseExplorer: React.FC<CodebaseExplorerProps> = ({ repositoryId }) => {
  const [tree, setTree] = useState<TreeItem[]>([]);
  const [branches, setBranches] = useState<Array<{ name: string; commit_sha: string }>>([]);
  const [selectedBranch, setSelectedBranch] = useState<string>('main');
  const [selectedPath, setSelectedPath] = useState<string>('sample_app/calculator.py');
  const [fileContent, setFileContent] = useState<string>('');
  const [fileMeta, setFileMeta] = useState<{ lines: number; size: number; language: string } | null>(null);
  const [loadingTree, setLoadingTree] = useState<boolean>(true);
  const [loadingFile, setLoadingFile] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({
    sample_app: true,
    tests: true,
  });

  // Load branches & tree
  useEffect(() => {
    if (!repositoryId) return;
    const loadInit = async () => {
      setLoadingTree(true);
      try {
        const [branchList, treeData] = await Promise.all([
          fetchRepositoryBranches(repositoryId).catch(() => [{ name: 'main', commit_sha: '' }]),
          fetchRepositoryTree(repositoryId, selectedBranch),
        ]);
        setBranches(branchList);
        setTree(treeData.tree || []);

        const hasDefault = treeData.tree?.some((t) => t.path === selectedPath);
        if (!hasDefault && treeData.tree?.length) {
          const firstBlob = treeData.tree.find((t) => t.type === 'blob');
          if (firstBlob) setSelectedPath(firstBlob.path);
        }
      } catch (err) {
        console.error('Failed to load codebase explorer:', err);
      } finally {
        setLoadingTree(false);
      }
    };
    loadInit();
  }, [repositoryId, selectedBranch]);

  // Load active file content
  useEffect(() => {
    if (!repositoryId || !selectedPath) return;
    const loadContent = async () => {
      setLoadingFile(true);
      try {
        const data = await fetchRepositoryBlob(repositoryId, selectedPath, selectedBranch);
        setFileContent(data.content);
        setFileMeta({ lines: data.lines, size: data.size, language: data.language });
      } catch (err) {
        setFileContent('// Failed to load file content from GitHub repository.');
      } finally {
        setLoadingFile(false);
      }
    };
    loadContent();
  }, [repositoryId, selectedPath, selectedBranch]);

  const handleCopy = () => {
    navigator.clipboard.writeText(fileContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const toggleFolder = (folderName: string) => {
    setExpandedFolders((prev) => ({ ...prev, [folderName]: !prev[folderName] }));
  };

  // Group tree items by folder
  const folders: Record<string, TreeItem[]> = { '/': [] };
  tree.forEach((item) => {
    if (item.type === 'tree') {
      if (!folders[item.path]) folders[item.path] = [];
    } else {
      const parts = item.path.split('/');
      if (parts.length === 1) {
        folders['/'].push(item);
      } else {
        const folder = parts.slice(0, -1).join('/');
        if (!folders[folder]) folders[folder] = [];
        folders[folder].push(item);
      }
    }
  });

  const getFileIcon = (path: string) => {
    if (path.endsWith('.py')) return <FileCode className="w-3.5 h-3.5 text-zinc-400 shrink-0" strokeWidth={1.5} />;
    if (path.endsWith('.md')) return <FileText className="w-3.5 h-3.5 text-zinc-400 shrink-0" strokeWidth={1.5} />;
    return <File className="w-3.5 h-3.5 text-zinc-500 shrink-0" strokeWidth={1.5} />;
  };

  return (
    <div className="space-y-5">
      {/* Header Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-ink-900 border border-white/[0.08] px-5 py-3.5 rounded-panel">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-control bg-ink-800 border border-white/[0.08] flex items-center justify-center text-zinc-200">
            <Code2 className="w-3.5 h-3.5" strokeWidth={1.5} />
          </div>
          <div>
            <div className="text-xs font-semibold text-white">Codebase Explorer</div>
            <div className="text-[11px] text-zinc-500">Live Git tree and blob inspection</div>
          </div>
        </div>

        {/* Branch Selector */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-ink-950 border border-white/[0.08] px-2.5 py-1 rounded-control text-xs font-mono text-zinc-300">
            <GitBranch className="w-3.5 h-3.5 text-zinc-400" strokeWidth={1.5} />
            <select
              value={selectedBranch}
              onChange={(e) => setSelectedBranch(e.target.value)}
              className="bg-transparent text-zinc-200 focus:outline-none cursor-pointer pr-1"
            >
              {branches.map((b) => (
                <option key={b.name} value={b.name} className="bg-ink-900 text-zinc-200">
                  {b.name}
                </option>
              ))}
            </select>
          </div>

          <span className="text-[11px] text-zinc-500 font-mono">
            {tree.filter((t) => t.type === 'blob').length} files indexed
          </span>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: File Tree */}
        <div className="lg:col-span-4 bg-ink-900 border border-white/[0.08] rounded-panel p-3.5 flex flex-col h-[680px]">
          <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500 mb-2.5 px-2 flex items-center justify-between">
            <span>Filesystem</span>
            {loadingTree && <RotateCw className="w-3 h-3 text-zinc-400 animate-spin" strokeWidth={1.5} />}
          </div>

          <div className="flex-1 overflow-y-auto space-y-0.5 font-mono text-xs pr-1">
            {/* Root-level files */}
            {folders['/']?.map((item) => (
              <button
                key={item.path}
                onClick={() => setSelectedPath(item.path)}
                className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-control text-left transition-colors ${
                  selectedPath === item.path
                    ? 'bg-ink-800 text-zinc-100 border border-white/[0.1]'
                    : 'text-zinc-400 hover:bg-ink-850 hover:text-zinc-200'
                }`}
              >
                {getFileIcon(item.path)}
                <span className="truncate">{item.path}</span>
              </button>
            ))}

            {/* Subfolders */}
            {Object.keys(folders)
              .filter((k) => k !== '/')
              .map((folder) => {
                const isExpanded = expandedFolders[folder] ?? true;
                return (
                  <div key={folder} className="space-y-0.5">
                    <button
                      onClick={() => toggleFolder(folder)}
                      className="w-full flex items-center gap-1.5 px-2 py-1.5 rounded-control text-left text-zinc-400 hover:text-zinc-200 hover:bg-ink-850 transition-colors font-medium"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-3 h-3 text-zinc-500" strokeWidth={1.5} />
                      ) : (
                        <ChevronRight className="w-3 h-3 text-zinc-500" strokeWidth={1.5} />
                      )}
                      <Folder className="w-3.5 h-3.5 text-zinc-400 shrink-0" strokeWidth={1.5} />
                      <span className="truncate">{folder}</span>
                    </button>

                    {isExpanded && (
                      <div className="ml-3.5 pl-2 border-l border-white/[0.06] space-y-0.5">
                        {folders[folder]?.map((item) => (
                          <button
                            key={item.path}
                            onClick={() => setSelectedPath(item.path)}
                            className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-control text-left transition-colors ${
                              selectedPath === item.path
                                ? 'bg-ink-800 text-zinc-100 border border-white/[0.1] font-medium'
                                : 'text-zinc-400 hover:bg-ink-850 hover:text-zinc-200'
                            }`}
                          >
                            {getFileIcon(item.path)}
                            <span className="truncate">{item.path.split('/').pop()}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
          </div>
        </div>

        {/* Right Column: Code Viewer */}
        <div className="lg:col-span-8 bg-ink-900 border border-white/[0.08] rounded-panel overflow-hidden flex flex-col h-[680px]">
          {/* File Tab Bar */}
          <div className="bg-ink-950 border-b border-white/[0.08] px-4 py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-2 font-mono text-xs">
              {getFileIcon(selectedPath)}
              <span className="font-semibold text-zinc-200">{selectedPath}</span>
              {fileMeta && (
                <span className="text-[11px] text-zinc-500 ml-2">
                  {fileMeta.lines} lines • {fileMeta.size} B
                </span>
              )}
            </div>

            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 px-2 py-1 rounded-control bg-ink-850 hover:bg-ink-800 text-zinc-300 text-xs font-mono border border-white/[0.08] transition-colors"
            >
              {copied ? (
                <Check className="w-3 h-3 text-emerald-400" strokeWidth={1.5} />
              ) : (
                <Copy className="w-3 h-3 text-zinc-400" strokeWidth={1.5} />
              )}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>

          {/* Source Code Content with Line Numbers */}
          <div className="flex-1 overflow-auto bg-ink-950 p-4 font-mono text-xs leading-relaxed select-text">
            {loadingFile ? (
              <div className="h-full flex items-center justify-center text-zinc-500 text-xs gap-2">
                <RotateCw className="w-3.5 h-3.5 animate-spin text-zinc-400" strokeWidth={1.5} />
                <span>Fetching blob from GitHub...</span>
              </div>
            ) : (
              <table className="w-full border-collapse">
                <tbody>
                  {fileContent.split('\n').map((line, idx) => (
                    <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                      <td className="w-10 pr-4 text-right text-zinc-600 select-none font-mono text-[11px] align-top">
                        {idx + 1}
                      </td>
                      <td className="text-zinc-200 whitespace-pre font-mono">{line || ' '}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
