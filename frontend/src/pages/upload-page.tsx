import { IntroSection } from "../components/upload/intro-section";
import { UploadModule } from "../components/upload/upload-module";
import type { MedicalFormValues } from "../types/medical-record";

type UploadPageProps = {
  onGenerate: (values: MedicalFormValues) => void;
};

export function UploadPage({ onGenerate }: UploadPageProps) {
  return (
    <main className="page-main">
      <UploadModule onGenerate={onGenerate} />
      <IntroSection />
    </main>
  );
}
