const featureItems = [
  {
    eyebrow: "Capability",
    title: "系统能力",
    body: "将分散的患者信息整理为结构清晰的标准病历，并集中呈现辅助分析、诊疗信息与检查资料。",
  },
  {
    eyebrow: "Workflow",
    title: "流程闭环",
    body: "覆盖病例录入、附件处理、智能分析、病历生成与结果查看，形成完整清晰的病例处理流程。",
  },
  {
    eyebrow: "Architecture",
    title: "技术架构",
    body: "采用 React、Spring Boot、Flask AI 与 MongoDB 的分层架构，模块职责清晰，便于联调与扩展。",
  },
];

export function IntroSection() {
  return (
    <section className="intro-section" aria-labelledby="intro-title">
      <div className="section-heading section-heading--compact">
        <span className="section-kicker">Overview</span>
        <h2 id="intro-title">从信息录入到结果呈现</h2>
        <p>围绕一次病例处理任务组织页面，让录入、生成和查看保持清晰连续。</p>
      </div>

      <div className="intro-grid">
        {featureItems.map((item) => (
          <article className="intro-item" key={item.title}>
            <span>{item.eyebrow}</span>
            <h3>{item.title}</h3>
            <p>{item.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
