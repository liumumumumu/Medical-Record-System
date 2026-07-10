const featureItems = [
  {
    eyebrow: "Capability",
    title: "系统能力",
    body: "将分散的患者信息整理为结构清晰的标准病历，并集中呈现辅助分析、诊疗信息与检查资料。",
  },
  {
    eyebrow: "Scenario",
    title: "适用场景",
    body: "面向课程答辩与功能演示，完整串联病例录入、内容生成和结果查看流程。",
  },
  {
    eyebrow: "Team",
    title: "开发团队",
    body: "xxx",
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
