import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.firecrawl_ingester import FirecrawlIngester
from data_pipeline.cleaners.noise_filter import NoiseFilter
from data_pipeline.cleaners.deduplicator import Deduplicator

def test_markdown_parser():
    ingester = FirecrawlIngester(api_key="mock_key")
    
    markdown = """# Ung thư phổi và các triệu chứng
    
    ## Triệu chứng lâm sàng
    Đây là triệu chứng lâm sàng của ung thư phổi bao gồm ho kéo dài, đau ngực và khó thở ở người lớn. Hãy liên hệ bác sĩ nếu có dấu hiệu trên.
    
    ### Chẩn đoán
    Chụp cắt lớp vi tính liều thấp LDCT là phương pháp chẩn đoán sàng lọc ung thư phổi hữu ích nhất hiện nay.
    
    ## Liên hệ đặt lịch khám
    Hotline đặt lịch khám của bệnh viện là 1900xxxx. Gọi ngay để được tư vấn miễn phí.
    """
    
    results = ingester.parse_markdown(markdown, "http://test.com", "test_source", "Fallback Title")
    
    # Assertions
    assert len(results) >= 2
    assert results[0]["title"] == "Ung thư phổi và các triệu chứng"
    assert results[0]["section_title"] == "Triệu chứng lâm sàng"
    assert "đau ngực và khó thở" in results[0]["content"]
    assert results[1]["section_title"] == "Chẩn đoán"
    
def test_noise_filter():
    filter_tool = NoiseFilter()
    
    # Clean text
    clean_text = "Chụp cắt lớp vi tính ngực liều thấp là một tiến bộ lớn của lĩnh vực sàng lọc ung thư phổi giúp phát hiện sớm khối u khi còn nhỏ."
    assert not filter_tool.is_noise(clean_text)
    
    # Noise text (too short)
    short_text = "Liên hệ ngay."
    assert filter_tool.is_noise(short_text)
    
    # Noise text (too many promotional keywords)
    promo_text = "Đặt lịch khám trực tuyến ngay hôm nay. Hãy gọi hotline tổng đài tư vấn sức khỏe của chúng tôi để được tư vấn miễn phí tại chuyên khoa."
    assert filter_tool.is_noise(promo_text)

def test_deduplicator():
    dedup = Deduplicator(similarity_threshold=0.85)
    
    existing = [
        "Ung thư phổi tế bào nhỏ chiếm 15% tổng số ca mắc bệnh và có liên quan mật thiết đến việc hút thuốc lá lâu năm ở nam giới."
    ]
    
    # Highly similar (duplicate, just missing the period at the end)
    dup_text = "Ung thư phổi tế bào nhỏ chiếm 15% tổng số ca mắc bệnh và có liên quan mật thiết đến việc hút thuốc lá lâu năm ở nam giới"
    assert dedup.is_duplicate(dup_text, existing)
    
    # Different text (non-duplicate)
    diff_text = "Chụp CT ngực liều thấp là phương thức sàng lọc hiệu quả giúp giảm thiểu tỷ lệ tử vong do ung thư phổi giai đoạn muộn."
    assert not dedup.is_duplicate(diff_text, existing)

if __name__ == "__main__":
    print("🧪 Running Firecrawl Ingestion Unit Tests...")
    test_markdown_parser()
    print("✅ Markdown Parser Test Passed!")
    test_noise_filter()
    print("✅ Noise Filter Test Passed!")
    test_deduplicator()
    print("✅ Deduplicator Test Passed!")
    print("🎉 All Tests Passed Successfully!")
