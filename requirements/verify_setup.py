#!/usr/bin/env python3
"""
验证 RAG Pipeline 环境配置
运行此脚本来检查所有依赖是否正确安装和配置
"""

import sys
import os

def check_python_version():
    """检查 Python 版本"""
    print("🔍 检查 Python 版本...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - 版本符合要求")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - 需要 Python 3.8 或更高版本")
        return False

def check_packages():
    """检查必要的包是否已安装"""
    print("\n🔍 检查必要的包...")
    
    packages = [
        ("haystack", "haystack-ai"),
        ("haystack_integrations", "haystack_integrations"),
        ("datasets", "datasets"),
        ("sentence_transformers", "sentence-transformers"),
        ("accelerate", "accelerate"),
        ("cohere", "cohere"),
        ("openai", "openai"),
        ("dotenv", "python-dotenv"),
        ("tqdm", "tqdm"),
        ("numpy", "numpy"),
        ("pandas", "pandas"),
    ]
    
    success = True
    for package_name, pip_name in packages:
        try:
            __import__(package_name)
            print(f"✅ {pip_name} - 已安装")
        except ImportError:
            print(f"❌ {pip_name} - 未安装")
            print(f"   安装命令: pip install {pip_name}")
            success = False
    
    return success

def check_environment():
    """检查环境变量配置"""
    print("\n🔍 检查环境变量...")
    
    # 尝试加载 .env 文件
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️ python-dotenv 未安装，无法加载 .env 文件")
    
    # 检查必要的环境变量
    env_vars = [
        ("COHERE_API_KEY", "Cohere API 密钥"),
        ("OPENAI_API_KEY", "OpenAI API 密钥"),
    ]
    
    success = True
    for var_name, description in env_vars:
        value = os.getenv(var_name)
        if value and value != "your_cohere_api_key_here" and value != "your_openai_api_key_here":
            print(f"✅ {var_name} - 已配置")
        else:
            print(f"❌ {var_name} - 未配置或使用默认值")
            print(f"   描述: {description}")
            success = False
    
    if not success:
        print("\n💡 提示:")
        print("1. 创建 .env 文件（可以复制 .env.template）")
        print("2. 在 .env 文件中设置您的 API 密钥")
    
    return success

def check_file_structure():
    """检查项目文件结构"""
    print("\n🔍 检查项目文件结构...")
    
    required_files = [
        ("incremental_indexing_rag.ipynb", "主要笔记本文件"),
        ("files/index_table.json", "数据文件"),
    ]
    
    success = True
    for file_path, description in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} - {description}")
        else:
            print(f"❌ {file_path} - {description} (缺失)")
            success = False
    
    # 检查输出目录
    if not os.path.exists("outputs"):
        print("📁 创建 outputs 目录...")
        os.makedirs("outputs", exist_ok=True)
        print("✅ outputs/ - 输出目录已创建")
    else:
        print("✅ outputs/ - 输出目录存在")
    
    return success

def test_imports():
    """测试关键导入"""
    print("\n🔍 测试关键导入...")
    
    try:
        from haystack import Pipeline
        from haystack.components.builders import PromptBuilder
        from haystack.components.generators import OpenAIGenerator
        from haystack_integrations.components.embedders.cohere import CohereDocumentEmbedder, CohereTextEmbedder
        print("✅ Haystack 核心组件导入成功")
        
        import json
        import os
        from tqdm import tqdm
        print("✅ 标准库和工具导入成功")
        
        return True
    except Exception as e:
        print(f"❌ 导入测试失败: {e}")
        return False

def main():
    """主验证函数"""
    print("🚀 RAG Pipeline 环境验证")
    print("=" * 50)
    
    checks = [
        ("Python 版本", check_python_version),
        ("包安装", check_packages),
        ("环境变量", check_environment),
        ("文件结构", check_file_structure),
        ("导入测试", test_imports),
    ]
    
    all_passed = True
    results = []
    
    for check_name, check_func in checks:
        result = check_func()
        results.append((check_name, result))
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    print("📊 验证结果总结:")
    
    for check_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {check_name}: {status}")
    
    if all_passed:
        print("\n🎉 所有检查通过！环境配置正确，可以运行笔记本。")
        return 0
    else:
        print("\n⚠️ 部分检查失败，请根据上述提示修复问题。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
