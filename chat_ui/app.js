// ===================== app.js (full integration) =====================
// - Slack-style sending: Enter=Send, Shift+Enter=newline
// - Multi-conversation storage in localStorage
// - Horizontal "bookshelf" convo picker with tooltips, search, top +New
(() => {
    const CONVO_KEY = "chatui_convos_v2";
    const MAX_CONVOS = 50;
    const TYPING_STEP_TARGET = 80;
    const SUBMIT_THROTTLE_MS = 120;
    const now = () => Date.now();

    // >>> ADD: point this at your API
    const BACKEND_URL = "http://localhost:8000/chat";

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

        if (!shelf || !messages || !form || !input) {
            console.error("Chat UI elements not found.");
            return;
        }

        let convos = loadConvos();
        let activeId = (convos[0]?.id) || null;
        let lastSubmitAt = 0;

        if (!convos.length) createConversation();
        renderConvos();
        renderMessages();

        // ---------- helpers ----------
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

            // Keep input in sync unless user is currently editing
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

        // ---------- title input + delete button ----------
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

        // ---------- Submit handler (calls backend) ----------
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const text = input.value.trim();
            if (!text) return;

            // Optimistic UI: add user message
            appendMessage("user", text);
            addMessage(text, "me");
            input.value = "";
            autoResize();

            // Add a placeholder assistant bubble we can update
            const placeholder = addMessage("...", "bot", /*returnEl*/ true);

            try {
                const reply = await sendToBackend(text);
                // Save & render assistant message
                appendMessage("assistant", reply);
                placeholder.textContent = "";
                streamBotReplyInto(placeholder, reply); // type-on effect
            } catch (err) {
                const msg = (err && err.message) ? err.message : "Network error.";
                placeholder.textContent = `⚠️ ${msg}`;
            }
        });

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

        // ---------- API call ----------
        async function sendToBackend(userText) {
            const res = await fetch(BACKEND_URL, {
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

        function streamBotReplyInto(div, fullText) {
            let i = 0;
            const step = Math.max(2, Math.floor(fullText.length / TYPING_STEP_TARGET));
            const tick = () => {
                i += step;
                div.textContent = fullText.slice(0, i);
                messages.scrollTop = messages.scrollHeight;
                if (i < fullText.length) requestAnimationFrame(tick);
            };
            requestAnimationFrame(tick);
        }

        // Optional keyboard nav across books
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
