import React, { useState, useEffect } from 'react';
import { IconConfig } from '../engine/types';
import {
  generateDesignGuidelines,
  DesignSystemDoc,
  downloadMarkdown,
  downloadHtml,
} from '../engine/designSystem';
import {
  BookOpen,
  FileText,
  Code,
  Download,
  Ruler,
  Palette,
  Layout,
  Target,
  Ban,
  FileDown,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface DesignSystemPanelProps {
  config: IconConfig;
}

export function DesignSystemPanel({ config }: DesignSystemPanelProps) {
  const [doc, setDoc] = useState<DesignSystemDoc | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['overview', 'size', 'colors'])
  );

  useEffect(() => {
    const guidelines = generateDesignGuidelines(config);
    setDoc(guidelines);
  }, [config]);

  const toggleSection = (sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  const handleDownloadMarkdown = () => {
    if (doc) {
      downloadMarkdown(doc, `${config.text.toLowerCase()}-design-guidelines`);
    }
  };

  const handleDownloadHtml = () => {
    if (doc) {
      downloadHtml(doc, `${config.text.toLowerCase()}-design-guidelines`);
    }
  };

  const getSectionIcon = (sectionId: string) => {
    const icons: Record<string, React.ReactNode> = {
      overview: <BookOpen className="w-5 h-5" />,
      size: <Ruler className="w-5 h-5" />,
      colors: <Palette className="w-5 h-5" />,
      spacing: <Layout className="w-5 h-5" />,
      style: <Target className="w-5 h-5" />,
      usage: <FileText className="w-5 h-5" />,
      background: <Layout className="w-5 h-5" />,
      donts: <Ban className="w-5 h-5" />,
      export: <FileDown className="w-5 h-5" />,
    };
    return icons[sectionId] || <FileText className="w-5 h-5" />;
  };

  if (!doc) return null;

  return (
    <div className="bg-white rounded-2xl shadow-xl p-6">
      <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-xl">
            <BookOpen className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-800">设计系统规范</h3>
            <p className="text-sm text-gray-500">生成配套图标使用规范文档</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleDownloadMarkdown}
            className="flex items-center gap-1 px-3 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            <Code className="w-4 h-4" />
            MD
          </button>
          <button
            onClick={handleDownloadHtml}
            className="flex items-center gap-1 px-3 py-2 text-sm font-medium text-white bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg hover:from-indigo-600 hover:to-purple-600 transition-all"
          >
            <Download className="w-4 h-4" />
            HTML
          </button>
        </div>
      </div>

      <div className="mb-6 p-4 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl border border-indigo-100">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-semibold text-indigo-800">{doc.title}</h4>
            <p className="text-sm text-indigo-600">版本 {doc.version}</p>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-lg shadow-md"
              style={{ backgroundColor: config.primaryColor }}
            />
            <div
              className="w-8 h-8 rounded-lg shadow-md"
              style={{ backgroundColor: config.secondaryColor }}
            />
          </div>
        </div>
      </div>

      <div className="space-y-2 max-h-[500px] overflow-y-auto pr-2">
        {doc.sections.map((section) => (
          <div
            key={section.id}
            className="border border-gray-100 rounded-xl overflow-hidden"
          >
            <button
              onClick={() => toggleSection(section.id)}
              className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors text-left"
            >
              <div className="flex items-center gap-3">
                <span className="text-indigo-500">{getSectionIcon(section.id)}</span>
                <span className="font-medium text-gray-800">{section.title}</span>
              </div>
              {expandedSections.has(section.id) ? (
                <ChevronUp className="w-5 h-5 text-gray-400" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-400" />
              )}
            </button>

            {expandedSections.has(section.id) && (
              <div className="px-4 pb-4 pt-2">
                <p className="text-gray-600 text-sm mb-4">{section.content}</p>

                {section.items && section.items.length > 0 && (
                  <div className="overflow-hidden rounded-lg border border-gray-200">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">项目</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">值</th>
                          <th className="px-3 py-2 text-left font-medium text-gray-600">说明</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {section.items.map((item, index) => (
                          <tr key={index} className="hover:bg-gray-50">
                            <td className="px-3 py-2 text-gray-800 font-medium">
                              {item.label}
                            </td>
                            <td className="px-3 py-2">
                              {/^#[0-9A-Fa-f]{6}$/.test(item.value) ? (
                                <span className="flex items-center gap-2">
                                  <span
                                    className="w-5 h-5 rounded border-2 border-white shadow-sm"
                                    style={{ backgroundColor: item.value }}
                                  />
                                  <code className="font-mono text-xs text-gray-600">
                                    {item.value}
                                  </code>
                                </span>
                              ) : (
                                <code className="font-mono text-xs bg-gray-100 px-2 py-1 rounded text-gray-700">
                                  {item.value}
                                </code>
                              )}
                            </td>
                            <td className="px-3 py-2 text-gray-500 text-xs">
                              {item.description}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-100">
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>生成时间: {new Date(doc.generatedAt).toLocaleString()}</span>
          <span>·</span>
          <span>{doc.sections.length} 个规范章节</span>
        </div>
      </div>
    </div>
  );
}
