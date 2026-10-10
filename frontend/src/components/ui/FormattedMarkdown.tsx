import React from 'react';

interface FormattedMarkdownProps {
  content: string;
  className?: string;
  onCitationClick?: (citationText: string) => void;
}

export const FormattedMarkdown: React.FC<FormattedMarkdownProps> = ({
  content,
  className = '',
  onCitationClick,
}) => {
  if (!content) return null;

  // Render inline tokens (bold, italic, code, citations, line breaks)
  const renderInline = (text: string): React.ReactNode[] => {
    // Replace raw <br> or <br/> tags with newline marker
    const normalized = text.replace(/<br\s*\/?>/gi, '\n');

    // Regex to capture citations [DOC-...], bold **...**, inline code `...`, italic *...*
    const tokenRegex = /(\[[A-Z0-9_\-]+(?:\:[^\]]+|\,[^\]]+)?\]|\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*|\n)/g;
    const parts = normalized.split(tokenRegex);

    return parts.map((part, idx) => {
      if (!part) return null;

      // Newlines inside inline text
      if (part === '\n') {
        return <br key={`br-${idx}`} />;
      }

      // Inline Citation badge: [DOC-OPS-001, v2, §4] or [TRANSACTION: TXN-001]
      if (part.startsWith('[') && part.endsWith(']') && (part.includes('DOC-') || part.includes('TRANSACTION:') || part.includes('ACCOUNT:') || part.includes('GRAPH-'))) {
        return (
          <span
            key={`cit-${idx}`}
            onClick={() => onCitationClick && onCitationClick(part)}
            className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-[10px] font-mono font-bold bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A] shadow-2xs cursor-pointer hover:bg-[#FDE68A] transition-colors align-baseline"
            title="Verified Forensic Citation"
          >
            {part}
          </span>
        );
      }

      // Bold: **text**
      if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
        return (
          <strong key={`b-${idx}`} className="font-bold text-[#002D72]">
            {part.slice(2, -2)}
          </strong>
        );
      }

      // Inline Code: `text`
      if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
        return (
          <code key={`c-${idx}`} className="px-1 py-0.5 rounded bg-[#F1F5F9] text-[#002D72] font-mono text-[11px] font-semibold border border-[#E2E8F0]">
            {part.slice(1, -1)}
          </code>
        );
      }

      // Italic: *text*
      if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
        return (
          <em key={`i-${idx}`} className="italic text-[#475569]">
            {part.slice(1, -1)}
          </em>
        );
      }

      return <span key={`t-${idx}`}>{part}</span>;
    });
  };

  // Parse markdown into blocks (Headers, Tables, Lists, Quotes, Paragraphs)
  const lines = content.split('\n');
  const blocks: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    // 1. Skip completely empty lines
    if (!trimmed) {
      i++;
      continue;
    }

    // 2. Markdown Table Detection: line starts and ends with '|' or contains multiple '|'
    if (trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.includes('|')) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i].trim());
        i++;
      }

      if (tableLines.length >= 2) {
        // Parse header
        const headerCells = tableLines[0]
          .split('|')
          .slice(1, -1)
          .map((c) => c.trim());

        // Skip separator line (e.g. |---|---|)
        const rowStartIndex = tableLines[1].replace(/[-| :]/g, '').length === 0 ? 2 : 1;
        const dataRows = tableLines.slice(rowStartIndex).map((rowStr) =>
          rowStr
            .split('|')
            .slice(1, -1)
            .map((c) => c.trim())
        );

        blocks.push(
          <div key={`table-${blocks.length}`} className="my-3 overflow-x-auto rounded-[10px] border border-[#E2E8F0] shadow-2xs">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-[#002D72] text-white uppercase text-[10.5px] font-bold tracking-wider">
                <tr>
                  {headerCells.map((h, hIdx) => (
                    <th key={`th-${hIdx}`} className="px-3.5 py-2.5 font-bold border-r border-[#1E40AF] last:border-0">
                      {renderInline(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E2E8F0] text-[#0F172A] bg-white">
                {dataRows.map((row, rIdx) => (
                  <tr key={`tr-${rIdx}`} className={rIdx % 2 === 1 ? 'bg-[#F8FAFC]' : 'bg-white hover:bg-[#FFFBEB] transition-colors'}>
                    {row.map((cell, cIdx) => (
                      <td key={`td-${cIdx}`} className="px-3.5 py-2.5 text-xs leading-relaxed border-r border-[#E2E8F0] last:border-0 align-top">
                        {renderInline(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        continue;
      }
    }

    // 3. Main Headings: #, ##, ###
    if (trimmed.startsWith('# ')) {
      blocks.push(
        <h2 key={`h1-${blocks.length}`} className="text-base font-extrabold text-[#002D72] mt-4 mb-2 pb-1 border-b border-[#E2E8F0] uppercase tracking-wide">
          {renderInline(trimmed.slice(2))}
        </h2>
      );
      i++;
      continue;
    }

    if (trimmed.startsWith('## ')) {
      blocks.push(
        <h3 key={`h2-${blocks.length}`} className="text-sm font-bold text-[#002D72] mt-3.5 mb-1.5 flex items-center gap-1.5 uppercase tracking-wide">
          <span className="w-1.5 h-3.5 rounded-full bg-[#F9A825]" />
          {renderInline(trimmed.slice(3))}
        </h3>
      );
      i++;
      continue;
    }

    if (trimmed.startsWith('### ')) {
      blocks.push(
        <h4 key={`h3-${blocks.length}`} className="text-xs font-bold text-[#0F172A] mt-2.5 mb-1">
          {renderInline(trimmed.slice(4))}
        </h4>
      );
      i++;
      continue;
    }

    // 4. Standalone Bold Titles (e.g. **Internal Banking Policy - Restoring Account Access...**)
    if (trimmed.startsWith('**') && trimmed.endsWith('**') && !trimmed.slice(2, -2).includes('**')) {
      const titleText = trimmed.slice(2, -2);
      blocks.push(
        <div key={`title-banner-${blocks.length}`} className="mt-3 mb-2 p-2.5 bg-[#F4F1EC] border-l-4 border-[#002D72] rounded-r-[8px]">
          <h3 className="text-xs font-extrabold text-[#002D72] uppercase tracking-wide">
            {titleText}
          </h3>
        </div>
      );
      i++;
      continue;
    }

    // 5. Unordered Lists: - or *
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const listItems: string[] = [];
      while (i < lines.length && (lines[i].trim().startsWith('- ') || lines[i].trim().startsWith('* '))) {
        listItems.push(lines[i].trim().slice(2));
        i++;
      }
      blocks.push(
        <ul key={`ul-${blocks.length}`} className="my-2 space-y-1.5 pl-4 list-disc text-xs text-[#1E293B]">
          {listItems.map((item, lIdx) => (
            <li key={`li-${lIdx}`} className="leading-relaxed">
              {renderInline(item)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // 6. Ordered Lists: 1. 2. 3.
    if (/^\d+\.\s/.test(trimmed)) {
      const listItems: string[] = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i].trim())) {
        listItems.push(lines[i].trim().replace(/^\d+\.\s/, ''));
        i++;
      }
      blocks.push(
        <ol key={`ol-${blocks.length}`} className="my-2 space-y-1.5 pl-4 list-decimal text-xs text-[#1E293B]">
          {listItems.map((item, lIdx) => (
            <li key={`oli-${lIdx}`} className="leading-relaxed font-normal">
              {renderInline(item)}
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // 7. Blockquotes: > ...
    if (trimmed.startsWith('> ')) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('> ')) {
        quoteLines.push(lines[i].trim().slice(2));
        i++;
      }
      blocks.push(
        <blockquote key={`quote-${blocks.length}`} className="my-2.5 p-3 bg-[#F8FAFC] border-l-3 border-[#F9A825] rounded-r-[8px] text-xs text-[#334155] italic">
          {renderInline(quoteLines.join(' '))}
        </blockquote>
      );
      continue;
    }

    // 8. Standard Paragraph
    blocks.push(
      <p key={`p-${blocks.length}`} className="text-xs text-[#1E293B] leading-relaxed my-1.5">
        {renderInline(trimmed)}
      </p>
    );
    i++;
  }

  return <div className={`space-y-1 ${className}`}>{blocks}</div>;
};
