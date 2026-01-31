import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Navbar.css';
import solmuLogo from '../../../assets/Solmu.png';

export default function Navbar() {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
          <img src={solmuLogo} alt="Solmu" className="navbar-logo" />
          <div className="navbar-title">
            <div className="navbar-name">Solmu - Guitar Music Network</div>
            <div className="navbar-tagline">Our repertoire, all in one place</div>
          </div>
        </Link>

        <button 
          className="hamburger-menu" 
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle menu"
        >
          <span></span>
          <span></span>
          <span></span>
        </button>

        <ul className={`navbar-links ${mobileMenuOpen ? 'mobile-open' : ''}`}>
          <li>
            <Link 
              to="/" 
              className={`navbar-link ${isActive('/composers') ? 'active' : ''}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              Composers
            </Link>
          </li>
          <li>
            <Link 
              to="/works" 
              className={`navbar-link ${isActive('/works') ? 'active' : ''}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              Works
            </Link>
          </li>
          <li>
            <Link 
              to="/about" 
              className={`navbar-link ${isActive('/about') ? 'active' : ''}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              About
            </Link>
          </li>
        </ul>
      </div>
    </nav>
  );
}
