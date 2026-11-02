// Book2TTS V2 全面重设计 —— S1 结构 / S2 设计系统 / P1-P5 核心页

const { DesignCanvas, DCSection, DCArtboard, DCPostIt } = window;

// ---------- 图标 ----------
const ICONS = {
  play: { d: "M8 5v14l11-7z", fill: true },
  pause: { d: "M7 5h4v14H7zM13 5h4v14h-4z", fill: true },
  dots: { d: "M6 12a1.4 1.4 0 1 0 2.8 0 1.4 1.4 0 0 0-2.8 0zm4.6 0a1.4 1.4 0 1 0 2.8 0 1.4 1.4 0 0 0-2.8 0zm4.6 0a1.4 1.4 0 1 0 2.8 0 1.4 1.4 0 0 0-2.8 0z", fill: true },
  plus: { d: "M12 5v14M5 12h14", stroke: true },
  sun: { d: "M12 4v2m0 12v2M4 12h2m12 0h2M6.3 6.3l1.4 1.4m8.6 8.6l1.4 1.4m0-11.4l-1.4 1.4M7.7 16.3l-1.4 1.4M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z", stroke: true },
  chevron: { d: "M6 9l6 6 6-6", stroke: true },
  arrow: { d: "M5 12h14M13 6l6 6-6 6", stroke: true },
  search: { d: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm10 17l-4.35-4.35", stroke: true },
  upload: { d: "M12 16V4m0 0l-5 5m5-5l5 5M4 20h16", stroke: true },
  download: { d: "M12 4v12m0 0l-5-5m5 5l5-5M4 20h16", stroke: true },
  file: { d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zM14 2v6h6", stroke: true },
  type: { d: "M4 7V4h16v3M12 4v16M9 20h6", stroke: true },
  globe: { d: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM3 12h18M12 3c2.5 2.5 3.5 5.5 3.5 9s-1 6.5-3.5 9c-2.5-2.5-3.5-5.5-3.5-9s1-6.5 3.5-9z", stroke: true },
  eye: { d: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7zm10 3.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z", stroke: true },
  wave: { d: "M3 12h2l2-6 3 12 3-9 2 5 2-3h4", stroke: true },
  folder: { d: "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z", stroke: true },
  book: { d: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5v15zM4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5", stroke: true },
  mic: { d: "M12 3a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM19 10v1a7 7 0 0 1-14 0v-1M12 18v4M8 22h8", stroke: true },
  compass: { d: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zm4.2 4.8l-2.4 5.4-5.4 2.4 2.4-5.4 5.4-2.4z", stroke: true },
  chat: { d: "M21 12a8 8 0 0 1-8 8H4l2-3a8 8 0 1 1 15-5z", stroke: true },
  skipBack: { d: "M19 20L9 12l10-8v16zM7 5v14", stroke: true },
  skipFwd: { d: "M5 20l10-8L5 4v16zM17 5v14", stroke: true },
  check: { d: "M5 12l5 5L20 7", stroke: true },
};

function Icon({ name, size = 16, style }) {
  const p = ICONS[name];
  if (!p) return null;
  return p.fill
    ? <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" style={style}><path d={p.d} /></svg>
    : <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
        strokeLinecap="round" strokeLinejoin="round" style={style}><path d={p.d} /></svg>;
}

const PALETTE = [
  { bg: "#8b6fd8", deep: "#6d4fb8" }, { bg: "#5b9fc0", deep: "#417f9f" },
  { bg: "#5aa77a", deep: "#3f8a5f" }, { bg: "#d9973f", deep: "#b87a28" },
  { bg: "#c96f6f", deep: "#a95050" }, { bg: "#7b82cc", deep: "#5d64b0" },
];

function BookCover({ i = 0, title, author, w = 120, radius = 12, style, className }) {
  const p = PALETTE[i % PALETTE.length];
  return (
    <div className={className} style={{ width: w, height: Math.round(w * 4 / 3), borderRadius: radius,
      background: `linear-gradient(155deg, ${p.bg}, ${p.deep})`, color: "#fff",
      padding: Math.round(w * 0.11), position: "relative", overflow: "hidden",
      display: "flex", flexDirection: "column", justifyContent: "space-between",
      boxShadow: "0 6px 18px rgba(25,22,34,.16)", flexShrink: 0, ...style }}>
      <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: Math.max(4, w * 0.05),
        background: "rgba(255,255,255,.22)", borderRadius: "8px 0 0 8px" }} />
      <div style={{ width: 18, height: 2, background: "rgba(255,255,255,.55)", marginTop: 3 }} />
      <div>
        <div style={{ fontSize: Math.max(12, w * 0.13), fontWeight: 700, lineHeight: 1.35 }}>《{title}》</div>
        <div style={{ fontSize: Math.max(9, w * 0.085), opacity: .72, marginTop: 4 }}>{author}</div>
      </div>
    </div>
  );
}

function Wave({ w = 46, h = 16, played = .55, style }) {
  const hs = [5, 8, 4, 11, 6, 13, 7, 10, 5, 12, 8, 6, 11, 5, 9, 7];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 2, width: w, height: h, ...style }}>
      {hs.map((v, i) => (
        <span key={i} style={{ width: 2, height: Math.round(h * v / 13), borderRadius: 1,
          background: i / hs.length < played ? "var(--accent)" : "var(--line-2)" }} />
      ))}
    </div>
  );
}

// ---------- V2 顶栏（IA：工坊 / 声音库 / 探索 / 社区 / 关于） ----------
function Nav2({ active, auth = true }) {
  return (
    <header className="nav">
      <a className="brand" href="#"><img src="logo.png" alt="" /><span>Book2TTS</span></a>
      <a className={"nav-item" + (active === "studio" ? " active" : "")} href="#">
        工坊 <Icon name="chevron" size={11} className="caret" />
      </a>
      <a className={"nav-item" + (active === "library" ? " active" : "")} href="#">
        声音库 <Icon name="chevron" size={11} className="caret" />
      </a>
      <a className={"nav-item" + (active === "explore" ? " active" : "")} href="#">探索</a>
      <a className={"nav-item" + (active === "community" ? " active" : "")} href="#">社区</a>
      <a className={"nav-item" + (active === "about" ? " active" : "")} href="#">关于</a>
      <div className="nav-right">
        <span className="search-pill"><Icon name="search" size={13} />搜索…<span className="kbd">⌘K</span></span>
        <button className="icon-btn"><Icon name="sun" size={16} /></button>
        {auth
          ? <div className="avatar">F</div>
          : <React.Fragment>
              <a className="nav-item" style={{ padding: "7px 8px" }} href="#">登录</a>
              <a className="btn btn-primary sm" href="#">免费注册</a>
            </React.Fragment>}
      </div>
    </header>
  );
}

// ================= S1 信息架构 =================
function Tree({ children }) {
  return <div className="tree">{children}</div>;
}

function BoardIA() {
  return (
    <div className="ia" data-screen-label="信息架构 · 结构重组">
      <div className="ia-col">
        <h3>现状 V1（5 项一级 · 心智混杂）</h3>
        <Tree>
          <div className="troot">制作 <span className="tsub">→ 三栏编辑器（但入口叫"制作"）</span></div>
          <div className="troot">作品 <span className="tsub">→ 音频流</span></div>
          <div className="troot">书库 ▾ <span className="tsub">我的书籍 / 成品 / 队列 / 对话脚本</span></div>
          <div className="tnode"><b className="old">✗</b> "书库"混装了【输入（书籍）】与【产出（成品/脚本）】</div>
          <div className="tnode"><b className="old">✗</b> "作品"与"成品"两处看同类内容，语义重叠</div>
          <div className="troot">发现 ▾ <span className="tsub">探索 / 讨论区</span></div>
          <div className="tnode"><b className="old">✗</b> 队列藏在二级，等待合成的关键路径太深</div>
        </Tree>
      </div>
      <div className="ia-col">
        <h3>V2 提案（5 项一级 · 创作 × 资产 × 对外）</h3>
        <Tree>
          <div className="troot v2">工坊 ▾</div>
          <div className="tnode">制作台（中枢，三栏编辑器）<span className="tsub">/workbench</span></div>
          <div className="tnode">我的书籍（输入：上传/EPUB/PDF）</div>
          <div className="tnode">生成队列 <span className="tsub">⚡ 实时进度提升为一级可见</span></div>
          <div className="troot v2">声音库 ▾</div>
          <div className="tnode">我的作品（音频流）· 有声书成品 · 对话脚本<span className="tsub">产出三兄弟团聚</span></div>
          <div className="troot v2">探索</div>
          <div className="tnode">公开内容 → 播放详情（沉浸收听页）</div>
          <div className="troot v2">社区 · 关于</div>
          <div className="tnode">讨论区 / 帮助</div>
          <div className="tnode" style={{ color: "var(--accent-deep)", fontWeight: 700 }}>
            全局层：⌘K 搜索 · 常驻迷你播放器 · 明暗主题
          </div>
        </Tree>
      </div>
      <div className="journey">
        <div className="jbar">
          <h4>访客旅程</h4>
          <div className="jsteps">
            <span className="jstep">落地页</span><span className="jarrow">→</span>
            <span className="jstep hot">试听（探索/播放详情）</span><span className="jarrow">→</span>
            <span className="jstep brand">注册</span><span className="jarrow">→</span>
            <span className="jstep">上传书籍</span><span className="jarrow">→</span>
            <span className="jstep hot">第一次合成</span><span className="jarrow">→</span>
            <span className="jstep">收听</span>
          </div>
        </div>
        <div className="jbar">
          <h4>创作者旅程（日循环）</h4>
          <div className="jsteps">
            <span className="jstep brand">工坊：选书/章节</span><span className="jarrow">→</span>
            <span className="jstep">排版/翻译</span><span className="jarrow">→</span>
            <span className="jstep">选音色</span><span className="jarrow">→</span>
            <span className="jstep hot">合成（队列实时态）</span><span className="jarrow">→</span>
            <span className="jstep">声音库：成品</span><span className="jarrow">→</span>
            <span className="jstep">发布 / RSS</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ================= S2 设计系统 V2 =================
function Sw2({ color, name }) {
  return (
    <div>
      <div style={{ height: 46, borderRadius: 10, background: color, border: "1px solid var(--line)" }} />
      <div style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 5, fontWeight: 600 }}>{name}</div>
    </div>
  );
}

function BoardDS2() {
  return (
    <div className="ds2" data-screen-label="设计系统 V2" style={{ background: "#fff", height: "100%" }}>
      <h2 style={{ fontSize: 19, fontWeight: 800 }}>设计系统 V2</h2>
      <p style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 5 }}>回填 tailwind/daisyUI 主题：深紫墨（ink）替代纯黑，暖纸底色，全局圆角两档（10/18）。</p>
      <div className="ds2-grid">
        <div>
          <div className="ds-h" style={{ fontSize: 12, fontWeight: 700, color: "var(--ink-3)", letterSpacing: 1.5, marginBottom: 12 }}>色彩</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 10 }}>
            <Sw2 color="#6d28d9" name="brand 主CTA" />
            <Sw2 color="#e65302" name="accent 播放" />
            <Sw2 color="#191622" name="ink 文字" />
            <Sw2 color="#837e8f" name="ink-3 次要" />
            <Sw2 color="#f6f5f2" name="bg 底色" />
            <Sw2 color="#efe9fd" name="brand-tint" />
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
            {PALETTE.map((p, i) => (
              <div key={i} style={{ width: 40, height: 40, borderRadius: 9, background: `linear-gradient(155deg, ${p.bg}, ${p.deep})` }} />
            ))}
          </div>
          <div style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 5 }}>书籍封面 6 色调色板（按书名 hash）</div>
        </div>
        <div>
          <div className="ds-h" style={{ fontSize: 12, fontWeight: 700, color: "var(--ink-3)", letterSpacing: 1.5, marginBottom: 12 }}>字阶（8 档）</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ fontSize: 30, fontWeight: 800, letterSpacing: "-0.5px" }}>展示 30-44</div>
            <div style={{ fontSize: 22, fontWeight: 800 }}>标题 22</div>
            <div style={{ fontSize: 18, fontWeight: 700 }}>区块 18</div>
            <div style={{ fontSize: 16, fontWeight: 700 }}>卡片 16</div>
            <div style={{ fontSize: 14, color: "var(--ink-2)" }}>正文 14</div>
            <div style={{ fontSize: 12.5, color: "var(--ink-3)" }}>辅助 12.5</div>
          </div>
        </div>
        <div>
          <div className="ds-h" style={{ fontSize: 12, fontWeight: 700, color: "var(--ink-3)", letterSpacing: 1.5, marginBottom: 12 }}>组件 & 交互态</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 14, alignItems: "flex-start" }}>
            <div style={{ display: "flex", gap: 9, alignItems: "center" }}>
              <span className="btn btn-primary">主操作</span>
              <span className="btn btn-ghost">次操作</span>
              <span className="btn btn-text">文字链 <Icon name="arrow" size={13} /></span>
            </div>
            <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
              <span className="play lg"><Icon name="play" size={20} style={{ marginLeft: 2 }} /></span>
              <span className="play md"><Icon name="play" size={16} style={{ marginLeft: 2 }} /></span>
              <span style={{ fontSize: 11, color: "var(--ink-3)" }}>播放键 56/44/32 · 唯一暖色</span>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <span className="badge">徽章</span>
              <span className="tag ok">已发布</span><span className="tag warn">生成中</span>
              <span className="tag err">失败</span><span className="tag info">草稿</span>
            </div>
            <div style={{ background: "var(--bg)", border: "1px solid var(--line)", borderRadius: 10, padding: "10px 12px", fontSize: 12, color: "var(--ink-2)", lineHeight: 1.8, width: "100%" }}>
              <span className="bolt">⚡ 交互语言：</span>hover 上浮 1px + 阴影加深 · focus ring brand/30 ·
              空格键全局播放暂停 · ⌘K 全局搜索 · 次要操作 hover 才出现
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ================= P1 落地页 V2 =================
function BoardLanding() {
  return (
    <div data-screen-label="落地页 V2" style={{ background: "var(--bg)", height: "100%" }}>
      <Nav2 active={null} auth={false} />
      <div className="hero2">
        <div>
          <span className="eyebrow" style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 13,
            border: "1px solid var(--line-2)", background: "var(--surface)", borderRadius: 999, padding: "6px 14px", color: "var(--ink-2)" }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--accent)" }} />
            EPUB / PDF → 有声书 → 播客 RSS
          </span>
          <h1 style={{ marginTop: 20 }}>把一本书，<br />变成<span className="hl2">一档节目</span>。</h1>
          <p style={{ fontSize: 17, lineHeight: 1.85, color: "var(--ink-2)", marginTop: 18, maxWidth: "30em" }}>
            上传即自动分章、多音色朗读；成书即成台——生成标准播客 RSS，在任意播客 App 追更你自己的有声书。
          </p>
          <div style={{ display: "flex", alignItems: "center", gap: 22, marginTop: 28 }}>
            <a className="btn btn-primary" style={{ padding: "13px 26px", fontSize: 15 }} href="#">免费开始制作</a>
            <a className="btn-text" href="#">先听听公开作品 <Icon name="arrow" size={14} /></a>
          </div>
          <p style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 20 }}>免费注册 · 中文多音色 · 章节与 SRT 字幕自动生成</p>
        </div>
        <div style={{ position: "relative", height: 420 }}>
          <BookCover i={0} title="夜航船" author="张岱" w={188} radius={16}
            style={{ position: "absolute", left: 30, top: 24, transform: "rotate(-6deg)", zIndex: 2 }} />
          <BookCover i={3} title="山茶文具店" author="小川糸" w={182} radius={16}
            style={{ position: "absolute", left: 186, top: 56, transform: "rotate(4deg)", zIndex: 1 }} />
          <BookCover i={1} title="人类简史" author="尤瓦尔·赫拉利" w={196} radius={16}
            style={{ position: "absolute", left: 104, top: 168, transform: "rotate(2deg)", zIndex: 3 }} />
          <div style={{ position: "absolute", right: 8, bottom: 42, zIndex: 5, background: "var(--surface)",
            borderRadius: 14, padding: "10px 14px", boxShadow: "var(--shadow-pop)", display: "flex",
            alignItems: "center", gap: 11, transform: "rotate(-2deg)" }}>
            <span className="play sm"><Icon name="play" size={13} style={{ marginLeft: 1 }} /></span>
            <div>
              <div style={{ fontSize: 12.5, fontWeight: 600 }}>第三章 · 江湖纪闻</div>
              <Wave w={46} h={13} />
            </div>
          </div>
        </div>
      </div>
      {/* 三步流程 —— 回答"怎么用" */}
      <div className="steps3">
        {[
          { n: "1", t: "上传书籍", d: "拖入 EPUB / PDF，扫描件自动 OCR；目录章节一键解析。", icon: "upload" },
          { n: "2", t: "工坊精修", d: "原文排版、LLM 翻译润色、多角色对话脚本与音色分配。", icon: "type" },
          { n: "3", t: "合成发布", d: "多音色合成 + 字幕章节，一键生成播客 RSS 订阅。", icon: "wave" },
        ].map((s) => (
          <div className="stepc" key={s.n}>
            <div className="n"><Icon name={s.icon} size={15} /></div>
            <h3>{s.t}</h3>
            <p>{s.d}</p>
          </div>
        ))}
      </div>
      {/* CTA 收束带 */}
      <div className="cta-band">
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 19, fontWeight: 800 }}>现在上传第一本书</div>
          <div style={{ fontSize: 13, opacity: .7, marginTop: 4 }}>免费额度足够合成一整章</div>
        </div>
        <a className="btn btn-accent" href="#">免费开始 <Icon name="arrow" size={14} /></a>
      </div>
    </div>
  );
}

// ================= P2 作品流 V2（含迷你播放条交互标注） =================
function AudioRow({ i, book, title, meta, playing }) {
  return (
    <div className="card" style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 16px" }}>
      <BookCover i={i} title={book} author="有声书" w={52} radius={8} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <span className="badge">{book}</span>
        <div style={{ fontSize: 15.5, fontWeight: 700, marginTop: 6, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{title}</div>
        <div style={{ fontSize: 12.5, color: "var(--ink-3)", marginTop: 3 }}>{meta}</div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
        <span className={"play " + (playing ? "" : "md")} style={playing ? { width: 40, height: 40 } : null}>
          <Icon name={playing ? "pause" : "play"} size={15} style={{ marginLeft: 2 }} />
        </span>
        <span className="ghost-ico" style={{ width: 26, height: 26 }}><Icon name="dots" size={15} /></span>
      </div>
    </div>
  );
}

function BoardWorks() {
  const [expanded, setExpanded] = React.useState(false);
  return (
    <div data-screen-label="作品流 V2" style={{ background: "var(--bg)", height: "100%", display: "flex", flexDirection: "column" }}>
      <Nav2 active="library" />
      <div style={{ maxWidth: 1160, margin: "0 auto", width: "100%", padding: "26px 32px 20px", flex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.4px" }}>早上好，Fury</h1>
            <p style={{ fontSize: 13.5, color: "var(--ink-3)", marginTop: 5 }}>继续你的上一章，或者开始一本新书。</p>
          </div>
          <a className="btn btn-primary" href="#"><Icon name="plus" size={14} /> 制作新音频</a>
        </div>
        {/* 继续收听 */}
        <div className="card" style={{ display: "flex", alignItems: "center", gap: 18, padding: "16px 18px", marginBottom: 26 }}>
          <BookCover i={0} title="夜航船" author="有声书" w={78} radius={10} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--accent-deep)", letterSpacing: 1 }}>继续收听</div>
            <div style={{ fontSize: 18, fontWeight: 800, marginTop: 5 }}>第三章 江湖纪闻</div>
            <div className="progress" style={{ height: 5, borderRadius: 3, background: "var(--line)", marginTop: 10 }}>
              <span style={{ display: "block", width: "42%", height: "100%", background: "var(--accent)", borderRadius: 3 }} />
            </div>
            <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 6 }}>剩约 18 分钟 · 《夜航船》</div>
          </div>
          <span className="play lg"><Icon name="play" size={20} style={{ marginLeft: 2 }} /></span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 14 }}>
          <h2 style={{ fontSize: 17, fontWeight: 800 }}>我的作品 <span style={{ fontSize: 12, fontWeight: 500, color: "var(--ink-3)" }}>24</span></h2>
          <a className="btn-text" style={{ fontSize: 13 }} href="#">按书籍分组 <Icon name="chevron" size={12} /></a>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <AudioRow i={1} book="人类简史" title="第一章 人类也是一种没有什么特别的动物" meta="今天 09:12 · 41 分钟 · 已发布" />
          <AudioRow i={3} book="山茶文具店" title="代笔人序 · 鸠子写给祖母的信" meta="昨天 21:03 · 18 分钟 · 已发布" />
          <AudioRow i={2} book="夜航西飞" title="第四章 北方的沙漠，城市的边缘" meta="3 天前 · 27 分钟 · 草稿" />
        </div>
      </div>
      {/* 常驻迷你播放条：⚡ 空格键播放/暂停；点展开区切到完整播放页 */}
      <div className="mini" onClick={() => setExpanded(!expanded)} style={{ cursor: "pointer" }}>
        <BookCover i={0} title="夜航船" author="" w={40} radius={6} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13.5, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            夜航船 · 第三章 江湖纪闻</div>
          <div className="mini-bar" style={{ height: 3, borderRadius: 2, background: "var(--line)", marginTop: 8 }}>
            <span style={{ display: "block", width: "38%", height: "100%", background: "var(--accent)", borderRadius: 2 }} />
          </div>
        </div>
        <Wave w={40} h={14} />
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button className="ghost-ico" onClick={(e) => e.stopPropagation()}><Icon name="skipBack" size={15} /></button>
          <button className="play sm" onClick={(e) => e.stopPropagation()}><Icon name="pause" size={13} /></button>
          <button className="ghost-ico" onClick={(e) => e.stopPropagation()}><Icon name="skipFwd" size={15} /></button>
        </div>
        <span className="expand-hint"><Icon name="chevron" size={12} /> 展开播放页</span>
      </div>
      {expanded && (
        <div style={{ position: "absolute", inset: "auto 0 0 0", top: "38%", background: "var(--ink)", color: "#fff",
          padding: "26px 36px", display: "flex", gap: 26, alignItems: "center", zIndex: 30,
          borderRadius: "22px 22px 0 0", boxShadow: "var(--shadow-pop)" }}>
          <BookCover i={0} title="夜航船" author="张岱" w={150} radius={14} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 11, color: "rgba(255,255,255,.55)", letterSpacing: 2 }}>正在播放 · CHAPTER 3</div>
            <div style={{ fontSize: 24, fontWeight: 800, marginTop: 8 }}>江湖纪闻</div>
            <div style={{ fontSize: 13, opacity: .6, marginTop: 6 }}>《夜航船》 · Fury 的有声书</div>
            <div style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 20 }}>
              <span className="play lg" style={{ background: "var(--accent)" }}><Icon name="pause" size={20} /></span>
              <span style={{ fontSize: 12, opacity: .6 }}>⚡ 空格键 播放 / 暂停</span>
            </div>
          </div>
          <div style={{ fontSize: 12, opacity: .55, alignSelf: "flex-end" }}>字幕 & 章节在完整播放页 →</div>
        </div>
      )}
    </div>
  );
}

// ================= P3 播放详情 V2 =================
function BoardPlayDetail() {
  return (
    <div data-screen-label="播放详情 V2" style={{ background: "var(--bg)", height: "100%" }}>
      <Nav2 active="explore" />
      <div style={{ maxWidth: 1160, margin: "0 auto", padding: "22px 32px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--ink-3)" }}>
          探索 <Icon name="chevron" size={11} /> 夜航船 <Icon name="chevron" size={11} /> 第三章 江湖纪闻
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "370px 1fr", gap: 48, marginTop: 22, alignItems: "start" }}>
          <div className="card" style={{ padding: 22, display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
            <BookCover i={0} title="夜航船" author="张岱" w={228} radius={16} />
            <div style={{ width: "100%", height: 6, borderRadius: 3, background: "var(--line)", position: "relative" }}>
              <span style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "34%", background: "var(--accent)", borderRadius: 3 }} />
              <i style={{ position: "absolute", left: "34%", top: "50%", width: 14, height: 14, borderRadius: "50%",
                background: "#fff", border: "3px solid var(--accent)", transform: "translate(-50%,-50%)" }} />
            </div>
            <div style={{ width: "100%", display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--ink-3)" }}>
              <span>14:02</span><span>-27:18</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 22, color: "var(--ink-2)" }}>
              <Icon name="skipBack" size={19} />
              <span className="play" style={{ width: 62, height: 62 }}><Icon name="play" size={23} style={{ marginLeft: 3 }} /></span>
              <Icon name="skipFwd" size={19} />
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <span className="btn btn-ghost sm">下载音频</span>
              <span className="btn btn-ghost sm">下载字幕</span>
            </div>
            <div style={{ fontSize: 11, color: "var(--ink-3)", display: "flex", alignItems: "center", gap: 5 }}>
              <span className="bolt">⚡</span> 空格键 播放/暂停 · ←→ 快进快退 15s
            </div>
          </div>
          <div style={{ minWidth: 0 }}>
            <span className="badge">夜航船</span>
            <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: "-0.4px", marginTop: 10, lineHeight: 1.3 }}>第三章 江湖纪闻</h1>
            <p style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 8 }}>Fury 制作 · 41 分钟 · 3 天前更新 · 1.2k 次收听</p>
            <p style={{ fontSize: 14.5, lineHeight: 1.85, color: "var(--ink-2)", marginTop: 14, maxWidth: "36em" }}>
              江湖纪闻一卷，记奇人异士、市井传说。本章从一位说书人的视角展开，讲述夜航船上的众生相……</p>
            <div style={{ display: "flex", gap: 2, borderBottom: "1px solid var(--line)", marginTop: 24 }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: "var(--brand-deep)", padding: "9px 15px", boxShadow: "inset 0 -2px 0 var(--brand)" }}>章节 · 12</span>
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink-3)", padding: "9px 15px" }}>字幕 SRT</span>
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink-3)", padding: "9px 15px" }}>相似作品</span>
            </div>
            <div style={{ marginTop: 8 }}>
              {[
                { n: 3, t: "第三章 江湖纪闻", d: "41:20", on: true },
                { n: 4, t: "第四章 奇技淫巧", d: "38:05" },
                { n: 5, t: "第五章 四方异闻", d: "44:12" },
                { n: 6, t: "第六章 舟车忆旧", d: "36:47" },
              ].map((c) => (
                <div key={c.n} style={{ display: "flex", alignItems: "center", gap: 12, padding: "11px 12px",
                  borderBottom: "1px solid var(--line)", borderRadius: 10,
                  background: c.on ? "var(--accent-tint)" : "transparent" }}>
                  <span style={{ width: 26, height: 26, borderRadius: 8, flexShrink: 0, fontSize: 11.5,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    background: c.on ? "var(--accent)" : "var(--bg)", color: c.on ? "#fff" : "var(--ink-3)",
                    border: c.on ? "none" : "1px solid var(--line)", fontFamily: "ui-monospace,monospace" }}>{c.n}</span>
                  <span style={{ fontSize: 14, fontWeight: c.on ? 700 : 500, flex: 1 }}>{c.t}</span>
                  {c.on && <Wave w={36} h={13} />}
                  <span style={{ fontSize: 12, color: "var(--ink-3)" }}>{c.d}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ================= P4 制作台 V2 =================
function BoardStudio() {
  const [tab, setTab] = React.useState("toc");
  return (
    <div data-screen-label="制作台 V2" style={{ background: "var(--bg)", height: "100%", display: "flex", flexDirection: "column" }}>
      <Nav2 active="studio" />
      {/* 书籍工具条 */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "9px 16px", background: "var(--surface)", borderBottom: "1px solid var(--line)" }}>
        <span style={{ fontSize: 14.5, fontWeight: 800 }}>《夜航船》</span>
        <span className="tag warn">合成中 · 62%</span>
        <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--ink-3)" }}>⚡ 自动保存 · 刚刚</span>
      </div>
      <div style={{ flex: 1, display: "flex", gap: 10, padding: 10, minHeight: 0 }}>
        {/* 左：目录 */}
        <div style={{ width: 252, flexShrink: 0, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 14, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ display: "flex", padding: "0 8px", borderBottom: "1px solid var(--line)" }}>
            {[["toc", `目录 · 48`], ["pages", `页面 · 210`]].map(([k, label]) => (
              <span key={k} onClick={() => setTab(k)} style={{ padding: "9px 11px", fontSize: 12.5, cursor: "pointer",
                fontWeight: tab === k ? 700 : 500, color: tab === k ? "var(--brand-deep)" : "var(--ink-3)",
                boxShadow: tab === k ? "inset 0 -2px 0 var(--brand)" : "none" }}>{label}</span>
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 5, padding: "7px 10px", borderBottom: "1px solid var(--line)" }}>
            <span style={{ fontSize: 11, color: "var(--ink-3)", marginRight: "auto", whiteSpace: "nowrap" }}>已选 3 项</span>
            <span className="btn btn-ghost btn-sm" style={{ height: 22, minHeight: 22, fontSize: 11, padding: "0 7px", whiteSpace: "nowrap" }}>全选</span>
            <span className="btn btn-ghost btn-sm" style={{ height: 22, minHeight: 22, fontSize: 11, padding: "0 7px", whiteSpace: "nowrap" }}>清除</span>
            <span className="btn btn-xs bg-primary border-none text-white" style={{ height: 22, minHeight: 22, fontSize: 11, padding: "0 8px", whiteSpace: "nowrap" }}>加载</span>
          </div>
          <div style={{ flex: 1, padding: 6, overflow: "hidden", fontSize: 12.5 }}>
            {[
              { l: "第一卷 叙列系", f: "folder", d: 0, c: "6" },
              { l: "第一章 天文纪", f: "file", d: 1 }, { l: "第二章 地理纪", f: "file", d: 1 },
              { l: "第二卷 物产纪", f: "folder", d: 0, c: "9" },
              { l: "第一章 江湖纪闻", f: "file", d: 1, on: true, ck: true },
              { l: "第二章 奇技淫巧", f: "file", d: 1, ck: true },
              { l: "第三章 四方异闻", f: "file", d: 1, ck: true },
              { l: "第四章 舟车忆旧", f: "file", d: 1 },
            ].map((n, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 7, padding: "5px 8px 5px " + (8 + n.d * 14),
                borderRadius: 8, background: n.on ? "var(--accent-tint)" : "transparent",
                borderLeft: n.on ? "3px solid var(--accent)" : "3px solid transparent" }}>
                <span style={{ width: 12, height: 12, borderRadius: 3, border: n.ck ? "none" : "1.5px solid var(--line-2)",
                  background: n.ck ? "var(--brand)" : "transparent", color: "#fff", fontSize: 8,
                  display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{n.ck ? "✓" : ""}</span>
                <Icon name={n.f === "folder" ? "chevron" : "file"} size={11}
                  style={{ color: n.f === "folder" ? "var(--brand)" : "var(--ink-3)" }} />
                <span style={{ color: n.on ? "var(--accent-deep)" : "var(--ink-2)", fontWeight: n.on ? 600 : 400, flex: 1 }}>{n.l}</span>
                {n.c && <span style={{ fontSize: 10, color: "var(--ink-3)" }}>{n.c}</span>}
              </div>
            ))}
          </div>
        </div>
        {/* 中：阅读区 */}
        <div style={{ flex: 1, minWidth: 0, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 14, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 14px", borderBottom: "1px solid var(--line)", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600, whiteSpace: "nowrap" }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--accent)" }} />第三章 江湖纪闻
              </span>
              <span style={{ fontSize: 11, color: "var(--ink-3)", border: "1px solid var(--line-2)", borderRadius: 999, padding: "1px 8px" }}>3,240 字</span>
            </div>
            <div style={{ display: "flex", gap: 2, flexShrink: 0 }}>
              <span className="btn btn-ghost btn-sm rounded-lg" style={{ height: 26, minHeight: 26, fontSize: 12 }}><Icon name="eye" size={12} />原文</span>
              <span style={{ width: 1, height: 14, background: "var(--line)", margin: "0 4px" }} />
              <span className="btn btn-ghost btn-sm rounded-lg" style={{ height: 26, minHeight: 26, fontSize: 12 }}><Icon name="type" size={12} />排版</span>
              <span className="btn btn-ghost btn-sm rounded-lg" style={{ height: 26, minHeight: 26, fontSize: 12 }}><Icon name="globe" size={12} />翻译</span>
            </div>
          </div>
          <div style={{ flex: 1, overflow: "hidden", padding: "22px 34px", fontFamily: 'Georgia, "Songti SC", serif' }}>
            <p style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>第三章 江湖纪闻</p>
            <p style={{ fontSize: 14, lineHeight: 1.95, color: "var(--ink-2)", marginBottom: 10 }}>
              江湖之上，舟车相望，奇人异士多出于其间。说书者每及此卷，辄眉飞色舞，听者忘倦。</p>
            <p style={{ fontSize: 14, lineHeight: 1.95, color: "var(--ink-2)" }}>
              余尝夜泊瓜洲，闻邻舟有客谈剑仙事，音节朗朗，若出金石。起而视之，惟见月色满江，橹声欸乃而已……</p>
          </div>
        </div>
        {/* 右：合成配置 */}
        <div style={{ width: 258, flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>
          <div className="card" style={{ padding: 12 }}>
            <div style={{ fontSize: 10.5, fontWeight: 700, color: "var(--ink-3)", letterSpacing: 1.5, marginBottom: 8 }}>合成配置</div>
            <div style={{ border: "1px solid var(--line-2)", borderRadius: 8, padding: "7px 10px", fontSize: 12.5, display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              云希 · 男声 <Icon name="chevron" size={11} style={{ color: "var(--ink-3)" }} />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <span style={{ fontSize: 11.5, color: "var(--ink-2)" }}>语速</span>
              <div style={{ flex: 1, height: 4, borderRadius: 2, background: "var(--line)", position: "relative" }}>
                <span style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "50%", background: "var(--accent)", borderRadius: 2 }} />
                <span style={{ position: "absolute", left: "50%", top: "50%", width: 11, height: 11, borderRadius: "50%", background: "#fff", border: "2.5px solid var(--accent)", transform: "translate(-50%,-50%)" }} />
              </div>
              <span style={{ fontSize: 11.5, color: "var(--ink-3)" }}>100%</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <span className="btn btn-ghost btn-sm" style={{ fontSize: 12.5, border: "1.5px solid var(--line-2)" }}><Icon name="wave" size={12} />多角色音频</span>
              <span className="btn btn-primary btn-sm" style={{ fontSize: 12.5 }}><Icon name="wave" size={11} />合成音频</span>
            </div>
          </div>
          <div className="card" style={{ padding: 12, flex: 1 }}>
            <div style={{ fontSize: 10.5, fontWeight: 700, color: "var(--ink-3)", letterSpacing: 1.5, marginBottom: 8 }}>本页音频</div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              <span className="tag ok">第1页 已生成</span>
              <span className="tag info">第2页 队列中</span>
              <span className="tag draft" style={{ border: "1px solid var(--line-2)", color: "var(--ink-3)" }}>第3页 未生成</span>
            </div>
            <div style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 10, lineHeight: 1.7 }}>
              ⚡ 任务入队后由此处与「生成队列」实时反馈进度</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ================= P5 脚本编辑器 V2 =================
function BoardScriptEditor() {
  return (
    <div data-screen-label="脚本编辑器 V2" style={{ background: "var(--bg)", height: "100%", display: "flex", flexDirection: "column" }}>
      <Nav2 active="studio" />
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, padding: "16px 24px 12px" }}>
        <div style={{ minWidth: 0 }}>
          <span className="badge">夜航船 · 对话脚本</span>
          <h1 style={{ fontSize: 21, fontWeight: 800, letterSpacing: "-0.3px", marginTop: 8 }}>第一章 广播剧脚本</h1>
          <p style={{ fontSize: 12.5, color: "var(--ink-3)", marginTop: 5 }}>12 段 · 2 个角色 · 创建于 2025-01-12</p>
        </div>
        <div style={{ display: "flex", gap: 8, flexShrink: 0, alignItems: "center" }}>
          <span className="btn btn-ghost btn-sm" style={{ color: "var(--err)" }}><Icon name="file" size={12} />删除</span>
          <span className="btn btn-ghost btn-sm"><Icon name="type" size={12} />编辑</span>
          <span className="btn btn-primary btn-sm"><Icon name="arrow" size={12} />发布音频</span>
        </div>
      </div>
      <div style={{ flex: 1, display: "flex", gap: 12, padding: "0 24px 18px", minHeight: 0 }}>
        <div style={{ flex: 2, minWidth: 0, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 16, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "11px 18px", borderBottom: "1px solid var(--line)", display: "flex", justifyContent: "space-between" }}>
            <span style={{ fontSize: 13.5, fontWeight: 700 }}>对话内容</span>
            <span style={{ fontSize: 11.5, color: "var(--ink-3)" }}>悬停段落：试听 / 编辑</span>
          </div>
          <div style={{ flex: 1, padding: 13, display: "flex", flexDirection: "column", gap: 9, overflow: "hidden" }}>
            <div style={{ background: "var(--bg)", borderRadius: 11, padding: "10px 14px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#a8a29e" }} />
                <span style={{ fontSize: 12.5, fontWeight: 700, color: "var(--ink-2)" }}>旁白</span>
              </div>
              <p style={{ fontSize: 13, lineHeight: 1.8, color: "var(--ink-2)", marginTop: 5 }}>江湖之上，舟车相望，奇人异士多出于其间。</p>
            </div>
            <div style={{ background: "var(--accent-tint)", borderRadius: 11, padding: "10px 14px", border: "1px solid #f6d5bb" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--accent)" }} />
                  <span style={{ fontSize: 12.5, fontWeight: 700, color: "var(--accent-deep)" }}>鸭子</span>
                  <span style={{ fontSize: 10, border: "1px solid var(--line-2)", borderRadius: 999, padding: "1px 7px", color: "var(--ink-3)", background: "var(--surface)" }}>晓晓 · 女声</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 10.5, color: "var(--ink-3)" }}>#07</span>
                  <span className="play sm" style={{ width: 26, height: 26 }}><Icon name="play" size={10} style={{ marginLeft: 1 }} /></span>
                  <span className="ghost-ico" style={{ width: 24, height: 24 }}><Icon name="file" size={12} /></span>
                </div>
              </div>
              <p style={{ fontSize: 13, lineHeight: 1.8, marginTop: 5 }}>客言：此剑仙也，非烈士，盖有通天之术。</p>
            </div>
            <div style={{ background: "var(--bg)", borderRadius: 11, padding: "10px 14px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#a8a29e" }} />
                <span style={{ fontSize: 12.5, fontWeight: 700, color: "var(--ink-2)" }}>旁白</span>
              </div>
              <p style={{ fontSize: 13, lineHeight: 1.8, color: "var(--ink-2)", marginTop: 5 }}>余闻而异之，起而视之，惟见月色满江。</p>
            </div>
            <div style={{ background: "var(--surface)", borderRadius: 11, padding: "10px 14px", border: "1px dashed var(--line-2)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#5b9fc0" }} />
                <span style={{ fontSize: 12.5, fontWeight: 700, color: "#417f9f" }}>容儿</span>
                <span style={{ fontSize: 10, border: "1px solid var(--line-2)", borderRadius: 999, padding: "1px 7px", color: "var(--ink-3)" }}>云希 · 男声</span>
              </div>
              <p style={{ fontSize: 13, lineHeight: 1.8, color: "var(--ink-3)", marginTop: 5, fontStyle: "italic" }}>点击编辑此段台词……</p>
            </div>
          </div>
        </div>
        <div style={{ width: 296, flexShrink: 0, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 16, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "11px 16px", borderBottom: "1px solid var(--line)", fontSize: 13.5, fontWeight: 700 }}>角色音色</div>
          <div style={{ flex: 1, padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
            {[{ c: "#e65302", n: "鸭子", v: "晓晓 · 女声" }, { c: "#5b9fc0", n: "容儿", v: "云希 · 男声" }].map((r, i) => (
              <div key={i} style={{ border: "1px solid var(--line)", borderRadius: 11, padding: 11 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ width: 26, height: 26, borderRadius: "50%", background: r.c, color: "#fff", fontSize: 11, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>{r.n[0]}</span>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{r.n}</span>
                  <span className="play sm" style={{ marginLeft: "auto", width: 26, height: 26 }}><Icon name="play" size={10} style={{ marginLeft: 1 }} /></span>
                </div>
                <div style={{ marginTop: 9, border: "1px solid var(--line-2)", borderRadius: 8, padding: "6px 10px", fontSize: 11.5, display: "flex", justifyContent: "space-between", color: "var(--ink-2)" }}>
                  {r.v}<Icon name="chevron" size={11} style={{ color: "var(--ink-3)" }} />
                </div>
              </div>
            ))}
          </div>
          <div style={{ padding: 12, borderTop: "1px solid var(--line)", display: "flex", gap: 8 }}>
            <span className="btn btn-ghost btn-sm" style={{ flex: 1, border: "1.5px solid var(--line-2)" }}><Icon name="play" size={11} />试听全部</span>
            <span className="btn btn-primary btn-sm" style={{ flex: 1.4 }}><Icon name="wave" size={11} />合成音频</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ================= Q1 生成队列（实时态） =================
function QueueCard({ cover, name, title, state, progress, msg, actions }) {
  return (
    <div className="card" style={{ display: "flex", gap: 14, padding: "14px 16px", alignItems: "center" }}>
      <BookCover i={cover} title={name} author="" w={46} radius={8} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 14.5, fontWeight: 700 }}>{title}</span>
          {state === "run" && <span className="tag warn"><span style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: "var(--warn)", marginRight: 4 }} />生成中</span>}
          {state === "queued" && <span className="tag info">排队中 · 第 1 位</span>}
          {state === "done" && <span className="tag ok">已完成</span>}
          {state === "fail" && <span className="tag err">失败</span>}
        </div>
        <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 4 }}>{msg}</div>
        {progress != null && (
          <div style={{ height: 5, borderRadius: 3, background: "var(--line)", marginTop: 8 }}>
            <span style={{ display: "block", width: progress + "%", height: "100%", background: "var(--accent)", borderRadius: 3 }} />
          </div>
        )}
      </div>
      <div style={{ display: "flex", gap: 7, flexShrink: 0 }}>{actions}</div>
    </div>
  );
}

function BoardQueue() {
  return (
    <div data-screen-label="生成队列 · 实时态" style={{ background: "var(--bg)", height: "100%" }}>
      <Nav2 active="studio" />
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "24px 32px" }}>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 18 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.4px" }}>生成队列</h1>
            <p style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 5, display: "flex", alignItems: "center", gap: 5 }}>
              <span className="bolt">⚡</span> 实时轮询中 · 任务状态由后台线程同步</p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <span className="tag warn">进行中 2</span><span className="tag info">排队 1</span>
            <span className="tag ok">今日完成 5</span><span className="tag err">失败 1</span>
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <QueueCard cover={0} name="夜航船" title="第三章 江湖纪闻" state="run" progress={62}
            msg="正在合成 243/392 段 · 已运行 6 分钟 · 预计还需 4 分钟"
            actions={<span className="btn btn-ghost btn-sm">取消</span>} />
          <QueueCard cover={3} name="山茶文具店" title="代笔人序 · 鸠子写给祖母的信" state="queued"
            msg="等待前序任务完成 · 提交于 18:29" />
          <QueueCard cover={1} name="人类简史" title="第一章 人类也是一种没有什么特别的动物" state="done"
            msg="41 分钟 · 消耗 380 积分 · 2 小时前"
            actions={<React.Fragment>
              <span className="play sm"><Icon name="play" size={11} style={{ marginLeft: 1 }} /></span>
              <span className="btn btn-ghost btn-sm">查看</span>
            </React.Fragment>} />
          <QueueCard cover={4} name="夜航西飞" title="第四章 北方的沙漠，城市的边缘" state="fail"
            msg="积分不足：需要 320 积分，剩余 90 积分"
            actions={<React.Fragment>
              <span className="btn btn-primary btn-sm">重试</span>
              <span className="btn btn-ghost btn-sm">详情</span>
            </React.Fragment>} />
        </div>
        <div style={{ marginTop: 18, fontSize: 12, color: "var(--ink-3)", lineHeight: 1.8 }}>
          <span className="bolt">⚡ 交互说明：</span>页面每 3 秒轮询 check_task_status；
          「取消」将未领取的任务直接置为失败；「重试」重新入队并复用分段缓存。
        </div>
      </div>
    </div>
  );
}

// ================= Q2 声音库 · 成品（按书分组） =================
function BoardAudiobooks() {
  const groups = [
    { i: 0, name: "夜航船", eps: 12, dur: "7 小时 24 分", pct: 100, author: "张岱" },
    { i: 1, name: "人类简史", eps: 9, dur: "5 小时 02 分", pct: 75, author: "尤瓦尔·赫拉利" },
    { i: 2, name: "夜航西飞", eps: 4, dur: "1 小时 48 分", pct: 30, author: "柏瑞尔·马卡姆" },
  ];
  return (
    <div data-screen-label="声音库 · 成品" style={{ background: "var(--bg)", height: "100%" }}>
      <Nav2 active="library" />
      <div style={{ maxWidth: 980, margin: "0 auto", padding: "24px 32px" }}>
        <div style={{ marginBottom: 20 }}>
          <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.4px" }}>有声书成品</h1>
          <p style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 5 }}>按书分组的内容资产，可发布为播客 RSS。</p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {groups.map((g) => (
            <div key={g.name} className="card" style={{ display: "flex", alignItems: "center", gap: 18, padding: 16 }}>
              <BookCover i={g.i} title={g.name} author={g.author} w={86} radius={12} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 17, fontWeight: 800 }}>《{g.name}》</span>
                  {g.pct === 100 ? <span className="tag ok">已完结</span> : <span className="tag warn">连载中 {g.pct}%</span>}
                </div>
                <div style={{ fontSize: 12.5, color: "var(--ink-3)", marginTop: 6 }}>{g.eps} 集 · {g.dur} · 最近更新今天</div>
                <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                  <span className="btn btn-ghost btn-sm">播客 RSS</span>
                  <span className="btn btn-ghost btn-sm">章节管理</span>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ textAlign: "right", marginRight: 6 }}>
                  <div style={{ fontSize: 19, fontWeight: 800 }}>{g.eps}</div>
                  <div style={{ fontSize: 10.5, color: "var(--ink-3)" }}>集数</div>
                </div>
                <span className="play md"><Icon name="play" size={16} style={{ marginLeft: 2 }} /></span>
                <Icon name="chevron" size={14} style={{ color: "var(--ink-3)" }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ================= C1 社区列表 =================
function BoardCommunity() {
  const topics = [
    { i: 2, n: "官", pin: true, cat: "公告", t: "Book2TTS 新增播客 RSS 与章节标注支持", ex: "现在每本书都可以生成独立 RSS，字幕与章节文件随音频一起产出……", r: 23, v: "1.4k", t2: "2 小时前" },
    { i: 1, n: "Momo", cat: "技术交流", t: "扫描版 PDF 的 OCR 识别准确率怎么提高？", ex: "古籍书扫描件直出乱码比较多，试试先调对比度再上传……", r: 8, v: "402", t2: "5 小时前" },
    { i: 5, n: "Lao Wang", cat: "求助问答", t: "多音色对话脚本：只换一个角色的音色，会全部重新计费吗？", ex: "如题，只改了一个角色的声音，还是全部章节都要重新生成……", r: 4, v: "156", t2: "昨天" },
    { i: 3, n: "小鹿", cat: "反馈建议", t: "移动端播放器希望支持倍速", ex: "通勤时用 1.5 倍听书，现在的播放条没有倍速按钮……", r: 12, v: "630", t2: "昨天" },
  ];
  return (
    <div data-screen-label="社区" style={{ background: "var(--bg)", height: "100%" }}>
      <Nav2 active="community" />
      <div style={{ maxWidth: 820, margin: "0 auto", padding: "24px 32px" }}>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 16 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.4px" }}>社区</h1>
            <p style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 5 }}>制作技巧、音色经验与反馈建议。</p>
          </div>
          <span className="btn btn-primary btn-sm"><Icon name="plus" size={13} />发起讨论</span>
        </div>
        <div style={{ display: "flex", gap: 10, marginBottom: 14 }}>
          <span className="search-pill" style={{ flex: 1 }}><Icon name="search" size={13} />搜索主题…</span>
          <span className="chip active" style={{ fontSize: 13, fontWeight: 600, padding: "7px 16px", borderRadius: 999, background: "var(--brand-tint)", color: "var(--brand-deep)" }}>全部</span>
          <span className="chip" style={{ fontSize: 13, padding: "7px 16px", border: "1px solid var(--line-2)", borderRadius: 999, color: "var(--ink-2)" }}>综合</span>
          <span className="chip" style={{ fontSize: 13, padding: "7px 16px", border: "1px solid var(--line-2)", borderRadius: 999, color: "var(--ink-2)" }}>技术</span>
        </div>
        <div className="card" style={{ overflow: "hidden" }}>
          {topics.map((tp, idx) => (
            <div key={idx} style={{ display: "flex", gap: 13, padding: "15px 18px", borderTop: idx ? "1px solid var(--line)" : "none" }}>
              <div style={{ width: 38, height: 38, borderRadius: "50%", flexShrink: 0,
                background: `linear-gradient(155deg, ${PALETTE[tp.i].bg}, ${PALETTE[tp.i].deep})`,
                color: "#fff", fontSize: 13, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>{tp.n}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  {tp.pin && <span className="tag info">置顶</span>}
                  <span className="badge">{tp.cat}</span>
                </div>
                <div style={{ fontSize: 14.5, fontWeight: 700, marginTop: 5 }}>{tp.t}</div>
                <div style={{ fontSize: 12.5, color: "var(--ink-3)", marginTop: 4, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{tp.ex}</div>
              </div>
              <div style={{ textAlign: "right", flexShrink: 0, fontSize: 12, color: "var(--ink-3)" }}>
                <div>回复 {tp.r} · 查看 {tp.v}</div>
                <div style={{ marginTop: 4 }}>{tp.t2}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ================= C2 帖子详情 =================
function BoardThread() {
  return (
    <div data-screen-label="帖子详情" style={{ background: "var(--bg)", height: "100%" }}>
      <Nav2 active="community" />
      <div style={{ maxWidth: 780, margin: "0 auto", padding: "22px 32px" }}>
        <div style={{ fontSize: 13, color: "var(--ink-3)", marginBottom: 14 }}>社区 <Icon name="chevron" size={11} /> 技术交流</div>
        <span className="badge">技术交流</span>
        <h1 style={{ fontSize: 23, fontWeight: 800, letterSpacing: "-0.4px", marginTop: 10, lineHeight: 1.35 }}>
          扫描版 PDF 的 OCR 识别准确率怎么提高？</h1>
        <div style={{ display: "flex", alignItems: "center", gap: 9, marginTop: 10 }}>
          <div style={{ width: 30, height: 30, borderRadius: "50%", background: `linear-gradient(155deg, ${PALETTE[1].bg}, ${PALETTE[1].deep})`,
            color: "#fff", fontSize: 11.5, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>M</div>
          <span style={{ fontSize: 13, fontWeight: 600 }}>Momo</span>
          <span style={{ fontSize: 12.5, color: "var(--ink-3)" }}>· 今天 09:12 · 8 回复 · 402 查看</span>
        </div>
        <div className="card" style={{ padding: 18, marginTop: 16 }}>
          <p style={{ fontSize: 14, lineHeight: 1.9, color: "var(--ink-2)" }}>
            古籍书扫描件直出乱码比较多，试了几本书：调高对比度后识别率明显提升，
            但竖排繁体还是差。大家有什么经验？比如预处理流程或 OCR 参数怎么选？</p>
        </div>
        <h2 style={{ fontSize: 14, fontWeight: 700, margin: "22px 0 10px" }}>回复 <span style={{ fontSize: 12, fontWeight: 500, color: "var(--ink-3)" }}>8</span></h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {[{ i: 0, n: "Fury", t: "作者（你）", main: true, txt: "上传前用 Preview 导出一次再传，重压缩后的 PDF 识别率会好很多。" },
            { i: 3, n: "小鹿", t: "2 小时前", txt: "网页版排版（LLM）对 OCR 错字也有一定修正效果，可以先跑一遍再校对。" }].map((c, idx) => (
            <div key={idx} className="card" style={{ padding: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 8 }}>
                <div style={{ width: 30, height: 30, borderRadius: "50%", flexShrink: 0,
                  background: `linear-gradient(155deg, ${PALETTE[c.i].bg}, ${PALETTE[c.i].deep})`,
                  color: "#fff", fontSize: 11, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>{c.n[0]}</div>
                <span style={{ fontSize: 13, fontWeight: 700 }}>{c.n}</span>
                {c.main && <span className="tag info">楼主</span>}
                <span style={{ fontSize: 12, color: "var(--ink-3)", marginLeft: "auto" }}>{c.t}</span>
              </div>
              <p style={{ fontSize: 13.5, lineHeight: 1.85, color: "var(--ink-2)" }}>{c.txt}</p>
              <div style={{ marginTop: 8, fontSize: 12, color: "var(--ink-3)" }}>回复</div>
            </div>
          ))}
        </div>
        <div className="card" style={{ padding: 14, marginTop: 14 }}>
          <textarea placeholder="写下你的回复…" style={{ width: "100%", height: 66, border: "1px solid var(--line-2)",
            borderRadius: 10, padding: 10, fontSize: 13.5, fontFamily: "inherit", resize: "none", background: "var(--bg)" }} />
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
            <span className="btn btn-primary btn-sm"><Icon name="arrow" size={12} />发表回复</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ================= U1 个人中心 =================
function BoardProfile() {
  return (
    <div data-screen-label="个人中心" style={{ background: "var(--bg)", height: "100%" }}>
      <Nav2 active={null} />
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "24px 32px" }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.4px" }}>个人中心</h1>
        <p style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 5 }}>账户、积分与收听数据</p>
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 14, marginTop: 20 }}>
          <div className="card" style={{ padding: 18 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ width: 48, height: 48, borderRadius: "50%", background: `linear-gradient(155deg, ${PALETTE[0].bg}, ${PALETTE[0].deep})`,
                color: "#fff", fontSize: 17, fontWeight: 800, display: "flex", alignItems: "center", justifyContent: "center" }}>FU</div>
              <div>
                <div style={{ fontSize: 17, fontWeight: 800 }}>Fury</div>
                <div style={{ fontSize: 12.5, color: "var(--ink-3)" }}>pingfury@outlook.com · 2024-06 加入</div>
              </div>
            </div>
            <div style={{ marginTop: 14, display: "flex", alignItems: "center", gap: 8, background: "var(--bg)",
              border: "1px solid var(--line)", borderRadius: 10, padding: "8px 12px" }}>
              <Icon name="wave" size={13} style={{ color: "var(--accent-deep)" }} />
              <span style={{ fontSize: 12, fontFamily: "ui-monospace,monospace", color: "var(--ink-2)", flex: 1 }}>rss://b2t.pingfury.top/token/a79b…</span>
              <span className="btn btn-ghost btn-sm" style={{ fontSize: 11.5 }}>复制</span>
            </div>
            <div style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 6 }}>你的专属播客 RSS —— 粘贴到任意播客 App 即可订阅自己的作品</div>
          </div>
          <div className="card" style={{ padding: 18 }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>积分余量</div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
              <span style={{ fontSize: 30, fontWeight: 800 }}>2,380</span>
              <span style={{ fontSize: 12.5, color: "var(--ink-3)" }}>积分</span>
              <span className="tag ok" style={{ marginLeft: "auto" }}>充足</span>
            </div>
            <div style={{ height: 6, borderRadius: 3, background: "var(--line)", marginTop: 12 }}>
              <span style={{ display: "block", width: "78%", height: "100%", borderRadius: 3, background: "var(--brand)" }} />
            </div>
            <div style={{ fontSize: 11.5, color: "var(--ink-3)", marginTop: 8 }}>音频约 6.5 小时 · OCR 约 130 页</div>
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginTop: 14 }}>
          {[{ t: "书籍", v: 6 }, { t: "音频", v: 24 }, { t: "已发布", v: 21 }, { t: "收听时长", v: "38h" }].map((s) => (
            <div key={s.t} className="card" style={{ padding: 14 }}>
              <div style={{ fontSize: 11.5, color: "var(--ink-3)" }}>{s.t}</div>
              <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4 }}>{s.v}</div>
            </div>
          ))}
        </div>
        <div className="card" style={{ padding: 16, marginTop: 14, display: "flex", alignItems: "center", gap: 12 }}>
          <Icon name="file" size={15} style={{ color: "var(--ink-3)" }} />
          <span style={{ fontSize: 13.5, fontWeight: 600, flex: 1 }}>操作记录</span>
          <span style={{ fontSize: 12, color: "var(--ink-3)" }}>全部操作留痕，可审计</span>
          <a className="btn-text" style={{ fontSize: 13 }} href="#">查看 <Icon name="arrow" size={12} /></a>
        </div>
      </div>
    </div>
  );
}

// ================= A1 登录 / 注册 =================
function AuthCard({ mode }) {
  return (
    <div className="card" style={{ width: 340, padding: 26 }}>
      <h2 style={{ fontSize: 18, fontWeight: 800, marginBottom: 4 }}>{mode === "login" ? "欢迎回来" : "创建账户"}</h2>
      <p style={{ fontSize: 12.5, color: "var(--ink-3)", marginBottom: 18 }}>{mode === "login" ? "继续你的有声书工坊" : "免费额度足够合成一整章"}</p>
      {[mode === "login" ? ["用户名", "请输入用户名"] : ["用户名", "设置用户名"],
        mode === "login" ? ["密码", "请输入密码"] : ["邮箱", "name@example.com"],
        ...(mode === "register" ? [["密码", "至少 8 位"], ["确认密码", "再输入一次"]] : [])].map(([l, p], i) => (
        <div key={i} style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--ink-2)", marginBottom: 5 }}>{l}</div>
          <div style={{ border: "1px solid var(--line-2)", borderRadius: 10, padding: "9px 12px", fontSize: 13, color: "var(--ink-3)" }}>{p}</div>
        </div>
      ))}
      <button className="btn btn-primary" style={{ width: "100%", marginTop: 6 }}>
        {mode === "login" ? "登录" : "免费注册"}
      </button>
      <div style={{ fontSize: 12, color: "var(--ink-3)", textAlign: "center", marginTop: 12 }}>
        {mode === "login" ? "没有账号？去注册" : "已有账号？去登录"}
      </div>
    </div>
  );
}

function BoardAuth() {
  return (
    <div data-screen-label="登录 / 注册" style={{ background: "var(--bg)", height: "100%" }}>
      <Nav2 active={null} auth={false} />
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", paddingTop: 40 }}>
        <img src="logo.png" alt="" style={{ width: 52, height: 52, borderRadius: 15, boxShadow: "0 8px 22px rgba(109,40,217,.25)" }} />
        <h1 style={{ fontSize: 24, fontWeight: 800, marginTop: 14 }}>把一本书，变成一档节目</h1>
        <p style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 6, marginBottom: 24 }}>免费注册，立即合成你的第一章</p>
        <div style={{ display: "flex", gap: 18 }}>
          <AuthCard mode="login" />
          <AuthCard mode="register" />
        </div>
      </div>
    </div>
  );
}

// ================= M1 移动端三屏 =================
function Phone({ label, children }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, alignItems: "center" }}>
      <div style={{ width: 320, height: 700, borderRadius: 34, background: "var(--bg)", border: "6px solid #1c1a22",
        overflow: "hidden", display: "flex", flexDirection: "column", position: "relative" }}>{children}</div>
      <span style={{ fontSize: 11.5, color: "var(--ink-3)", fontWeight: 600 }}>{label}</span>
    </div>
  );
}

function BoardMobile() {
  return (
    <div data-screen-label="移动端三屏" style={{ background: "#eceae5", height: "100%", display: "flex",
      gap: 26, alignItems: "center", justifyContent: "center", padding: 20 }}>
      <Phone label="落地页">
        <div style={{ padding: "26px 18px 12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
            <img src="logo.png" alt="" style={{ width: 22, height: 22, borderRadius: 6 }} />
            <span style={{ fontSize: 14, fontWeight: 800 }}>Book2TTS</span>
            <span style={{ marginLeft: "auto", fontSize: 12, fontWeight: 600, color: "var(--brand-deep)" }}>登录</span>
          </div>
          <h1 style={{ fontSize: 27, fontWeight: 800, lineHeight: 1.25, marginTop: 26 }}>把一本书，<br />变成一档节目。</h1>
          <p style={{ fontSize: 13.5, lineHeight: 1.8, color: "var(--ink-2)", marginTop: 12 }}>上传 EPUB / PDF，自动分章、多音色朗读，生成属于你的有声书。</p>
          <button className="btn btn-primary" style={{ width: "100%", marginTop: 18 }}>免费开始制作</button>
        </div>
        <BookCover i={1} title="人类简史" author="尤瓦尔·赫拉利" w={150} radius={14} style={{ margin: "18px auto 0", transform: "rotate(-3deg)" }} />
      </Phone>
      <Phone label="作品流 + 迷你播放条">
        <div style={{ padding: "16px 14px", flex: 1 }}>
          <div style={{ fontSize: 18, fontWeight: 800 }}>早上好，Fury</div>
          <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 3 }}>继续你的上一章</div>
          <div className="card" style={{ padding: 12, marginTop: 14, display: "flex", gap: 10 }}>
            <BookCover i={0} title="夜航船" author="" w={44} radius={7} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: "var(--accent-deep)", letterSpacing: 1 }}>继续收听</div>
              <div style={{ fontSize: 13.5, fontWeight: 700, marginTop: 3 }}>江湖纪闻</div>
              <div style={{ height: 4, borderRadius: 2, background: "var(--line)", marginTop: 8 }}>
                <span style={{ display: "block", width: "42%", height: "100%", background: "var(--accent)", borderRadius: 2 }} /></div>
            </div>
            <span className="play sm"><Icon name="play" size={11} style={{ marginLeft: 1 }} /></span>
          </div>
          <div style={{ fontSize: 13, fontWeight: 800, margin: "16px 0 8px" }}>我的作品</div>
          <AudioRow i={1} book="人类简史" title="第一章 没有什么特别的动物" meta="今天 09:12" />
          <div style={{ height: 8 }} />
          <AudioRow i={3} book="山茶文具店" title="代笔人序 · 给祖母的信" meta="昨天 21:03" />
        </div>
        <div className="mini" style={{ padding: "9px 14px" }}>
          <BookCover i={0} title="夜航船" author="" w={32} radius={5} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 11.5, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>江湖纪闻</div>
            <div style={{ height: 3, borderRadius: 2, background: "var(--line)", marginTop: 6 }}>
              <span style={{ display: "block", width: "38%", height: "100%", background: "var(--accent)" }} /></div>
          </div>
          <span className="play sm" style={{ width: 28, height: 28 }}><Icon name="pause" size={11} /></span>
        </div>
      </Phone>
      <Phone label="播放详情">
        <div style={{ padding: "18px 16px", display: "flex", flexDirection: "column", alignItems: "center", flex: 1 }}>
          <div style={{ alignSelf: "flex-start", fontSize: 12, color: "var(--ink-3)", marginBottom: 12 }}>← 探索 · 夜航船</div>
          <BookCover i={0} title="夜航船" author="张岱" w={170} radius={16} />
          <div style={{ fontSize: 17, fontWeight: 800, marginTop: 16 }}>第三章 江湖纪闻</div>
          <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 4 }}>Fury 制作 · 41 分钟</div>
          <div style={{ width: "100%", height: 5, borderRadius: 3, background: "var(--line)", marginTop: 18, position: "relative" }}>
            <span style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "34%", background: "var(--accent)", borderRadius: 3 }} /></div>
          <div style={{ width: "100%", display: "flex", justifyContent: "space-between", fontSize: 10.5, color: "var(--ink-3)", marginTop: 6 }}>
            <span>14:02</span><span>-27:18</span></div>
          <div style={{ display: "flex", alignItems: "center", gap: 24, marginTop: 18, color: "var(--ink-2)" }}>
            <Icon name="skipBack" size={18} /><span className="play md"><Icon name="play" size={16} style={{ marginLeft: 2 }} /></span><Icon name="skipFwd" size={18} />
          </div>
          <div style={{ alignSelf: "stretch", marginTop: 20, display: "flex", gap: 8 }}>
            <span className="btn btn-ghost btn-sm" style={{ flex: 1, fontSize: 12 }}>下载音频</span>
            <span className="btn btn-ghost btn-sm" style={{ flex: 1, fontSize: 12 }}>字幕</span>
          </div>
        </div>
      </Phone>
    </div>
  );
}

// ================= Q3 成品书籍详情（章节集列表） =================
function BoardBookDetail() {
  const eps = [
    { n: 1, t: "第一章 天文纪", d: "36:12", pub: true },
    { n: 2, t: "第二章 地理纪", d: "40:03", pub: true },
    { n: 3, t: "第三章 江湖纪闻", d: "41:20", pub: true, on: true },
    { n: 4, t: "第四章 奇技洨巧", d: "38:05", pub: true },
    { n: 5, t: "第五章 四方异闻", d: "44:12", pub: false },
    { n: 6, t: "第六章 舟车忆旧", d: "36:47", pub: false },
  ];
  return (
    <div data-screen-label="成品书籍详情 · 章节集" style={{ background: "var(--bg)", height: "100%" }}>
      <Nav2 active="library" />
      {/* 书籍 Hero：封面 + 元信息 + 主 CTA + RSS */}
      <div style={{ maxWidth: 920, margin: "0 auto", padding: "22px 32px 18px", display: "flex", gap: 22 }}>
        <BookCover i={0} title="夜航船" author="张岱" w={128} radius={14} />
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="tag ok">已完结</span>
            <span className="badge">张岱 · 古典笔记</span>
          </div>
          <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: "-0.5px", marginTop: 9 }}>《夜航船》</h1>
          <p style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 6 }}>
            12 集 · 共 7 小时 24 分 · 你的有声书 · 更新于今天</p>
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 16 }}>
            <span className="play md"><Icon name="play" size={16} style={{ marginLeft: 2 }} /></span>
            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--ink-2)" }}>继续收听 · 第 3 集</span>
            <span style={{ width: 1, height: 18, background: "var(--line-2)" }} />
            <span className="btn btn-ghost btn-sm"><Icon name="wave" size={12} />播客 RSS</span>
            <span className="btn btn-ghost btn-sm">章节管理</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 14 }}>
            <div style={{ flex: 1, height: 5, borderRadius: 3, background: "var(--line)" }}>
              <span style={{ display: "block", width: "100%", height: "100%", background: "var(--ok)", borderRadius: 3 }} />
            </div>
            <span style={{ fontSize: 11, color: "var(--ok)", fontWeight: 700, flexShrink: 0 }}>已发布 10/12</span>
          </div>
        </div>
      </div>
      {/* 章节集列表：点击行即播放；次要操作 hover 出现 */}
      <div style={{ maxWidth: 920, margin: "0 auto", padding: "0 32px 24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
          <h2 style={{ fontSize: 14, fontWeight: 700 }}>章节集 <span style={{ fontSize: 12, fontWeight: 500, color: "var(--ink-3)" }}>12</span></h2>
          <span style={{ fontSize: 11.5, color: "var(--ink-3)", display: "flex", alignItems: "center", gap: 4 }}>
            <span className="bolt">⚡</span> 点击行播放 · 悬停行出现更多操作</span>
        </div>
        <div className="card" style={{ overflow: "hidden" }}>
          {eps.map((ep) => (
            <div key={ep.n} style={{ display: "flex", alignItems: "center", gap: 13, padding: "12px 18px",
              borderTop: "1px solid var(--line)", background: ep.on ? "var(--accent-tint)" : "transparent" }}>
              <span style={{ width: 30, height: 30, borderRadius: 9, flexShrink: 0, fontSize: 12,
                display: "flex", alignItems: "center", justifyContent: "center",
                background: ep.on ? "var(--accent)" : "var(--bg)", color: ep.on ? "#fff" : "var(--ink-3)",
                border: ep.on ? "none" : "1px solid var(--line)", fontFamily: "ui-monospace,monospace" }}>
                {ep.on ? <Icon name="pause" size={12} /> : ep.n}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: ep.on ? 700 : 600, color: ep.on ? "var(--accent-deep)" : "var(--ink)" }}>{ep.t}</div>
                <div style={{ fontSize: 11.5, color: "var(--ink-3)", marginTop: 3 }}>{ep.d} · 上传于 3 天前</div>
              </div>
              {ep.on && <Wave w={34} h={13} />}
              <span className={ep.pub ? "tag ok" : "tag warn"}>{ep.pub ? "已发布" : "草稿"}</span>
              <div style={{ display: "flex", gap: 2, opacity: ep.on ? 1 : 0, transition: "opacity .15s" }}>
                <span className="ghost-ico" style={{ width: 26, height: 26 }}><Icon name="download" size={13} /></span>
                <span className="ghost-ico" style={{ width: 26, height: 26 }}><Icon name="dots" size={14} /></span>
              </div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 12, fontSize: 12, color: "var(--ink-3)", lineHeight: 1.8 }}>
          <span className="bolt">⚡ 交互说明：</span>草稿集的取消/发布操作收在 ⋯ 菜单；
          未发布集在工作台可见，前台不可见；正在播放的集高亮 + 动态声纹。
        </div>
      </div>
    </div>
  );
}

// ================= E1 探索 V2 =================
function ExploreCard({ i, book, title, meta }) {
  return (
    <div className="card" style={{ display: "flex", gap: 13, padding: 13, alignItems: "center" }}>
      <BookCover i={i} title={book} author="" w={62} radius={9} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <span className="badge">{book}</span>
        <div style={{ fontSize: 14.5, fontWeight: 700, marginTop: 6, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{title}</div>
        <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 3 }}>{meta}</div>
      </div>
      <span className="play md"><Icon name="play" size={15} style={{ marginLeft: 2 }} /></span>
    </div>
  );
}

function BoardExplore2() {
  return (
    <div data-screen-label="探索 V2" style={{ background: "var(--bg)", height: "100%" }}>
      <Nav2 active="explore" />
      <div style={{ maxWidth: 1160, margin: "0 auto", padding: "24px 32px" }}>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 16, marginBottom: 18 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.4px" }}>探索</h1>
            <p style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 5 }}>社区公开的有声书与对话作品，可直接收听。</p>
          </div>
          <span className="search-pill" style={{ width: 380 }}><Icon name="search" size={13} />搜索书名、标题或作者…</span>
        </div>
        <div style={{ display: "flex", gap: 8, marginBottom: 18 }}>
          <span className="btn btn-primary btn-sm">全部</span>
          {["小说", "历史", "科幻", "散文", "英语学习"].map((c) => (
            <span key={c} className="btn btn-ghost btn-sm">{c}</span>
          ))}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
          <ExploreCard i={1} book="人类简史" title="第一章 人类也是一种没有什么特别的动物" meta="Fury · 41 分钟" />
          <ExploreCard i={3} book="山茶文具店" title="代笔人序 · 鸠子写给祖母的信" meta="Momo · 18 分钟" />
          <ExploreCard i={2} book="夜航西飞" title="第四章 北方的沙漠，城市的边缘" meta="Lao Wang · 27 分钟" />
          <ExploreCard i={0} book="夜航船" title="第三章 江湖纪闻" meta="Fury · 34 分钟" />
          <ExploreCard i={5} book="万物有灵" title="故乡的野菜" meta="小鹿 · 12 分钟" />
          <ExploreCard i={4} book="城南旧事" title="惠安馆 · 上" meta="阿禾 · 25 分钟" />
        </div>
      </div>
    </div>
  );
}

// ================= D1 暗色主题 =================
const DK = { bg: "#14121a", surface: "#1d1a26", line: "rgba(255,255,255,.08)", line2: "rgba(255,255,255,.16)",
  ink: "#ece9f4", ink2: "#b6b1c4", ink3: "#7d7889", brand: "#8b5cf6", tint: "rgba(139,92,246,.16)",
  accent: "#f97316", accentTint: "rgba(249,115,22,.14)" };

function DarkRow({ i, book, title, meta }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 12px", borderRadius: 12,
      background: DK.surface, border: "1px solid " + DK.line }}>
      <BookCover i={i} title={book} author="" w={44} radius={7} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <span style={{ fontSize: 10.5, fontWeight: 600, color: DK.ink3, border: "1px solid " + DK.line2, borderRadius: 999, padding: "1px 8px" }}>{book}</span>
        <div style={{ fontSize: 13.5, fontWeight: 700, color: DK.ink, marginTop: 5, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{title}</div>
        <div style={{ fontSize: 11, color: DK.ink3, marginTop: 3 }}>{meta}</div>
      </div>
      <span className="play md" style={{ background: DK.accent, boxShadow: "0 4px 14px rgba(249,115,22,.35)" }}><Icon name="play" size={14} style={{ marginLeft: 2 }} /></span>
    </div>
  );
}

function BoardDark() {
  return (
    <div data-screen-label="暗色主题" style={{ background: DK.bg, height: "100%", padding: "26px 34px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 19, fontWeight: 800, color: DK.ink }}>暗色主题</h2>
          <p style={{ fontSize: 12.5, color: DK.ink3, marginTop: 5 }}>深紫墨底 + 提亮 brand/accent；文字对齐 WCAG AA；播放键仍为唯一暖色。</p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {[{ l: "bg", c: DK.bg }, { l: "surface", c: DK.surface }, { l: "brand", c: DK.brand }, { l: "accent", c: DK.accent }, { l: "ink", c: DK.ink }].map((s) => (
            <div key={s.l} style={{ textAlign: "center" }}>
              <div style={{ width: 42, height: 42, borderRadius: 10, background: s.c, border: "1px solid " + DK.line2 }} />
              <div style={{ fontSize: 10, color: DK.ink3, marginTop: 4 }}>{s.l}</div>
            </div>
          ))}
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 22 }}>
        {/* 暗色作品流缩略 */}
        <div style={{ background: DK.bg, border: "1px solid " + DK.line, borderRadius: 16, padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <span style={{ fontSize: 16, fontWeight: 800, color: DK.ink }}>早上好，Fury</span>
            <span className="btn btn-primary btn-sm" style={{ background: DK.brand }}><Icon name="plus" size={12} />制作新音频</span>
          </div>
          <div style={{ background: DK.surface, border: "1px solid " + DK.line, borderRadius: 12, padding: 13, display: "flex", gap: 13, marginBottom: 10 }}>
            <BookCover i={0} title="夜航船" author="" w={62} radius={9} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: DK.accent, letterSpacing: 1 }}>继续收听</div>
              <div style={{ fontSize: 14.5, fontWeight: 800, color: DK.ink, marginTop: 4 }}>第三章 江湖纪闻</div>
              <div style={{ height: 4, borderRadius: 2, background: DK.line, marginTop: 8 }}>
                <span style={{ display: "block", width: "42%", height: "100%", background: DK.accent, borderRadius: 2 }} /></div>
            </div>
            <span className="play md" style={{ background: DK.accent }}><Icon name="play" size={14} style={{ marginLeft: 2 }} /></span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <DarkRow i={1} book="人类简史" title="第一章 没有什么特别的动物" meta="今天 09:12 · 41 分钟" />
            <DarkRow i={3} book="山茶文具店" title="代笔人序 · 给祖母的信" meta="昨天 21:03 · 18 分钟" />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 12, padding: "9px 12px",
            background: DK.surface, border: "1px solid " + DK.line, borderRadius: 12 }}>
            <BookCover i={0} title="夜航船" author="" w={32} radius={5} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 11.5, fontWeight: 600, color: DK.ink }}>江湖纪闻</div>
              <div style={{ height: 3, borderRadius: 2, background: DK.line, marginTop: 5 }}>
                <span style={{ display: "block", width: "38%", height: "100%", background: DK.accent }} /></div>
            </div>
            <span className="play sm" style={{ background: DK.accent }}><Icon name="pause" size={11} /></span>
          </div>
        </div>
        {/* 暗色播放详情缩略 */}
        <div style={{ background: DK.bg, border: "1px solid " + DK.line, borderRadius: 16, padding: 16 }}>
          <div style={{ display: "flex", gap: 16 }}>
            <BookCover i={0} title="夜航船" author="张岱" w={130} radius={13} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <span style={{ fontSize: 10.5, fontWeight: 600, color: DK.ink3, border: "1px solid " + DK.line2, borderRadius: 999, padding: "1px 8px" }}>夜航船</span>
              <div style={{ fontSize: 17, fontWeight: 800, color: DK.ink, marginTop: 7 }}>第三章 江湖纪闻</div>
              <div style={{ fontSize: 11.5, color: DK.ink3, marginTop: 5 }}>Fury 制作 · 41 分钟 · 1.2k 次收听</div>
              <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 16, color: DK.ink2 }}>
                <Icon name="skipBack" size={16} />
                <span className="play md" style={{ background: DK.accent }}><Icon name="play" size={15} style={{ marginLeft: 2 }} /></span>
                <Icon name="skipFwd" size={16} />
              </div>
            </div>
          </div>
          <div style={{ marginTop: 16 }}>
            {[{ n: 3, t: "第三章 江湖纪闻", d: "41:20", on: true },
              { n: 4, t: "第四章 奇技洨巧", d: "38:05" },
              { n: 5, t: "第五章 四方异闻", d: "44:12" }].map((c) => (
              <div key={c.n} style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 10px", borderRadius: 9,
                marginBottom: 5, background: c.on ? DK.accentTint : DK.surface, border: "1px solid " + (c.on ? "rgba(249,115,22,.3)" : DK.line) }}>
                <span style={{ width: 22, height: 22, borderRadius: 6, fontSize: 10, flexShrink: 0, display: "flex",
                  alignItems: "center", justifyContent: "center", background: c.on ? DK.accent : DK.bg,
                  color: c.on ? "#fff" : DK.ink3, fontFamily: "ui-monospace,monospace" }}>{c.n}</span>
                <span style={{ fontSize: 12.5, fontWeight: c.on ? 700 : 500, color: c.on ? DK.accent : DK.ink2, flex: 1 }}>{c.t}</span>
                <span style={{ fontSize: 10.5, color: DK.ink3 }}>{c.d}</span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 10, fontSize: 11, color: DK.ink3, display: "flex", alignItems: "center", gap: 5 }}>
            <span className="bolt">⚡</span> 暗色下播放键提亮为 #f97316，保证对深底 3:1 对比
          </div>
        </div>
      </div>
    </div>
  );
}

// ================= W1 我的书籍 + 上传 =================
function BookShelfCard({ i, name, tag, tagCls, meta }) {
  return (
    <div className="card" style={{ padding: 14, display: "flex", gap: 13 }}>
      <BookCover i={i} title={name} author="" w={72} radius={10} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 14.5, fontWeight: 700 }}>《{name}》</div>
        <div style={{ marginTop: 6 }}><span className={"tag " + tagCls}>{tag}</span></div>
        <div style={{ fontSize: 11.5, color: "var(--ink-3)", marginTop: 7 }}>{meta}</div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, justifyContent: "center" }}>
        <span className="btn btn-primary btn-sm">继续制作</span>
        <span className="btn btn-ghost btn-sm">更多</span>
      </div>
    </div>
  );
}

function BoardMyBooks() {
  return (
    <div data-screen-label="我的书籍 + 上传" style={{ background: "var(--bg)", height: "100%" }}>
      <Nav2 active="studio" />
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "24px 32px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.4px" }}>我的书籍</h1>
            <p style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 5 }}>创作输入侧：书架与上传解析。</p>
          </div>
          <span className="btn btn-primary"><Icon name="upload" size={14} />上传书籍</span>
        </div>
        {/* 上传流（拖放 + 解析步骤） */}
        <div style={{ display: "grid", gridTemplateColumns: "1.35fr 1fr", gap: 14, marginBottom: 18 }}>
          <div style={{ border: "2px dashed var(--line-2)", borderRadius: 16, background: "var(--surface)",
            padding: "24px 20px", textAlign: "center" }}>
            <div style={{ width: 46, height: 46, borderRadius: 13, background: "var(--brand-tint)", color: "var(--brand-deep)",
              display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 10px" }}>
              <Icon name="upload" size={21} /></div>
            <div style={{ fontSize: 14.5, fontWeight: 700 }}>拖入 EPUB / PDF，或点击上传</div>
            <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 5 }}>扫描件自动 OCR · 单文件 ≤ 100MB</div>
          </div>
          <div className="card" style={{ padding: 16 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--ink-3)", letterSpacing: 1.5, marginBottom: 12 }}>解析流水线</div>
            {[{ t: "上传完成", ok: true }, { t: "解析目录 · 48 章", ok: true }, { t: "OCR 扫描页 · 进行中" }].map((s, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 9 }}>
                <span style={{ width: 18, height: 18, borderRadius: "50%", fontSize: 10, display: "flex",
                  alignItems: "center", justifyContent: "center", flexShrink: 0,
                  background: s.ok ? "var(--ok)" : "var(--brand-tint)", color: s.ok ? "#fff" : "var(--brand-deep)" }}>
                  {s.ok ? <Icon name="check" size={10} /> : i + 1}</span>
                <span style={{ fontSize: 12.5, fontWeight: s.ok ? 600 : 500, color: s.ok ? "var(--ink-2)" : "var(--ink)" }}>{s.t}</span>
              </div>
            ))}
            <div style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 4 }}>
              <span className="bolt">⚡</span> 解析由任务线程执行，完成后书架自动出现新书
            </div>
          </div>
        </div>
        {/* 书架 */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 12 }}>
          <BookShelfCard i={0} name="夜航船" tag="已完结" tagCls="ok" meta="12 集 · 7 小时 24 分 · 上传于 1 月 12 日" />
          <BookShelfCard i={2} name="夜航西飞" tag="连载中 30%" tagCls="warn" meta="4 集 · 1 小时 48 分 · 上传于 3 天前" />
        </div>
      </div>
    </div>
  );
}

// ================= W2 对话脚本列表 + 创建 =================
function BoardScripts() {
  const scripts = [
    { t: "夜航船 · 第一章 广播剧脚本", book: "夜航船", segs: 12, roles: 2, st: "已生成音频", cls: "ok" },
    { t: "人类简史 · 开篇对话", book: "人类简史", segs: 8, roles: 2, st: "草稿", cls: "draft" },
    { t: "产品介绍播客脚本", book: null, segs: 16, roles: 3, st: "已生成音频", cls: "ok" },
  ];
  return (
    <div data-screen-label="对话脚本列表 + 创建" style={{ background: "var(--bg)", height: "100%" }}>
      <Nav2 active="library" />
      <div style={{ maxWidth: 1160, margin: "0 auto", padding: "24px 32px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1.25fr 1fr", gap: 20 }}>
          <div>
            <h1 style={{ fontSize: 21, fontWeight: 800, letterSpacing: "-0.4px", marginBottom: 14 }}>对话脚本</h1>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {scripts.map((s, i) => (
                <div key={i} className="card" style={{ padding: 14, display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ width: 38, height: 38, borderRadius: 10, background: "var(--brand-tint)", color: "var(--brand-deep)",
                    display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}><Icon name="chat" size={16} /></div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.t}</div>
                    <div style={{ fontSize: 11.5, color: "var(--ink-3)", marginTop: 4 }}>{s.segs} 段 · {s.roles} 角色 · 关联《{s.book}》</div>
                  </div>
                  <span className={"tag " + s.cls}>{s.st}</span>
                  <span className="btn btn-ghost btn-sm">打开编辑器 <Icon name="arrow" size={11} /></span>
                </div>
              ))}
            </div>
          </div>
          <div className="card" style={{ padding: 18, alignSelf: "start" }}>
            <div style={{ fontSize: 15, fontWeight: 800, marginBottom: 4 }}>创建对话脚本</div>
            <div style={{ fontSize: 12, color: "var(--ink-3)", marginBottom: 14 }}>粘贴文本，AI 转换为多角色对话</div>
            <div style={{ fontSize: 12, fontWeight: 600, color: "var(--ink-2)", marginBottom: 5 }}>脚本标题</div>
            <div style={{ border: "1px solid var(--line-2)", borderRadius: 10, padding: "8px 11px", fontSize: 12.5, color: "var(--ink-3)", marginBottom: 12 }}>为脚本起一个标题</div>
            <div style={{ fontSize: 12, fontWeight: 600, color: "var(--ink-2)", marginBottom: 5 }}>原始文本</div>
            <div style={{ border: "1px solid var(--line-2)", borderRadius: 10, padding: "10px 11px", fontSize: 12, color: "var(--ink-3)", height: 96, marginBottom: 12 }}>
              粘贴需要转换的文本内容…（支持长文自动分段）</div>
            <span className="btn btn-primary btn-sm" style={{ width: "100%" }}><Icon name="chat" size={12} />创建对话脚本</span>
            <div style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 9, lineHeight: 1.7 }}>
              <span className="bolt">⚡</span> 提交后 on_commit 入队；长文自动分段并缓存，失败重试不重复扣费
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ================= S3 ⌘K 全局搜索 =================
function BoardSearch() {
  const groups = [
    { g: "最近", items: [{ i: 0, icon: "play", t: "夜航船 · 第三章 江湖纪闻", s: "最近播放 · 14:02" }] },
    { g: "我的作品", items: [
      { i: 1, icon: "file", t: "第一章 没有什么特别的动物", s: "人类简史 · 41 分钟" },
      { i: 3, icon: "file", t: "代笔人序 · 给祖母的信", s: "山茶文具店 · 18 分钟" }] },
    { g: "书籍", items: [{ i: 0, icon: "book", t: "夜航船", s: "12 集 · 已完结" }] },
    { g: "社区", items: [{ i: 2, icon: "chat", t: "扫描版 PDF 的 OCR 识别准确率怎么提高？", s: "Momo · 8 回复" }] },
  ];
  return (
    <div data-screen-label="⌘K 全局搜索" style={{ height: "100%", background: "rgba(25,22,34,.45)",
      display: "flex", justifyContent: "center", paddingTop: 70 }}>
      <div style={{ width: 620, height: 470, background: "var(--surface)", borderRadius: 18,
        boxShadow: "var(--shadow-pop)", overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "15px 18px", borderBottom: "1px solid var(--line)", color: "var(--ink-3)" }}>
          <Icon name="search" size={16} />
          <span style={{ fontSize: 15, color: "var(--ink)", flex: 1 }}>夜航<span style={{ opacity: 0 }}>|</span></span>
          <span className="kbd" style={{ fontSize: 10, border: "1px solid var(--line-2)", borderRadius: 5, padding: "1px 5px" }}>ESC</span>
        </div>
        <div style={{ flex: 1, overflow: "hidden", padding: "8px 10px" }}>
          {groups.map((grp) => (
            <div key={grp.g} style={{ marginBottom: 6 }}>
              <div style={{ fontSize: 10.5, fontWeight: 700, color: "var(--ink-3)", letterSpacing: 1.2, padding: "6px 10px" }}>{grp.g}</div>
              {grp.items.map((it, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 10px", borderRadius: 9,
                  background: grp.g === "最近" && i === 0 ? "var(--brand-tint)" : "transparent" }}>
                  <span style={{ width: 28, height: 28, borderRadius: 8, background: "var(--bg)", border: "1px solid var(--line)",
                    display: "flex", alignItems: "center", justifyContent: "center", color: "var(--ink-3)", flexShrink: 0 }}>
                    <Icon name={it.icon} size={13} /></span>
                  <span style={{ fontSize: 13, fontWeight: 500, flex: 1 }}>{it.t}</span>
                  <span style={{ fontSize: 11, color: "var(--ink-3)" }}>{it.s}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
        <div style={{ padding: "9px 16px", borderTop: "1px solid var(--line)", fontSize: 11, color: "var(--ink-3)", display: "flex", gap: 16 }}>
          <span>↑↓ 选择</span><span>↵ 打开</span><span>esc 关闭</span>
          <span style={{ marginLeft: "auto" }}>⚡ 全局搜索：作品 / 书籍 / 探索内容 / 社区帖</span>
        </div>
      </div>
    </div>
  );
}

// ================= M2 边界页合集 =================
function BoardEdge() {
  return (
    <div data-screen-label="边界页合集" style={{ background: "var(--bg)", height: "100%", padding: "24px 32px" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
        {/* 关于 */}
        <div className="card" style={{ padding: 18, height: 380 }}>
          <div style={{ fontSize: 15, fontWeight: 800, marginBottom: 10 }}>关于</div>
          <div style={{ fontSize: 12, color: "var(--ink-2)", lineHeight: 1.85 }}>
            Book2TTS 是为图书制作人打造的在线工作台：电子书解析、LLM 排版翻译、
            多音色合成到播客发布，一站式完成。</div>
          <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 7, fontSize: 11.5, color: "var(--ink-3)" }}>
            <span>· 书籍工作台：目录/页面双视图</span>
            <span>· LLM 智能处理：排版/翻译/脚本</span>
            <span>· 音频与发布：多音色 + RSS</span>
          </div>
          <div style={{ marginTop: 14, fontSize: 11, color: "var(--ink-3)" }}>© 2026 pingfury</div>
        </div>
        {/* 404 */}
        <div className="card" style={{ padding: 18, height: 380, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center" }}>
          <div style={{ fontSize: 52, fontWeight: 800, color: "var(--ink)", opacity: .12 }}>404</div>
          <div style={{ fontSize: 15, fontWeight: 700, marginTop: 6 }}>页面走丢了</div>
          <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 6, lineHeight: 1.7 }}>你要找的页面不存在，<br />或已被移动。</div>
          <span className="btn btn-primary btn-sm" style={{ marginTop: 16 }}>返回首页</span>
        </div>
        {/* 空状态 */}
        <div className="card" style={{ padding: 18, height: 380, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center" }}>
          <div style={{ width: 52, height: 52, borderRadius: 15, background: "var(--brand-tint)", color: "var(--brand-deep)",
            display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 12 }}>
            <Icon name="book" size={22} /></div>
          <div style={{ fontSize: 15, fontWeight: 700 }}>书架还是空的</div>
          <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 6, lineHeight: 1.7 }}>上传第一本书，<br />开始你的有声书之旅。</div>
          <span className="btn btn-primary btn-sm" style={{ marginTop: 16 }}><Icon name="upload" size={12} />上传书籍</span>
        </div>
        {/* 登出 */}
        <div className="card" style={{ padding: 18, height: 380, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center" }}>
          <img src="logo.png" alt="" style={{ width: 44, height: 44, borderRadius: 12, marginBottom: 12 }} />
          <div style={{ fontSize: 15, fontWeight: 700 }}>已安全登出</div>
          <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 6 }}>感谢使用，期待你的下一本有声书</div>
          <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
            <span className="btn btn-primary btn-sm">重新登录</span>
            <span className="btn btn-ghost btn-sm">首页</span>
          </div>
        </div>
      </div>
      <div style={{ marginTop: 16, fontSize: 12, color: "var(--ink-3)", lineHeight: 1.8 }}>
        <span className="bolt">⚡</span> 空状态系统：每个空态均携带「下一步动作」主按钮；
        图标统一用 brand-tint 底 + brand 色，不用插画。
      </div>
    </div>
  );
}

// ================= App =================
function B2TV2() {
  return (
    <DesignCanvas>
      <DCSection id="structure" title="V2 · 结构先行" subtitle="信息架构重组 + 设计语言升级">
        <DCArtboard id="s1" label="S1 · 信息架构" width={1240} height={780}><BoardIA /></DCArtboard>
        <DCArtboard id="s2" label="S2 · 设计系统 V2" width={1240} height={520}><BoardDS2 /></DCArtboard>
      </DCSection>
      <DCSection id="pages" title="核心页 V2" subtitle="落地页 · 作品流 · 播放详情">
        <DCArtboard id="p1" label="P1 · 落地页" width={1440} height={1060}><BoardLanding /></DCArtboard>
        <DCArtboard id="p2" label="P2 · 作品流（点迷你播放条看展开态）" width={1440} height={820}><BoardWorks /></DCArtboard>
        <DCArtboard id="p3" label="P3 · 播放详情" width={1440} height={820}><BoardPlayDetail /></DCArtboard>
      </DCSection>
      <DCSection id="studio" title="工坊 V2" subtitle="编辑器交互语言：⚡ 标注为交互说明">
        <DCArtboard id="p4" label="P4 · 制作台（目录/页面 tab 可切换）" width={1440} height={720}><BoardStudio /></DCArtboard>
        <DCArtboard id="p5" label="P5 · 脚本编辑器" width={1440} height={680}><BoardScriptEditor /></DCArtboard>
      </DCSection>
      <DCSection id="ops" title="队列 · 资产 · 账户" subtitle="实时态 + 内容资产 + 账户层">
        <DCArtboard id="q1" label="Q1 · 生成队列（实时态）" width={1440} height={640}><BoardQueue /></DCArtboard>
        <DCArtboard id="q2" label="Q2 · 有声书成品" width={1440} height={620}><BoardAudiobooks /></DCArtboard>
        <DCArtboard id="q3" label="Q3 · 成品书籍详情（章节集）" width={1440} height={780}><BoardBookDetail /></DCArtboard>
        <DCArtboard id="u1" label="U1 · 个人中心" width={1240} height={620}><BoardProfile /></DCArtboard>
      </DCSection>
      <DCSection id="community" title="社区" subtitle="列表 + 帖子详情">
        <DCArtboard id="c1" label="C1 · 社区列表" width={1440} height={620}><BoardCommunity /></DCArtboard>
        <DCArtboard id="c2" label="C2 · 帖子详情" width={1440} height={720}><BoardThread /></DCArtboard>
      </DCSection>
      <DCSection id="auth-mobile" title="账户 & 移动端" subtitle="登录注册合一 · 移动端三屏">
        <DCArtboard id="a1" label="A1 · 登录 / 注册" width={1200} height={620}><BoardAuth /></DCArtboard>
        <DCArtboard id="m1" label="M1 · 移动端三屏" width={1160} height={800}><BoardMobile /></DCArtboard>
      </DCSection>
      <DCSection id="fill" title="补充 · 内容 / 暗色 / 工坊输入 / 搜索 / 边界" subtitle="全站覆盖收尾">
        <DCArtboard id="e1" label="E1 · 探索 V2" width={1440} height={720}><BoardExplore2 /></DCArtboard>
        <DCArtboard id="d1" label="D1 · 暗色主题" width={1440} height={640}><BoardDark /></DCArtboard>
        <DCArtboard id="w1" label="W1 · 我的书籍 + 上传" width={1440} height={700}><BoardMyBooks /></DCArtboard>
        <DCArtboard id="w2" label="W2 · 对话脚本列表 + 创建" width={1440} height={620}><BoardScripts /></DCArtboard>
        <DCArtboard id="s3" label="S3 · ⌘K 全局搜索" width={1200} height={640}><BoardSearch /></DCArtboard>
        <DCArtboard id="m2" label="M2 · 边界页合集" width={1440} height={560}><BoardEdge /></DCArtboard>
      </DCSection>
    </DesignCanvas>
  );
}

Object.assign(window, { B2TV2 });
