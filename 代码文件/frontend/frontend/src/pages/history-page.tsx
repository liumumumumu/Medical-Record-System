import { FileTextOutlined, SearchOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { isUnauthorized, listCases } from "../services/medical-api";
import type { CaseRecordView } from "../types/medical-record";

type HistoryPageProps = {
  isLoggedIn: boolean;
  onAuthExpired: () => void;
  onRequireLogin: () => void;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function diagnosisOf(record: CaseRecordView) {
  return record.aiResult?.analysis.diagnosisTop1 || record.patientInput.preliminaryDiagnosis || "等待分析结果";
}

export function HistoryPage({ isLoggedIn, onAuthExpired, onRequireLogin }: HistoryPageProps) {
  const [keyword, setKeyword] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [records, setRecords] = useState<CaseRecordView[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const pageSize = 10;

  useEffect(() => {
    if (!isLoggedIn) return;
    let active = true;
    setLoading(true);
    setError("");
    listCases(query, page, pageSize)
      .then((result) => {
        if (!active) return;
        setRecords(result.items);
        setTotal(result.total);
      })
      .catch((requestError) => {
        if (!active) return;
        if (isUnauthorized(requestError)) onAuthExpired();
        else setError(requestError instanceof Error ? requestError.message : "历史记录加载失败");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [isLoggedIn, onAuthExpired, page, query]);

  if (!isLoggedIn) {
    return (
      <main className="results-main results-main--empty">
        <section className="results-empty">
          <span className="results-empty__icon"><FileTextOutlined /></span>
          <p className="section-kicker">Case History</p>
          <h2>登录后查看病例记录</h2>
          <p>历史列表与分析结果仅在登录状态下访问，避免病例信息在浏览器中被未授权展示。</p>
          <button className="primary-button" type="button" onClick={onRequireLogin}>登录后查看</button>
        </section>
      </main>
    );
  }

  return (
    <main className="history-main">
      <header className="history-heading">
        <div>
          <p className="section-kicker">Case History</p>
          <h2>病例记录</h2>
          <p>查看已提交病例及其生成状态，选择一条记录进入完整结果。</p>
        </div>
        <Link className="primary-button" to="/upload">录入新病例</Link>
      </header>

      <form className="history-search" onSubmit={(event) => { event.preventDefault(); setPage(0); setQuery(keyword.trim()); }}>
        <SearchOutlined aria-hidden="true" />
        <input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="按患者姓名或主诉检索" aria-label="检索病例" />
        <button className="secondary-button" type="submit">检索</button>
      </form>

      {error ? <p className="history-feedback history-feedback--error">{error}</p> : null}
      {loading ? <p className="history-feedback">正在读取病例记录...</p> : null}
      {!loading && !error && records.length === 0 ? (
        <section className="history-empty">
          <FileTextOutlined aria-hidden="true" />
          <p>尚无病例记录。完成录入并提交分析后，记录会显示在这里。</p>
        </section>
      ) : null}
      {!loading && records.length > 0 ? (
        <section className="history-list" aria-label="病例记录列表">
          {records.map((record) => (
            <Link className="history-row" to={`/results/${record.id}`} key={record.id}>
              <div className="history-row__patient">
                <strong>{record.patientInput.patientName || "未命名患者"}</strong>
                <span>{record.patientInput.gender === "male" ? "男" : "女"} · {record.patientInput.age} 岁</span>
              </div>
              <p>{record.patientInput.chiefComplaint}</p>
              <p>{diagnosisOf(record)}</p>
              <span className={`case-status case-status--${record.status.toLowerCase()}`}>{record.status === "COMPLETED" ? "分析完成" : record.status === "ANALYSIS_FAILED" ? "分析失败" : "处理中"}</span>
              <time dateTime={record.createdAt}>{formatDate(record.createdAt)}</time>
            </Link>
          ))}
        </section>
      ) : null}
      {total > pageSize ? (
        <nav className="history-pagination" aria-label="历史记录分页">
          <button className="secondary-button" type="button" disabled={page === 0} onClick={() => setPage((current) => current - 1)}>上一页</button>
          <span>第 {page + 1} 页，共 {Math.ceil(total / pageSize)} 页</span>
          <button className="secondary-button" type="button" disabled={(page + 1) * pageSize >= total} onClick={() => setPage((current) => current + 1)}>下一页</button>
        </nav>
      ) : null}
    </main>
  );
}
