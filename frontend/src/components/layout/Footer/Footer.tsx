import { useState } from 'react';
import { Link } from 'react-router-dom';
import SuggestNewWorkModal from '../../ui/SuggestNewWorkModal';
import { useAuth } from '../../../contexts/useAuth';
import './Footer.css';

export default function Footer() {
  const [showSuggestModal, setShowSuggestModal] = useState(false);
  const { isAuthenticated } = useAuth();

  return (
    <>
      <footer className="app-footer">
        <div className="footer-content">
          <div className="footer-links">
            <button 
              onClick={() => setShowSuggestModal(true)} 
              className="footer-link footer-link-button"
            >
              Suggest a Work
            </button>
            <Link to="/privacy" className="footer-link">Privacy Policy</Link>
            <Link to="/about" className="footer-link">About</Link>
            <Link to={isAuthenticated ? '/admin' : '/admin/login'} className="footer-link">Admin</Link>
          </div>
          <div className="footer-copyright">
            © {new Date().getFullYear()} Solmu - Guitar Music Network
          </div>
        </div>
      </footer>

      <SuggestNewWorkModal 
        isOpen={showSuggestModal} 
        onClose={() => setShowSuggestModal(false)} 
      />
    </>
  );
}
