import { IntroSection } from "../components/upload/intro-section";
import { UploadModule } from "../components/upload/upload-module";
import type { MedicalFormValues } from "../types/medical-record";

type UploadPageProps = {
  isLoggedIn: boolean;
  onGenerate: (values: MedicalFormValues) => Promise<{ id: string }>;
  onRequireLogin: () => void;
};

export function UploadPage({ isLoggedIn, onGenerate, onRequireLogin }: UploadPageProps) {
  return (
    <main className="page-main">
      <UploadModule isLoggedIn={isLoggedIn} onGenerate={onGenerate} onRequireLogin={onRequireLogin} />
      <IntroSection />
    </main>
  );
}
