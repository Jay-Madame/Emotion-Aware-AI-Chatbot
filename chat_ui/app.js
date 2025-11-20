// ===================== Authentication & Configuration =====================
const CONVO_KEY = "chatui_convos_v2";
const MAX_CONVOS = 50;
const SUBMIT_THROTTLE_MS = 120;
const RETRY_SECONDS = 5;

const now = () => Date.now();

// Auto-detect environment for API
const isLocalhost =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1";

const API_BASE = isLocalhost ? "http://localhost:8000" : "";
const CHAT_URL = `${API_BASE}/chat`;

// --- Global State ---
let basicAuthToken = ''; 
let convos = [];
let activeId = null;
let lastSubmitAt = 0;

// --- DOM Elements (Login + Main App) ---
const mainAppContainer = document.getElementById('mainAppContainer');
const loginOverlay = document.getElementById('loginOverlay');
const loginForm = document.getElementById('loginForm');
const loginButton = document.getElementById('loginButton');
const statusMessage = document.getElementById('statusMessage');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');

// --- Helper Functions (Original Chat UI Helpers) ---

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

/**
 * Encodes username and password into a Base64 string for Basic Auth.
 */
const encodeCredentials = (username, password) => {
    const credentials = `${username}:${password}`;
    return btoa(credentials);
};


// ===================== Login Gate Logic =====================

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = usernameInput.value;
    const password = passwordInput.value;
    
    const encoded = encodeCredentials(username, password);
    const token = `Basic ${encoded}`;
    
    // Disable form submission and show loading status
    loginButton.disabled = true;
    usernameInput.disabled = true;
    passwordInput.disabled = true;
    statusMessage.className = 'status-message status-loading';
    statusMessage.textContent = 'Attempting login...';

    try {
        // Use the secured /users/me endpoint to validate the credentials
        const response = await fetch(`${API_BASE}/users/me`, {
            method: 'GET',
            headers: {
                'Authorization': token,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            // Success: Store the token and switch views
            basicAuthToken = token;
            statusMessage.className = 'status-message status-success';
            statusMessage.textContent = 'Login successful!';
            
            // Wait 500ms before showing the main app and STARTING THE CHAT UI
            setTimeout(() => {
                loginOverlay.style.display = 'none';
                mainAppContainer.style.display = 'grid'; 
                startChatUI(); // *** Crucial: Start the main application here ***
            }, 500);

        } else if (response.status === 401) {
            // Failure: Show error and implement 5-second retry
            statusMessage.className = 'status-message status-error';
            
            let countdown = RETRY_SECONDS;
            statusMessage.textContent = `Login failed. Retrying in ${countdown} seconds...`;
            
            const interval = setInterval(() => {
                countdown -= 1;
                statusMessage.textContent = `Login failed. Retrying in ${countdown} seconds...`;
                if (countdown <= 0) {
                    clearInterval(interval);
                    statusMessage.textContent = 'Ready to try again.';
                    loginButton.disabled = false;
                    usernameInput.disabled = false;
                    passwordInput.disabled = false;
                }
            }, 1000);

        } else {
            // Other errors
            statusMessage.className = 'status-message status-error';
            statusMessage.textContent = 'An unknown server error occurred. Try again.';
            loginButton.disabled = false;
            usernameInput.disabled = false;
            passwordInput.disabled = false;
        }
    } catch (error) {
        console.error('Network Error:', error);
        statusMessage.className = 'status-message status-error';
        statusMessage.textContent = 'Network error. Check your server connection.';
        loginButton.disabled = false;
        usernameInput.disabled = false;
        passwordInput.disabled = false;
    }
});

// Initial focus on username field when the page loads
document.addEventListener('DOMContentLoaded', () => {
    usernameInput.focus();
    convos = loadConvos(); // Load conversations early
    activeId = (convos[0]?.id) || null;
});


// ===================== Chat UI Logic (startChatUI) =====================

function startChatUI() {
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

    // bgpanel elements
    const botPanelSprite = document.getElementById("botPanelSprite"); 
    const botStageImg = document.getElementById("botStageImg");       
    const botStageText = document.getElementById("botStageText");     

    // Since DOM elements were already verified, proceed with chat setup
    
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
        // console.log("setBotStage:", stage); // Keep this commented unless debugging
    }

    function resetBotStageToIdleLater() {
        setTimeout(() => {
            setBotStage("idle");
        }, 2000);
    }

    // initial state
    setBotStage("idle");


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
        if (!convos.length) {
            createConversation();
            return;
        }
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
                // Use a custom modal in a real app, but prompt is okay for dev
                const val = prompt("Rename chat:", c.title || "New chat"); 
                if (val != null) renameConversation(c.id, val);
            });
            book.addEventListener("contextmenu", (e) => {
                e.preventDefault();
                // Use a custom modal in a real app
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
        if (!c) {
            messages.innerHTML = "";
            return;
        }

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
            // Use a custom modal in a real app
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
                // when text fully rendered, relax to idle after a moment
                resetBotStageToIdleLater();
            }
        };

        tick();
    }

    // ---------- API call (UPDATED with Authorization Header) ----------
    async function sendToBackend(userText) {
        const res = await fetch(CHAT_URL, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                // *** IMPORTANT: Add the Basic Auth Token here ***
                "Authorization": basicAuthToken 
            },
            body: JSON.stringify({ message: userText }),
        });
        
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

    // ---------- Submit handler (uses sprite stages + typing) ----------
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = input.value.trim();
        if (!text) return;

        // Optimistic UI: add user message
        appendMessage("user", text);
        addMessage(text, "me");
        input.value = "";
        autoResize();

        // bot goes into "thinking" animation as soon as user sends
        setBotStage("thinking");

        // Placeholder assistant bubble we'll type into
        const placeholder = addMessage("", "bot", true);

        try {
            const reply = await sendToBackend(text);

            // store in history
            appendMessage("assistant", reply);

            // switch to "writing" animation while we type reply into bubble
            setBotStage("writing");

            // type text into placeholder
            streamBotReplyInto(placeholder, reply);
        } catch (err) {
            const msg = (err && err.message) ? err.message : "Network error.";
            setBotStage("error");
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
            const delta = now() - t;
            if (delta < delayMs) {
                cancelAnimationFrame(rAF);
            }
            t = now();
            rAF = requestAnimationFrame(() => fn(...args));
        };
    }

    // Final checks and render after successful login
    if (!convos.length) createConversation();
    renderConvos();
    renderMessages();
    input.focus();
}