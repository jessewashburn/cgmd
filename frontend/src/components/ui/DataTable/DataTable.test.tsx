import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DataTable, { Column } from './DataTable';

interface Row {
  id: number;
  name: string;
  count: number;
}

const rows: Row[] = [
  { id: 1, name: 'Alpha', count: 3 },
  { id: 2, name: 'Beta', count: 7 },
];

const columns: Column<Row>[] = [
  { header: 'Name', accessor: 'name', sortKey: 'name' },
  { header: 'Count', accessor: (r) => `#${r.count}` }, // render fn, not sortable
];

describe('DataTable', () => {
  it('renders headers and cells from the column config', () => {
    render(<DataTable data={rows} columns={columns} getRowKey={(r) => r.id} />);
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('#7')).toBeInTheDocument(); // render-fn accessor
  });

  it('calls onSort with the column sortKey when a sortable header is clicked', async () => {
    const onSort = vi.fn();
    render(
      <DataTable data={rows} columns={columns} getRowKey={(r) => r.id} onSort={onSort} />,
    );
    await userEvent.click(screen.getByText('Name'));
    expect(onSort).toHaveBeenCalledWith('name');
  });

  it('shows the sort arrow and aria-sort on the active column', () => {
    render(
      <DataTable
        data={rows}
        columns={columns}
        getRowKey={(r) => r.id}
        onSort={vi.fn()}
        sort={{ key: 'name', dir: 'desc' }}
      />,
    );
    expect(screen.getByText(/Name/).textContent).toContain('↓');
    const header = screen.getByText(/Name/).closest('th');
    expect(header).toHaveAttribute('aria-sort', 'descending');
  });

  it('does not make non-sortable headers interactive', async () => {
    const onSort = vi.fn();
    render(
      <DataTable data={rows} columns={columns} getRowKey={(r) => r.id} onSort={onSort} />,
    );
    await userEvent.click(screen.getByText('Count'));
    expect(onSort).not.toHaveBeenCalled();
  });

  it('triggers sort on Enter for keyboard users', async () => {
    const onSort = vi.fn();
    render(
      <DataTable data={rows} columns={columns} getRowKey={(r) => r.id} onSort={onSort} />,
    );
    screen.getByText('Name').focus();
    await userEvent.keyboard('{Enter}');
    expect(onSort).toHaveBeenCalledWith('name');
  });

  it('renders the loading and empty states', () => {
    const { rerender } = render(
      <DataTable data={[]} columns={columns} getRowKey={(r) => r.id} loading />,
    );
    expect(screen.getByText('Loading...')).toBeInTheDocument();

    rerender(
      <DataTable
        data={[]}
        columns={columns}
        getRowKey={(r) => r.id}
        emptyMessage="Nothing here"
      />,
    );
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
  });
});
