import os
import sys
import json
import csv
import datetime
import subprocess
from urllib.parse import urlparse

# Ensure absolute imports work regardless of run directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_pipeline.cleaners.noise_filter import NoiseFilter
from data_pipeline.cleaners.deduplicator import Deduplicator

class FirecrawlIngester:
    def __init__(self, api_key=None, api_url=None):
        self.api_key = api_key or os.environ.get("FIRECRAWL_API_KEY")
        self.api_url = api_url or os.environ.get("FIRECRAWL_API_URL", "https://api.firecrawl.dev")
        self.noise_filter = NoiseFilter()
        self.deduplicator = Deduplicator(similarity_threshold=0.85)

    def parse_markdown(self, markdown_text: str, url: str, source_name: str, fallback_title: str) -> list[dict]:
        """
        Parses Markdown text from Firecrawl into section-based chunks.
        Splits sections on markdown headings (##, ###) and collects paragraph content.
        """
        if not markdown_text:
            return []

        lines = markdown_text.split('\n')
        title = fallback_title
        
        # Look for the first H1 header for title
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith('# '):
                title = line_stripped[2:].strip()
                break

        sections = []
        current_section = "Tổng quan"
        current_content = []

        # Split content on ## or ### headers
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith('## ') or line_stripped.startswith('### '):
                if current_content:
                    content_str = "\n".join(current_content).strip()
                    # Filter and add
                    if len(content_str) >= 100:
                        sections.append({
                            "source": source_name,
                            "url": url,
                            "title": title,
                            "section_title": current_section,
                            "content": content_str,
                            "priority": "hospital",
                            "source_type": "firecrawl",
                            "last_updated": datetime.date.today().isoformat()
                        })
                current_section = line_stripped.lstrip('#').strip()
                current_content = []
            elif line_stripped.startswith('# '):
                # Skip main H1 title
                continue
            else:
                current_content.append(line)

        # Add the remaining text section
        if current_content:
            content_str = "\n".join(current_content).strip()
            if len(content_str) >= 100:
                sections.append({
                    "source": source_name,
                    "url": url,
                    "title": title,
                    "section_title": current_section,
                    "content": content_str,
                    "priority": "hospital",
                    "source_type": "firecrawl",
                    "last_updated": datetime.date.today().isoformat()
                })

        return sections

    def ingest_url(self, url: str, mode: str = "scrape") -> dict:
        """
        Scrapes or crawls a URL using Firecrawl, cleans/filters, and adds to database.
        Returns execution log summary.
        """
        if not self.api_key:
            raise ValueError(
                "Chưa có Firecrawl API Key. Hãy đặt biến môi trường FIRECRAWL_API_KEY hoặc điền khóa API."
            )

        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=self.api_key, api_url=self.api_url)

        domain = urlparse(url).netloc
        source_name = domain.replace("www.", "")
        
        status_log = []
        new_chunks = []
        
        # Load existing database to retrieve existing texts for deduplication
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        kb_path = os.path.join(project_root, "data", "knowledge_base.json")
        csv_path = os.path.join(project_root, "data", "knowledge_base.csv")
        
        existing_data = []
        if os.path.exists(kb_path):
            with open(kb_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        
        existing_texts = [doc["content"] for doc in existing_data]

        status_log.append(f"🔌 Kết nối tới Firecrawl API: {self.api_url}")
        
        try:
            if mode == "scrape":
                status_log.append(f"📥 Đang cào dữ liệu đơn lẻ từ URL: {url}...")
                result = app.scrape_url(url, formats=["markdown"])
                
                # Convert BaseModel to dict
                if hasattr(result, "model_dump"):
                    result_dict = result.model_dump()
                elif hasattr(result, "dict"):
                    result_dict = result.dict()
                else:
                    result_dict = dict(result)
                
                markdown = result_dict.get("markdown", "")
                title = result_dict.get("metadata", {}).get("title", "Thông tin từ " + source_name)
                
                raw_docs = self.parse_markdown(markdown, url, source_name, title)
                status_log.append(f"📑 Trích xuất được {len(raw_docs)} đoạn văn thô.")
                
                # Filter and deduplicate
                for doc in raw_docs:
                    # 1. Noise Filter
                    if self.noise_filter.is_noise(doc["content"]):
                        continue
                    
                    # 2. Deduplicator
                    if not self.deduplicator.is_duplicate(doc["content"], existing_texts):
                        new_chunks.append(doc)
                        existing_texts.append(doc["content"])
                
            elif mode == "crawl":
                status_log.append(f"🕸️ Đang quét (crawl) toàn bộ website từ: {url} (Giới hạn tối đa 5 trang)...")
                # Wait for crawl (limits to 5 pages for safety/quota)
                crawl_status = app.crawl_url(url, limit=5, formats=["markdown"])
                
                # Convert BaseModel to dict
                if hasattr(crawl_status, "model_dump"):
                    crawl_dict = crawl_status.model_dump()
                elif hasattr(crawl_status, "dict"):
                    crawl_dict = crawl_status.dict()
                else:
                    crawl_dict = dict(crawl_status)
                
                pages = crawl_dict.get("data", [])
                status_log.append(f"✅ Quét xong. Tìm thấy {len(pages)} trang.")
                
                for page in pages:
                    page_url = page.get("metadata", {}).get("sourceURL", url)
                    page_markdown = page.get("markdown", "")
                    page_title = page.get("metadata", {}).get("title", "Thông tin từ " + source_name)
                    
                    page_docs = self.parse_markdown(page_markdown, page_url, source_name, page_title)
                    
                    for doc in page_docs:
                        if self.noise_filter.is_noise(doc["content"]):
                            continue
                        if not self.deduplicator.is_duplicate(doc["content"], existing_texts):
                            new_chunks.append(doc)
                            existing_texts.append(doc["content"])
            
            # Save new chunks if any
            if new_chunks:
                status_log.append(f"✨ Lọc trùng lặp & tin rác thành công. Nhận được {len(new_chunks)} đoạn chất lượng mới.")
                
                # Append and re-assign IDs
                combined_data = existing_data + new_chunks
                for i, chunk in enumerate(combined_data):
                    chunk["id"] = i + 1
                    
                with open(kb_path, "w", encoding="utf-8") as f:
                    json.dump(combined_data, f, ensure_ascii=False, indent=2)
                
                # Save as CSV with UTF-8 BOM
                with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=["id", "source", "url", "title", "section_title", "content", "priority", "source_type", "last_updated"])
                    writer.writeheader()
                    # standard fields check
                    for chunk in combined_data:
                        writer.writerow({
                            "id": chunk.get("id"),
                            "source": chunk.get("source"),
                            "url": chunk.get("url"),
                            "title": chunk.get("title"),
                            "section_title": chunk.get("section_title"),
                            "content": chunk.get("content"),
                            "priority": chunk.get("priority", "hospital"),
                            "source_type": chunk.get("source_type", "firecrawl"),
                            "last_updated": chunk.get("last_updated", "")
                        })
                
                status_log.append("💾 Đã lưu thành công vào cơ sở dữ liệu JSON và CSV.")
                
                # Trigger R stats update
                try:
                    r_script_path = os.path.join(project_root, "analyze_kb.R")
                    if os.path.exists(r_script_path):
                        status_log.append("📊 Đang cập nhật lại biểu đồ thống kê R...")
                        subprocess.run(["Rscript", r_script_path], cwd=project_root, check=True)
                        status_log.append("✅ Đã cập nhật xong biểu đồ thống kê R.")
                except Exception as r_err:
                    status_log.append(f"⚠️ Không thể cập nhật biểu đồ R: {str(r_err)}")
                    
            else:
                status_log.append("ℹ️ Không tìm thấy nội dung y văn mới (tất cả đều bị trùng hoặc không đủ điều kiện).")
                
            return {
                "success": True,
                "chunks_added": len(new_chunks),
                "log": "\n".join(status_log),
                "chunks": new_chunks
            }
            
        except Exception as e:
            status_log.append(f"❌ Xảy ra lỗi trong quá trình cào: {str(e)}")
            return {
                "success": False,
                "chunks_added": 0,
                "log": "\n".join(status_log),
                "chunks": []
            }
