import json
import os
import sys
import requests
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

# Force UTF-8 encoding for Windows terminal output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

CHATBOT_API_URL = "http://localhost:5080/api/chat"
QUESTIONS_FILE = "data/evaluation_questions.json"
OUTPUT_FILE = "data/generated_responses.json"

def load_questions():
    if not os.path.exists(QUESTIONS_FILE):
        print(f"❌ Không tìm thấy tệp câu hỏi tại: {QUESTIONS_FILE}")
        sys.exit(1)
    with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def check_server():
    try:
        r = requests.get("http://localhost:5080/api/health", timeout=3)
        if r.status_code == 200:
            print("✅ Kết nối tới Chatbot Server thành công.")
            return True
    except Exception:
        pass
    print("❌ Chatbot Server (FastAPI) chưa hoạt động tại cổng 5080!")
    print("💡 Vui lòng chạy file start_lungcare.bat hoặc uvicorn để khởi động server trước.")
    return False

def query_single_question(q):
    print(f"⏳ Đang gửi câu hỏi {q['id']}: '{q['question'][:50]}...'")
    try:
        res = requests.post(CHATBOT_API_URL, json={
            "messages": [{"role": "user", "content": q["question"]}],
            "stream": False
        }, timeout=180)
        
        if res.status_code == 200:
            chat_data = res.json()
            return {
                "id": q["id"],
                "category": q["category"],
                "question": q["question"],
                "chatbot_response": chat_data.get("message", ""),
                "sources_used": chat_data.get("sources", [])
            }
        else:
            print(f"❌ Lỗi câu {q['id']}: Status code {res.status_code}")
            return {
                "id": q["id"],
                "category": q["category"],
                "question": q["question"],
                "chatbot_response": f"[Lỗi API: {res.status_code} - {res.text}]",
                "sources_used": []
            }
    except Exception as e:
        print(f"❌ Lỗi kết nối khi gửi câu {q['id']}: {e}")
        return {
            "id": q["id"],
            "category": q["category"],
            "question": q["question"],
            "chatbot_response": f"[Lỗi kết nối: {str(e)}]",
            "sources_used": []
        }

def main():
    print("==========================================")
    print("🚀 LUỒNG 1: SINH CÂU TRẢ LỜI CỦA CHATBOT")
    print("==========================================")
    
    if not check_server():
        sys.exit(1)
        
    questions = load_questions()
    print(f"📋 Đã tải {len(questions)} câu hỏi từ {QUESTIONS_FILE}")
    
    responses = []
    
    # Truy vấn tuần tự (1 luồng) để tránh quá tải và đảm bảo ngữ cảnh tối đa cho llama-server
    print("⚡ Bắt đầu truy vấn chatbot (tuần tự từng câu)...")
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = {executor.submit(query_single_question, q): q for q in questions}
        for fut in as_completed(futures):
            res_data = fut.result()
            responses.append(res_data)
            
    # Sắp xếp lại theo ID để đảm bảo thứ tự
    responses.sort(key=lambda x: x["id"])
    
    # Lưu kết quả
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(responses, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ Đã lưu toàn bộ câu trả lời của {len(responses)} câu hỏi vào: {OUTPUT_FILE}")
    print("👉 Hãy chạy Luồng 2 (run_gemini_evaluation.py) để bắt đầu đánh giá chất lượng bằng Google Gemini!")

if __name__ == "__main__":
    main()
