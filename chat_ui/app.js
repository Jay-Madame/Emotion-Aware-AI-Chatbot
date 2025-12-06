// ===================== app.js (JWT Authentication Version) =====================
// - Uses JWT tokens stored in localStorage from login.html
// - Redirects to login.html if not authenticated
// - Slack-style sending: Enter=Send, Shift+Enter=newline
// - Multi-conversation storage in localStorage
// - Horizontal "bookshelf" convo picker with tooltips, search, top +New
// - Bot sprite animation in bgpanel (idle -> thinking -> writing -> error)

console.log('App.js loaded - Starting initialization...');

(() => {
    const CONVO_KEY = "chatui_convos_v2";
    const MAX_CONVOS = 50;
    const SUBMIT_THROTTLE_MS = 120;
    const now = () => Date.now();

    // Auto-detect environment:
    const isLocalhost =
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1";

    const API_BASE = isLocalhost ? "http://localhost:8000" : "";
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
        try {
            return JSON.parse(json);
        } catch {
            return fallback;
        }
    }

    function loadConvos() {
        const raw = localStorage.getItem(CONVO_KEY);
        const arr = safeParse(raw, []);
        return Array.isArray(arr) ? arr : [];
    }
    
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

    // ---------- Authentication Check ----------
    function checkAuth() {
        const token = localStorage.getItem('access_token');
        const userId = localStorage.getItem('user_id');
        
        if (!token || !userId) {
            // Redirect to login if not authenticated
            window.location.href = 'login.html';
            return false;
        }
        return true;
    }

    // ---------- Load Chat History from Database ----------
    async function loadChatHistoryFromDB() {
        const userId = localStorage.getItem('user_id');
        if (!userId) return;

        try {
            const response = await fetch(`${API_BASE}/chat/history/${userId}?limit=50`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                console.warn('Could not load chat history from database');
                return;
            }

            const data = await response.json();
            console.log(`📚 Loaded ${data.messages.length} messages from database`);

            // Convert database messages to conversations
            // Group messages into a single conversation for now
            if (data.messages.length > 0) {
                const existingConvo = convos.find(c => c.title === "Previous Chats");
                
                if (!existingConvo) {
                    // Create a conversation from database history
                    const dbConvo = {
                        id: "db-history",
                        title: "Previous Chats",
                        createdAt: new Date(data.messages[data.messages.length - 1].timestamp).getTime(),
                        updatedAt: new Date(data.messages[0].timestamp).getTime(),
                        messages: []
                    };

                    // Add messages in chronological order (oldest first)
                    data.messages.reverse().forEach(msg => {
                        dbConvo.messages.push({
                            role: "user",
                            text: msg.message
                        });
                        dbConvo.messages.push({
                            role: "assistant",
                            text: msg.response
                        });
                    });

                    convos.unshift(dbConvo); // Add to beginning
                    saveConvos();
                    console.log('Created conversation from database history');
                }
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
        }
    }

    // ---------- Logout Function ----------
    function logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_id');
        localStorage.removeItem('username');
        localStorage.removeItem('email');
        window.location.href = 'login.html';
    }

    document.addEventListener("DOMContentLoaded", init, { once: true });

    function init() {
        console.log('🔍 Init function called');
        
        // Check authentication first
        if (!checkAuth()) {
            console.log('Authentication check failed, should redirect');
            return;
        }
        
        console.log('Authentication passed');

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

        console.log('📦 Elements found:', {
            shelf: !!shelf,
            messages: !!messages,
            form: !!form,
            input: !!input
        });

        // bgpanel elements
        const botPanelSprite = document.getElementById("botPanelSprite");
        const botStageImg = document.getElementById("botStageImg");
        const botStageText = document.getElementById("botStageText");

        if (!shelf || !messages || !form || !input) {
            console.error("Chat UI elements not found.");
            return;
        }
        
        console.log('All required elements found, continuing initialization...');

        // ---------- User Menu Setup ----------
        const userMenuButton = document.getElementById('userMenuButton');
        const userMenuDropdown = document.getElementById('userMenuDropdown');
        const userMenuName = document.getElementById('userMenuName');
        const userMenuEmail = document.getElementById('userMenuEmail');
        const logoutBtn = document.getElementById('logoutBtn');
        const changePasswordBtn = document.getElementById('changePasswordBtn');

        // Set user info
        const username = localStorage.getItem('username') || 'User';
        const email = localStorage.getItem('email') || '';
        if (userMenuName) userMenuName.textContent = username;
        if (userMenuEmail) userMenuEmail.textContent = email;

        // Toggle dropdown
        if (userMenuButton && userMenuDropdown) {
            userMenuButton.addEventListener('click', (e) => {
                e.stopPropagation();
                userMenuDropdown.classList.toggle('active');
            });

            // Close dropdown when clicking outside
            document.addEventListener('click', (e) => {
                if (!userMenuDropdown.contains(e.target) && !userMenuButton.contains(e.target)) {
                    userMenuDropdown.classList.remove('active');
                }
            });
        }

        // Logout handler
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                if (confirm('Are you sure you want to logout?')) {
                    logout();
                }
            });
        }

        // Change password handler
        if (changePasswordBtn) {
            changePasswordBtn.addEventListener('click', () => {
                userMenuDropdown.classList.remove('active');
                window.location.href = 'change-password.html';
            });
        }

        // Hide login overlay and show main app (if index.html still has overlay)
        const loginOverlay = document.getElementById("loginOverlay");
        const mainAppContainer = document.getElementById("mainAppContainer");
        if (loginOverlay) loginOverlay.style.display = 'none';
        if (mainAppContainer) mainAppContainer.style.display = 'grid';

        let convos = loadConvos();
        let activeId = null;
        let lastSubmitAt = 0;

        // Load chat history from database
        loadChatHistoryFromDB().then(() => {
            console.log('Chat history loaded from database');
            if (convos.length === 0) {
                createConversation();
            } else {
                activeId = convos[0].id;
                renderConvos();
                renderMessages();
            }
        });

        // ---------- BOT SPRITE ANIMATION SETUP ----------
        const BOT_SPRITE_SEQUENCES = {
            idle: [
                "Images/Wait1.png",
                "Images/Wait2.png",
                "Images/Wait3.png",
                "Images/Wait4.png"
            ],
            thinking: [
                "Images/Think1.png",
                "Images/Think2.png",
                "Images/Think3.png"
            ],
            writing: [
                "Images/Wait1.png",
                "Images/Wait2.png",
                "Images/Wait3.png",
                "Images/Wait4.png"
            ],
            error: [
                "Images/Wait1.png"
            ]
        };

        const BOT_STAGE_TEXT = {
            idle: "Ready to chat",
            thinking: "Thinking…",
            writing: "Writing a reply…",
            error: "Error talking to the server."
        };

        const BOT_STAGE_FRAME_DELAY = {
            idle: 650,
            thinking: 260,
            writing: 180,
            error: 500
        };

        let botStage = "idle";
        let botFrameIndex = 0;
        let botFrameTimerId = null;

        function startBotFrameLoop() {
            if (!botStageText) return;

            if (botFrameTimerId) {
                clearInterval(botFrameTimerId);
                botFrameTimerId = null;
            }

            const seq = BOT_SPRITE_SEQUENCES[botStage] || [];
            if (!seq.length) return;

            botFrameIndex = 0;

            const first = seq[botFrameIndex];
            if (botStageImg) botStageImg.src = first;
            if (botPanelSprite) botPanelSprite.src = first;

            const delay = BOT_STAGE_FRAME_DELAY[botStage] || 400;

            botFrameTimerId = setInterval(() => {
                botFrameIndex = (botFrameIndex + 1) % seq.length;
                const frame = seq[botFrameIndex];
                if (botStageImg) botStageImg.src = frame;
                if (botPanelSprite) botPanelSprite.src = frame;
            }, delay);
        }

        function setBotStage(stage) {
            if (!BOT_SPRITE_SEQUENCES[stage]) {
                stage = "idle";
            }
            botStage = stage;

            if (botStageText) {
                botStageText.textContent = BOT_STAGE_TEXT[stage] || "";
            }

            startBotFrameLoop();
        }

        function resetBotStageToIdleLater() {
            setTimeout(() => {
                setBotStage("idle");
            }, 2000);
        }

        // initial state
        setBotStage("idle");

        // ---------- conversation management ----------
        function saveConvos() {
            try {
                const sorted = [...convos].sort((a, b) => b.updatedAt - a.updatedAt);
                const trimmed = sorted.slice(0, MAX_CONVOS);
                localStorage.setItem(CONVO_KEY, JSON.stringify(trimmed));
                convos = trimmed;
            } catch (err) {
                console.error("saveConvos error:", err);
            }
        }

        function findConvo(id) {
            return convos.find(c => c.id === id);
        }

        function createConversation(firstMessage = "") {
            const id = uuid();
            const c = {
                id,
                title: "New chat",
                createdAt: now(),
                updatedAt: now(),
                messages: []
            };
            if (firstMessage) {
                c.messages.push({ role: "user", text: firstMessage });
            }
            convos.push(c);
            saveConvos();
            switchTo(id);
        }

        function switchTo(id) {
            activeId = id;
            renderConvos();
            renderMessages();
        }

        function deleteConversation(id) {
            convos = convos.filter(c => c.id !== id);
            saveConvos();

            if (activeId === id) {
                activeId = convos.length > 0 ? convos[0].id : null;
            }
            renderConvos();
            renderMessages();
        }

        function renameConversation(id, newTitle) {
            const c = findConvo(id);
            if (!c) return;
            c.title = newTitle;
            c.updatedAt = now();
            saveConvos();
            renderConvos();
            updateShelfInfo();
        }

        function appendMessage(role, text) {
            const c = findConvo(activeId);
            if (!c) return;
            c.messages.push({ role, text });
            c.updatedAt = now();
            saveConvos();
        }

        // ---------- bookshelf render ----------
        function renderConvos(filterStr = "") {
            const frag = document.createDocumentFragment();

            const filtered = filterStr
                ? convos.filter(c => c.title.toLowerCase().includes(filterStr))
                : convos;

            const sorted = [...filtered].sort((a, b) => b.updatedAt - a.updatedAt);

            sorted.forEach(c => {
                const div = document.createElement("div");
                div.className = "book";
                if (c.id === activeId) div.classList.add("active");

                const band = document.createElement("div");
                band.className = "book__band";
                div.appendChild(band);

                const tt = document.createElement("div");
                tt.className = "book__tt";
                tt.textContent = c.title || "New chat";
                div.appendChild(tt);

                div.addEventListener("click", () => switchTo(c.id));
                frag.appendChild(div);
            });

            // "+New" book
            const newBook = document.createElement("div");
            newBook.className = "book book--new";
            newBook.addEventListener("click", () => createConversation());
            frag.appendChild(newBook);

            requestAnimationFrame(() => {
                shelf.innerHTML = "";
                shelf.appendChild(frag);
            });
        }

        // ---------- message render ----------
        function renderMessages() {
            const c = findConvo(activeId);
            const frag = document.createDocumentFragment();
            if (c) {
                for (const m of c.messages) {
                    const div = document.createElement("div");
                    div.className = "msg" + (m.role === "user" ? " me" : "");
                    div.textContent = m.text;
                    frag.appendChild(div);
                }
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
            const c = findConvo(activeId);
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

        // Typing animation for reply text
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

        // ---------- API call with JWT ----------
        async function sendToBackend(userText) {
            const userId = localStorage.getItem('user_id');
            
            if (!userId) {
                throw new Error("User session lost. Please log in again.");
            }

            // Build chat history from current conversation
            const c = findConvo(activeId);
            const chatHistory = c ? c.messages.map(m => ({
                role: m.role === "user" ? "user" : "assistant",
                content: m.text
            })) : [];

            const res = await fetch(CHAT_URL, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ 
                    message: userText,
                    user_id: parseInt(userId),
                    chat_history: chatHistory
                }),
            });

            if (res.status === 401 || res.status === 403) {
                logout();
                throw new Error("Authentication expired. Please log in again.");
            }
            
            if (res.status === 404) {
                throw new Error("User not found. Please log in again.");
            }
            
            if (!res.ok) {
                let detail = "";
                try {
                    detail = (await res.json()).detail;
                } catch { }
                throw new Error(detail || `HTTP ${res.status}`);
            }
            const data = await res.json();
            return data.reply || "";
        }

        // ---------- Submit handler ----------
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const text = input.value.trim();
            if (!text) return;

            // Create conversation if needed
            if (!activeId || !findConvo(activeId)) {
                createConversation();
            }

            // Optimistic UI: add user message
            appendMessage("user", text);
            addMessage(text, "me");
            input.value = "";
            autoResize();

            setBotStage("thinking");

            const placeholder = addMessage("", "bot", true);

            try {
                const reply = await sendToBackend(text);
                appendMessage("assistant", reply);
                setBotStage("writing");
                streamBotReplyInto(placeholder, reply);
            } catch (err) {
                const msg = (err && err.message) ? err.message : "Network error.";
                setBotStage("error");
                placeholder.textContent = ` ${msg}`;
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

        // ---------- Initial render ----------
        // Note: Initial render moved to after loadChatHistoryFromDB() completes
    }
})();