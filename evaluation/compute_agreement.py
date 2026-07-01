import os
import json
import pandas as pd
from sklearn.metrics import cohen_kappa_score
import numpy as np

def compute_agreement(expert_file="data/expert_annotations.xlsx", results_file="data/evaluation_results.json"):
    print("🚀 Bắt đầu tính toán độ đồng thuận (Inter-Rater Agreement)...")
    
    if not os.path.exists(expert_file):
        print(f"❌ Không tìm thấy file {expert_file}. Hãy nhờ chuyên gia điền điểm vào file Excel trước.")
        return
        
    if not os.path.exists(results_file):
        print(f"❌ Không tìm thấy file {results_file}.")
        return
        
    df_expert = pd.read_excel(expert_file)
    with open(results_file, "r", encoding="utf-8") as f:
        llm_results = json.load(f)
        
    # Tạo dict để tra cứu điểm LLM dễ hơn
    llm_dict = {item["case_id"]: item["scores"] for item in llm_results}
    
    # Biến lưu trữ điểm
    metrics = {
        "guideline_adherence": {"expert": [], "llm": []},
        "safety_of_recommendations": {"expert": [], "llm": []},
        "recognition_of_key_risks": {"expert": [], "llm": []},
        "accuracy_of_grading": {"expert": [], "llm": []},
        "conversational_explanation": {"expert": [], "llm": []},
        "clarity": {"expert": [], "llm": []},
        "overall_helpfulness": {"expert": [], "llm": []}
    }
    
    # Ánh xạ cột Excel sang key JSON
    col_mapping = {
        "Expert_Guideline_Adherence (0/1)": "guideline_adherence",
        "Expert_Safety (0/1)": "safety_of_recommendations",
        "Expert_Risk_Recognition (0/1)": "recognition_of_key_risks",
        "Expert_Grading_Accuracy (0/1)": "accuracy_of_grading",
        "Expert_Conversational (0/1)": "conversational_explanation",
        "Expert_Clarity (1-5)": "clarity",
        "Expert_Helpfulness (1-5)": "overall_helpfulness"
    }
    
    valid_cases = 0
    for index, row in df_expert.iterrows():
        case_id = row["Case ID"]
        if pd.isna(row["Expert_Safety (0/1)"]) or case_id not in llm_dict:
            continue # Bỏ qua nếu chuyên gia chưa chấm
            
        valid_cases += 1
        llm_scores = llm_dict[case_id]
        
        for excel_col, json_key in col_mapping.items():
            try:
                expert_score = float(row[excel_col])
                llm_score = float(llm_scores.get(json_key, 0))
                
                metrics[json_key]["expert"].append(expert_score)
                metrics[json_key]["llm"].append(llm_score)
            except Exception as e:
                print(f"Lỗi parse điểm case {case_id}, cột {excel_col}: {e}")
                
    if valid_cases == 0:
        print("❌ Không có dữ liệu hợp lệ để tính toán. Đảm bảo chuyên gia đã điền đủ số vào Excel.")
        return
        
    print(f"\n📊 Kết quả tính toán trên {valid_cases} case:")
    print("-" * 60)
    print(f"{'Tiêu chí (Criteria)':<35} | {'Cohen\'s Kappa (κ) / Correlation'}")
    print("-" * 60)
    
    # 5 tiêu chí nhị phân (dùng Cohen's Kappa)
    binary_metrics = ["guideline_adherence", "safety_of_recommendations", 
                      "recognition_of_key_risks", "accuracy_of_grading", "conversational_explanation"]
                      
    for metric in binary_metrics:
        expert = metrics[metric]["expert"]
        llm = metrics[metric]["llm"]
        
        # Đảm bảo phân loại nhị phân (int)
        expert = [int(x) for x in expert]
        llm = [int(x) for x in llm]
        
        kappa = cohen_kappa_score(expert, llm)
        print(f"{metric:<35} | κ = {kappa:.3f}")
        
    # 2 tiêu chí Likert (dùng Pearson Correlation)
    likert_metrics = ["clarity", "overall_helpfulness"]
    for metric in likert_metrics:
        expert = metrics[metric]["expert"]
        llm = metrics[metric]["llm"]
        
        corr = np.corrcoef(expert, llm)[0, 1]
        print(f"{metric:<35} | r = {corr:.3f}")
        
    print("-" * 60)
    print("\n💡 Hướng dẫn giải thích trong Paper:")
    print("- Kappa (κ) > 0.60: Đồng thuận TỐT (Substantial agreement).")
    print("- Kappa (κ) > 0.80: Đồng thuận RẤT TỐT (Almost perfect agreement).")
    print("- Dùng kết quả này để chứng minh Gemini chấm điểm rất sát với bác sĩ thật.")

if __name__ == "__main__":
    compute_agreement()
