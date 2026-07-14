import { useState } from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LinkListEditor, { DraftLink } from './LinkListEditor';

// Controlled harness so interactions flow through real state, like the forms do.
function Harness({ initial = [] as DraftLink[] }) {
  const [links, setLinks] = useState<DraftLink[]>(initial);
  return (
    <>
      <LinkListEditor links={links} onChange={setLinks} />
      <output data-testid="state">{JSON.stringify(links)}</output>
    </>
  );
}

const state = () => JSON.parse(screen.getByTestId('state').textContent || '[]');

describe('LinkListEditor', () => {
  it('adds, edits, and removes a link row', async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole('button', { name: '+ Add link' }));
    expect(screen.getByLabelText('Link title')).toBeInTheDocument();

    await user.type(screen.getByLabelText('Link title'), 'Publisher');
    await user.type(screen.getByLabelText('Link URL'), 'https://vogtfritz.de');
    expect(state()).toEqual([{ label: 'Publisher', url: 'https://vogtfritz.de' }]);

    await user.click(screen.getByRole('button', { name: 'Remove link' }));
    expect(state()).toEqual([]);
  });

  it('pre-fills existing links', () => {
    render(<Harness initial={[{ label: 'BCGS Commission', url: 'https://bcgs.org', link_type: 'commission' }]} />);
    expect(screen.getByLabelText('Link title')).toHaveValue('BCGS Commission');
    expect(screen.getByLabelText('Link URL')).toHaveValue('https://bcgs.org');
  });
});
