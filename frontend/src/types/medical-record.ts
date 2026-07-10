export type FieldValue = string | string[];

export type MedicalFormValues = Record<string, FieldValue>;

export type GeneratedRecord = {
  id: string;
  generatedAt: string;
  values: MedicalFormValues;
};
