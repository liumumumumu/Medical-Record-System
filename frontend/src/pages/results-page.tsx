import { FileTextOutlined, LeftOutlined } from "@ant-design/icons";
import { Link } from "react-router-dom";
import type { GeneratedRecord } from "../types/medical-record";

type ResultsPageProps = {
  record: GeneratedRecord | null;
};

const genderLabels: Record<string, string> = { male: "男", female: "女" };
const departmentLabels: Record<string, string> = {
  internal: "内科",
  surgery: "外科",
  pediatrics: "儿科",
  emergency: "急诊",
  other: "其他",
};

function text(value: string | string[] | undefined, fallback = "未填写") {
  if (Array.isArray(value)) return value.length ? value.join("、") : fallback;
  return value?.trim() || fallback;
}

export function ResultsPage({ record }: ResultsPageProps) {
  if (!record) {
    return (
      <main className="results-main results-main--empty">
        <section className="results-empty" aria-labelledby="empty-title">
          <span className="results-empty__icon" aria-hidden="true"><FileTextOutlined /></span>
          <p className="section-kicker">No Generated Record</p>
          <h2 id="empty-title">还没有可查看的分析结果</h2>
          <p>先完成一份病例录入，生成后的结构化病历和分析内容会集中显示在这里。</p>
          <Link className="primary-button" to="/upload">前往录入病例</Link>
        </section>
      </main>
    );
  }

  const { values } = record;
  const patientName = text(values.patientName, "未命名患者");
  const gender = genderLabels[text(values.gender, "")] ?? text(values.gender);
  const department = departmentLabels[text(values.department, "")] ?? text(values.department);
  const attachments = text(values.attachments, "暂无检查资料");
  const generatedTime = new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(record.generatedAt));

  return (
    <main className="results-main">
      <header className="results-heading">
        <div>
          <p className="section-kicker">Generated Record</p>
          <h2>{patientName}的病例分析</h2>
          <p>生成编号 {record.id} · {generatedTime}</p>
        </div>
        <Link className="text-link" to="/upload"><LeftOutlined />返回修改病例</Link>
      </header>

      <div className="results-document">
        <section className="result-section" aria-labelledby="summary-title">
          <div className="result-section__index">01</div>
          <div className="result-section__content">
            <p className="section-kicker">Summary</p>
            <h3 id="summary-title">病例摘要</h3>
            <dl className="summary-list">
              <div><dt>患者</dt><dd>{patientName}</dd></div>
              <div><dt>性别</dt><dd>{gender}</dd></div>
              <div><dt>年龄</dt><dd>{text(values.age)} 岁</dd></div>
              <div><dt>就诊科室</dt><dd>{department}</dd></div>
              <div><dt>就诊日期</dt><dd>{text(values.visitDate)}</dd></div>
              <div><dt>主诉</dt><dd>{text(values.chiefComplaint)}</dd></div>
            </dl>
          </div>
        </section>

        <section className="result-section" aria-labelledby="record-title">
          <div className="result-section__index">02</div>
          <div className="result-section__content">
            <p className="section-kicker">Structured Record</p>
            <h3 id="record-title">结构化病历</h3>
            <div className="record-copy">
              <article><h4>现病史</h4><p>{text(values.presentIllness)}</p></article>
              <article><h4>既往病史</h4><p>{text(values.pastHistory)}</p></article>
              <article><h4>过敏史</h4><p>{text(values.allergyHistory)}</p></article>
              <article><h4>生命体征与体格检查</h4><p>{text(values.vitalSigns)}；{text(values.physicalExam)}</p></article>
              <article><h4>辅助检查</h4><p>{text(values.auxiliaryExam)}</p></article>
            </div>
          </div>
        </section>

        <section className="result-section" aria-labelledby="analysis-title">
          <div className="result-section__index">03</div>
          <div className="result-section__content">
            <p className="section-kicker">Clinical Notes</p>
            <h3 id="analysis-title">分析与诊疗信息</h3>
            <div className="analysis-grid">
              <article><span>初步诊断</span><p>{text(values.preliminaryDiagnosis, "等待专业人员结合检查结果判断")}</p></article>
              <article><span>已采取治疗</span><p>{text(values.treatmentTaken)}</p></article>
              <article><span>用药情况</span><p>{text(values.medicationUsage)}</p></article>
              <article><span>生成需求</span><p>{text(values.generationNeeds, "标准病历与基础分析")}</p></article>
            </div>
            <p className="medical-notice">本页面为课程演示生成结果，仅用于信息整理，不替代执业医师的诊断与治疗意见。</p>
          </div>
        </section>

        <section className="result-section" aria-labelledby="files-title">
          <div className="result-section__index">04</div>
          <div className="result-section__content">
            <p className="section-kicker">Attachments</p>
            <h3 id="files-title">检查资料</h3>
            <div className="attachment-row"><FileTextOutlined /><span>{attachments}</span></div>
          </div>
        </section>
      </div>
    </main>
  );
}
