import { DownloadOutlined, EditOutlined, FileTextOutlined, LeftOutlined, SaveOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { downloadReport, getCase, isUnauthorized, updateCase } from "../services/medical-api";
import type { AiResult, CaseRecordView } from "../types/medical-record";

type ResultsPageProps = {
  isLoggedIn: boolean;
  onAuthExpired: () => void;
  onRequireLogin: () => void;
};

const genderLabels: Record<string, string> = { male: "男", female: "女" };
const departmentLabels: Record<string, string> = { internal: "内科", surgery: "外科", pediatrics: "儿科", emergency: "急诊", other: "其他" };

function text(value: string | string[] | null | undefined, fallback = "未填写") {
  if (Array.isArray(value)) return value.length ? value.join("、") : fallback;
  return value?.trim() || fallback;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function generatedText(record: CaseRecordView) {
  return record.editedRecord || record.generatedRecord || record.aiResult?.structuredRecord.generatedRecord || "后端暂未返回可编辑的结构化病历文本。";
}

function AnalysisContent({ aiResult }: { aiResult: AiResult | null }) {
  if (!aiResult) return <p className="result-muted">本病例尚未获得 AI 分析结果，请查看状态说明或稍后重试。</p>;
  const { analysis } = aiResult;
  return (
    <>
      <div className="analysis-grid">
        <article><span>主要诊断建议</span><p>{text(analysis.diagnosisTop1, "未生成")}</p></article>
        <article><span>候选诊断</span><p>{text(analysis.diagnosisCandidates, "未生成")}</p></article>
        <article><span>判断依据</span><p>{text(analysis.diagnosisReason, "未生成")}</p></article>
        <article><span>处理建议</span><p>{text(analysis.treatmentAdvice, "未生成")}</p></article>
      </div>
      <div className="term-groups">
        <div><span>识别症状</span><p>{text(analysis.symptoms, "未识别")}</p></div>
        <div><span>医学术语</span><p>{text(analysis.medicalTerms, "未识别")}</p></div>
      </div>
      {analysis.lowConfidence ? <p className="medical-notice">模型对当前结果的可靠性提示：{text(analysis.lowConfidenceReason, "请结合完整病史、检查结果及执业医师判断。")}</p> : null}
      <p className="medical-notice">{text(analysis.disclaimer, "该结果仅用于信息整理与辅助参考，不替代执业医师的诊断与治疗意见。")}</p>
    </>
  );
}

export function ResultsPage({ isLoggedIn, onAuthExpired, onRequireLogin }: ResultsPageProps) {
  const { id } = useParams();
  const [record, setRecord] = useState<CaseRecordView | null>(null);
  const [loading, setLoading] = useState(Boolean(id));
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [editedText, setEditedText] = useState("");
  const [saving, setSaving] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!id || !isLoggedIn) return;
    let active = true;
    setLoading(true);
    setError("");
    getCase(id)
      .then((nextRecord) => {
        if (!active) return;
        setRecord(nextRecord);
        setEditedText(generatedText(nextRecord));
      })
      .catch((requestError) => {
        if (!active) return;
        if (isUnauthorized(requestError)) onAuthExpired();
        else setError(requestError instanceof Error ? requestError.message : "病例结果加载失败");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id, isLoggedIn, onAuthExpired]);

  async function saveEditedRecord() {
    if (!record) return;
    setSaving(true);
    setError("");
    try {
      const nextRecord = await updateCase(record.id, editedText.trim());
      setRecord(nextRecord);
      setEditedText(generatedText(nextRecord));
      setEditing(false);
    } catch (requestError) {
      if (isUnauthorized(requestError)) onAuthExpired();
      else setError(requestError instanceof Error ? requestError.message : "保存失败，请稍后重试。");
    } finally { setSaving(false); }
  }

  async function handleDownload() {
    if (!record) return;
    setDownloading(true);
    setError("");
    try {
      const file = await downloadReport(record.id);
      const url = URL.createObjectURL(file);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `medical-record-${record.id}.docx`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      if (isUnauthorized(requestError)) onAuthExpired();
      else setError(requestError instanceof Error ? requestError.message : "报告下载失败，请稍后重试。");
    } finally { setDownloading(false); }
  }

  if (!isLoggedIn) {
    return <main className="results-main results-main--empty"><section className="results-empty"><span className="results-empty__icon"><FileTextOutlined /></span><p className="section-kicker">Analysis Result</p><h2>登录后查看分析结果</h2><p>病例结果属于登录用户的受保护数据，请先完成身份验证。</p><button className="primary-button" type="button" onClick={onRequireLogin}>前往登录</button></section></main>;
  }
  if (!id) {
    return <main className="results-main results-main--empty"><section className="results-empty"><span className="results-empty__icon"><FileTextOutlined /></span><p className="section-kicker">Analysis Result</p><h2>请选择一条病例记录</h2><p>提交病例后会自动打开对应分析结果，也可以从历史记录进入。</p><Link className="primary-button" to="/history">查看病例记录</Link></section></main>;
  }
  if (loading) return <main className="results-main results-main--empty"><p className="history-feedback">正在加载病例与 AI 分析结果...</p></main>;
  if (error && !record) return <main className="results-main results-main--empty"><section className="results-empty"><p className="section-kicker">Load Failed</p><h2>结果暂时无法打开</h2><p>{error}</p><Link className="primary-button" to="/history">返回病例记录</Link></section></main>;
  if (!record) return null;

  const patient = record.aiResult?.summary ?? record.patientInput;
  const structured = record.aiResult?.structuredRecord;
  const attachments = record.aiResult?.attachments ?? [];

  return (
    <main className="results-main">
      <header className="results-heading">
        <div><p className="section-kicker">Analysis Result</p><h2>{patient.patientName || "未命名患者"}的病例分析</h2><p>病例编号 {record.id} · {formatDate(record.updatedAt)}</p></div>
        <div className="results-heading__actions">
          <Link className="text-link" to="/history"><LeftOutlined />返回记录</Link>
          <button className="secondary-button" type="button" onClick={() => setEditing((current) => !current)}><EditOutlined />{editing ? "取消编辑" : "编辑病历"}</button>
          <button className="primary-button" type="button" disabled={downloading} onClick={() => { void handleDownload(); }}><DownloadOutlined />{downloading ? "下载中" : "下载 DOCX"}</button>
        </div>
      </header>
      {error ? <p className="history-feedback history-feedback--error">{error}</p> : null}

      <div className="results-document">
        <section className="result-section"><div className="result-section__index">01</div><div className="result-section__content"><p className="section-kicker">Summary</p><h3>病例摘要</h3><dl className="summary-list"><div><dt>患者</dt><dd>{text(patient.patientName, "未命名患者")}</dd></div><div><dt>性别</dt><dd>{genderLabels[patient.gender] ?? "未填写"}</dd></div><div><dt>年龄</dt><dd>{patient.age || "未填写"} 岁</dd></div><div><dt>就诊科室</dt><dd>{departmentLabels[patient.department ?? ""] ?? "未填写"}</dd></div><div><dt>就诊日期</dt><dd>{text(patient.visitDate)}</dd></div><div><dt>主诉</dt><dd>{text(patient.chiefComplaint)}</dd></div></dl></div></section>

        <section className="result-section"><div className="result-section__index">02</div><div className="result-section__content"><p className="section-kicker">Structured Record</p><h3>结构化病历</h3>{editing ? <div className="record-editor"><label htmlFor="edited-record">可编辑病历文本</label><textarea id="edited-record" className="form-input form-textarea" value={editedText} onChange={(event) => setEditedText(event.target.value)} /><button className="primary-button" type="button" disabled={saving} onClick={() => { void saveEditedRecord(); }}><SaveOutlined />{saving ? "保存中" : "保存修改"}</button></div> : <div className="record-copy"><article><h4>生成病历</h4><p>{generatedText(record)}</p></article><article><h4>现病史</h4><p>{text(structured?.presentIllness ?? record.patientInput.presentIllness)}</p></article><article><h4>既往病史</h4><p>{text(structured?.pastHistory ?? record.patientInput.pastHistory, "未提供")}</p></article><article><h4>过敏史</h4><p>{text(structured?.allergyHistory ?? record.patientInput.allergyHistory)}</p></article><article><h4>生命体征与体格检查</h4><p>{text(structured?.vitalSigns ?? record.patientInput.vitalSigns)}；{text(structured?.physicalExam ?? record.patientInput.physicalExam)}</p></article><article><h4>辅助检查</h4><p>{text(structured?.auxiliaryExam ?? record.patientInput.auxiliaryExam)}</p></article></div>}</div></section>

        <section className="result-section"><div className="result-section__index">03</div><div className="result-section__content"><p className="section-kicker">AI Assisted Analysis</p><h3>分析建议</h3><AnalysisContent aiResult={record.aiResult} />{record.status === "ANALYSIS_FAILED" ? <p className="medical-notice">本次分析未完成：{text(record.lastError, "后端暂未提供失败原因")}。病例已保留，可在服务恢复后重新处理。</p> : null}</div></section>

        <section className="result-section"><div className="result-section__index">04</div><div className="result-section__content"><p className="section-kicker">Attachments</p><h3>检查资料</h3>{attachments.length ? <div className="attachment-list">{attachments.map((attachment) => <div className="attachment-row" key={attachment.id}><FileTextOutlined /><span>{attachment.fileName}</span><small>{attachment.processingStatus === "metadata_only" ? "仅保存元数据，尚未解析文件内容" : attachment.processingStatus}</small></div>)}</div> : <p className="result-muted">当前病例未附带可解析的检查资料。前端现阶段仅提交文件名元数据，真实文件上传需后端另行提供 multipart 接口。</p>}</div></section>
      </div>
    </main>
  );
}
