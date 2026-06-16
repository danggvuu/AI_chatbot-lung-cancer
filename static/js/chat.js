document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatMessages = document.getElementById("chat-messages");
    const stopBtn = document.getElementById("stop-btn");
    const sendBtn = document.getElementById("send-btn");
    const statusDot = document.getElementById("status-dot");
    const statusText = document.getElementById("status-text");
    const modelBadge = document.getElementById("model-badge");
    const emergencyBanner = document.getElementById("emergency-banner");
    const closeBannerBtn = document.getElementById("close-banner-btn");
    
    // Tab Elements
    const tabActiveSources = document.getElementById("tab-active-sources");
    const tabAllSources = document.getElementById("tab-all-sources");
    const paneActiveSources = document.getElementById("pane-active-sources");
    const paneAllSources = document.getElementById("pane-all-sources");
    const activeSourcesEmpty = document.getElementById("active-sources-empty");
    const activeSourcesList = document.getElementById("active-sources-list");
    const allSourcesList = document.getElementById("all-sources-list");
    const totalChunksCount = document.getElementById("total-chunks-count");
    
    // Suggested Prompts
    const promptBtns = document.querySelectorAll(".prompt-btn");

    // Chat History State
    let conversationHistory = [
        {
            role: "assistant",
            content: "Xin chào! Tôi là LungCare AI, trợ lý ảo hỗ trợ thông tin y khoa về ung thư phổi. Tôi có thể giúp bạn tìm hiểu về triệu chứng nhận biết sớm, đối tượng cần sàng lọc, yếu tố nguy cơ, và tổng quan các phương pháp điều trị hiện nay. Bạn muốn hỏi tôi điều gì?"
        }
    ];
    let currentSources = [];

    // Initialize Page
    checkSystemStatus();
    loadAllSources();
    setupEventListeners();

    let isGenerating = false;
    let abortController = null;

    // Event Listeners Setup
    function setupEventListeners() {
        // Close Warning Banner
        if (closeBannerBtn && emergencyBanner) {
            closeBannerBtn.addEventListener("click", () => {
                emergencyBanner.classList.add("hidden");
            });
        }

        // Stop generation button
        if (stopBtn) {
            stopBtn.addEventListener("click", () => {
                if (abortController) {
                    abortController.abort();
                }
            });
        }

        // Tab Switching
        tabActiveSources.addEventListener("click", () => switchTab("active-sources"));
        tabAllSources.addEventListener("click", () => switchTab("all-sources"));

        // Prompt Suggestions
        promptBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                if (isGenerating) return;
                const promptText = btn.getAttribute("data-prompt");
                chatInput.value = promptText;
                chatForm.dispatchEvent(new Event("submit"));
            });
        });

        // Chat Form Submission
        chatForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (isGenerating) return;
            
            const query = chatInput.value.trim();
            if (!query) return;

            isGenerating = true;

            chatInput.value = "";
            chatInput.disabled = true;
            if (sendBtn) {
                sendBtn.disabled = true;
                sendBtn.classList.add("hidden");
            }
            if (stopBtn) stopBtn.classList.remove("hidden");

            appendMessage("user", query);
            conversationHistory.push({ role: "user", content: query });

            const typingIndicator = showTypingIndicator();

            try {
                abortController = new AbortController();
                const response = await fetch("/api/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ 
                        messages: conversationHistory,
                        stream: true
                    }),
                    signal: abortController.signal
                });

                if (!response.ok) {
                    const data = await response.json();
                    typingIndicator.remove();
                    const errMsg = data.error || "Có lỗi xảy ra khi kết nối tới máy chủ.";
                    appendMessage("assistant", `⚠️ **Lỗi:** ${errMsg}\n\n*Chi tiết:* ${data.detail || "Không có"}`);
                    return;
                }

                typingIndicator.remove();

                const assistantMessageDiv = appendEmptyMessage("assistant");
                const contentDiv = assistantMessageDiv.querySelector(".message-content");
                let fullText = "";

                const reader = response.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let buffer = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split("\n");
                    
                    buffer = lines.pop();

                    for (const line of lines) {
                        const cleanLine = line.trim();
                        if (!cleanLine || !cleanLine.startsWith("data: ")) continue;

                        try {
                            const jsonData = JSON.parse(cleanLine.substring(6));
                            
                            if (jsonData.sources) {
                                currentSources = jsonData.sources;
                                renderActiveSources(jsonData.sources);
                            } 
                            else if (jsonData.delta) {
                                fullText += jsonData.delta;
                                contentDiv.innerHTML = parseMarkdown(fullText);
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                            }
                            else if (jsonData.error) {
                                contentDiv.innerHTML += `<br>⚠️ **Lỗi:** ${jsonData.error}`;
                            }
                        } catch (errParser) {
                            console.error("Failed to parse stream line", errParser, cleanLine);
                        }
                    }
                }

                conversationHistory.push({ role: "assistant", content: fullText });

            } catch (err) {
                typingIndicator.remove();
                if (err.name === 'AbortError') {
                    appendMessage("assistant", `*(Bạn đã ngừng tạo phản hồi)*`);
                } else {
                    appendMessage("assistant", `⚠️ **Lỗi kết nối:** Không thể kết nối tới máy chủ. Vui lòng kiểm tra xem server đã được khởi chạy chưa.`);
                    console.error(err);
                }
            } finally {
                isGenerating = false;
                abortController = null;
                chatInput.disabled = false;
                if (sendBtn) {
                    sendBtn.disabled = false;
                    sendBtn.classList.remove("hidden");
                }
                if (stopBtn) stopBtn.classList.add("hidden");
                chatInput.focus();
            }
        });

        // Click citation link to highlight & scroll to source card
        document.addEventListener("click", (e) => {
            const link = e.target.closest(".citation-link");
            if (link) {
                if (link.getAttribute("href") === "#") {
                    e.preventDefault();
                }
                const citationIdx = parseInt(link.getAttribute("data-citation")) - 1;
                
                switchTab("active-sources");
                
                const cards = activeSourcesList.querySelectorAll(".source-card");
                if (citationIdx >= 0 && citationIdx < cards.length) {
                    const targetCard = cards[citationIdx];
                    
                    targetCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
                    
                    targetCard.classList.remove("highlight-flash");
                    void targetCard.offsetWidth;
                    targetCard.classList.add("highlight-flash");
                }
            }
        });
    }

    // Check Backend & Ollama health
    async function checkSystemStatus() {
        statusDot.className = "status-dot loading";
        statusText.textContent = "Đang kiểm tra kết nối...";
        
        try {
            const res = await fetch("/api/health");
            const data = await res.json();
            
            if (res.ok && data.status === "healthy") {
                if (data.ollama_connection === "online") {
                    statusDot.className = "status-dot online";
                    statusText.textContent = `Ollama Sẵn Sàng (${data.ollama_model})`;
                    modelBadge.textContent = `Model: ${data.ollama_model}`;
                } else {
                    statusDot.className = "status-dot offline";
                    statusText.textContent = "Ollama Ngoại Tuyến (Chưa bật)";
                    modelBadge.textContent = "Ollama Offline";
                }
            } else {
                statusDot.className = "status-dot offline";
                statusText.textContent = "Lỗi hệ thống";
            }
        } catch (err) {
            statusDot.className = "status-dot offline";
            statusText.textContent = "Mất kết nối Server";
        }
    }

    // Determine badge class from source name
    function getBadgeClass(sourceName) {
        if (sourceName.includes("Bệnh viện K") || sourceName === "Bệnh viện K") return "badge-bvk";
        if (sourceName.includes("Tâm Anh")) return "badge-tamanh";
        if (sourceName.includes("Vinmec")) return "badge-vinmec";
        if (sourceName.includes("Bạch Mai")) return "badge-bachmai";
        if (sourceName.includes("Bộ Y tế")) return "badge-byt";
        return "badge-tamanh";
    }

    // Load all scraped sources for the database tab
    async function loadAllSources() {
        try {
            const res = await fetch("/api/sources");
            if (!res.ok) return;
            const sources = await res.json();
            
            totalChunksCount.textContent = sources.length;
            
            if (sources.length === 0) {
                allSourcesList.innerHTML = `<div class="empty-state"><p>Không có dữ liệu sẵn.</p></div>`;
                return;
            }

            allSourcesList.innerHTML = "";
            
            sources.forEach(src => {
                const card = document.createElement("div");
                card.className = "source-card";
                card.id = `all-src-${src.id}`;
                
                const badgeClass = getBadgeClass(src.source);
                
                card.innerHTML = `
                    <div class="source-card-header">
                        <span class="source-card-badge badge ${badgeClass}">${src.source}</span>
                        <span class="source-card-id" style="font-size:0.75rem; color:var(--text-muted)">ID: #${src.id}</span>
                    </div>
                    <div class="source-card-title">${src.title}</div>
                    <div class="source-card-section">Mục: ${src.section_title}</div>
                    <a href="${src.url}" target="_blank" rel="noopener" class="source-card-link">
                        Xem bài gốc 🔗
                    </a>
                `;
                allSourcesList.appendChild(card);
            });
        } catch (err) {
            console.error("Error loading sources:", err);
            allSourcesList.innerHTML = `<div class="empty-state"><p>Không thể tải dữ liệu.</p></div>`;
        }
    }

    // Switch between reference tabs
    function switchTab(tabName) {
        if (tabName === "active-sources") {
            tabActiveSources.classList.add("active");
            tabAllSources.classList.remove("active");
            paneActiveSources.classList.add("active");
            paneAllSources.classList.remove("active");
        } else {
            tabActiveSources.classList.remove("active");
            tabAllSources.classList.add("active");
            paneActiveSources.classList.remove("active");
            paneAllSources.classList.add("active");
        }
    }

    // Render active sources cited for the current response
    function renderActiveSources(sources) {
        if (!sources || sources.length === 0) {
            activeSourcesEmpty.classList.remove("hidden");
            activeSourcesList.classList.add("hidden");
            return;
        }

        activeSourcesEmpty.classList.add("hidden");
        activeSourcesList.classList.remove("hidden");
        activeSourcesList.innerHTML = "";

        sources.forEach((src, index) => {
            const card = document.createElement("div");
            card.className = "source-card highlighted";
            
            const badgeClass = getBadgeClass(src.source);
            
            card.innerHTML = `
                <div class="source-card-header">
                    <span class="source-card-badge badge ${badgeClass}">${src.source}</span>
                    <span class="badge" style="background-color: var(--accent-color); color: white; font-size: 0.75rem; border-radius: 4px; padding: 2px 6px;">Tài liệu [${index + 1}]</span>
                    <span style="font-size:0.75rem; color:var(--text-muted)">ID Match: #${src.id}</span>
                </div>
                <div class="source-card-title">${src.title}</div>
                <div class="source-card-section">Phần đối chiếu: ${src.section_title}</div>
                <div class="source-card-snippet">"${src.snippet}"</div>
                <a href="${src.url}" target="_blank" rel="noopener" class="source-card-link">
                    Xem bài gốc 🔗
                </a>
            `;
            activeSourcesList.appendChild(card);
        });

        switchTab("active-sources");
    }

    // Append a message bubble to the chat feed
    function appendMessage(role, text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${role}-message`;

        const avatar = role === "user" ? "👤" : "🫁";
        const parsedHTML = parseMarkdown(text);

        msgDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                ${parsedHTML}
            </div>
        `;

        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Append an empty assistant message bubble for streaming
    function appendEmptyMessage(role) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${role}-message`;
        const avatar = role === "user" ? "👤" : "🫁";
        msgDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content"></div>
        `;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return msgDiv;
    }

    // Show loading typing indicator
    function showTypingIndicator() {
        const indicatorDiv = document.createElement("div");
        indicatorDiv.className = "message assistant-message typing-indicator-container";
        indicatorDiv.innerHTML = `
            <div class="message-avatar">🫁</div>
            <div class="message-content" style="padding: 10px 14px;">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        chatMessages.appendChild(indicatorDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return indicatorDiv;
    }

    // Get short source name for citation display
    function getShortSourceName(sourceName) {
        return sourceName
            .replace("Bệnh viện ", "")
            .replace("Báo ", "")
            .replace("Bộ ", "");
    }

    // Lightweight Markdown parser
    function parseMarkdown(text) {
        let html = text;

        html = html
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        html = html.replace(/\*\*([\s\S]*?)\*\*/g, "<strong>$1</strong>");
        html = html.replace(/\*([\s\S]*?)\*/g, "<em>$1</em>");
        html = html.replace(/_([\s\S]*?)_/g, "<em>$1</em>");

        html = html.replace(/\[([1-4])\]/g, (match, p1) => {
            const idx = parseInt(p1) - 1;
            const src = (currentSources && currentSources[idx]) ? currentSources[idx] : null;
            if (src) {
                const shortSource = getShortSourceName(src.source);
                return `<a href="${src.url}" target="_blank" rel="noopener" class="citation-link" data-citation="${p1}">[${p1} - ${shortSource}]</a>`;
            }
            return `<a href="#" class="citation-link" data-citation="${p1}">[${p1}]</a>`;
        });

        html = html.replace(/^&gt; (.*$)/gim, '<blockquote>$1</blockquote>');

        const lines = html.split("\n");
        let inList = false;
        let listHTML = [];

        for (let i = 0; i < lines.length; i++) {
            let line = lines[i].trim();
            if (line.startsWith("- ") || line.startsWith("* ") || line.startsWith("&lt;li&gt;") || line.startsWith("• ")) {
                if (!inList) {
                    listHTML.push("<ul>");
                    inList = true;
                }
                const content = line.substring(2);
                listHTML.push(`<li>${content}</li>`);
            } else {
                if (inList) {
                    listHTML.push("</ul>");
                    inList = false;
                }
                listHTML.push(lines[i]);
            }
        }
        if (inList) {
            listHTML.push("</ul>");
        }
        
        html = listHTML.join("\n");

        html = html.split("\n\n").map(p => {
            p = p.trim();
            if (!p) return "";
            if (p.startsWith("<ul") || p.startsWith("<ol") || p.startsWith("<blockquote")) return p;
            return `<p>${p.replace(/\n/g, "<br>")}</p>`;
        }).join("");

        return html;
    }
});
