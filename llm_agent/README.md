# LLM Agent Module (Phục vụ Phase 2 - Pentest Lab)

Thư mục này được thiết kế để chứa các mô-đun LLM Agent ở **Giai đoạn 2 (Phase 2)** của luận văn/dự án.

## Dự kiến ở Phase 2:
1. **MCP Client Wrapper**: Kết nối LLM Agent (dùng OpenAI API, Claude API, hoặc Ollama LLaMA-3 cục bộ) tới `mcp_server/server.py`.
2. **System Prompts**: Cấu hình các vai trò LLM Trợ lý vận hành nhà máy sản xuất.
3. **Attack Scripts**: Kịch bản thực thi Prompt Injection tự động (Direct Injection, Indirect Prompt Injection qua SOP manual, Tool Poisoning, Excessive Agency).
