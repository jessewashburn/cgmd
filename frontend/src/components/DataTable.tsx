import { ReactNode } from 'react';

export interface Column<T> {
  header: string | ReactNode;
  accessor: keyof T | ((row: T) => ReactNode);
  width?: string;
  align?: 'left' | 'center' | 'right';
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  getRowKey: (row: T) => string | number;
  onRowClick?: (row: T) => void;
  loading?: boolean;
  emptyMessage?: string;
}

export default function DataTable<T>({
  data,
  columns,
  getRowKey,
  onRowClick,
  loading = false,
  emptyMessage = 'No data available',
}: DataTableProps<T>) {
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: '#666' }}>
        <p>Loading...</p>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: '#666' }}>
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

  return (
    <div style={{ marginBottom: '2rem', overflowX: 'auto' }}>
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          background: 'white',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        }}
      >
        <thead>
          <tr style={{ background: '#f5f5f5', borderBottom: '2px solid #ddd' }}>
            {columns.map((column, index) => (
              <th
                key={index}
                style={{
                  padding: '1rem',
                  textAlign: column.align || 'left',
                  fontWeight: '600',
                  width: column.width,
                }}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr
              key={getRowKey(row)}
              style={{
                borderBottom: '1px solid #eee',
                cursor: onRowClick ? 'pointer' : 'default',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = '#f9f9f9')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'white')}
              onClick={() => onRowClick?.(row)}
            >
              {columns.map((column, index) => (
                <td
                  key={index}
                  style={{
                    padding: '1rem',
                    textAlign: column.align || 'left',
                    color: '#666',
                  }}
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
