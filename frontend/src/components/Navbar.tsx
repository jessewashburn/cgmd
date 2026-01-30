import { Link, useLocation } from 'react-router-dom';

export default function Navbar() {
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === '/' && location.pathname === '/') return true;
    if (path !== '/' && location.pathname.startsWith(path)) return true;
    return false;
  };

  const linkStyle = (path: string) => ({
    textDecoration: 'none',
    color: isActive(path) ? '#2e7d32' : '#555',
    fontWeight: isActive(path) ? '600' : '500',
    padding: '0.5rem 1rem',
    borderBottom: isActive(path) ? '2px solid #2e7d32' : '2px solid transparent',
    transition: 'all 0.2s ease',
  });

  return (
    <nav
      style={{
        background: 'white',
        borderBottom: '1px solid #e0e0e0',
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
        position: 'sticky',
        top: 0,
        zIndex: 1000,
      }}
    >
      <div
        style={{
          maxWidth: '1400px',
          margin: '0 auto',
          padding: '0 2rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          height: '64px',
        }}
      >
        {/* Logo/Brand */}
        <Link
          to="/"
          style={{
            textDecoration: 'none',
            color: '#1a1a1a',
            fontSize: '1.25rem',
            fontWeight: '700',
          }}
        >
          CGMD
        </Link>

        {/* Navigation Links */}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Link to="/" style={linkStyle('/')}>
            Works
          </Link>
          <Link to="/composers" style={linkStyle('/composers')}>
            Composers
          </Link>
          <Link to="/about" style={linkStyle('/about')}>
            About
          </Link>
        </div>
      </div>
    </nav>
  );
}
