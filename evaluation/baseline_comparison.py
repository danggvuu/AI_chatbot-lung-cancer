import os
import sys
# Thêm thư mục gốc vào sys.path để import được rag_engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from pprint import pprint

from rag_engine.chat_service import ChatService
from indexing.retriever_orchestrator import RetrieverOrchestrator
from rag_engine.prompt_builder import PromptBuilder
from rag_engine.llm_client import OllamaClient
from evaluate_lung_chatbot import QUESTIONS

def run_evaluation_for_config(config_name, questions):
    print(f"\n🚀 Bắt đầu chạy Baseline: {config_name.upper()} ({len(questions)} câu)")
    
    # Setup instances
    chat_service = ChatService()
    retriever = chat_service.retriever
    llm = chat_service.llm_client
    
    results = []
    
    def process_case(q):
        start_time = time.time()
        docs = []
        try:
            if config_name == "no_rag":
                docs = []
                messages = chat_service.prompt_builder.build_prompt(q["question"], docs)
                resp = asyncio.run(llm.generate(messages, temperature=0.1, num_predict=500, num_ctx=4096))
                
            elif config_name == "bm25_only":
                bm25_res = retriever.bm25.search(q["question"], top_k=3)
                docs = [{"id": r[0], "content": retriever.doc_map.get(r[0], {}).get("content", ""), "source": retriever.doc_map.get(r[0], {}).get("source", "")} for r in bm25_res]
                messages = chat_service.prompt_builder.build_prompt(q["question"], docs)
                resp = asyncio.run(llm.generate(messages, temperature=0.1, num_predict=500, num_ctx=4096))
                
            elif config_name == "dense_only":
                query_vec = retriever.embedder.encode([q["question"]])[0]
                dense_res = retriever.qdrant.search(query_vec, top_k=3)
                docs = [{"id": r[0], "content": retriever.doc_map.get(r[0], {}).get("content", ""), "source": retriever.doc_map.get(r[0], {}).get("source", "")} for r in dense_res]
                messages = chat_service.prompt_builder.build_prompt(q["question"], docs)
                resp = asyncio.run(llm.generate(messages, temperature=0.1, num_predict=500, num_ctx=4096))
                
            elif config_name == "hybrid":
                # Chạy qua luồng chuẩn
                res = asyncio.run(chat_service.get_chat_response_sync(q["question"]))
                resp = res["message"]
                docs = res.get("sources", [])
                
            else:
                resp = "Invalid config"
                
            end_time = time.time()
            print(f"  [{config_name.upper()}] Xong câu {q['id']}")
            
            return {
                "case_id": q["id"],
                "category": q["category"],
                "question": q["question"],
                "chatbot_response": resp,
                "sources_used": docs,
                "response_time_ms": int((end_time - start_time) * 1000)
            }
        except Exception as e:
            print(f"  ❌ Lỗi ở câu {q['id']}: {e}")
            return None

    # Chạy song song để tiết kiệm thời gian
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(process_case, q): q for q in questions}
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
                
    results.sort(key=lambda x: x["case_id"])
    return results

def main():
    configs = ["no_rag", "bm25_only", "dense_only", "hybrid"]
    all_results = {}
    
    os.makedirs("data", exist_ok=True)
    out_file = "data/baseline_results.json"
    
    # Load previously saved results if any to resume
    if os.path.exists(out_file):
        with open(out_file, "r", encoding="utf-8") as f:
            all_results = json.load(f)
    
    for cfg in configs:
        if cfg in all_results and len(all_results[cfg]) == len(QUESTIONS):
            print(f"✅ Bỏ qua {cfg} vì đã có dữ liệu cache.")
            continue
            
        cfg_res = run_evaluation_for_config(cfg, QUESTIONS)
        all_results[cfg] = cfg_res
        
        # Save intermediate
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
            
    print(f"\n🎉 Đã thu thập xong phản hồi cho 4 Baseline! Dữ liệu lưu tại {out_file}")
    print("👉 Hãy dùng script này kết hợp với batch_evaluate_gemini.py để Gemini tự chấm 4 phiên bản.")

if __name__ == "__main__":
    main()
