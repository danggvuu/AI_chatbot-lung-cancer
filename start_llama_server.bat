@echo off
chcp 65001 >nul
echo.
echo   🤖  ╔══════════════════════════════════════════╗
echo       ║    LungCare AI - Llama.cpp GPU Server    ║
echo       ║   Khởi chạy mô hình trên card đồ họa GPU   ║
echo       ╚══════════════════════════════════════════╝
echo.

if not exist "qwen2.5-3b-instruct-q4_k_m.gguf" (
    echo   ❌  Không tìm thấy tệp model 'qwen2.5-3b-instruct-q4_k_m.gguf' ở thư mục gốc của dự án!
    echo       Vui lòng sao chép tệp model này vào thư mục dự án này và chạy lại file bat này.
    echo.
    pause
    exit /b 1
)

echo   ⏳  Đang khởi chạy llama-server.exe trên GPU (VRAM)...
echo   💡  Sử dụng tham số -ngl 99 để đẩy toàn bộ mô hình lên GPU VRAM.
echo   💡  Cấu hình kích thước ngữ cảnh lớn -c 16384 (16k) để chứa RAG tốt nhất.
echo   💡  Chạy đơn luồng để tránh chia nhỏ ngữ cảnh và quá tải GPU.
echo   💡  Giữ cửa sổ này mở để chatbot hoạt động.
echo.

llama_cpp\llama-server.exe -m qwen2.5-3b-instruct-q4_k_m.gguf -c 16384 --port 8080 --host 0.0.0.0 -ngl 99
