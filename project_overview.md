# 🫁 Tổng quan Dự án: LungCare AI - Trợ lý Ảo Tư vấn Ung thư Phổi

## 1. Giới thiệu chung
**LungCare AI** là một hệ thống chatbot tư vấn y khoa chuyên sâu về bệnh ung thư phổi, được xây dựng dựa trên kiến trúc **RAG (Retrieval-Augmented Generation)**. Hệ thống kết hợp khả năng xử lý ngôn ngữ tự nhiên của các mô hình ngôn ngữ lớn (LLM) với một cơ sở dữ liệu y khoa đáng tin cậy được thu thập từ các nguồn chính thống.

Mục tiêu của dự án là cung cấp các thông tin tham khảo nhanh chóng, chính xác và an toàn cho người bệnh hoặc người nhà bệnh nhân về các triệu chứng, phương pháp tầm soát và hướng điều trị ung thư phổi.

---

## 2. Kiến trúc Hệ thống & Công nghệ (Tech Stack)

Hệ thống được chia làm 3 phân hệ chính:

### 🖥️ Frontend (Giao diện người dùng)
- **Công nghệ**: React, TypeScript, Tailwind CSS, Vite.
- **Tính năng**:
  - Giao diện Chat trực quan, hiển thị tin nhắn dạng luồng (Streaming).
  - Bảng điều khiển quản lý **Nguồn dữ liệu (Knowledge Base)**: Cho phép xem danh sách các phân đoạn kiến thức, kiểm tra trạng thái và **xóa** các nguồn dữ liệu không đạt yêu cầu.
  - Hiển thị trích dẫn (Citations) để minh bạch hóa nguồn gốc câu trả lời của AI.

### ⚙️ Backend (API Server)
- **Công nghệ**: FastAPI (Python), Uvicorn.
- **Tính năng**:
  - `rag_engine`: Lõi xử lý RAG, chịu trách nhiệm nhúng (embedding), tìm kiếm ngữ nghĩa (vector search) và xây dựng prompt.
  - Tích hợp công cụ **Firecrawl** để cào (crawl) dữ liệu tự động từ các trang web y tế uy tín và đưa vào cơ sở dữ liệu.
  - Quản lý Vector DB nhẹ (lưu trữ in-memory dựa trên numpy/scikit-learn hoặc FAISS).

### 🧠 LLM Backend (Động cơ AI)
- **Công nghệ**: Hỗ trợ đồng thời **Ollama** và **Llama.cpp** (ưu tiên GPU).
- **Mô hình**: Sử dụng mô hình `Qwen 2.5 3B` (hoặc các mô hình LLM tương tự) được tối ưu hóa cho tốc độ và khả năng suy luận.
- **Cơ chế tự động**: Backend tự động phát hiện xem Llama.cpp có đang chạy (cổng 8080) hay không để định tuyến request nhằm đạt tốc độ tối đa, nếu không sẽ tự động fallback về Ollama (cổng 11434).

---

## 3. Luồng hoạt động của RAG (Retrieval-Augmented Generation)

1. **Thu thập dữ liệu**: Người dùng nhập URL trang web y khoa. Hệ thống dùng Firecrawl cào nội dung, chia nhỏ (chunking) và nhúng (embedding) thành vector.
2. **Truy vấn**: Người dùng đặt câu hỏi. Hệ thống nhúng câu hỏi này thành vector.
3. **Tìm kiếm (Retrieval)**: Hệ thống tìm 3-5 đoạn văn bản (chunks) có ngữ nghĩa gần nhất với câu hỏi từ Vector DB.
4. **Sinh văn bản (Generation)**: LLM nhận câu hỏi cùng với các đoạn văn bản tham khảo để tổng hợp câu trả lời chính xác, kèm theo trích dẫn nguồn.
5. **Bảo vệ (Guardrails)**: Nếu câu hỏi nằm ngoài phạm vi y khoa, hoặc hệ thống không tìm thấy thông tin đáng tin cậy trong cơ sở dữ liệu, AI sẽ từ chối trả lời để đảm bảo an toàn y tế.

---

## 4. 📊 Đánh giá Chất lượng Lâm sàng (Evaluation)

Dự án đi kèm với một bộ công cụ đánh giá tự động sử dụng **Google Gemini** làm giám khảo (LLM-as-a-Judge). Quá trình đánh giá được thực hiện trên tập hợp các tình huống lâm sàng giả định (Nhận diện triệu chứng, Sàng lọc chủ động, Điều trị).

### Tóm tắt Điểm số Chất lượng

| Tiêu chí Đánh giá (Metrics) | Tỷ lệ Đạt (%) / Điểm trung bình | Ý nghĩa |
| :--- | :--- | :--- |
| **Tuân thủ Hướng dẫn lâm sàng** *(guideline_adherence)* | **92.0%** | Phản hồi tuân thủ đúng các phác đồ điều trị và hướng dẫn chuẩn. |
| **Mức độ An toàn** *(safety_of_recommendations)* | **100.0%** | Không đưa ra lời khuyên nguy hiểm, luôn khuyến cáo đi khám chuyên khoa. |
| **Nhận diện Rủi ro** *(recognition_of_key_risks)* | **100.0%** | Nhận diện chính xác các triệu chứng "cờ đỏ" (ho ra máu, sụt cân). |
| **Phân loại Mức độ Khẩn cấp** *(accuracy_of_grading)* | **100.0%** | Đánh giá đúng mức độ nghiêm trọng để khuyên bệnh nhân đi cấp cứu hoặc tầm soát. |
| **Giải thích dễ hiểu** *(conversational_explanation)* | **84.0%** | Giọng điệu đồng cảm, tránh lạm dụng thuật ngữ y khoa phức tạp. |
| **Độ rõ ràng** *(clarity)* | **4.46 / 5.0** | Cấu trúc câu trả lời mạch lạc, dễ đọc. |
| **Độ hữu ích** *(overall_helpfulness)* | **4.58 / 5.0** | Cung cấp thông tin thực sự có giá trị cho bệnh nhân. |

> [!TIP]
> **Đánh giá tổng quan:** Hệ thống đạt độ an toàn tuyệt đối (100%) trong việc không đưa ra lời khuyên gây hại. Đây là yếu tố quan trọng nhất đối với một AI y tế. Tuy nhiên, phần hành văn tự nhiên (conversational) vẫn còn dư địa để cải thiện (84%) do đôi khi AI bị "cứng nhắc" khi bám sát quá sát vào tài liệu y khoa.

---

## 5. Các tính năng nổi bật vừa được cập nhật
- **Trộn (Merge) tri thức**: Kết hợp thành công 150 phân đoạn kiến thức từ chuyên gia vào hệ thống quản lý web.
- **Xóa Dữ Liệu**: Bổ sung nút xóa trực tiếp trên giao diện để người quản trị dễ dàng loại bỏ các bài viết bị cào lỗi.
- **Tăng tốc với Llama.cpp**: Cấu trúc lại mã nguồn để hỗ trợ engine Llama.cpp GPU siêu tốc, mang lại trải nghiệm chat tức thời (Streaming response).
- **Bộ công cụ Evaluate**: Script đánh giá hàng loạt (Batch Evaluate) tự động chấm điểm và xuất báo cáo Markdown chuyên nghiệp.
