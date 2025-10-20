import os
import json
import time
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv 

# ===============================
# 环境变量加载
# ===============================
# 自动加载 .env 文件中的 OPENAI_API_KEY
load_dotenv('.env')

# 获取 API KEY
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY in environment or .env file. Please export OPENAI_API_KEY or add it to .env file.")

client = OpenAI(api_key=API_KEY)

# ===============================
# 配置
# ===============================
QUESTIONS = [
    "1. Does the app declare the collection of data?",
    "2. If the app declares the collection of data, what type of data does it collect?",
    "3. Does the app declare the purpose of data collection and use?",
    "4. Can the user opt out of data collection or delete data?",
    "5. Does the app share data with third parties?",
    "6. If the app shares data with third parties, what third parties does the app share data with?",
]

INDEX_FILE = "index_table.json"
OUTPUT_DIR = "output"
MODEL = "gpt-4o-mini"  # 可以改为 "gpt-5" 或 "gpt-4.1"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===============================
# 工具函数
# ===============================
def fetch_page_content(url, timeout=20):
    """抓取网页内容（超时自动跳过）"""
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"⚠️ [Fetch Error] {url} -> {e}")
        return ""

def ask_gpt(app_id, app_url, app_name, question, context, timeout=120):
    """调用 GPT 生成 JSON 答案（错误或超时自动跳过）"""
    prompt = f"""
You are a privacy policy expert. You are provided with {app_url}, which contains the privacy policy document for an app.
Your task is to:
 - answer the question based on the privacy policy document,
 - provide references for your answers based on the section in the privacy policy document from which your answer is generated,
 - produce your results strictly in the JSON format below (no extra text beyond JSON),
 - ensure that the 'url' in the 'meta' section is exactly {app_url}.

JSON format:
{{
   "meta": {{
       "id": {app_id},
       "url": "{app_url}",
       "title": "{app_name}"
   }},
   "reply": {{
       "qid": "",
       "question": "",
       "answer": {{
           "full_answer": "",
           "simple_answer": "",
           "extended_simple_answer": {{
               "comment": "",
               "content": ""
           }}
       }},
       "analysis": "",
       "reference": ""
   }}
}}

Context:
{context[:7000]}
Question: {question}
Answer:
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            timeout=timeout
        )
        text = response.choices[0].message.content.strip()
        return json.loads(text)
    except Exception as e:
        print(f"⚠️ [GPT Error] {app_url} Q: {question[:30]} -> {e}")
        return None

# ===============================
# 主流程
# ===============================
def main():
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        apps = json.load(f)

    for app in apps:
        app_id = app.get("id")
        app_url = app.get("url")
        app_name = ""
        output_path = os.path.join(OUTPUT_DIR, f"{app_id}.json")

        if os.path.exists(output_path):
            print(f"⏭️ Skip existing {output_path}")
            continue

        print(f"\n🟡 Processing app_id={app_id} ...")
        context = fetch_page_content(app_url)

        if not context.strip():
            print(f"⚠️ No content found at {app_url}, skipping...")
            continue

        results = []
        for q in QUESTIONS:
            print(f"   → Asking: {q}")
            answer_json = ask_gpt(app_id, app_url, app_name, q, context)
            if answer_json:
                results.append(answer_json)
            else:
                print(f"   ⚠️ Skipped unanswered question: {q}")
            time.sleep(1)

        if results:
            with open(output_path, "w", encoding="utf-8") as out:
                json.dump(results, out, ensure_ascii=False, indent=2)
            print(f"✅ Saved: {output_path}")
        else:
            print(f"⚠️ No valid results for {app_url}, skipping file.")

if __name__ == "__main__":
    main()
