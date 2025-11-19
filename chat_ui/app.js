// ===================== app.js (full integration) =====================
// - Slack-style sending: Enter=Send, Shift+Enter=newline
// - Multi-conversation storage in localStorage
// - Horizontal "bookshelf" convo picker with tooltips, search, top +New
// - Bot stage animation in bottom-left bgpanel (waiting -> thinking -> writing)
(() => {
    
    const CONVO_KEY = "chatui_convos_v2";
    const MAX_CONVOS = 50;
    const SUBMIT_THROTTLE_MS = 120;
    const now = () => Date.now();

    // --- FIX APPLIED HERE ---
    // The API_BASE is set to "" (empty string) so that the browser 
    // uses the current deployed URL (e.g., https://your-app.onrender.com) 
    // when requesting the /chat endpoint.
    const API_BASE = ""; 
    
    // Full chat endpoint
    const CHAT_URL = `${API_BASE}/chat`;

    function uuid() {
        if (crypto && crypto.randomUUID) return crypto.randomUUID();
        return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
            const r = (Math.random() * 16) | 0;
            const v = c === "x" ? r : (r & 0x3) | 0x8;
            return v.toString(16);
        });
    }

    function safeParse(json, fallback) {
        try { return JSON.parse(json); } catch { return fallback; }
    }

    function loadConvos() {
        const raw = localStorage.getItem(CONVO_KEY);
        const arr = safeParse(raw, []);
        return Array.isArray(arr) ? arr : [];
    }

    document.addEventListener("DOMContentLoaded", init, { once: true });

    function init() {
        const shelf = document.getElementById("convoShelf");
        const chatSearch = document.getElementById("chatSearch");
        const newChatTop = document.getElementById("newChatTop");
        const shelfInfo = document.getElementById("shelfInfo");
        const chatTitleInput = document.getElementById("chatTitleInput");
        const shelfMeta = document.getElementById("shelfMeta");
        const deleteChatBtn = document.getElementById("deleteChatBtn");
        const messages = document.getElementById("messages");
        const form = document.getElementById("composer");
        const input = document.getElementById("input");

        // NEW: bgpanel stage elements
        const botStageImg = document.getElementById("botStageImg");
        const botStageText = document.getElementById("botStageText");

        if (!shelf || !messages || !form || !input) {
            console.error("Chat UI elements not found.");
            return;
        }

        let convos = loadConvos();
        let activeId = (convos[0]?.id) || null;
        let lastSubmitAt = 0;

        // ---------- bot stage controller ----------
        let stageInterval = null;

        function setBotStage(stage, dots = 0) {
            if (!botStageImg || !botStageText) return;

            switch (stage) {
                case "idle":
                    botStageImg.src = "Images/temp-idle.png";   // adjust if needed
                    botStageText.textContent = "Ready to chat";
                    break;
                case "waiting":
                    botStageImg.src = "Images/temp-waiting.png";
                    botStageText.textContent = "Waiting…";
                    break;
                case "thinking":
                    botStageImg.src = "Images/temp-thinking.png";
                    botStageText.textContent = "Thinking" + ".".repeat(dots);
                    break;
                case "writing":
                    botStageImg.src = "Images/temp-writing.png";
                    botStageText.textContent = "Writing a reply…";
                    break;
                case "error":
                    botStageImg.src = "Images/temp-thinking.png"; // or a dedicated error icon
                    botStageText.textContent = "Error talking to the server.";
                    break;
            }

            console.log("setBotStage:", stage, dots); 
        }

        function resetBotStageToIdleLater() {
            // After some delay, go back to idle so it doesn't stay on "writing" forever
            setTimeout(() => {
                setBotStage("idle");
            }, 2000);
        }

        function startBotStageCycle() {
            if (!botStageImg || !botStageText) {
                return {
                    toWriting() { },
                    showError() { },
                    stop() { }
                };
            }

            // Clear any previous animation
            if (stageInterval) clearInterval(stageInterval);

            let state = "waiting";
            let dots = 0;
            const startTime = Date.now();

            setBotStage("waiting");

            stageInterval = setInterval(() => {
                const elapsed = Date.now() - startTime;

                if (elapsed > 500 && state === "waiting") {
                    state = "thinking";
                    dots = 0;
                } else if (state === "thinking") {
                    dots = (dots + 1) % 4;
                }

                if (state === "waiting") {
                    setBotStage("waiting");
                } else if (state === "thinking") {
                    setBotStage("thinking", dots);
                }
            }, 350);

            return {
                toWriting() {
                    if (stageInterval) clearInterval(stageInterval);
                    setBotStage("writing");
                },
                showError() {
                    if (stageInterval) clearInterval(stageInterval);
                    setBotStage("error");
                },
                stop() {
                    if (stageInterval) clearInterval(stageInterval);
                    setBotStage("idle");
                }
            };
        }

        // Set initial idle state
        setBotStage("idle");

        // ---------- initial setup ----------
        if (!convos.length) createConversation();
        renderConvos();
        renderMessages();

        // ---------- persistence helpers ----------
        function saveConvos() {
            try {
                localStorage.setItem(CONVO_KEY, JSON.stringify(convos.slice(0, MAX_CONVOS)));
            } catch (e) {
                console.warn("localStorage save failed:", e);
            }
        }

        function createConversation(title = "New chat") {
            const id = uuid();
            const convo = { id, title, createdAt: now(), updatedAt: now(), messages: [] };
            convos = [convo, ...convos].slice(0, MAX_CONVOS);
            activeId = id;
            saveConvos();
            renderConvos();
            renderMessages();
            return id;
        }

        function setActiveConversation(id) {
            activeId = id;
            renderConvos(chatSearch?.value.trim().toLowerCase() || "");
            renderMessages();
        }

        function renameConversation(id, title) {
            const c = convos.find(x => x.id === id);
            if (!c) return;
            const trimmed = (title || "").trim();
            if (trimmed) {
                c.title = trimmed;
            }
            c.updatedAt = now();
            saveConvos();
            renderConvos(chatSearch?.value.trim().toLowerCase() || "");
            updateShelfInfo();
        }

        function deleteConversation(id) {
            const i = convos.findIndex(x => x.id === id);
            if (i >= 0) {
                convos.splice(i, 1);
                if (activeId === id) {
                    activeId = convos[0]?.id || null;
                    if (!activeId) {
                        createConversation();
                    }
                }
                saveConvos();
                renderConvos(chatSearch?.value.trim().toLowerCase() || "");
                renderMessages();
            }
        }

        function appendMessage(role, text) {
            const c = convos.find(x => x.id === activeId) || convos[0];
            if (!c) return;
            c.messages.push({ id: uuid(), role, text, ts: now() });
            c.updatedAt = now();
            if (role === "user" && (!c.title || c.title === "New chat") && c.messages.length === 1) {
                const t = text.trim().replace(/\s+/g, " ").slice(0, 40);
                c.title = t || "New chat";
            }
            saveConvos();
        }

        // ---------- render bookshelf ----------
        function renderConvos(query = "") {
            if (!convos.length) { createConversation(); return; }
            const list = query
                ? convos.filter(c => (c.title || "New chat").toLowerCase().includes(query))
                : convos;

            const frag = document.createDocumentFragment();

            const newBook = document.createElement("div");
            newBook.className = "book book--new";
            newBook.title = "New chat";
            newBook.setAttribute("aria-label", "New chat");
            newBook.addEventListener("click", () => createConversation());
            frag.appendChild(newBook);

            list.forEach(c => {
                const book = document.createElement("div");
                book.className = "book" + (c.id === activeId ? " active" : "");
                book.dataset.id = c.id;
                book.setAttribute("role", "button");
                book.setAttribute("tabindex", "0");
                book.setAttribute("aria-label", c.title || "New chat");

                const band = document.createElement("div");
                band.className = "book__band";
                book.appendChild(band);

                const tt = document.createElement("div");
                tt.className = "book__tt";
                tt.textContent = c.title || "New chat";
                book.appendChild(tt);

                book.addEventListener("click", () => setActiveConversation(c.id));
                book.addEventListener("dblclick", () => {
                    const val = prompt("Rename chat:", c.title || "New chat");
                    if (val != null) renameConversation(c.id, val);
                });
                book.addEventListener("contextmenu", (e) => {
                    e.preventDefault();
                    if (confirm("Delete this conversation?")) deleteConversation(c.id);
                });

                frag.appendChild(book);
            });

            requestAnimationFrame(() => {
                shelf.innerHTML = "";
                shelf.appendChild(frag);
                updateShelfInfo();
            });
        }

        // ---------- render messages ----------
        function renderMessages() {
            const c = convos.find(x => x.id === activeId);
            if (!c) { messages.innerHTML = ""; return; }

            const frag = document.createDocumentFragment();
            for (const m of c.messages) {
                const div = document.createElement("div");
                div.className = "msg" + (m.role === "user" ? " me" : "");
                div.textContent = m.text;
                frag.appendChild(div);
            }
            requestAnimationFrame(() => {
                messages.innerHTML = "";
                messages.appendChild(frag);
                messages.scrollTop = messages.scrollHeight;
                updateShelfInfo();
            });
        }

        // ---------- info strip ----------
        function updateShelfInfo() {
            if (!shelfInfo) return;
            const c = convos.find(x => x.id === activeId);
            if (!c) {
                if (chatTitleInput && document.activeElement !== chatTitleInput) {
                    chatTitleInput.value = "";
                }
                if (shelfMeta) shelfMeta.textContent = "";
                return;
            }
            const count = c.messages.length;
            const updated = new Date(c.updatedAt).toLocaleString();

            if (chatTitleInput && document.activeElement !== chatTitleInput) {
                chatTitleInput.value = c.title || "New chat";
            }
            if (shelfMeta) {
                shelfMeta.textContent = `${count} message${count === 1 ? "" : "s"} • updated ${updated}`;
            }
        }

        // ---------- top controls ----------
        if (newChatTop) {
            newChatTop.addEventListener("click", () => createConversation());
        }
        if (chatSearch) {
            chatSearch.addEventListener("input", () => {
                renderConvos(chatSearch.value.trim().toLowerCase());
            });
        }

        // ---------- title input + delete ----------
        function renameActiveFromInput() {
            if (!chatTitleInput || !activeId) return;
            const val = chatTitleInput.value.trim();
            if (!val) return;
            renameConversation(activeId, val);
        }

        if (chatTitleInput) {
            chatTitleInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    renameActiveFromInput();
                    chatTitleInput.blur();
                }
            });
            chatTitleInput.addEventListener("blur", () => {
                renameActiveFromInput();
            });
        }

        if (deleteChatBtn) {
            deleteChatBtn.addEventListener("click", () => {
                if (!activeId) return;
                if (confirm("Delete this conversation?")) {
                    deleteConversation(activeId);
                }
            });
        }

        // ---------- Composer: Slack-style Enter ----------
        input.addEventListener("keydown", (e) => {
            if (e.isComposing) return;
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                const t = now();
                if (t - lastSubmitAt > SUBMIT_THROTTLE_MS) {
                    lastSubmitAt = t;
                    form.requestSubmit();
                }
            }
        });

        input.addEventListener("input", debounceRAF(autoResize, 0));
        function autoResize() {
            input.style.height = "auto";
            input.style.height = Math.min(input.scrollHeight, window.innerHeight * 0.3) + "px";
        }

        window.addEventListener("keydown", (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
                e.preventDefault();
                input.focus();
            }
        }, { passive: false });

        // ---------- message helpers ----------
        function addMessage(text, who = "bot", returnEl = false) {
            const div = document.createElement("div");
            div.className = "msg" + (who === "me" ? " me" : "");
            div.textContent = text;
            requestAnimationFrame(() => {
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
            });
            return returnEl ? div : undefined;
        }

        // Typing animation for reply text in chat area
        function streamBotReplyInto(div, fullText) {
            if (!div) return;
            let i = 0;
            const step = 1;
            const delayMs = 15;

            const tick = () => {
                i += step;
                div.textContent = fullText.slice(0, i);
                messages.scrollTop = messages.scrollHeight;
                if (i < fullText.length) {
                    setTimeout(tick, delayMs);
                } else {
                    resetBotStageToIdleLater();
                }
            };

            tick();
        }

        // ---------- API call ----------
        async function sendToBackend(userText) {
            const res = await fetch(CHAT_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: userText }),
            });
            if (!res.ok) {
                let detail = "";
                try { detail = (await res.json()).detail; } catch { }
                throw new Error(detail || `HTTP ${res.status}`);
            }
            const data = await res.json();
            return data.reply || "";
        }


        // ---------- Submit handler (uses bgpanel stage + typing) ----------
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const text = input.value.trim();
            if (!text) return;

            // Optimistic UI: add user message
            appendMessage("user", text);
            addMessage(text, "me");
            input.value = "";
            autoResize();

            // Start librarian animation (waiting -> thinking)
            const stage = startBotStageCycle();

            // Placeholder assistant bubble we'll type into
            const placeholder = addMessage("", "bot", true);

            try {
                const reply = await sendToBackend(text);

                // store in history
                appendMessage("assistant", reply);

                // librarian goes to "writing" mode
                stage.toWriting();

                // type text into placeholder
                streamBotReplyInto(placeholder, reply);
            } catch (err) {
                const msg = (err && err.message) ? err.message : "Network error.";
                stage.showError();
                placeholder.textContent = `⚠️ ${msg}`;
                resetBotStageToIdleLater();
            }
        });

        // ---------- bookshelf keyboard nav ----------
        shelf.addEventListener("keydown", (e) => {
            if (!["ArrowLeft", "ArrowRight"].includes(e.key)) return;
            const books = [...shelf.querySelectorAll(".book")];
            const i = books.findIndex(b => b.classList.contains("active"));
            const next = e.key === "ArrowRight"
                ? Math.min(i + 1, books.length - 1)
                : Math.max(i - 1, 0);
            books[next]?.click();
            books[next]?.scrollIntoView({ behavior: "smooth", inline: "center" });
        });

        // ---------- debounce helper ----------
        function debounceRAF(fn, delayMs = 0) {
            let t = 0, rAF = 0;
            return (...args) => {
                if (t) clearTimeout(t);
                t = setTimeout(() => {
                    if (rAF) cancelAnimationFrame(rAF);
                    rAF = requestAnimationFrame(() => fn(...args));
                }, delayMs);
            };
        }
    }
})();