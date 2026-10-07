import React from 'react';

export const TableContainer: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <div
    className={`w-full overflow-x-auto rounded-[16px] border border-[#E0DDD6] bg-white shadow-sm ${className}`}
    {...props}
  >
    {children}
  </div>
);

export const Table: React.FC<React.TableHTMLAttributes<HTMLTableElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <table className={`w-full border-collapse text-left ${className}`} {...props}>
    {children}
  </table>
);

export const TableHeader: React.FC<React.HTMLAttributes<HTMLTableSectionElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <thead className={`bg-[#F4F1EC] border-b border-[#E0DDD6] ${className}`} {...props}>
    {children}
  </thead>
);

export const TableHead: React.FC<React.ThHTMLAttributes<HTMLTableCellElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <th
    className={`px-4 py-3.5 text-[11px] font-bold uppercase tracking-wider text-[#475569] select-none ${className}`}
    {...props}
  >
    {children}
  </th>
);

export const TableBody: React.FC<React.HTMLAttributes<HTMLTableSectionElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <tbody className={`divide-y divide-[#E0DDD6] bg-white ${className}`} {...props}>
    {children}
  </tbody>
);

export const TableRow: React.FC<React.HTMLAttributes<HTMLTableRowElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <tr
    className={`hover:bg-[#F9F8F6] transition-colors duration-150 ${className}`}
    {...props}
  >
    {children}
  </tr>
);

export const TableCell: React.FC<React.TdHTMLAttributes<HTMLTableCellElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <td className={`px-4 py-3.5 text-sm text-[#0F172A] ${className}`} {...props}>
    {children}
  </td>
);
