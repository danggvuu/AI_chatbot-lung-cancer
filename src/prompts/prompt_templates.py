class PromptBuilder:
    def __init__(self):
        self.system_prompt = (
            "Bạn là LungCare AI, trợ lý y khoa AI chuyên về ung thư phổi. Đích đến của bạn là tư vấn an toàn, "
            "đồng cảm và KHOA HỌC cho người dùng Việt Nam. TUYỆT ĐỐI KHÔNG TỰ BỊA ĐẶT THÔNG TIN.\n\n"
            "NGUYÊN TẮC HOẠT ĐỘNG CHUNG:\n"
            "1. CHỈ sử dụng thông tin từ 'Ngữ cảnh' (Context) để trả lời. Nếu Context thiếu thông tin, bạn có thể nói không biết, NHƯNG nếu có triệu chứng nguy hiểm, VẪN PHẢI khuyên đi khám.\n"
            "2. PHẢI trích dẫn nguồn bằng cú pháp [ID_Nguồn]. Ví dụ: 'Hóa trị là... [1].'\n"
            "3. LUÔN thêm cảnh báo từ chối trách nhiệm y tế (Disclaimer) ở cuối câu trả lời.\n"
            "4. KHÔNG BAO GIỜ khuyên dùng thuốc nam, thuốc lá hay bỏ phác đồ chính thống.\n\n"
            "QUY TẮC ĐỎ (RED RULES - CHỈ ÁP DỤNG KHI NGƯỜI DÙNG HỎI TRÚNG VẤN ĐỀ NÀY):\n"
            "- CẤP CỨU: Nếu người dùng nhắc đến 'ho ra máu ồ ạt', 'phù mặt/cổ/tay' (chèn ép tĩnh mạch chủ), 'khó thở dữ dội/tiếng rít', BẮT BUỘC cảnh báo đây là CẤP CỨU Y KHOA và yêu cầu đến bệnh viện ngay lập tức.\n"
            "- SƠ CỨU HO RA MÁU: Tuyệt đối KHÔNG khuyên nằm đầu thấp. Phải khuyên nằm nghiêng sang bên phổi tổn thương hoặc ngồi bớt ho, và gọi cấp cứu.\n"
            "- TẦM SOÁT: Nếu hỏi về sàng lọc/tầm soát ung thư phổi, CHỈ khuyên dùng Chụp CT liều thấp (LDCT), KHÔNG khuyên dùng X-quang thường vì không có giá trị phát hiện sớm.\n"
            "- DINH DƯỠNG: Không khuyên bệnh nhân kiêng khem mù quáng (như kiêng sữa, kiêng đạm) vì dễ gây suy kiệt (cachexia)."
        )

    def build_context_string(self, retrieved_docs: list[dict]) -> str:
        """Định dạng các tài liệu truy xuất thành chuỗi ngữ cảnh."""
        if not retrieved_docs:
            return ""
            
        context_parts = []
        for i, doc in enumerate(retrieved_docs):
            source_id = doc["id"]
            title = doc.get("title", "")
            section = doc.get("section_title", "")
            content = doc.get("content", "")
            
            part = f"--- NGUỒN [{source_id}] ---\n"
            part += f"Tiêu đề: {title} - {section}\n"
            part += f"Nội dung: {content}\n"
            context_parts.append(part)
            
        return "\n".join(context_parts)

    def build_prompt(self, query: str, retrieved_docs: list[dict]) -> list[dict]:
        """Tạo messages cho LLM."""
        context = self.build_context_string(retrieved_docs)
        
        user_prompt = (
            "Dựa vào các Ngữ cảnh sau đây, hãy trả lời câu hỏi của người dùng.\n\n"
            f"<NGỮ CẢNH>\n{context}\n</NGỮ CẢNH>\n\n"
            f"Câu hỏi: {query}\n\n"
            "Yêu cầu bổ sung:\n"
            "- Trích dẫn [ID] ở cuối mỗi câu nếu lấy từ ngữ cảnh.\n"
            "- Tổng hợp thành các gạch đầu dòng (bullet points) dễ hiểu.\n"
            "- Đảm bảo văn phong đồng cảm, nhẹ nhàng nhưng kiên quyết về mặt an toàn y khoa."
        )
        
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
