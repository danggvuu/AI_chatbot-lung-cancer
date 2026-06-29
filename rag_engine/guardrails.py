class Guardrails:
    def __init__(self, settings=None):
        self.settings = settings or {}
        # Các ngưỡng an toàn
        self.min_retrieval_score = self.settings.get("guardrails", {}).get("min_retrieval_score", 1.0)
        
    def should_abstain(self, retrieved_docs: list[dict]) -> bool:
        """Kiểm tra xem hệ thống có nên từ chối trả lời do thiếu thông tin không.
        Đã vô hiệu hóa để LLM tự quyết định và vẫn có thể đưa ra cảnh báo cấp cứu.
        """
        return False
        
    def get_abstention_message(self) -> str:
        return (
            "Dựa trên cơ sở dữ liệu hiện tại, tôi không có đủ thông tin y khoa chính thống "
            "để trả lời câu hỏi này. Vui lòng tham khảo ý kiến trực tiếp từ bác sĩ chuyên khoa "
            "hoặc tái khám tại bệnh viện để được tư vấn chính xác nhất."
        )
