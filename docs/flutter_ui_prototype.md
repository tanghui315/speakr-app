# EchoMind Flutter 界面原型方案

## 1. 设计基调
- **主色 `#5840FF`**：按钮、主操作、录音状态指示，配合 8dp 圆角，体现专业科技感。
- **高亮 `#21C5E5` 渐变**：实时字幕高亮、连接状态条；与主色组成纵向或对角渐变背景。
- **辅助色 `#FFC857`**：额度提醒、提示 Banner、订阅动效。
- **浅背景 `#F4F5F9` / 深背景 `#101321`**：分别用于日间/夜间主题，整体留白充足。
- **文字颜色**：正文 `#1F2430`，次要文字 `#6B7280`，禁用/分隔线使用 12% 黑。
- **字体**：SF Pro / Noto Sans（自动随系统语言切换），字号从 12–32，间距遵循 4pt 栅格。

## 2. 组件体系
- **顶栏**：透明渐变背景 + 高亮连接指示；右侧头像/设置入口、左侧返回或 Logo。
- **主操作按钮**：浮动底部或中部圆形录音按钮，默认主色填充、录制中渐变动画。
- **卡片**：录音、AI 建议、额度提示等采用阴影 DP=2、圆角 12。
- **标签与过滤器**：Chip 风格，选中主色描边填充，高亮色 hover 动画。
- **底部导航**：四栏（主页、库、AI、设置）；活跃项使用主色线条与图标填充。
- **实时字幕气泡**：圆角矩形背景（浅背景下为白，深背景下为深色），当前语句高亮边框。

## 3. 核心界面草图

### 3.1 启动与认证
```
[Splash Screen]
- 上半部渐变背景 (5840FF→21C5E5)，中央 EchoMind 标志
- 下部展示“回声智心 | EchoMind”字样与加载动画

[登录选择]
- 顶栏文字：欢迎回来
- 卡片容纳 Apple/Google/邮箱登录按钮
- 底部显示隐私链接与语言切换 (中/EN)

[生物识别解锁]
- 模态底部弹窗，展示 FaceID 图标 + 副标题
```

### 3.2 主页 / 录音仪表盘
```
Top App Bar: 左侧 Logo，右侧额度计数器(主色描边)
Body:
1. CTA 区域：中央浮动录音按钮 (圆形、渐变动效)
   - 按钮下方显示 "Tap to start" / "点按录音"
2. 状态卡：列出实时字幕服务、后端连接状态 (使用高亮色指示灯)
3. 快捷入口：录音库、AI Inquire、订阅（卡片布局）
Bottom Nav: Home / Library / AI / Settings
```

### 3.3 录音进行中
```
背景：深色模糊 + 渐变上叠
Top Bar: 显示录音时长、网络状态、关闭按钮
Main Panel:
- 实时波形占据上半部 (just_audio + 自绘波形)，主色线条
- 字幕流：气泡自上而下滚动，当前语句主色高亮，已确认语句浅灰
- 置信度/延迟指示条 (高亮色)
Controls:
- 中央暂停/继续按钮 (主色 → 黄色渐变表示暂停)
- 左侧标记按钮、右侧添加标签按钮
- 底部显示当前剩余免费分钟数
```

### 3.4 录音库
```
列表头：搜索框 (圆角 12)、过滤 Chip (标签/日期/状态)
列表项：
- 左侧缩略波形 + 状态图标
- 标题 + 时间 + 时长
- 标签集合横向滚动
滑动手势：左滑收藏/标记、右滑删除
```

### 3.5 录音详情
```
Header: 波形可视化背景 + 播放控制浮层
Tabs:
1. Transcript（默认）: 按说话人折叠，支持高亮段落
2. Summary: AI 摘要卡片，主色标题 + 黄色提示点
3. Events: 时间线视图，事件可导出
Side Actions (顶部右侧): 分享、标签管理、删除
底部固定条：AI 聊天入口 (文本域 + 发送按钮)
```

### 3.6 AI 交互
```
Top Bar: "EchoMind AI" + 历史记录按钮
Body:
- 会话列表卡片：用户消息右对齐，主色背景白字
- AI 回复左对齐，浅背景卡片 + 引用链接标签
- 输入区域：文本域 + 附件/过滤器按钮（标签筛选）
- 推荐问题 Chips (高亮描边)
```

### 3.7 订阅与用量
```
Quota 卡片：渐变背景，展示剩余分钟环形图 (主色填充)
Plan 卡片：月订阅方案，主色按钮 + 黄色提示“热销”
历史记录：列表，浅灰分隔线
IAP 成功后，顶部展示绿色通知条
```

### 3.8 设置与诊断
```
Section List：
- 账户与安全 (设备管理、密码重置)
- 偏好设置 (语言切换、中英文、主题切换)
- 缓存与存储 (展示占用，提供清理)
- 诊断 (ASR 状态、版本号、日志上传)
列表项右侧使用次要文字 + Chevron
```

### 3.9 分享深链视图
```
渐变顶部条 + 分享者信息
录音摘要卡片 → 可折叠展开全文
播放控件固定底部，提供下载、反馈按钮
```

## 4. 交互与动效
- 录音按钮按下放大 1.1 倍并带脉冲，停止后渐变退去。
- 实时字幕行出现时淡入+向上轻微浮动，最终句子形成时主色边框闪烁。
- 列表滑动操作带震动反馈。
- 主题切换时采用 200ms 淡入动画。

## 5. 适配与无障碍
- 采用 4 列栅格以保证 iPhone mini 及常规机型兼容，Android 需验证 18:9 屏。
- 文本与背景对比度 >= 4.5：1；考虑 VoiceOver/TalkBack 标签。
- 关键按钮支持长按语音播报提醒，录音中提供可视与听觉反馈。

## 6. 原型交付
- 可在 Figma 以 Design Token 方式记录颜色、阴影、字号。
- 迭代顺序：先输出 Alpha 阶段关键界面（主页、录音中、字幕流），再扩展录音详情和 AI 交互。
- 建议准备浅色/深色两套主界面，方便开发时切换主题。

## 7. 效果图建议与 AI 生成提示
- **启动与登录界面效果图**：呈现渐变启动页与登录选项，展示品牌与双语切换。
- **主页仪表盘效果图**：突出录音主按钮、状态卡与快捷入口，体现主色渐变。
- **录音进行中效果图**：展示波形、实时字幕流、置信度与延迟指示。
- **录音详情/AI 摘要效果图**：显示转录、摘要、事件 Tab 与标签管理。
- **AI 对话界面效果图**：左右分隔的对话气泡、引用链接、推荐问题 Chip。
- **订阅与额度效果图**：渐变额度卡 + 订阅方案，强调黄色提示与 CTA。
- **宣传海报/横幅**：用于官方渠道的亮色渐变宣传图，包含“回声智心”与 EchoMind 品牌。
- **品牌 Logo 元素**：包含 EchoMind 字母组合与声波/脑波符号，用于应用图标与宣传物料。

AI 生成提示词示例：
- `Generate a high-fidelity mobile app splash screen for an AI voice assistant named EchoMind, featuring a diagonal gradient from #5840FF to #21C5E5, minimalist logo in the center, bilingual tagline “回声智心 | EchoMind”, dark textured background, sleek futuristic style.`
- `Design a mobile home dashboard for an AI-powered recording app showing a large circular record button with pulsing gradient, status cards for live captions, quick access tiles for Library / AI / Subscription, soft shadows, color palette #5840FF, #21C5E5, #F4F5F9.`
- `Create a mobile UI mockup of an active recording screen with real-time waveform in purple tones, caption bubbles streaming upward, latency and confidence indicators using cyan highlights, semi-transparent dark background, modern flat design.`
- `Produce a mobile screen showing transcript tabs (Transcript, Summary, Events) with wave visualization header, tags, AI summary cards in EchoMind brand colors, clean typography, Noto Sans style.`
- `Illustrate an AI chat interface in a voice insights app, user messages right-aligned with purple gradient bubbles, AI replies left-aligned on light cards with citation chips, include quick question chips, overall palette violet and cyan accents.`
- `Design a subscription management screen for a mobile AI transcription app featuring a gradient quota card with circular progress, pricing cards with yellow highlight labels, white background, rounded corners, soft shadows.`
- `Create a marketing banner for “EchoMind 回声智心” showcasing a smartphone mockup with live captions, gradient background in purple-cyan, tagline “AI 语音洞察助手”, contemporary tech aesthetic.`
- `Design a minimalistic logo for EchoMind, combining the letter E with a stylized soundwave or neural pulse motif, color palette #5840FF and #21C5E5, suitable for app icon and brand mark.`
