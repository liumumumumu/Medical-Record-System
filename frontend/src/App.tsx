import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { LoginDialog } from "./components/auth/login-dialog";
import { TopNav } from "./components/layout/top-nav";
import { HistoryPage } from "./pages/history-page";
import { ResultsPage } from "./pages/results-page";
import { UploadPage } from "./pages/upload-page";
import {
  clearStoredToken,
  createAndAnalyze,
  getCurrentUser,
  isUnauthorized,
  login,
  logout,
  register,
} from "./services/medical-api";
import type { AuthUser, MedicalFormValues, RegisterRequest } from "./types/medical-record";

function App() {
  const navigate = useNavigate();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loginOpen, setLoginOpen] = useState(false);

  function handleAuthExpired() {
    clearStoredToken();
    setUser(null);
    setLoginOpen(true);
  }

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then((currentUser) => {
        if (active) setUser(currentUser);
      })
      .catch(() => {
        clearStoredToken();
      });
    return () => { active = false; };
  }, []);

  async function handleLogin(username: string, password: string) {
    const session = await login(username, password);
    setUser(session.user);
    setLoginOpen(false);
  }

  async function handleRegister(request: RegisterRequest) {
    const session = await register(request);
    setUser(session.user);
    setLoginOpen(false);
  }

  async function handleLogout() {
    try {
      await logout();
    } finally {
      setUser(null);
      navigate("/upload");
    }
  }

  async function handleGenerate(values: MedicalFormValues) {
    try {
      return await createAndAnalyze(values);
    } catch (error) {
      if (isUnauthorized(error)) handleAuthExpired();
      throw error;
    }
  }

  return (
    <div className="app-shell">
      <div className="background-grid" aria-hidden="true" />
      <TopNav
        user={user}
        onLogin={() => setLoginOpen(true)}
        onLogout={() => { void handleLogout(); }}
      />

      <Routes>
        <Route path="/" element={<Navigate replace to="/upload" />} />
        <Route path="/upload" element={<UploadPage isLoggedIn={Boolean(user)} onGenerate={handleGenerate} onRequireLogin={() => setLoginOpen(true)} />} />
        <Route path="/history" element={<HistoryPage isLoggedIn={Boolean(user)} onAuthExpired={handleAuthExpired} onRequireLogin={() => setLoginOpen(true)} />} />
        <Route path="/results" element={<ResultsPage isLoggedIn={Boolean(user)} onAuthExpired={handleAuthExpired} onRequireLogin={() => setLoginOpen(true)} />} />
        <Route path="/results/:id" element={<ResultsPage isLoggedIn={Boolean(user)} onAuthExpired={handleAuthExpired} onRequireLogin={() => setLoginOpen(true)} />} />
        <Route path="*" element={<Navigate replace to="/upload" />} />
      </Routes>

      <LoginDialog open={loginOpen} onClose={() => setLoginOpen(false)} onLogin={handleLogin} onRegister={handleRegister} />
    </div>
  );
}

export default App;
