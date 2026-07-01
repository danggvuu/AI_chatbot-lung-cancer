import os
import json
import pandas as pd
import random

def export_for_expert(num_samples=20, input_file="data/evaluation_results.json", output_file="data/expert_annotations.xlsx"):
    print(f"🚀 Bắt đầu xuất {num_samples} case ngẫu nhiên cho chuyên gia chấm...")
    
    if not os.path.exists(input_file):
        print(f"❌ Không tìm thấy file {input_file}. Vui lòng chạy đánh giá trước.")
        return
        
    with open(input_file, "r", encoding="utf-8") as f:
        results = json.load(f)
        
    if len(results) < num_samples:
        print(f"⚠️ Cảnh báo: Chỉ có {len(results)} case trong file, sẽ xuất tất cả.")
        num_samples = len(results)
        
    # Lấy mẫu ngẫu nhiên (cố định seed để dễ debug nếu cần)
    random.seed(42)
    sampled_cases = random.sample(results, num_samples)
    
    # Tạo dataframe cho Excel
    data = []
    for item in sampled_cases:
        data.append({
            "Case ID": item["case_id"],
            "Category": item["category"],
            "Question": item["question"],
            "Chatbot Response": item["chatbot_response"],
            "Expert_Guideline_Adherence (0/1)": "",
            "Expert_Safety (0/1)": "",
            "Expert_Risk_Recognition (0/1)": "",
            "Expert_Grading_Accuracy (0/1)": "",
            "Expert_Conversational (0/1)": "",
            "Expert_Clarity (1-5)": "",
            "Expert_Helpfulness (1-5)": "",
            "Expert_Notes": ""
        })
        
    df = pd.DataFrame(data)
    
    os.makedirs("data", exist_ok=True)
    
    # Lưu ra Excel với định dạng độ rộng cột
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Expert_Eval')
        
        # Chỉnh độ rộng cột cho dễ đọc
        worksheet = writer.sheets['Expert_Eval']
        worksheet.column_dimensions['C'].width = 40  # Question
        worksheet.column_dimensions['D'].width = 80  # Chatbot Response
        for col in ['E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']:
            worksheet.column_dimensions[col].width = 15
            
    print(f"✅ Đã xuất file thành công: {output_file}")
    print("👉 Hãy gửi file này cho chuyên gia/bác sĩ. Yêu cầu họ điền điểm vào các cột 'Expert_...'")

if __name__ == "__main__":
    export_for_expert()
