interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalCount: number;
  onPageChange: (page: number) => void;
  itemName?: string;
}

export default function Pagination({
  currentPage,
  totalPages,
  totalCount,
  onPageChange,
  itemName = 'items',
}: PaginationProps) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: '1rem',
        marginTop: '2rem',
      }}
    >
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        style={{
          padding: '0.5rem 1rem',
          background: currentPage === 1 ? '#ddd' : '#4CAF50',
          color: currentPage === 1 ? '#999' : 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
        }}
      >
        Previous
      </button>

      <span style={{ color: '#666' }}>
        Page {currentPage} of {totalPages} ({totalCount.toLocaleString()} {itemName})
      </span>

      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        style={{
          padding: '0.5rem 1rem',
          background: currentPage === totalPages ? '#ddd' : '#4CAF50',
          color: currentPage === totalPages ? '#999' : 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
        }}
      >
        Next
      </button>
    </div>
  );
}
