export type MedicalFieldGroupKey =
  | "patient"
  | "condition"
  | "exam"
  | "treatment";

export type MedicalFieldType =
  | "text"
  | "number"
  | "select"
  | "date"
  | "textarea"
  | "multiselect"
  | "file";

export type MedicalFieldOption = {
  label: string;
  value: string;
};

export type MedicalFieldConfig = {
  key: string;
  label: string;
  type: MedicalFieldType;
  group: MedicalFieldGroupKey;
  required: boolean;
  placeholder?: string;
  options?: MedicalFieldOption[];
  defaultVisible: boolean;
  fullWidth?: boolean;
  min?: number;
  max?: number;
  maxLength?: number;
  unit?: string;
  errorMessage?: string;
};

export type MedicalFieldGroup = {
  key: MedicalFieldGroupKey;
  title: string;
  description: string;
};

export const medicalFieldGroups: MedicalFieldGroup[] = [
  {
    key: "patient",
    title: "患者基础信息",
    description: "用于生成病历首页与初步判断所需的核心身份信息。",
  },
  {
    key: "condition",
    title: "病情描述",
    description: "影响病历生成、症状识别与诊断分析的核心描述区域。",
  },
  {
    key: "exam",
    title: "检查信息",
    description: "用于补充客观检查、体征与辅助资料。",
  },
  {
    key: "treatment",
    title: "诊疗信息",
    description: "用于完善初步诊断、治疗过程与报告输出需求。",
  },
];

export const medicalFieldConfigs: MedicalFieldConfig[] = [
  {
    key: "patientName",
    label: "姓名",
    type: "text",
    group: "patient",
    required: true,
    placeholder: "请输入患者姓名",
    defaultVisible: true,
    maxLength: 30,
    errorMessage: "请输入患者姓名",
  },
  {
    key: "gender",
    label: "性别",
    type: "select",
    group: "patient",
    required: true,
    placeholder: "请选择性别",
    options: [
      { label: "男", value: "male" },
      { label: "女", value: "female" },
    ],
    defaultVisible: true,
    errorMessage: "请选择患者性别",
  },
  {
    key: "age",
    label: "年龄",
    type: "number",
    group: "patient",
    required: true,
    placeholder: "请输入年龄",
    defaultVisible: true,
    min: 0,
    max: 130,
    unit: "岁",
    errorMessage: "请输入 0 至 130 之间的年龄",
  },
  {
    key: "department",
    label: "就诊科室",
    type: "select",
    group: "patient",
    required: false,
    placeholder: "请选择科室",
    options: [
      { label: "内科", value: "internal" },
      { label: "外科", value: "surgery" },
      { label: "儿科", value: "pediatrics" },
      { label: "急诊", value: "emergency" },
      { label: "其他", value: "other" },
    ],
    defaultVisible: false,
  },
  {
    key: "visitDate",
    label: "就诊日期",
    type: "date",
    group: "patient",
    required: false,
    defaultVisible: false,
  },
  {
    key: "chiefComplaint",
    label: "主诉",
    type: "textarea",
    group: "condition",
    required: true,
    placeholder: "例如：发热、咳嗽 3 天",
    defaultVisible: true,
    fullWidth: true,
    maxLength: 200,
    errorMessage: "请填写患者主诉",
  },
  {
    key: "presentIllness",
    label: "现病史",
    type: "textarea",
    group: "condition",
    required: true,
    placeholder: "请描述本次疾病的发生、发展与症状变化",
    defaultVisible: false,
    fullWidth: true,
    maxLength: 1200,
    errorMessage: "请填写现病史",
  },
  {
    key: "pastHistory",
    label: "既往病史",
    type: "textarea",
    group: "condition",
    required: false,
    placeholder: "请填写高血压、糖尿病、手术史等信息；未填写将标记为未提供",
    defaultVisible: false,
    fullWidth: true,
    maxLength: 800,
  },
  {
    key: "allergyHistory",
    label: "过敏史",
    type: "textarea",
    group: "condition",
    required: false,
    placeholder: "请填写药物、食物或其他过敏情况",
    defaultVisible: false,
  },
  {
    key: "vitalSigns",
    label: "生命体征",
    type: "textarea",
    group: "exam",
    required: false,
    placeholder: "例如：体温、血压、心率、呼吸等",
    defaultVisible: false,
  },
  {
    key: "physicalExam",
    label: "体格检查",
    type: "textarea",
    group: "exam",
    required: false,
    placeholder: "例如：咽部充血、肺部啰音等",
    defaultVisible: false,
  },
  {
    key: "auxiliaryExam",
    label: "辅助检查结果",
    type: "textarea",
    group: "exam",
    required: false,
    placeholder: "请填写血常规、影像检查、化验结果等",
    defaultVisible: false,
    fullWidth: true,
  },
  {
    key: "attachments",
    label: "上传检查资料",
    type: "file",
    group: "exam",
    required: false,
    defaultVisible: false,
    fullWidth: true,
  },
  {
    key: "preliminaryDiagnosis",
    label: "初步诊断",
    type: "textarea",
    group: "treatment",
    required: false,
    placeholder: "例如：上呼吸道感染",
    defaultVisible: false,
  },
  {
    key: "treatmentTaken",
    label: "已采取治疗",
    type: "textarea",
    group: "treatment",
    required: false,
    placeholder: "例如：退热、输液、抗感染等",
    defaultVisible: false,
  },
  {
    key: "medicationUsage",
    label: "用药情况",
    type: "textarea",
    group: "treatment",
    required: false,
    placeholder: "请填写当前或既往用药情况",
    defaultVisible: false,
  },
  {
    key: "generationNeeds",
    label: "生成需求",
    type: "multiselect",
    group: "treatment",
    required: false,
    options: [
      { label: "生成标准病历", value: "record" },
      { label: "生成症状分析", value: "symptom" },
      { label: "生成诊断建议", value: "diagnosis" },
      { label: "生成治疗建议", value: "treatment" },
      { label: "生成完整分析报告", value: "full-report" },
    ],
    defaultVisible: false,
    fullWidth: true,
  },
];
