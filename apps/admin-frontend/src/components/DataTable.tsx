"use client";

import React, { useState, ReactNode } from "react";
import { Search, ChevronLeft, ChevronRight, Inbox } from "lucide-react";

export interface Column<T> {
  header: string;
  accessorKey?: keyof T;
  cell?: (item: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  searchPlaceholder?: string;
  searchFilter?: (item: T, query: string) => boolean;
  pageSize?: number;
  emptyMessage?: string;
  actions?: ReactNode;
}

export function DataTable<T extends Record<string, any>>({
  data,
  columns,
  searchPlaceholder = "Search records...",
  searchFilter,
  pageSize = 10,
  emptyMessage = "No records found matching criteria.",
  actions,
}: DataTableProps<T>) {
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  const filteredData = React.useMemo(() => {
    if (!searchQuery.trim()) return data;
    if (searchFilter) {
      return data.filter((item) => searchFilter(item, searchQuery.toLowerCase().trim()));
    }
    // Default search across all string/number fields
    return data.filter((item) =>
      Object.values(item).some(
        (val) =>
          val !== null &&
          val !== undefined &&
          String(val).toLowerCase().includes(searchQuery.toLowerCase().trim())
      )
    );
  }, [data, searchQuery, searchFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredData.length / pageSize));
  const paginatedData = React.useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredData.slice(start, start + pageSize);
  }, [filteredData, currentPage, pageSize]);

  return (
    <div className="rounded-xl border border-[#2A2A30] bg-[#111114] overflow-hidden">
      {/* Search and Action Toolbar */}
      <div className="p-4 border-b border-[#2A2A30] flex flex-col sm:flex-row items-center justify-between gap-3 bg-[#111114]">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-[#71717A]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder={searchPlaceholder}
            className="w-full bg-[#1F1F23] border border-[#2A2A30] rounded-lg pl-9 pr-4 py-2 text-xs text-[#F5F5F5] placeholder-[#71717A] focus:outline-none focus:border-[#6366F1] transition"
          />
        </div>
        {actions && <div className="flex items-center gap-2 w-full sm:w-auto">{actions}</div>}
      </div>

      {/* Table view */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#18181B] text-[#A1A1AA] uppercase tracking-wider text-[10px] font-semibold border-b border-[#2A2A30]">
            <tr>
              {columns.map((col, idx) => (
                <th key={idx} className={`px-4 py-3 ${col.className || ""}`}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1F1F23] text-[#D4D4D8]">
            {paginatedData.length > 0 ? (
              paginatedData.map((row, rowIdx) => (
                <tr key={rowIdx} className="hover:bg-[#18181B]/50 transition">
                  {columns.map((col, colIdx) => (
                    <td key={colIdx} className={`px-4 py-3.5 ${col.className || ""}`}>
                      {col.cell ? col.cell(row) : col.accessorKey ? String(row[col.accessorKey] ?? "") : null}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="py-12 text-center text-[#71717A]">
                  <div className="flex flex-col items-center justify-center">
                    <Inbox className="h-8 w-8 text-[#3F3F46] mb-2" />
                    <span>{emptyMessage}</span>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div className="p-4 border-t border-[#2A2A30] flex items-center justify-between text-xs text-[#A1A1AA] bg-[#111114]">
          <span>
            Showing {(currentPage - 1) * pageSize + 1} -{" "}
            {Math.min(currentPage * pageSize, filteredData.length)} of {filteredData.length} entries
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="px-2">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1.5 rounded-lg border border-[#2A2A30] bg-[#1F1F23] hover:bg-[#2A2A30] disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

