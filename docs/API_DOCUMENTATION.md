# Speakr API 接口文档

## 概述

Speakr 是一个自托管的AI转录和智能笔记平台。本文档详细描述了所有可用的API接口。

**基础信息:**
- 基础URL: `http://localhost:8899`
- 认证方式: Session-based authentication
- 数据格式: JSON
- CSRF保护: 需要在请求头中包含CSRF token

---

## 认证相关 🔐

### 用户注册
```http
POST /register
```

**请求参数:**
- `username` (string, required): 用户名
- `email` (string, required): 邮箱地址  
- `password` (string, required): 密码

**响应:**
- 成功: 重定向到登录页面
- 失败: 返回错误信息

---

### 用户登录
```http
POST /login
```

**请求参数:**
- `email` (string, required): 邮箱地址
- `password` (string, required): 密码

**响应:**
```json
{
  "success": true,
  "redirect_url": "/"
}
```

---

### 用户登出
```http
GET /logout
```

**响应:** 重定向到登录页面

---

## 系统信息 ⚙️

### 获取系统信息
```http
GET /api/system/info
```

**响应:**
```json
{
  "version": "0.5.6",
  "llm_endpoint": "https://openrouter.ai/api/v1",
  "llm_model": "openai/gpt-4o-mini",
  "whisper_endpoint": "https://api.openai.com/v1",
  "asr_enabled": true,
  "asr_endpoint": "http://whisper-asr:9000"
}
```

---

### 获取CSRF令牌
```http
GET /api/csrf-token
```

**响应:**
```json
{
  "csrf_token": "IjY2M2Y4ZDk5NmY5MjA4MzI5YjEwZTAzNmM4ZGI3ZGI4ODc3OTRhNGUi..."
}
```

---

## 录音管理 📁

### 获取录音列表
```http
GET /api/recordings
```

**查询参数:**
- `page` (int, optional): 页码，默认1
- `per_page` (int, optional): 每页条数，默认25，最大100
- `q` (string, optional): 搜索查询，支持特殊语法:
  - `date:2024-01-01` - 按日期筛选
  - `date_from:2024-01-01` - 开始日期
  - `date_to:2024-12-31` - 结束日期
  - `tag:meeting` - 按标签筛选

**响应:**
```json
{
  "recordings": [
    {
      "id": 1,
      "title": "Meeting with Team",
      "duration": 1800,
      "created_at": "2024-01-01T10:00:00Z",
      "status": "COMPLETED",
      "transcription": "会议内容转录...",
      "summary": "会议摘要...",
      "tags": ["meeting", "team"]
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 25,
    "total": 100,
    "pages": 4
  }
}
```

---

### 上传音频文件
```http
POST /upload
```

**请求类型:** `multipart/form-data`

**请求参数:**
- `audio` (file, required): 音频文件
- `title` (string, optional): 录音标题
- `language` (string, optional): 转录语言代码
- `tag_id` (int, optional): 关联标签ID
- `min_speakers` (int, optional): 最少说话人数
- `max_speakers` (int, optional): 最多说话人数

**响应:**
```json
{
  "success": true,
  "recording_id": 123,
  "message": "文件上传成功，正在处理中..."
}
```

---

### 获取录音状态
```http
GET /status/{recording_id}
```

**路径参数:**
- `recording_id` (int): 录音ID

**响应:**
```json
{
  "status": "PROCESSING",
  "progress": 45,
  "message": "正在转录音频...",
  "error": null
}
```

**状态值:**
- `PENDING`: 等待处理
- `PROCESSING`: 处理中
- `COMPLETED`: 完成
- `FAILED`: 失败

---

### 删除录音
```http
DELETE /recording/{recording_id}
```

**路径参数:**
- `recording_id` (int): 录音ID

**响应:**
```json
{
  "success": true,
  "message": "录音删除成功"
}
```

---

### 获取音频文件
```http
GET /audio/{recording_id}
```

**路径参数:**
- `recording_id` (int): 录音ID

**响应:** 返回音频文件流

---

## 转录处理 📝

### 生成摘要
```http
POST /recording/{recording_id}/generate_summary
```

**路径参数:**
- `recording_id` (int): 录音ID

**请求参数:**
```json
{
  "language": "zh",
  "custom_prompt": "请重点关注会议决策和行动项目"
}
```

**响应:**
```json
{
  "success": true,
  "summary": "生成的摘要内容...",
  "processing_time": 12.5
}
```

---

### 更新说话人信息
```http
POST /recording/{recording_id}/update_speakers
```

**路径参数:**
- `recording_id` (int): 录音ID

**请求参数:**
```json
{
  "speakers": {
    "SPEAKER_00": "张三",
    "SPEAKER_01": "李四"
  }
}
```

**响应:**
```json
{
  "success": true,
  "message": "说话人信息更新成功"
}
```

---

### 自动识别说话人
```http
POST /recording/{recording_id}/auto_identify_speakers
```

**路径参数:**
- `recording_id` (int): 录音ID

**响应:**
```json
{
  "success": true,
  "identified_speakers": {
    "SPEAKER_00": "John Smith",
    "SPEAKER_01": "Jane Doe"
  }
}
```

---

### 重新转录
```http
POST /recording/{recording_id}/reprocess_transcription
```

**路径参数:**
- `recording_id` (int): 录音ID

**请求参数:**
```json
{
  "language": "en",
  "min_speakers": 2,
  "max_speakers": 5
}
```

**响应:**
```json
{
  "success": true,
  "message": "重新转录任务已启动"
}
```

---

## 文档下载 📄

### 下载转录文本
```http
GET /recording/{recording_id}/download/transcript
```

**查询参数:**
- `format` (string): 下载格式 (`txt`, `docx`, `pdf`)
- `template_id` (int, optional): 转录模板ID

**响应:** 返回文档文件

---

### 下载摘要
```http
GET /recording/{recording_id}/download/summary
```

**查询参数:**
- `format` (string): 下载格式 (`txt`, `docx`, `pdf`)

**响应:** 返回文档文件

---

### 下载聊天记录
```http
POST /recording/{recording_id}/download/chat
```

**请求参数:**
```json
{
  "format": "pdf",
  "messages": [
    {
      "role": "user",
      "content": "会议讨论了什么？"
    },
    {
      "role": "assistant", 
      "content": "会议主要讨论了项目进度..."
    }
  ]
}
```

**响应:** 返回聊天记录文档

---

## 标签管理 🏷️

### 获取标签列表
```http
GET /api/tags
```

**响应:**
```json
[
  {
    "id": 1,
    "name": "会议",
    "color": "#3B82F6",
    "custom_prompt": "专注于会议要点和决策",
    "default_language": "zh",
    "default_min_speakers": 2,
    "default_max_speakers": 10
  }
]
```

---

### 创建标签
```http
POST /api/tags
```

**请求参数:**
```json
{
  "name": "项目讨论",
  "color": "#10B981",
  "custom_prompt": "重点关注项目进度和问题",
  "default_language": "zh",
  "default_min_speakers": 2,
  "default_max_speakers": 5
}
```

**响应:**
```json
{
  "id": 2,
  "name": "项目讨论",
  "color": "#10B981",
  "message": "标签创建成功"
}
```

---

### 更新标签
```http
PUT /api/tags/{tag_id}
```

**路径参数:**
- `tag_id` (int): 标签ID

**请求参数:**
```json
{
  "name": "更新后的标签名",
  "color": "#EF4444"
}
```

**响应:**
```json
{
  "success": true,
  "message": "标签更新成功"
}
```

---

### 删除标签
```http
DELETE /api/tags/{tag_id}
```

**路径参数:**
- `tag_id` (int): 标签ID

**响应:**
```json
{
  "success": true,
  "message": "标签删除成功"
}
```

---

### 为录音添加标签
```http
POST /api/recordings/{recording_id}/tags
```

**路径参数:**
- `recording_id` (int): 录音ID

**请求参数:**
```json
{
  "tag_id": 1
}
```

**响应:**
```json
{
  "success": true,
  "message": "标签添加成功"
}
```

---

### 从录音移除标签
```http
DELETE /api/recordings/{recording_id}/tags/{tag_id}
```

**路径参数:**
- `recording_id` (int): 录音ID
- `tag_id` (int): 标签ID

**响应:**
```json
{
  "success": true,
  "message": "标签移除成功"
}
```

---

## 说话人管理 🗣️

### 获取说话人列表
```http
GET /speakers
```

**响应:**
```json
[
  {
    "id": 1,
    "name": "张三",
    "email": "zhangsan@example.com",
    "created_at": "2024-01-01T10:00:00Z"
  }
]
```

---

### 搜索说话人
```http
GET /speakers/search
```

**查询参数:**
- `q` (string): 搜索关键词

**响应:**
```json
[
  {
    "id": 1,
    "name": "张三",
    "email": "zhangsan@example.com"
  }
]
```

---

### 创建说话人
```http
POST /speakers
```

**请求参数:**
```json
{
  "name": "王五",
  "email": "wangwu@example.com"
}
```

**响应:**
```json
{
  "id": 2,
  "name": "王五",
  "message": "说话人创建成功"
}
```

---

### 删除说话人
```http
DELETE /speakers/{speaker_id}
```

**路径参数:**
- `speaker_id` (int): 说话人ID

**响应:**
```json
{
  "success": true,
  "message": "说话人删除成功"
}
```

---

## 分享功能 📤

### 获取录音分享信息
```http
GET /api/recording/{recording_id}/share
```

**路径参数:**
- `recording_id` (int): 录音ID

**响应:**
```json
{
  "public_id": "abc123def456",
  "share_url": "http://localhost:8899/share/abc123def456",
  "expires_at": "2024-12-31T23:59:59Z",
  "password_protected": false
}
```

---

### 创建分享链接
```http
POST /api/recording/{recording_id}/share
```

**路径参数:**
- `recording_id` (int): 录音ID

**请求参数:**
```json
{
  "expires_at": "2024-12-31T23:59:59Z",
  "password": "optional_password",
  "allow_download": true
}
```

**响应:**
```json
{
  "success": true,
  "public_id": "abc123def456",
  "share_url": "http://localhost:8899/share/abc123def456"
}
```

---

### 获取用户所有分享
```http
GET /api/shares
```

**响应:**
```json
[
  {
    "id": 1,
    "public_id": "abc123def456",
    "recording_title": "重要会议",
    "created_at": "2024-01-01T10:00:00Z",
    "expires_at": "2024-12-31T23:59:59Z",
    "password_protected": false
  }
]
```

---

### 更新分享设置
```http
PUT /api/share/{share_id}
```

**路径参数:**
- `share_id` (int): 分享ID

**请求参数:**
```json
{
  "expires_at": "2025-01-31T23:59:59Z",
  "password": "new_password"
}
```

**响应:**
```json
{
  "success": true,
  "message": "分享设置更新成功"
}
```

---

### 删除分享
```http
DELETE /api/share/{share_id}
```

**路径参数:**
- `share_id` (int): 分享ID

**响应:**
```json
{
  "success": true,
  "message": "分享删除成功"
}
```

---

## AI聊天功能 💬

### 与录音对话
```http
POST /chat
```

**请求参数:**
```json
{
  "message": "这次会议讨论了什么重要内容？",
  "recording_id": 123,
  "conversation_history": [
    {
      "role": "user",
      "content": "之前的问题"
    },
    {
      "role": "assistant",
      "content": "之前的回答"
    }
  ]
}
```

**响应:**
```json
{
  "response": "根据录音内容，这次会议主要讨论了...",
  "conversation_id": "conv_123456",
  "processing_time": 2.5
}
```

---

## 智能搜索 (Inquire Mode) 🔍

### 语义搜索
```http
POST /api/inquire/search
```

**请求参数:**
```json
{
  "query": "关于项目预算的讨论",
  "filters": {
    "tags": ["会议", "项目"],
    "date_from": "2024-01-01",
    "date_to": "2024-12-31",
    "speaker_names": ["张三", "李四"]
  },
  "limit": 10
}
```

**响应:**
```json
{
  "results": [
    {
      "recording_id": 123,
      "recording_title": "项目预算会议",
      "chunk_text": "我们讨论了下个季度的项目预算分配...",
      "similarity_score": 0.95,
      "start_time": 120.5,
      "end_time": 180.2
    }
  ],
  "total_results": 25
}
```

---

### 跨录音AI对话
```http
POST /api/inquire/chat
```

**请求参数:**
```json
{
  "message": "总结所有关于项目进度的讨论",
  "session_id": "session_123",
  "filters": {
    "tags": ["项目", "会议"]
  }
}
```

**响应:**
```json
{
  "response": "根据所有相关录音的分析，项目进度总体情况如下...",
  "sources": [
    {
      "recording_id": 123,
      "title": "项目进度会议",
      "relevance": 0.92
    }
  ]
}
```

---

## 事件提取 📅

### 获取录音中的事件
```http
GET /api/recording/{recording_id}/events
```

**路径参数:**
- `recording_id` (int): 录音ID

**响应:**
```json
[
  {
    "id": 1,
    "title": "项目评审会议",
    "start_datetime": "2024-02-15T14:00:00Z",
    "end_datetime": "2024-02-15T15:30:00Z",
    "description": "对项目第一阶段进行评审",
    "location": "会议室A"
  }
]
```

---

### 下载事件ICS文件
```http
GET /api/event/{event_id}/ics
```

**路径参数:**
- `event_id` (int): 事件ID

**响应:** 返回ICS格式的日历文件

---

### 下载录音所有事件的ICS文件
```http
GET /api/recording/{recording_id}/events/ics
```

**路径参数:**
- `recording_id` (int): 录音ID

**响应:** 返回包含所有事件的ICS文件

---

## 转录模板 📋

### 获取转录模板列表
```http
GET /api/transcript-templates
```

**响应:**
```json
[
  {
    "id": 1,
    "name": "标准格式",
    "content": "# {{title}}\n\n**日期:** {{date}}\n**时长:** {{duration}}\n\n## 转录内容\n{{transcription}}",
    "is_default": true
  }
]
```

---

### 创建转录模板
```http
POST /api/transcript-templates
```

**请求参数:**
```json
{
  "name": "会议纪要模板",
  "content": "# 会议纪要：{{title}}\n\n**时间:** {{date}}\n**参与者:** {{participants}}\n\n## 会议内容\n{{transcription}}\n\n## 总结\n{{summary}}",
  "is_default": false
}
```

**响应:**
```json
{
  "id": 2,
  "name": "会议纪要模板",
  "message": "模板创建成功"
}
```

---

### 更新转录模板
```http
PUT /api/transcript-templates/{template_id}
```

**路径参数:**
- `template_id` (int): 模板ID

**请求参数:**
```json
{
  "name": "更新后的模板名",
  "content": "更新后的模板内容",
  "is_default": false
}
```

**响应:**
```json
{
  "success": true,
  "message": "模板更新成功"
}
```

---

### 删除转录模板
```http
DELETE /api/transcript-templates/{template_id}
```

**路径参数:**
- `template_id` (int): 模板ID

**响应:**
```json
{
  "success": true,
  "message": "模板删除成功"
}
```

---

## 用户偏好设置 ⚙️

### 保存用户偏好
```http
POST /api/user/preferences
```

**请求参数:**
```json
{
  "language": "zh",
  "theme": "dark",
  "default_transcription_language": "zh",
  "auto_generate_summary": true
}
```

**响应:**
```json
{
  "success": true,
  "message": "偏好设置保存成功"
}
```

---

## 管理员功能 👑

### 获取统计数据
```http
GET /admin/stats
```

**权限要求:** 管理员

**响应:**
```json
{
  "total_users": 25,
  "total_recordings": 1250,
  "total_processing_time": 45000,
  "storage_used_gb": 128.5,
  "active_users_last_30_days": 18
}
```

---

### 获取用户列表
```http
GET /admin/users
```

**权限要求:** 管理员

**响应:**
```json
[
  {
    "id": 1,
    "name": "张三",
    "email": "zhangsan@example.com",
    "is_admin": false,
    "created_at": "2024-01-01T10:00:00Z",
    "last_login": "2024-01-15T09:30:00Z"
  }
]
```

---

### 创建用户
```http
POST /admin/users
```

**权限要求:** 管理员

**请求参数:**
```json
{
  "name": "新用户",
  "email": "newuser@example.com",
  "password": "secure_password",
  "is_admin": false
}
```

**响应:**
```json
{
  "id": 26,
  "name": "新用户",
  "message": "用户创建成功"
}
```

---

### 更新用户信息
```http
PUT /admin/users/{user_id}
```

**权限要求:** 管理员

**路径参数:**
- `user_id` (int): 用户ID

**请求参数:**
```json
{
  "name": "更新后的姓名",
  "email": "newemail@example.com"
}
```

**响应:**
```json
{
  "success": true,
  "message": "用户信息更新成功"
}
```

---

### 删除用户
```http
DELETE /admin/users/{user_id}
```

**权限要求:** 管理员

**路径参数:**
- `user_id` (int): 用户ID

**响应:**
```json
{
  "success": true,
  "message": "用户删除成功"
}
```

---

### 切换用户管理员权限
```http
POST /admin/users/{user_id}/toggle-admin
```

**权限要求:** 管理员

**路径参数:**
- `user_id` (int): 用户ID

**响应:**
```json
{
  "success": true,
  "is_admin": true,
  "message": "用户权限更新成功"
}
```

---

## 错误响应格式

所有API在出错时都会返回统一的错误格式：

```json
{
  "error": "错误描述信息",
  "code": "ERROR_CODE",
  "details": {
    "field": "具体错误字段",
    "message": "详细错误信息"
  }
}
```

**常见HTTP状态码:**
- `200`: 成功
- `400`: 请求参数错误
- `401`: 未认证
- `403`: 权限不足
- `404`: 资源不存在
- `429`: 请求频率限制
- `500`: 服务器内部错误

---

## 速率限制

某些API接口有速率限制：

- `/api/recordings`: 1250次/小时
- `/chat`: 100次/小时
- `/api/inquire/*`: 500次/小时

超过限制时会返回HTTP 429状态码。

---

## Webhook通知

系统支持webhook通知，当录音处理完成时会发送通知：

```json
{
  "event": "recording.completed",
  "recording_id": 123,
  "title": "会议录音",
  "status": "COMPLETED",
  "timestamp": "2024-01-01T10:00:00Z"
}
```

---

## 版本说明

当前API版本: v1  
文档版本: 2024-01-01  
Speakr版本: 0.5.6

如需获取最新的API信息，请访问 `/api/system/info` 接口。