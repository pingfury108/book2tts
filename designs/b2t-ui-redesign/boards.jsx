// Book2TTS UI 重设计 — 画板内容
// A 访客·延续版 / B 访客·大胆版 / C 登录后·作品流 / D 卡片解剖 / E 移动端

const { DesignCanvas, DCSection, DCArtboard, DCPostIt } = window;

// ---------- 图标 ----------
const ICON_PATHS = {
  play: { d: "M8 5v14l11-7z", fill: true },
  pause: { d: "M7 5h4v14H7zM13 5h4v14h-4z", fill: true },
  dots: { d: "M6 12a1.4 1.4 0 1 0 2.8 0 1.4 1.4 0 0 0-2.8 0zm4.6 0a1.4 1.4 0 1 0 2.8 0 1.4 1.4 0 0 0-2.8 0zm4.6 0a1.4 1.4 0 1 0 2.8 0 1.4 1.4 0 0 0-2.8 0z", fill: true },
  plus: { d: "M12 5v14M5 12h14", stroke: true },
  sun: { d: "M12 4v2m0 12v2M4 12h2m12 0h2M6.3 6.3l1.4 1.4m8.6 8.6l1.4 1.4m0-11.4l-1.4 1.4M7.7 16.3l-1.4 1.4M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z", stroke: true },
  chevron: { d: "M6 9l6 6 6-6", stroke: true },
  arrow: { d: "M5 12h14M13 6l6 6-6 6", stroke: true },
  menu: { d: "M4 7h16M4 12h16M4 17h16", stroke: true },
  skipBack: { d: "M19 20L9 12l10-8v16zM7 5v14", stroke: true },
  skipFwd: { d: "M5 20l10-8L5 4v16zM17 5v14", stroke: true },
  search: { d: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm10 17l-4.35-4.35", stroke: true },
  upload: { d: "M12 16V4m0 0l-5 5m5-5l5 5M4 20h16", stroke: true },
  file: { d: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zM14 2v6h6", stroke: true },
  type: { d: "M4 7V4h16v3M12 4v16M9 20h6", stroke: true },
  globe: { d: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM3 12h18M12 3c2.5 2.5 3.5 5.5 3.5 9s-1 6.5-3.5 9c-2.5-2.5-3.5-5.5-3.5-9s1-6.5 3.5-9z", stroke: true },
  eye: { d: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7zm10 3.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z", stroke: true },
  wave: { d: "M3 12h2l2-6 3 12 3-9 2 5 2-3h4", stroke: true },
};

function Icon({ name, size = 18, style }) {
  const p = ICON_PATHS[name];
  return p.fill ? (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" style={style}><path d={p.d} /></svg>
  ) : (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
         strokeLinecap="round" strokeLinejoin="round" style={style}><path d={p.d} /></svg>
  );
}

// ---------- 书籍封面（hash 取色的排版占位封面） ----------
const PALETTE = [
  { bg: "#8b6fd8", deep: "#6d4fb8" },
  { bg: "#5b9fc0", deep: "#417f9f" },
  { bg: "#5aa77a", deep: "#3f8a5f" },
  { bg: "#d9973f", deep: "#b87a28" },
  { bg: "#c96f6f", deep: "#a95050" },
  { bg: "#7b82cc", deep: "#5d64b0" },
];

function BookCover({ i = 0, title, author, w = 120, radius = 10, style, className }) {
  const p = PALETTE[i % PALETTE.length];
  return (
    <div className={className} style={{
      width: w, height: Math.round(w * 4 / 3), borderRadius: radius,
      background: `linear-gradient(155deg, ${p.bg}, ${p.deep})`,
      color: "#fff", padding: Math.round(w * 0.11), position: "relative", overflow: "hidden",
      display: "flex", flexDirection: "column", justifyContent: "space-between",
      boxShadow: "0 6px 18px rgba(28,25,23,.18)", flexShrink: 0, ...style,
    }}>
      <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: Math.max(4, w * 0.05),
                    background: "rgba(255,255,255,.22)", borderRadius: "8px 0 0 8px" }} />
      <div style={{ width: 18, height: 2, background: "rgba(255,255,255,.55)", marginTop: 4 }} />
      <div>
        <div style={{ fontSize: Math.max(12, w * 0.13), fontWeight: 700, lineHeight: 1.35 }}>《{title}》</div>
        <div style={{ fontSize: Math.max(9, w * 0.085), opacity: .72, marginTop: 5 }}>{author}</div>
      </div>
    </div>
  );
}

// ---------- 声波条 ----------
function Wave({ w = 46, h = 16, played = 0.55, style }) {
  const hs = [5, 8, 4, 11, 6, 13, 7, 10, 5, 12, 8, 6, 11, 5, 9, 7];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 2, width: w, height: h, ...style }}>
      {hs.map((v, idx) => (
        <span key={idx} style={{ width: 2, height: Math.round(h * v / 13), borderRadius: 1,
                                 background: idx / hs.length < played ? "var(--accent)" : "var(--line-2)" }} />
      ))}
    </div>
  );
}

// ---------- 悬浮播放 chip ----------
function PlayChip({ title, meta, style, className }) {
  return (
    <div className={className} style={{ background: "var(--surface)", borderRadius: 14, padding: "10px 14px",
         boxShadow: "var(--shadow-pop)", display: "flex", alignItems: "center", gap: 11, ...style }}>
      <span className="play-btn sm"><Icon name="play" size={14} style={{ marginLeft: 1 }} /></span>
      <div>
        <div style={{ fontSize: 12.5, fontWeight: 600 }}>{title}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
          <Wave w={44} h={12} />
          <span style={{ fontSize: 10.5, color: "var(--ink-3)" }}>{meta}</span>
        </div>
      </div>
    </div>
  );
}

// ---------- 导航 ----------
function TopNav({ auth = false, paper = false, active }) {
  const links = [
    { key: "make", label: "制作" },
    { key: "shelf", label: "书架" },
    { key: "discover", label: "发现", chevron: true },
    { key: "about", label: "关于" },
  ];
  return (
    <header className={"nav" + (paper ? " paper" : "")}>
      <a className="brand" href="#"><img src="logo.png" alt="" /><span>Book2TTS</span></a>
      <nav className="nav-links">
        {links.map((l) => (
          <a key={l.key} className={"nav-link" + (l.key === active ? " active" : "")} href="#">
            {l.label}{l.chevron && <Icon name="chevron" size={13} />}
          </a>
        ))}
      </nav>
      <div className="nav-right">
        {auth ? (
          <React.Fragment>
            <button className="icon-btn"><Icon name="sun" size={17} /></button>
            <div className="avatar">F</div>
          </React.Fragment>
        ) : (
          <React.Fragment>
            <a className="link-login" href="#">登录</a>
            <a className="btn-primary sm" href="#">免费注册</a>
          </React.Fragment>
        )}
      </div>
    </header>
  );
}

// ---------- 标准音频卡片（与画板 D 规格一致） ----------
function AudioCard({ cover, book, title, meta, coverW = 56 }) {
  return (
    <div className="card">
      <BookCover i={cover} title={book} author="有声书" w={coverW} radius={8} />
      <div className="card-body">
        <span className="badge-book">{book}</span>
        <div className="card-title">{title}</div>
        <div className="card-meta">{meta}</div>
      </div>
      <div className="card-actions">
        <button className="play-btn"><Icon name="play" size={17} style={{ marginLeft: 2 }} /></button>
        <button className="ghost-btn"><Icon name="dots" size={17} /></button>
      </div>
    </div>
  );
}

// ---------- 迷你播放条 ----------
function MiniPlayer() {
  return (
    <div className="mini">
      <BookCover i={0} title="夜航船" author="有声书" w={40} radius={6} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="mini-title">夜航船 · 第三章 江湖纪闻</div>
        <div className="mini-bar"><span style={{ width: "38%" }} /></div>
      </div>
      <div className="mini-ctrl">
        <button className="ghost-btn"><Icon name="skipBack" size={16} /></button>
        <button className="play-btn sm"><Icon name="pause" size={14} /></button>
        <button className="ghost-btn"><Icon name="skipFwd" size={16} /></button>
      </div>
    </div>
  );
}

// ================= A 访客首页 · 延续版 =================
function BoardGuestContinuity() {
  return (
    <div data-screen-label="访客首页 · 延续版" style={{ background: "var(--bg)", height: "100%" }}>
      <TopNav active="make" />
      <div className="hero">
        <div>
          <span className="eyebrow"><span className="dot" />在线 TTS · 有声书 · 播客 RSS</span>
          <h1 className="hero-title">把你的书，<br />变成<span className="hl">可以听</span>的书。</h1>
          <p className="hero-sub">上传 EPUB 或 PDF，自动分章、多音色朗读，生成属于你的有声书；一键产出播客 RSS，在任意播客 App 里收听。</p>
          <div className="cta-row">
            <a className="btn-primary" href="#">免费开始制作</a>
            <a className="btn-text" href="#">先听听公开作品 <Icon name="arrow" size={15} /></a>
          </div>
          <p className="trust">免费注册 · 支持中文多音色 · 章节与 SRT 字幕自动生成</p>
        </div>
        <div className="collage">
          <BookCover i={0} title="夜航船" author="张岱" w={190} radius={14}
                     style={{ position: "absolute", left: 34, top: 26, transform: "rotate(-7deg)", zIndex: 2 }} />
          <BookCover i={3} title="山茶文具店" author="小川糸" w={185} radius={14}
                     style={{ position: "absolute", left: 190, top: 60, transform: "rotate(5deg)", zIndex: 1 }} />
          <BookCover i={1} title="人类简史" author="尤瓦尔·赫拉利" w={200} radius={14}
                     style={{ position: "absolute", left: 108, top: 172, transform: "rotate(2deg)", zIndex: 3 }} />
          <PlayChip title="第三章 · 江湖纪闻" meta="12:40" className="b-chip"
                    style={{ position: "absolute", right: 6, bottom: 40, zIndex: 4 }} />
        </div>
      </div>
      <div className="section">
        <div className="section-head">
          <h2>最新公开作品</h2>
          <a className="btn-text" style={{ fontSize: 14 }} href="#">探索全部 <Icon name="arrow" size={14} /></a>
        </div>
        <div className="grid3">
          <AudioCard cover={1} book="人类简史" title="第一章 人类也是一种没有什么特别的动物" meta="今天 09:12 · 41 分钟" />
          <AudioCard cover={3} book="山茶文具店" title="代笔人序 · 鸠子写给祖母的信" meta="昨天 21:03 · 18 分钟" />
          <AudioCard cover={2} book="夜航西飞" title="第四章 北方的沙漠，城市的边缘" meta="3 天前 · 27 分钟" />
        </div>
      </div>
    </div>
  );
}

// ================= B 访客首页 · 大胆版 =================
function BoardGuestEditorial() {
  const strip = [
    { i: 0, title: "夜航船", author: "张岱", r: -5 },
    { i: 3, title: "山茶文具店", author: "小川糸", r: 3 },
    { i: 1, title: "人类简史", author: "尤瓦尔·赫拉利", r: -2 },
    { i: 4, title: "夜航西飞", author: "柏瑞尔·马卡姆", r: 4 },
    { i: 5, title: "万物有灵", author: "散文选", r: -3 },
    { i: 2, title: "城南旧事", author: "林海音", r: 2 },
  ];
  return (
    <div className="board-b" data-screen-label="访客首页 · 大胆版">
      <TopNav paper />
      <div className="b-wrap">
        <div className="b-kicker">BOOK2TTS · 文本转语音工坊</div>
        <h1 className="b-title">把一本书，<br />变成一档<span className="hl">可以订阅的节目</span>。</h1>
        <p className="b-sub">上传 EPUB 或 PDF，自动分章排版、多音色朗读；成书即成台——一键生成播客 RSS，在手机上像追更节目一样听完一本书。</p>
        <div className="b-cta">
          <a className="btn-primary" href="#">免费开始制作</a>
          <a className="btn-ghost" href="#">了解制作流程 <Icon name="arrow" size={15} /></a>
        </div>
      </div>
      <div className="strip">
        {strip.map((b, idx) => (
          <BookCover key={idx} i={b.i} title={b.title} author={b.author} w={158} radius={12}
                     style={{ marginLeft: idx === 0 ? 0 : -34, transform: `rotate(${b.r}deg)`,
                              zIndex: idx % 2 === 0 ? 2 : 1 }} />
        ))}
        <PlayChip title="夜航船 · 第一章" meta="正在播放"
                  style={{ marginLeft: -52, marginBottom: 120, zIndex: 6 }} />
      </div>
    </div>
  );
}

// ================= C 登录后首页 · 作品流 =================
function BoardLoggedIn() {
  return (
    <div data-screen-label="登录后首页 · 作品流" style={{ background: "var(--bg)", height: "100%", display: "flex", flexDirection: "column" }}>
      <TopNav auth active="make" />
      <div className="toolbar">
        <div>
          <h1>早上好，Fury</h1>
          <div className="sub">继续你的上一章，或者开始一本新书。</div>
        </div>
        <a className="btn-primary sm" style={{ marginLeft: "auto" }} href="#">
          <Icon name="plus" size={15} /> 制作新音频
        </a>
      </div>
      <div className="featured">
        <div className="card">
          <BookCover i={0} title="夜航船" author="有声书" w={84} radius={10} />
          <div className="card-body">
            <span className="badge-book">夜航船</span>
            <div className="card-title" style={{ fontSize: 19, marginTop: 9 }}>第三章 江湖纪闻</div>
            <div className="card-meta">上次听到 42% · 剩约 18 分钟</div>
            <div className="progress"><span style={{ width: "42%" }} /></div>
          </div>
          <div className="card-actions">
            <button className="play-btn lg"><Icon name="play" size={20} style={{ marginLeft: 2 }} /></button>
            <button className="ghost-btn"><Icon name="dots" size={17} /></button>
          </div>
        </div>
      </div>
      <div className="section" style={{ flex: 1 }}>
        <div className="section-head"><h2>我的作品</h2></div>
        <div className="grid3">
          <AudioCard cover={1} book="人类简史" title="第一章 人类也是一种没有什么特别的动物" meta="今天 09:12 · 已发布" />
          <AudioCard cover={3} book="山茶文具店" title="代笔人序 · 鸠子写给祖母的信" meta="昨天 21:03 · 已发布" />
          <AudioCard cover={2} book="夜航西飞" title="第四章 北方的沙漠，城市的边缘" meta="3 天前 · 草稿" />
        </div>
      </div>
      <MiniPlayer />
    </div>
  );
}

// ================= D 标准卡片 · 层级解剖 =================
function BoardAnatomy() {
  return (
    <div className="anatomy" data-screen-label="标准卡片 · 层级解剖" style={{ background: "#fff", height: "100%" }}>
      <h2>标准卡片 · 层级规则</h2>
      <div className="sub">回填 Django 模板时的规格：三个视觉簇，一个暖色焦点。</div>
      <div className="anatomy-grid">
        <div className="spec-card">
          <span className="pin" style={{ left: 84, top: 12 }}>1</span>
          <span className="pin" style={{ left: 84, top: 52 }}>2</span>
          <span className="pin" style={{ left: 84, top: 92 }}>3</span>
          <span className="pin" style={{ right: 2, top: 44 }}>4</span>
          <span className="pin" style={{ right: 2, top: 118 }}>5</span>
          <AudioCard cover={0} book="夜航船" title="第三章 江湖纪闻" meta="今天 09:12 · 41 分钟 · 已发布" coverW={72} />
          <div style={{ marginTop: 18, padding: "12px 16px", border: "1px dashed var(--line-2)", borderRadius: 12,
                        fontSize: 12.5, color: "var(--ink-3)", lineHeight: 1.7 }}>
            ⋯ 菜单内收纳：查看详情 / 下载字幕 / 查看 SRT / RSS 订阅此书 —— 卡片本体只保留两个动作。
          </div>
        </div>
        <div className="spec-list">
          <div className="spec-item"><span className="spec-num">1</span>
            <div><b>书名徽章 · 降权</b><p>由实心紫底白字降为描边小字（11px / 600 / 灰），归入元信息层。</p></div></div>
          <div className="spec-item"><span className="spec-num">2</span>
            <div><b>标题 · 第二层</b><p>16-17px / 700，是卡片的阅读起点；单行截断，完整标题进详情页。</p></div></div>
          <div className="spec-item"><span className="spec-num">3</span>
            <div><b>元信息 · 去图标</b><p>纯文字 + 「 · 」分隔（13px / 灰阶），删除日历等 FontAwesome 图标噪音。</p></div></div>
          <div className="spec-item"><span className="spec-num">4</span>
            <div><b>播放键 · 中心点</b><p>全站唯一暖色 accent（#ea580c），44px 圆形 + 投影，先被看到的一定是「播放」。</p></div></div>
          <div className="spec-item"><span className="spec-num">5</span>
            <div><b>次要操作 · 收纳</b><p>详情 / 字幕 / RSS 收进 ⋯ 菜单；每张卡的眼睛停留 ≤3 次。</p></div></div>
        </div>
      </div>
      <DCPostIt top={330} left={44} rotate={-2} width={230}>全页只允许一个暖色焦点——<br />让「播放」永远最先被看到。</DCPostIt>
    </div>
  );
}

// ================= E 访客首页 · 移动端 =================
function BoardMobile() {
  return (
    <div className="board-e" data-screen-label="访客首页 · 移动端">
      <div className="mnav">
        <a className="brand" href="#"><img src="logo.png" alt="" /><span>Book2TTS</span></a>
        <div className="nav-right" style={{ gap: 12 }}>
          <a className="link-login" style={{ fontSize: 13 }} href="#">登录</a>
          <a className="btn-primary sm" style={{ fontSize: 12.5, padding: "7px 13px" }} href="#">注册</a>
          <button className="icon-btn" style={{ width: 30, height: 30 }}><Icon name="menu" size={17} /></button>
        </div>
      </div>
      <div className="mhero">
        <span className="eyebrow"><span className="dot" />在线 TTS · 有声书 · 播客 RSS</span>
        <h1 className="hero-title">把你的书，<br />变成<span className="hl">可以听</span>的书。</h1>
        <p className="hero-sub">上传 EPUB 或 PDF，自动分章、多音色朗读，生成属于你的有声书。</p>
        <div className="mcta">
          <a className="btn-primary" href="#">免费开始制作</a>
          <a className="btn-text" href="#">先听听公开作品 <Icon name="arrow" size={14} /></a>
        </div>
      </div>
      <div className="mcover-wrap">
        <BookCover i={1} title="人类简史" author="尤瓦尔·赫拉利" w={158} radius={12} style={{ transform: "rotate(-3deg)" }} />
        <PlayChip title="第一章 · 人类也没什么特别" meta="41:20" className="mchip" />
      </div>
      <div className="msection">
        <div className="section-head">
          <h2>最新公开作品</h2>
          <a className="btn-text" style={{ fontSize: 13 }} href="#">全部 <Icon name="arrow" size={13} /></a>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <AudioCard cover={1} book="人类简史" title="第一章 人类也是一种没有什么特别的动物" meta="今天 09:12 · 41 分钟" coverW={48} />
          <AudioCard cover={3} book="山茶文具店" title="代笔人序 · 鸠子写给祖母的信" meta="昨天 21:03 · 18 分钟" coverW={48} />
        </div>
      </div>
    </div>
  );
}

// ================= F 设计系统 · Token 总览 =================
function Swatch({ color, name, note }) {
  return (
    <div>
      <div className="swatch" style={{ background: color, border: "1px solid var(--line)" }} />
      <div className="ds-label"><span style={{ color: "var(--ink)", fontWeight: 600 }}>{name}</span> · {note}</div>
    </div>
  );
}

function BoardDesignSystem() {
  return (
    <div className="anatomy" data-screen-label="设计系统 · Token 总览" style={{ background: "#fff", height: "100%" }}>
      <h2>设计系统 · Token 总览</h2>
      <div className="sub">回填 tailwind.config daisyUI 主题的依据；全站组件只允许使用这里的颜色与字阶。</div>
      <div className="ds-grid" style={{ marginTop: 26 }}>
        <div>
          <div className="ds-h">色彩</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <Swatch color="#7c3aed" name="primary" note="唯一主 CTA" />
            <Swatch color="#ea580c" name="accent" note="播放键专属 · 全页唯一暖色" />
            <Swatch color="#1c1917" name="ink" note="标题正文" />
            <Swatch color="#79716b" name="ink-3" note="元信息" />
            <Swatch color="#faf9f7" name="bg" note="页面底色" />
          </div>
        </div>
        <div>
          <div className="ds-h">书籍封面调色板（按书名 hash 取色）</div>
          <div style={{ display: "flex", gap: 10 }}>
            {PALETTE.map((p, i) => (
              <div key={i} className="swatch" style={{ background: `linear-gradient(155deg, ${p.bg}, ${p.deep})`, width: 52 }} />
            ))}
          </div>
          <div className="ds-label">6 色 muted 调色板 · 替换「全紫徽章」</div>
          <div className="ds-h" style={{ marginTop: 24 }}>字阶（六档）</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
            <div style={{ fontSize: 30, fontWeight: 800, lineHeight: 1.2 }}>大标题 30-46</div>
            <div style={{ fontSize: 20, fontWeight: 800 }}>标题 20</div>
            <div style={{ fontSize: 16, fontWeight: 700 }}>卡片标题 16</div>
            <div style={{ fontSize: 14, color: "var(--ink-2)", lineHeight: 1.5 }}>正文 14</div>
            <div style={{ fontSize: 13, color: "var(--ink-3)", lineHeight: 1.5 }}>元信息 13</div>
          </div>
        </div>
        <div>
          <div className="ds-h">组件</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 18, alignItems: "flex-start" }}>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span className="btn-primary sm">主按钮</span>
              <span className="btn-ghost" style={{ fontSize: 13, padding: "7px 14px" }}>次按钮</span>
              <span className="btn-text" style={{ fontSize: 13 }}>文字链 <Icon name="arrow" size={13} /></span>
            </div>
            <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
              <button className="play-btn lg"><Icon name="play" size={19} style={{ marginLeft: 2 }} /></button>
              <button className="play-btn"><Icon name="play" size={16} style={{ marginLeft: 2 }} /></button>
              <button className="play-btn sm"><Icon name="play" size={13} style={{ marginLeft: 1 }} /></button>
              <span className="ds-label" style={{ marginTop: 0 }}>播放键 52 / 44 / 36</span>
            </div>
            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <span className="badge-book">书名徽章</span>
              <span className="chip active">分类</span>
              <span className="chip">分类</span>
              <span className="tag pin">公告</span>
              <span className="tag ok">已发布</span>
              <span className="tag draft">草稿</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ================= G 探索页 =================
function BoardExplore() {
  return (
    <div data-screen-label="探索页" style={{ background: "var(--bg)", height: "100%" }}>
      <TopNav active="discover" />
      <div className="section" style={{ paddingTop: 34 }}>
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 20 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800 }}>探索</h1>
            <div style={{ fontSize: 14, color: "var(--ink-3)", marginTop: 6 }}>社区公开的有声书与对话作品，可直接收听。</div>
          </div>
          <div className="search"><Icon name="search" size={16} />搜索书名、标题或作者…</div>
        </div>
        <div className="chiprow" style={{ marginBottom: 22 }}>
          <span className="chip active">全部</span>
          <span className="chip">小说</span>
          <span className="chip">历史</span>
          <span className="chip">科幻</span>
          <span className="chip">散文</span>
          <span className="chip">英语学习</span>
        </div>
        <div className="grid3">
          <AudioCard cover={1} book="人类简史" title="第一章 人类也是一种没有什么特别的动物" meta="Fury · 41 分钟" />
          <AudioCard cover={3} book="山茶文具店" title="代笔人序 · 鸠子写给祖母的信" meta="Momo · 18 分钟" />
          <AudioCard cover={2} book="夜航西飞" title="第四章 北方的沙漠，城市的边缘" meta="Lao Wang · 27 分钟" />
          <AudioCard cover={0} book="夜航船" title="第三章 江湖纪闻" meta="Fury · 34 分钟" />
          <AudioCard cover={5} book="万物有灵" title="故乡的野菜" meta="小鹿 · 12 分钟" />
          <AudioCard cover={4} book="城南旧事" title="惠安馆 · 上" meta="阿禾 · 25 分钟" />
        </div>
      </div>
    </div>
  );
}

// ================= H 音频详情 · 播放页 =================
function BoardAudioDetail() {
  const chapters = [
    { n: 3, t: "第三章 江湖纪闻", d: "41:20", active: true },
    { n: 4, t: "第四章 奇技淫巧", d: "38:05" },
    { n: 5, t: "第五章 四方异闻", d: "44:12" },
    { n: 6, t: "第六章 舟车忆旧", d: "36:47" },
  ];
  return (
    <div data-screen-label="音频详情 · 播放页" style={{ background: "var(--bg)", height: "100%" }}>
      <TopNav active="discover" />
      <div className="section" style={{ paddingTop: 26 }}>
        <div className="crumb">探索 <Icon name="chevron" size={12} style={{ transform: "rotate(-90deg)" }} /> 夜航船 <Icon name="chevron" size={12} style={{ transform: "rotate(-90deg)" }} /> 第三章 江湖纪闻</div>
        <div className="detail-grid" style={{ marginTop: 24 }}>
          <div className="player-box">
            <BookCover i={0} title="夜航船" author="张岱" w={240} radius={14} />
            <div className="d-track"><span /><i /></div>
            <div className="d-time"><span>14:02</span><span>-27:18</span></div>
            <div className="big-ctrl">
              <button className="ghost-btn"><Icon name="skipBack" size={20} /></button>
              <button className="play-btn xl"><Icon name="play" size={24} style={{ marginLeft: 3 }} /></button>
              <button className="ghost-btn"><Icon name="skipFwd" size={20} /></button>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <span className="btn-ghost" style={{ fontSize: 13, padding: "8px 14px" }}>下载音频</span>
              <span className="btn-ghost" style={{ fontSize: 13, padding: "8px 14px" }}>下载字幕 SRT</span>
            </div>
          </div>
          <div>
            <span className="badge-book">夜航船</span>
            <h1 style={{ fontSize: 26, fontWeight: 800, marginTop: 10, lineHeight: 1.35 }}>第三章 江湖纪闻</h1>
            <div className="card-meta" style={{ marginTop: 8 }}>Fury 制作 · 41 分钟 · 3 天前更新</div>
            <p style={{ fontSize: 14.5, lineHeight: 1.85, color: "var(--ink-2)", marginTop: 14, maxWidth: "36em" }}>
              江湖纪闻一卷，记奇人异士、市井传说。本章从一位说书人的视角展开，讲述夜航船上的众生相……</p>
            <div className="tabs">
              <span className="tab active">章节 · 12</span>
              <span className="tab">字幕 SRT</span>
              <span className="tab">相似作品</span>
            </div>
            <div style={{ marginTop: 6 }}>
              {chapters.map((c) => (
                <div key={c.n} className={"ch-row" + (c.active ? " active" : "")}>
                  <span className="idx">{c.n}</span>
                  <span style={{ fontWeight: c.active ? 600 : 500 }}>{c.t}</span>
                  {c.active && <Wave w={40} h={14} />}
                  <span className="dur">{c.d}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ================= I 工作台 · 制作流程 =================
function RecentBook({ i, name, tag, tagCls, action }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 4px", borderBottom: "1px solid var(--line)" }}>
      <BookCover i={i} title={name} author="书籍" w={38} radius={6} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 14.5, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>《{name}》</div>
        <div style={{ marginTop: 4 }}><span className={"tag " + tagCls}>{tag}</span></div>
      </div>
      <span className="btn-text" style={{ fontSize: 13 }}>{action} <Icon name="arrow" size={13} /></span>
    </div>
  );
}

function BoardWorkbench() {
  return (
    <div data-screen-label="工作台 · 制作流程" style={{ background: "var(--bg)", height: "100%" }}>
      <TopNav active="make" />
      <div className="section" style={{ paddingTop: 30 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
          <h1 style={{ fontSize: 24, fontWeight: 800 }}>制作有声书</h1>
          <div className="steps">
            <span className="step active"><span className="n">1</span>上传书籍</span><span className="step"><span className="bar" /></span>
            <span className="step"><span className="n">2</span>选目录排版</span><span className="step"><span className="bar" /></span>
            <span className="step"><span className="n">3</span>选音色</span><span className="step"><span className="bar" /></span>
            <span className="step"><span className="n">4</span>生成</span>
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 24 }}>
          <div>
            <div className="dropzone">
              <div className="dz-icon"><Icon name="upload" size={24} /></div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "var(--ink)" }}>拖入 EPUB / PDF，或点击上传</div>
              <div style={{ fontSize: 13, color: "var(--ink-3)" }}>支持扫描 PDF（OCR 自动识别）· 单文件 ≤ 200MB</div>
              <span className="btn-primary sm" style={{ marginTop: 6 }}>选择文件</span>
            </div>
            <div style={{ marginTop: 16, fontSize: 13, color: "var(--ink-3)", lineHeight: 1.8 }}>
              上传后自动解析目录与章节；多音色对话脚本可在「选音色」一步为角色分配不同声音。</div>
          </div>
          <div style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--r-lg)", padding: "8px 18px", boxShadow: "var(--shadow-card)" }}>
            <div className="ds-h" style={{ marginTop: 12 }}>最近书籍</div>
            <RecentBook i={0} name="夜航船" tag="生成中 62%" tagCls="pin" action="查看队列" />
            <RecentBook i={1} name="人类简史" tag="已发布 12 集" tagCls="ok" action="继续制作" />
            <RecentBook i={4} name="城南旧事" tag="草稿" tagCls="draft" action="继续制作" />
            <div style={{ height: 10 }} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ================= J 讨论区 =================
function TopicRow({ i, name, title, ex, tag, tagCls, replies, views, time }) {
  return (
    <div className="topic">
      <div className="topic-avatar" style={{ background: PALETTE[i % 6].bg }}>{name}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="topic-title">
          {tag && <span className={"tag " + tagCls}>{tag}</span>}
          {title}
        </div>
        <div className="topic-ex">{ex}</div>
      </div>
      <div className="topic-meta"><span>回复 {replies}</span><span>查看 {views}</span><span>{time}</span></div>
    </div>
  );
}

function BoardDiscussions() {
  return (
    <div data-screen-label="讨论区" style={{ background: "var(--bg)", height: "100%" }}>
      <TopNav active="discover" />
      <div className="section" style={{ paddingTop: 34 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 800 }}>讨论区</h1>
            <div style={{ fontSize: 14, color: "var(--ink-3)", marginTop: 6 }}>制作技巧、音色经验与反馈建议。</div>
          </div>
          <span className="btn-primary sm"><Icon name="plus" size={14} /> 发起讨论</span>
        </div>
        <div className="chiprow" style={{ marginBottom: 10 }}>
          <span className="chip active">全部</span><span className="chip">综合</span><span className="chip">技术交流</span>
          <span className="chip">反馈建议</span><span className="chip">求助问答</span><span className="chip">公告</span>
        </div>
        <TopicRow i={2} name="官" tag="公告" tagCls="pin" title="Book2TTS 新增播客 RSS 与章节标注支持"
                  ex="现在每本书都可以生成独立 RSS，字幕与章节文件随音频一起产出……"
                  replies="23" views="1.4k" time="2 小时前" />
        <TopicRow i={1} name="Momo" title="扫描版 PDF 的 OCR 识别准确率怎么提高？"
                  ex="古籍书扫描件直出乱码比较多，试试先调对比度再上传……"
                  replies="8" views="402" time="5 小时前" />
        <TopicRow i={5} name="Lao Wang" title="多音色对话脚本：只换一个角色的音色，会全部重新计费吗？"
                  ex="如题，只改了一个角色的声音，还是全部章节都要重新生成……"
                  replies="4" views="156" time="昨天" />
        <TopicRow i={3} name="小鹿" title="反馈：移动端播放器希望支持倍速"
                  ex="通勤时用 1.5 倍听书，现在的播放条没有倍速按钮……"
                  replies="12" views="630" time="昨天" />
      </div>
    </div>
  );
}

// ================= F2 制作台 · 三栏工作区 =================
function ToolBtn({ icon, label, active }) {
  return (
    <span className={"btn btn-ghost btn-xs rounded-lg" + (active ? " text-primary" : "")}
          style={{ height: 26, minHeight: 26, fontSize: 12 }}>
      <Icon name={icon} size={12} />{label}
    </span>
  );
}

function TocItem({ icon, label, depth, active, checked, count }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 7, padding: "6px 8px", borderRadius: 8,
                  background: active ? "var(--accent-tint)" : "transparent",
                  borderLeft: active ? "3px solid var(--accent)" : "3px solid transparent",
                  paddingLeft: 8 + depth * 14, cursor: "pointer" }}>
      <span style={{ width: 13, height: 13, borderRadius: 3, border: checked ? "none" : "1.5px solid var(--line-2)",
                     background: checked ? "var(--primary)" : "transparent", color: "#fff",
                     display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, flexShrink: 0 }}>
        {checked ? "✓" : ""}
      </span>
      <span style={{ color: active ? "var(--accent-deep)" : icon === "folder" ? "var(--primary)" : "var(--ink-3)", flexShrink: 0 }}>
        <Icon name={icon === "folder" ? "chevron" : "file"} size={11} />
      </span>
      <span style={{ fontSize: 12.5, fontWeight: active ? 600 : 400, color: active ? "var(--accent-deep)" : "var(--ink-2)",
                     flex: 1, minWidth: 0, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{label}</span>
      {count && <span style={{ fontSize: 10, color: "var(--ink-3)", flexShrink: 0 }}>{count}</span>}
    </div>
  );
}

function BoardWorkbench3Pane() {
  return (
    <div data-screen-label="制作台 · 三栏工作区" style={{ background: "var(--bg)", height: "100%", display: "flex", flexDirection: "column" }}>
      {/* 顶栏 */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 16px", background: "var(--surface)", borderBottom: "1px solid var(--line)" }}>
        <span style={{ fontSize: 15, fontWeight: 800 }}>《夜航船》</span>
        <span style={{ fontSize: 12, color: "var(--ink-3)" }}>制作台</span>
        <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--ink-3)" }}>自动保存 · 刚刚</span>
      </div>
      {/* 三栏 */}
      <div style={{ flex: 1, display: "flex", gap: 10, padding: 10, minHeight: 0 }}>
        {/* 左：目录树 */}
        <div style={{ width: 258, flexShrink: 0, display: "flex", flexDirection: "column", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 12, overflow: "hidden" }}>
          <div style={{ display: "flex", borderBottom: "1px solid var(--line)", padding: "0 8px" }}>
            <span style={{ padding: "9px 10px", fontSize: 12.5, fontWeight: 700, color: "var(--primary-deep)", boxShadow: "inset 0 -2px 0 var(--primary)" }}>目录 · 48</span>
            <span style={{ padding: "9px 10px", fontSize: 12.5, color: "var(--ink-3)" }}>页面 · 210</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "7px 10px", borderBottom: "1px solid var(--line)" }}>
            <span style={{ fontSize: 11.5, color: "var(--ink-3)", fontWeight: 600, flexShrink: 0, whiteSpace: "nowrap" }}>已选 3 项</span>
            <div style={{ display: "flex", gap: 4, marginLeft: "auto" }}>
              <span className="btn btn-ghost btn-xs" style={{ height: 22, minHeight: 22, fontSize: 11, padding: "0 7px", whiteSpace: "nowrap", flexShrink: 0 }}>全选</span>
              <span className="btn btn-ghost btn-xs" style={{ height: 22, minHeight: 22, fontSize: 11, padding: "0 7px", whiteSpace: "nowrap", flexShrink: 0 }}>清除</span>
              <span className="btn btn-xs bg-primary hover:bg-primary-focus border-none text-primary-content" style={{ height: 22, minHeight: 22, fontSize: 11, padding: "0 8px", whiteSpace: "nowrap", flexShrink: 0 }}>加载选中</span>
            </div>
          </div>
          <div style={{ flex: 1, overflow: "hidden", padding: 6 }}>
            <TocItem icon="folder" label="第一卷 叙列系" depth={0} count="6" />
            <TocItem icon="file" label="第一章 天文纪" depth={1} />
            <TocItem icon="file" label="第二章 地理纪" depth={1} />
            <TocItem icon="folder" label="第二卷 物产纪" depth={0} count="9" />
            <TocItem icon="file" label="第一章 江湖纪闻" depth={1} active checked />
            <TocItem icon="file" label="第二章 奇技泄巧" depth={1} checked />
            <TocItem icon="file" label="第三章 四方异闻" depth={1} checked />
            <TocItem icon="file" label="第四章 舟车忆旧" depth={1} />
            <TocItem icon="folder" label="第三卷 快园记" depth={0} count="4" />
          </div>
        </div>
        {/* 中：阅读区 */}
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 12, overflow: "hidden" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 14px", borderBottom: "1px solid var(--line)", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
              <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600, whiteSpace: "nowrap" }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--accent)" }} />第三章 江湖纪闻
              </span>
              <span style={{ fontSize: 11.5, color: "var(--ink-3)", border: "1px solid var(--line-2)", borderRadius: 999, padding: "1px 8px", flexShrink: 0 }}>3,240 字</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 2, flexShrink: 0 }}>
              <ToolBtn icon="eye" label="查看原文" />
              <span style={{ width: 1, height: 14, background: "var(--line)", margin: "0 4px" }} />
              <ToolBtn icon="type" label="自动排版" />
              <ToolBtn icon="globe" label="翻译" />
              <ToolBtn icon="plus" label="" />
              <ToolBtn icon="menu" label="" />
            </div>
          </div>
          <div style={{ flex: 1, overflow: "hidden", padding: "22px 34px", fontFamily: 'Georgia, "Songti SC", serif' }}>
            <p style={{ fontSize: 15, fontWeight: 700, color: "var(--ink)", marginBottom: 12 }}>第三章 江湖纪闻</p>
            <p style={{ fontSize: 14, lineHeight: 1.95, color: "var(--ink-2)", marginBottom: 10 }}>江湖之上，舟车相望，奇人异士多出于其间。说书者每及此卷，辄眉飞色舞，听者忘倦。</p>
            <p style={{ fontSize: 14, lineHeight: 1.95, color: "var(--ink-2)" }}>余尝夜泊瓜洲，闻邻舟有客谈剑仙事，音节朗朗，若出金石。起而视之，惟见月色满江，橹声欸乃而已……</p>
          </div>
        </div>
        {/* 右：制作配置 */}
        <div style={{ width: 264, flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 12, padding: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--ink-3)", letterSpacing: 1, marginBottom: 8 }}>当前章节</div>
            <div style={{ fontSize: 13, fontWeight: 600 }}>第三章 江湖纪闻</div>
            <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
              <span className="tag ok">本页已生成</span>
              <span className="tag draft">全书 12/48</span>
            </div>
          </div>
          <div style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 12, padding: 12, flex: 1, overflow: "hidden" }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--ink-3)", letterSpacing: 1, marginBottom: 8 }}>合成配置</div>
            <div style={{ border: "1px solid var(--line-2)", borderRadius: 8, padding: "7px 10px", fontSize: 12.5, display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <span>云希 · 男声</span><Icon name="chevron" size={12} style={{ color: "var(--ink-3)" }} />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <span style={{ fontSize: 11.5, color: "var(--ink-2)", flexShrink: 0 }}>语速</span>
              <div style={{ flex: 1, height: 4, borderRadius: 2, background: "var(--line)", position: "relative" }}>
                <span style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: "50%", background: "var(--accent)", borderRadius: 2 }} />
                <span style={{ position: "absolute", left: "50%", top: "50%", width: 11, height: 11, borderRadius: "50%", background: "#fff", border: "2.5px solid var(--accent)", transform: "translate(-50%,-50%)" }} />
              </div>
              <span style={{ fontSize: 11.5, color: "var(--ink-3)", width: 30, textAlign: "right" }}>100%</span>
            </div>
            <div style={{ border: "1px solid var(--line-2)", borderRadius: 8, padding: "7px 10px", fontSize: 12, color: "var(--ink-3)", marginBottom: 12 }}>音频标题（选填）</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <span className="btn btn-ghost btn-sm rounded-lg" style={{ fontSize: 12.5, border: "1px solid var(--line-2)", whiteSpace: "nowrap" }}><Icon name="wave" size={12} />生成多角色音频</span>
              <span className="btn btn-sm rounded-xl bg-primary hover:bg-primary-focus border-none text-primary-content" style={{ fontSize: 12.5, whiteSpace: "nowrap" }}><Icon name="wave" size={11} />合成音频</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ================= F3 脚本编辑器 =================
function SegSpeaker({ color, name, voice }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ width: 7, height: 7, borderRadius: "50%", background: color }} />
      <span style={{ fontSize: 12.5, fontWeight: 700, color }}>{name}</span>
      {voice && <span style={{ fontSize: 10, border: "1px solid var(--line-2)", borderRadius: 999, padding: "1px 7px", color: "var(--ink-3)" }}>{voice}</span>}
    </div>
  );
}

function BoardDialogueEditor() {
  return (
    <div data-screen-label="脚本编辑器" style={{ background: "var(--bg)", height: "100%", display: "flex", flexDirection: "column" }}>
      {/* 页头 */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, padding: "18px 24px 14px" }}>
        <div style={{ minWidth: 0 }}>
          <span className="badge-book">夜航船</span>
          <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: "-0.3px", marginTop: 8, lineHeight: 1.3 }}>夜航船 · 第一章 广播剧脚本</h1>
          <p style={{ fontSize: 12.5, color: "var(--ink-3)", marginTop: 5 }}>12 段 · 2 个角色 · 创建于 2025-01-12</p>
        </div>
        <div style={{ display: "flex", gap: 8, flexShrink: 0, alignItems: "center" }}>
          <span className="btn btn-ghost btn-sm rounded-lg" style={{ fontSize: 13, color: "var(--error)" }}><Icon name="skipBack" size={12} />删除</span>
          <span className="btn btn-ghost btn-sm rounded-lg" style={{ fontSize: 13 }}><Icon name="type" size={12} />编辑</span>
          <span className="btn btn-sm rounded-xl bg-primary hover:bg-primary-focus border-none text-primary-content" style={{ fontSize: 13 }}><Icon name="arrow" size={12} />发布音频</span>
        </div>
      </div>
      {/* 双栏 */}
      <div style={{ flex: 1, display: "flex", gap: 12, padding: "0 24px 20px", minHeight: 0 }}>
        {/* 对话内容 */}
        <div style={{ flex: 2, minWidth: 0, display: "flex", flexDirection: "column", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 14, overflow: "hidden" }}>
          <div style={{ padding: "12px 18px", borderBottom: "1px solid var(--line)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 14, fontWeight: 700 }}>对话内容</span>
            <span style={{ fontSize: 11.5, color: "var(--ink-3)" }}>悬停段落可预听 / 编辑</span>
          </div>
          <div style={{ flex: 1, overflow: "hidden", padding: 14, display: "flex", flexDirection: "column", gap: 9 }}>
            <div style={{ background: "var(--bg)", borderRadius: 10, padding: "10px 14px" }}>
              <SegSpeaker color="#a8a29e" name="旁白" />
              <p style={{ fontSize: 13, lineHeight: 1.8, color: "var(--ink-2)", marginTop: 5 }}>江湖之上，舟车相望，奇人异士多出于其间。</p>
            </div>
            <div style={{ background: "var(--accent-tint)", borderRadius: 10, padding: "10px 14px", border: "1px solid #f9d3ba" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <SegSpeaker color="#ea580c" name="鸭子" voice="晓晓 · 女声" />
                <div style={{ display: "flex", alignItems: "center", gap: 8, opacity: 1 }}>
                  <span style={{ fontSize: 10.5, color: "var(--ink-3)" }}>#07</span>
                  <span className="play-btn sm" style={{ width: 26, height: 26 }}><Icon name="play" size={10} style={{ marginLeft: 1 }} /></span>
                  <span className="ghost-btn" style={{ width: 24, height: 24 }}><Icon name="file" size={12} /></span>
                </div>
              </div>
              <p style={{ fontSize: 13, lineHeight: 1.8, color: "var(--ink)", marginTop: 5 }}>客言：此剑仙也，非烈士，盖有通天之术。</p>
            </div>
            <div style={{ background: "var(--bg)", borderRadius: 10, padding: "10px 14px" }}>
              <SegSpeaker color="#a8a29e" name="旁白" />
              <p style={{ fontSize: 13, lineHeight: 1.8, color: "var(--ink-2)", marginTop: 5 }}>余闻而异之，起而视之，惥见月色满江。</p>
            </div>
            <div style={{ background: "var(--surface)", borderRadius: 10, padding: "10px 14px", border: "1px dashed var(--line-2)" }}>
              <SegSpeaker color="#5b9fc0" name="容儿" voice="云希 · 男声" />
              <p style={{ fontSize: 13, lineHeight: 1.8, color: "var(--ink-3)", marginTop: 5, fontStyle: "italic" }}>点击编辑此段台词……</p>
            </div>
          </div>
        </div>
        {/* 角色音色 */}
        <div style={{ width: 300, flexShrink: 0, display: "flex", flexDirection: "column", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 14, overflow: "hidden" }}>
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--line)", fontSize: 14, fontWeight: 700 }}>角色音色</div>
          <div style={{ flex: 1, padding: 12, display: "flex", flexDirection: "column", gap: 10, overflow: "hidden" }}>
            {[{ c: "#ea580c", n: "鸭子", v: "晓晓 · 女声" }, { c: "#5b9fc0", n: "容儿", v: "云希 · 男声" }].map((r, i) => (
              <div key={i} style={{ border: "1px solid var(--line)", borderRadius: 10, padding: 11 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ width: 26, height: 26, borderRadius: "50%", background: r.c, color: "#fff", fontSize: 11, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>{r.n[0]}</span>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{r.n}</span>
                  <span className="play-btn sm" style={{ marginLeft: "auto", width: 26, height: 26 }}><Icon name="play" size={10} style={{ marginLeft: 1 }} /></span>
                </div>
                <div style={{ marginTop: 9, border: "1px solid var(--line-2)", borderRadius: 7, padding: "5px 9px", fontSize: 11.5, display: "flex", justifyContent: "space-between", alignItems: "center", color: "var(--ink-2)" }}>
                  {r.v}<Icon name="chevron" size={11} style={{ color: "var(--ink-3)" }} />
                </div>
              </div>
            ))}
          </div>
          <div style={{ padding: 12, borderTop: "1px solid var(--line)", display: "flex", gap: 8 }}>
            <span className="btn btn-ghost btn-sm rounded-lg" style={{ flex: 1, fontSize: 12.5, border: "1px solid var(--line-2)", whiteSpace: "nowrap" }}><Icon name="play" size={11} />试听全部</span>
            <span className="btn btn-sm rounded-xl bg-primary hover:bg-primary-focus border-none text-primary-content" style={{ flex: 1.4, fontSize: 12.5, whiteSpace: "nowrap" }}><Icon name="wave" size={11} />合成音频</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ================= App =================
function B2TApp() {
  return (
    <DesignCanvas>
      <DCSection id="guest" title="访客首页" subtitle="推荐方向 A · B 仅作手法参考">
        <DCArtboard id="a" label="A · 延续版 ★ 推荐" width={1440} height={880}><BoardGuestContinuity /></DCArtboard>
        <DCArtboard id="b" label="B · 大胆版（参考）" width={1440} height={780}><BoardGuestEditorial /></DCArtboard>
        <DCArtboard id="e" label="E · 移动端" width={390} height={900}><BoardMobile /></DCArtboard>
      </DCSection>
      <DCSection id="app" title="登录后 & 组件规格" subtitle="作品流布局 + 回填模板用的卡片规则">
        <DCArtboard id="c" label="C · 登录后作品流" width={1440} height={780}><BoardLoggedIn /></DCArtboard>
        <DCArtboard id="d" label="D · 卡片解剖" width={1040} height={500}><BoardAnatomy /></DCArtboard>
        <DCArtboard id="f" label="F · 设计系统" width={1240} height={520}><BoardDesignSystem /></DCArtboard>
      </DCSection>
      <DCSection id="content" title="内容页原型" subtitle="所有列表页 / 详情页复用同一套卡片与播放组件">
        <DCArtboard id="g" label="G · 探索页" width={1440} height={620}><BoardExplore /></DCArtboard>
        <DCArtboard id="h" label="H · 播放详情页" width={1440} height={780}><BoardAudioDetail /></DCArtboard>
      </DCSection>
      <DCSection id="tools" title="工具 & 社区原型" subtitle="工作台代表全部制作流程页；讨论区代表社区页">
        <DCArtboard id="i" label="I · 工作台 · 制作" width={1440} height={640}><BoardWorkbench /></DCArtboard>
        <DCArtboard id="j" label="J · 讨论区" width={1440} height={700}><BoardDiscussions /></DCArtboard>
      </DCSection>
      <DCSection id="editor" title="应用型界面" subtitle="制作台三栏 & 脚本编辑器 · 只换 class 不动 htmx 结构">
        <DCArtboard id="f2" label="F2 · 制作台三栏" width={1440} height={760}><BoardWorkbench3Pane /></DCArtboard>
        <DCArtboard id="f3" label="F3 · 脚本编辑器" width={1440} height={700}><BoardDialogueEditor /></DCArtboard>
      </DCSection>
    </DesignCanvas>
  );
}

Object.assign(window, { B2TApp });
