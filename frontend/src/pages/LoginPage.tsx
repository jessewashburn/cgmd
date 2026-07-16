import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Authenticator, useAuthenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import { useAuth } from '../contexts/useAuth';
import { cognitoConfigured } from '../lib/amplify';
import './LoginPage.css';

// Rendered inside <Authenticator>; fires once Cognito reports an authenticated
// session, then syncs AuthContext and moves on to the admin dashboard.
function RedirectWhenAuthed() {
  const { authStatus } = useAuthenticator((ctx) => [ctx.authStatus]);
  const { refresh } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (authStatus === 'authenticated') {
      refresh().then(() => navigate('/admin', { replace: true }));
    }
  }, [authStatus, refresh, navigate]);

  return null;
}

export default function LoginPage() {
  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <h1>Admin Login</h1>
          <p>Solmu - Guitar Music Network</p>
        </div>

        {cognitoConfigured ? (
          <Authenticator hideSignUp>
            {() => <RedirectWhenAuthed />}
          </Authenticator>
        ) : (
          <div className="login-notice">
            Admin login isn’t configured yet.
          </div>
        )}
      </div>
    </div>
  );
}
