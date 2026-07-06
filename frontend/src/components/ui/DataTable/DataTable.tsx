import { ReactNode } from 'react';
import './DataTable.css';

export interface Column<T> {
  header: string | ReactNode;
  accessor: keyof T | ((row: T) => ReactNode);
  /** Backend ordering field. When set (with an onSort handler), the header is clickable and sortable. */
  sortKey?: string;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

export interface SortState {
  key: string;
  dir: 'asc' | 'desc';
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  getRowKey: (row: T) => string | number;
  onRowClick?: (row: T) => void;
  loading?: boolean;
  emptyMessage?: string;
  /** Current sort (backend field + direction). Drives the header arrow / aria-sort. */
  sort?: SortState | null;
  /** Called with a column's sortKey when a sortable header is clicked. */
  onSort?: (key: string) => void;
}

export default function DataTable<T>({
  data,
  columns,
  getRowKey,
  onRowClick,
  loading = false,
  emptyMessage = 'No data available',
  sort = null,
  onSort,
}: DataTableProps<T>) {
  if (loading) {
    return (
      <div className="loading-state">
        <p>Loading...</p>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="empty-state">
        <p>{emptyMessage}</p>
      </div>
    );
  }

  const getCellValue = (row: T, column: Column<T>) => {
    if (typeof column.accessor === 'function') {
      return column.accessor(row);
    }
    return row[column.accessor] as ReactNode;
  };

  const getAlignClass = (align?: string) => {
    if (align === 'center') return 'align-center';
    if (align === 'right') return 'align-right';
    return '';
  };

  const renderHeader = (column: Column<T>) => {
    const sortable = !!column.sortKey && !!onSort;
    if (!sortable) return column.header;

    const active = sort?.key === column.sortKey;
    const arrow = active ? (sort!.dir === 'asc' ? ' ↑' : ' ↓') : '';
    return (
      <span
        className="sort-header"
        role="button"
        tabIndex={0}
        onClick={() => onSort!(column.sortKey!)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onSort!(column.sortKey!);
          }
        }}
      >
        {column.header}
        {arrow}
      </span>
    );
  };

  const ariaSort = (column: Column<T>): 'ascending' | 'descending' | undefined => {
    if (!column.sortKey || sort?.key !== column.sortKey) return undefined;
    return sort!.dir === 'asc' ? 'ascending' : 'descending';
  };

  return (
    <div className="data-table-container">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column, index) => (
              <th
                key={index}
                className={getAlignClass(column.align)}
                style={{ width: column.width }}
                aria-sort={ariaSort(column)}
              >
                {renderHeader(column)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr
              key={getRowKey(row)}
              className={onRowClick ? 'clickable' : ''}
              onClick={() => onRowClick?.(row)}
            >
              {columns.map((column, index) => (
                <td
                  key={index}
                  className={getAlignClass(column.align)}
                >
                  {getCellValue(row, column)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
