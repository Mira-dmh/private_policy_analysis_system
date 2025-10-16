# RAG Pipeline with Incremental Indexing

这是一个基于 Haystack 的检索增强生成（RAG）项目，用于对应用隐私政策进行结构化问答与评估，支持增量索引、重排与自动化评测。

## 🚀 快速开始（Windows PowerShell）

### 1) 环境要求
- Python 3.8+（推荐 3.10/3.11）
- pip

建议使用虚拟环境隔离依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
```

### 2) 安装依赖

- 推荐（精简依赖）：

```powershell
pip install -r requirements\requirements_simple.txt
```

- 完整依赖：

```powershell
pip install -r requirements\requirements.txt
```

- 或手动安装核心包（如需）：

```powershell
pip install haystack-ai "datasets>=3.6.0" "sentence-transformers>=4.1.0" accelerate python-dotenv tqdm cohere openai
```

### 3) 配置环境变量

在仓库根目录或 `new version/` 目录放置 `.env` 文件（Notebook 会自动加载最近的 `.env`）：

```env
COHERE_API_KEY=your_actual_cohere_api_key
OPENAI_API_KEY=your_actual_openai_api_key
# 可选：如使用自建网关
CO_API_URL=https://api.cohere.ai/v1
```

若仓库提供 `.env.template`，可复制一份：

```powershell
copy .env.template .env
```

### 4) 验证环境（可选）

仓库提供了验证脚本：`requirements/verify_setup.py`。注意：脚本中的部分路径检查基于旧版结构，可能报告 Notebook 缺失但不影响运行。

```powershell
python requirements\verify_setup.py
```

### 5) 运行 Notebook

Notebook 位于：`new version/incremental_indexing_rag .ipynb`（注意文件名中 `.ipynb` 前有空格）。

```powershell
jupyter notebook "new version/incremental_indexing_rag .ipynb"
```

在 Notebook 中：
- 确保前两个单元已完成依赖安装与 API Key 加载。
- 如需控制处理数量，修改变量 `num_to_process`（默认 1）。

## 📁 关键目录与文件

```
POLICY-ANALYSIS/
├── files/
│   └── index_table.json                # 输入列表（包含 id 与隐私政策 URL）
├── new version/
│   ├── incremental_indexing_rag .ipynb # 主流程 Notebook（增量索引 + RAG + 评测）
│   ├── outputs/                        # Notebook 运行产生的 RAG 输出（每个 app_id 一个 JSON）
│   └── eval/                           # 评测结果输出（privacy_policy_rag_evaluation.json）
├── requirements/
│   ├── requirements_simple.txt
│   ├── requirements.txt
│   ├── INSTALLATION.md
│   └── verify_setup.py
├── groundtruth.json                    # 评测用标注（q1~q6）
└── README.md
```

说明：Notebook 内部从 `../files/index_table.json` 读取输入，因此建议在 `files/` 目录下维护输入文件。

## 🔧 主要功能

- 增量索引：逐 URL 抓取 → 转文档 → 清洗 → 分块 → 嵌入 → 写入临时内存库
- 语义检索：Cohere 文档/查询嵌入 + InMemory 检索
- 重排：Cohere rerank-english-v3.0，对召回结果做语义重排
- 生成：OpenAI GPT 生成严格 JSON 结构答案（内置 JSON 修复兜底）
- 评测：Faithfulness / SAS / Context Relevance 指标 + 二分类准确率

## 📋 输入数据格式

`files/index_table.json` 示例（仓库当前实际格式）：

```json
[
  { "content": "", "id": 1361356590, "url": "https://example.com/privacy" },
  { "content": "", "id": 1493155192, "url": "https://example.com/policy" }
]
```

字段说明：
- id：整数应用 ID（文件名即以此 ID 命名）
- url：隐私政策页面 URL
- content：可留空（抓取器会在线获取）

## ❓ 预设问题（6 个）

Notebook 默认会针对每个应用回答以下 6 个问题：

1. Does the app declare the collection of data?
2. If the app declares the collection of data, what type of data does it collect?
3. Does the app declare the purpose of data collection and use?
4. Can the user opt out of data collection or delete data?
5. Does the app share data with third parties?
6. If the app shares data with third parties, what third parties does the app share data with?

其中 q1/q3/q4/q5 为二分类（Yes/No），q2/q6 为开放题，答案结构会做区分（例如 q2/q6 的 simple_answer 可为 NOTUSED，详见 Notebook Prompt 约束）。

## 📄 输出与评测

- 生成答案：`new version/outputs/{app_id}.json`
- 评测结果：`new version/eval/privacy_policy_rag_evaluation.json`

单个应用输出文件为一个包含 6 条记录的数组，每条对应一个问题，核心结构如下（节选）：

```json
{
  "meta": { "id": 1361356590, "url": "https://example.com/privacy", "title": "Example App" },
  "reply": {
    "qid": "q1",
    "question": "1. Does the app declare the collection of data?",
    "answer": {
      "full_answer": "...",
      "simple_answer": "Yes",
      "extended_simple_answer": { "comment": "", "content": "" }
    },
    "analysis": "...",
    "reference": "原文片段 + URL"
  },
  "source_documents": [
    { "id": "...", "score": 0.87, "excerpt": "...", "url": "..." }
  ]
}
```

说明：
- Notebook 已内置 JSON 解析兜底逻辑，最大限度修复模型偶发的非严格 JSON 输出。
- `source_documents` 为可选，记录用于回答的证据片段摘要。

## 🔄 运行步骤概览

1) 准备 `files/index_table.json` 与 `.env`
2) 打开并运行 `new version/incremental_indexing_rag .ipynb`
3) 如需减少测试时间，先将 `num_to_process = 1` 并仅验证首条 URL
4) 检查 `new version/outputs/` 下生成的 `{app_id}.json`
5) 继续下方单元运行评测，结果在 `new version/eval/`

## 🛠️ 故障排查（FAQ）

1) 无法抓取页面（403/404/超时）
- Notebook 已对 URL 做常见变体回退（http/https、末尾斜杠、常见隐私路径）。仍失败时：
  - 检查 URL 是否可在浏览器打开
  - 需要代理的网络环境下，配置系统/终端代理
  - 个别站点可能需要更换入口页（将真实隐私页 URL 写入 `files/index_table.json`）

2) NLTK 下载失败或过慢
- Punkt 资源由 `nltk.download('punkt')` 下载，网络受限时可预先离线安装或配置代理。

3) API 配额或鉴权失败
- 确认 `.env` 中密钥有效且与当前账户/区域匹配
- OpenAI/Cohere 均可能因配额超限而报错，适当降低并发或处理数量

4) 评测阶段出错
- 确认 `groundtruth.json` 与生成的 `{app_id}.json` 中题号与问题文本能被正确匹配（README 中列出的 6 个问题）
- 若 `requirements/verify_setup.py` 指出 Notebook 路径缺失，可忽略该项（脚本基于旧路径约定）

5) 内存占用
- 本项目对每个应用使用独立的内存型文档库并复用 Pipeline，通常内存占用稳定；仍有压力时可减少 `top_k`、缩短分块长度，或分批运行。

## 📚 技术栈

- 框架：Haystack 2.x
- 嵌入：Cohere embed-english-v3.0（文档与查询）
- 重排：Cohere rerank-english-v3.0
- 生成：OpenAI GPT-3.5-turbo
- 评测：Faithfulness / SAS / Context Relevance

## 🤝 贡献

欢迎提交 Issue / PR 改进项目（例如将验证脚本路径更新为新结构、增加命令行入口、加入缓存的文档存储等）。

## 📄 许可证

本项目遵循相应的开源许可证条款。

---

重要提示：使用本项目需要有效的 Cohere 与 OpenAI API Key，请遵守服务条款与计费政策。
