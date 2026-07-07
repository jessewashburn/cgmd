import { ReactElement } from 'react';
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/server';
import { makeHarness } from '../test/utils';
import { resetRequestLog } from '../test/handlers';
import WorkListPage from './WorkListPage';
import ComposerListPage from './ComposerListPage';
import SearchPage from './SearchPage';

beforeEach(() => resetRequestLog());

function renderAt(ui: ReactElement, route: string) {
  const { wrapper: Wrapper } = makeHarness([route]);
  return render(<Wrapper>{ui}</Wrapper>);
}

const emptyList = () =>
  HttpResponse.json({ count: 0, next: null, previous: null, results: [] });

describe('WorkListPage', () => {
  it('renders rows from the API', async () => {
    renderAt(<WorkListPage />, '/works');
    expect(await screen.findByText('Row One')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Works' })).toBeInTheDocument();
  });

  it('shows the empty state when there are no results', async () => {
    server.use(http.get('*/api/works/', emptyList));
    renderAt(<WorkListPage />, '/works');
    expect(await screen.findByText(/No works found/i)).toBeInTheDocument();
  });

  it('shows an error with a working Retry button', async () => {
    server.use(http.get('*/api/works/', () => new HttpResponse(null, { status: 500 })));
    renderAt(<WorkListPage />, '/works');

    expect(await screen.findByText(/Failed to load works/i)).toBeInTheDocument();

    // Recover the endpoint, click Retry, and confirm rows load.
    server.use(
      http.get('*/api/works/', () =>
        HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [{ id: 1, title: 'Row One', composer: { id: 1, full_name: 'A' }, instrumentation_category: null }],
        }),
      ),
    );
    await userEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(await screen.findByText('Row One')).toBeInTheDocument();
  });
});

describe('ComposerListPage', () => {
  it('renders composer rows from the API', async () => {
    renderAt(<ComposerListPage />, '/composers');
    expect(await screen.findByText('Row One')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Composers' })).toBeInTheDocument();
  });
});

describe('SearchPage', () => {
  it('shows results for a query taken from the URL', async () => {
    renderAt(<SearchPage />, '/search?q=sor');
    await waitFor(() => expect(screen.getByText(/Found/i)).toBeInTheDocument());
    // "Row One" appears as both a work and a composer result.
    expect(screen.getAllByText('Row One').length).toBeGreaterThan(0);
  });

  it('prompts for input when there is no query', () => {
    renderAt(<SearchPage />, '/search');
    expect(screen.getByText(/Enter a search query/i)).toBeInTheDocument();
  });
});
