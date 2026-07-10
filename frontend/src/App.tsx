import { useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { LoginDialog } from "./components/auth/login-dialog";
import { TopNav } from "./components/layout/top-nav";
import { ResultsPage } from "./pages/results-page";
import { UploadPage } from "./pages/upload-page";
import type { GeneratedRecord, MedicalFormValues } from "./types/medical-record";

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);
  const [generatedRecord, setGeneratedRecord] = useState<GeneratedRecord | null>(() => {
    try {
      const storedRecord = window.sessionStorage.getItem("medical-generated-record");
      return storedRecord ? JSON.parse(storedRecord) as GeneratedRecord : null;
    } catch {
      return null;
    }
  });

  function handleGenerate(values: MedicalFormValues) {
    const nextRecord: GeneratedRecord = {
      id: `MR-${Date.now().toString().slice(-8)}`,
      generatedAt: new Date().toISOString(),
      values,
    };

    setGeneratedRecord(nextRecord);
    window.sessionStorage.setItem("medical-generated-record", JSON.stringify(nextRecord));
  }

  return (
    <div className="app-shell">
      <div className="background-grid" aria-hidden="true" />
      <TopNav
        isLoggedIn={isLoggedIn}
        onLogin={() => setLoginOpen(true)}
        onLogout={() => setIsLoggedIn(false)}
      />

      <Routes>
        <Route path="/" element={<Navigate replace to="/upload" />} />
        <Route path="/upload" element={<UploadPage onGenerate={handleGenerate} />} />
        <Route path="/results" element={<ResultsPage record={generatedRecord} />} />
        <Route path="*" element={<Navigate replace to="/upload" />} />
      </Routes>

      <LoginDialog
        open={loginOpen}
        onClose={() => setLoginOpen(false)}
        onLogin={() => {
          setIsLoggedIn(true);
          setLoginOpen(false);
        }}
      />
    </div>
  );
}

export default App;
