# RAG Pipeline 安装指南

## 环境要求

- Python 3.8 或更高版本
- pip 包管理器

## 快速安装

### 方式 1：使用简化依赖文件（推荐）

```bash
pip install -r requirements_simple.txt
```

### 方式 2：使用完整依赖文件

```bash
pip install -r requirements.txt
```

### 方式 3：手动安装核心包

```bash
# 安装核心包
pip install haystack-ai
pip install "datasets>=3.6.0"
pip install "sentence-transformers>=4.1.0"
pip install accelerate
pip install python-dotenv
pip install tqdm
pip install cohere
pip install openai
```

## 环境配置

1. 创建 `.env` 文件在项目根目录：

```env
COHERE_API_KEY=your_cohere_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
CO_API_URL=https://api.cohere.ai/v1
```

2. 替换 `your_cohere_api_key_here` 和 `your_openai_api_key_here` 为您的实际 API 密钥。

## API 密钥获取

### Cohere API Key
1. 访问 [Cohere Dashboard](https://dashboard.cohere.ai/)
2. 注册并登录
3. 在 API Keys 页面获取您的密钥

### OpenAI API Key
1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 注册并登录
3. 在 API Keys 页面创建新的密钥

## 验证安装

运行以下 Python 代码来验证安装：

```python
# 测试核心导入
from haystack import Pipeline
from haystack_integrations.components.embedders.cohere import CohereDocumentEmbedder
from dotenv import load_dotenv
import os

print("✅ 所有核心包安装成功！")

# 测试环境变量
load_dotenv()
cohere_key = os.getenv("COHERE_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

if cohere_key and openai_key:
    print("✅ API 密钥配置成功！")
else:
    print("⚠️ 请检查 .env 文件中的 API 密钥配置")
```

## 常见问题

### 1. 安装失败

如果遇到安装问题，尝试：

```bash
# 升级 pip
pip install --upgrade pip

# 使用清华源（国内用户）
pip install -r requirements_simple.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 2. Jupyter 环境

如果在 Jupyter Notebook 中运行，确保安装：

```bash
pip install jupyter ipykernel
```

### 3. GPU 支持

如果需要 GPU 加速（可选），安装对应的 PyTorch 版本：

```bash
# CUDA 版本（根据您的 CUDA 版本选择）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## 项目结构

```
POLICY-ANALYSIS/
├── incremental_indexing_rag.ipynb  # 主要笔记本
├── files/
│   └── index_table.json           # 数据文件
├── outputs/                       # 输出目录
├── requirements.txt               # 完整依赖
├── requirements_simple.txt        # 简化依赖
├── INSTALLATION.md               # 本文件
└── .env                          # 环境变量（需创建）
```

## 使用说明

1. 确保所有依赖已安装
2. 配置 `.env` 文件
3. 打开 `incremental_indexing_rag.ipynb`
4. 按顺序运行所有单元格

## 支持

如果遇到问题，请检查：
1. Python 版本是否符合要求
2. 所有依赖是否正确安装
3. API 密钥是否正确配置
4. 网络连接是否正常
