import { Link, useLocation } from 'react-router-dom';
import '../styles/components/Navbar.css';

export default function Navbar() {
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === '/' && location.pathname === '/') return true;
    if (path === '/composers' && location.pathname === '/') return true;
    if (path === '/works' && location.pathname === '/works') return true;
    if (path !== '/' && path !== '/works' && location.pathname.startsWith(path)) return true;
    return false;
  };

  return (
    <nav className="navbar">
      <div className="navbar-content">
        <Link to="/" className="navbar-brand">
          Solmu - Guitar Music Network
        </Link>

        <ul className="navbar-links">
          <li>
            <Link to="/" className={`navbar-link ${isActive('/composers') ? 'active' : ''}`}>
              Composers
            </Link>
          </li>
          <li>
            <Link to="/works" className={`navbar-link ${isActive('/works') ? 'active' : ''}`}>
              Works
            </Link>
          </li>
          <li>
            <Link to="/about" className={`navbar-link ${isActive('/about') ? 'active' : ''}`}>
              About
            </Link>
          </li>
        </ul>
      </div>
    </nav>
  );
}
