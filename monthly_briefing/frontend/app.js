const API_BASE = "http://127.0.0.1:8001/api";

// Elements
const monthPicker = document.getElementById('monthPicker');
const yearPicker = document.getElementById('yearPicker');
const fetchBtn = document.getElementById('fetchBtn');
const exportBtn = document.getElementById('exportBtn');
const newsContainer = document.getElementById('newsContainer');
const statusMessage = document.getElementById('statusMessage');
const sourcesContainer = document.getElementById('sourcesContainer');

// Init Date Picker to current month/year
const now = new Date();
monthPicker.value = now.getMonth();
yearPicker.value = now.getFullYear();

// Config
const SECTIONS = [
    "IFC Portfolio / Pipeline Highlights",
    "Macro Indicators",
    "Policy & Political Economy",
    "Financial Institutions & Capital Markets",
    "Real-Sector Deal Flow",
    "Uncategorized"
];

const AVAILABLE_SOURCES = [
    { id: 'gmail', label: 'Google Alerts' },
    { id: 'dsa', label: 'DealStreetAsia' },
    { id: 'The Business Times', label: 'The Business Times' },
    { id: 'The Straits Times', label: 'The Straits Times' },
    { id: 'Channel News Asia', label: 'Channel News Asia' },
    { id: 'Fintech News SG', label: 'Fintech News SG' },
    { id: 'The Diplomat', label: 'The Diplomat' },
    { id: 'ft', label: 'Financial Times' },
    { id: 'google', label: 'Google Research' }
];

// Initialize UI
renderSourceSelection();

function renderSourceSelection() {
    sourcesContainer.innerHTML = '';
    AVAILABLE_SOURCES.forEach(src => {
        const label = document.createElement('label');
        label.style = "display: flex; align-items: center; gap: 6px; font-size: 0.9rem; cursor: pointer; user-select: none;";

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = src.id;
        checkbox.checked = true; // Default all checked
        checkbox.style = "accent-color: var(--primary-color); width: 16px; height: 16px;";

        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(src.label));
        sourcesContainer.appendChild(label);
    });
}

function getSelectedSources() {
    const checkboxes = sourcesContainer.querySelectorAll('input[type="checkbox"]');
    const selected = [];
    checkboxes.forEach(cb => {
        if (cb.checked) selected.push(cb.value);
    });
    return selected;
}

// Events
fetchBtn.addEventListener('click', fetchNews);
exportBtn.addEventListener('click', exportNews);

const termLog = document.getElementById('logTerminal');
const processingView = document.getElementById('processingView');
const timeRemainingEl = document.getElementById('timeRemaining');

const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');
const step3 = document.getElementById('step3');
const aiStatusText = document.getElementById('aiStatusText');
const miniProgressBar = document.getElementById('miniProgressBar');
const toggleLogBtn = document.getElementById('toggleLogBtn');
const logCollapsible = document.getElementById('logCollapsible');


function updateStep(stepNumber) {
    // Reset all
    [step1, step2, step3].forEach((el, index) => {
        const num = index + 1;
        el.classList.remove('active', 'done');
        if (num < stepNumber) {
            el.classList.add('done');
        } else if (num === stepNumber) {
            el.classList.add('active');
        }
    });
}

async function fetchNews() {
    const selectedSources = getSelectedSources();
    if (selectedSources.length === 0) {
        alert("Please select at least one source.");
        return;
    }

    // Reset UI
    newsContainer.innerHTML = '';
    statusMessage.textContent = '';
    termLog.innerHTML = '';
    processingView.classList.remove('hidden');
    newsContainer.style.display = 'none';

    // Checkboxes disabled
    setLoading(true);

    // Initial State
    updateStep(1);
    timeRemainingEl.textContent = 'Estimating...';
    aiStatusText.textContent = "Waiting for content...";
    miniProgressBar.style.width = '0%';

    // Close log if open
    logCollapsible.classList.add('closed');
    toggleLogBtn.textContent = 'View detailed logs';

    const year = parseInt(yearPicker.value);
    const month = parseInt(monthPicker.value);

    // Start Date: 1st of selected month
    const dateStart = new Date(year, month, 1);

    // End Date: 1st of next month (backend should handle < end logic)
    // Or last day of month. Let's send start and end inclusive or exclusive?
    // Let's send start of next month as the upper bound (exclusive) often easier.
    const dateEnd = new Date(year, month + 1, 1);

    let curatingStartedTime = null;

    try {
        const response = await fetch(`${API_BASE}/fetch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                date_start: dateStart.toISOString(),
                date_end: dateEnd.toISOString(),
                sources: selectedSources
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            let lines = buffer.split("\n");
            buffer = lines.pop();

            for (let line of lines) {
                if (!line.trim()) continue;
                try {
                    const event = JSON.parse(line);
                    handleEvent(event);
                } catch (e) {
                    console.error("JSON parse error", e, line);
                }
            }
        }
    } catch (e) {
        addLog(`Critical Error: ${e.message}`, 'log-error');
        console.error(e);
        statusMessage.textContent = "Error fetching news. See logs.";
        setLoading(false);
    }

    function handleEvent(e) {
        if (e.type === 'log') {
            addLog(e.message, 'log-log');

            // Logic to advance steps based on messages
            const msg = e.message.toLowerCase();

            if (msg.includes("starting ai curation") || msg.includes("analysis pending")) {
                updateStep(2);
                aiStatusText.textContent = "Analyzing relevance...";
            }
            else if (msg.includes("curation complete")) {
                updateStep(3);
            }
        }
        else if (e.type === 'error') {
            addLog(e.message, 'log-error');
        }
        else if (e.type === 'progress') {
            console.log("Progress Event Received:", e);
            if (!curatingStartedTime) curatingStartedTime = Date.now();
            updateStep(2); // Ensure we are on step 2

            const pct = Math.round((e.completed / e.total) * 100);
            miniProgressBar.style.width = `${pct}%`;

            // Show Item Count in real time as requested
            let statusPrefix = `Analysing item ${e.completed} of ${e.total}`;
            if (e.currentItem) {
                aiStatusText.textContent = `${statusPrefix} (${e.currentItem})...`;
            } else {
                aiStatusText.textContent = `${statusPrefix}...`;
            }

            // Calc Time - Safely
            if (e.completed > 0) {
                const elapsed = (Date.now() - curatingStartedTime) / 1000;
                const rate = elapsed / e.completed;
                const remaining = Math.ceil((e.total - e.completed) * rate);

                // Only update if we have a sane estimation
                if (remaining >= 0 && isFinite(remaining)) {
                    if (remaining < 60) timeRemainingEl.textContent = `~${remaining}s remaining`;
                    else timeRemainingEl.textContent = `~${Math.floor(remaining / 60)}m ${remaining % 60}s remaining`;
                }
            }
        }
        else if (e.type === 'result') {
            finishProcessing(e);
        }
    }

    function finishProcessing(resultEvent) {
        updateStep(3);
        // Wait a slight moment for "done" animation to register visually before showing content
        setLoading(false);

        // Don't fully hide processing view immediately? or maybe collapse it?
        // Let's hide it to show news, as that's the goal.
        setTimeout(() => {
            processingView.classList.add('hidden');
            newsContainer.style.display = 'block';

            // Check if resultEvent has new structure (relevant/rejected) or old (array)
            // The API now returns { relevant: [], rejected: [] }
            // If legacy array, treat as relevant.
            let relevant = [];
            let rejected = [];

            if (Array.isArray(resultEvent.data)) {
                relevant = resultEvent.data;
            } else if (resultEvent.relevant || resultEvent.rejected) {
                relevant = resultEvent.relevant || [];
                rejected = resultEvent.rejected || [];
            }

            renderNews(relevant, rejected);
            statusMessage.textContent = `Loaded ${relevant.length} relevant items. (${rejected.length} rejected)`;
        }, 800);
    }
}

function addLog(msg, className = 'log-log') {
    const div = document.createElement('div');
    div.className = `log-line ${className}`;
    div.textContent = msg;
    termLog.appendChild(div);
    termLog.scrollTop = termLog.scrollHeight;
}

function toggleLog() {
    const el = document.getElementById('logCollapsible');
    const btn = document.getElementById('toggleLogBtn');
    el.classList.toggle('closed');
    if (el.classList.contains('closed')) {
        btn.textContent = 'View detailed logs';
    } else {
        btn.textContent = 'Hide detailed logs';
    }
}

async function exportNews() {
    try {
        const response = await fetch(`${API_BASE}/export`);
        const data = await response.json();

        // 1. Copy to clipboard
        const type = "text/html";
        const blob = new Blob([data.html], { type });
        const dataItem = [new ClipboardItem({ [type]: blob })];
        await navigator.clipboard.write(dataItem);

        alert("Briefing HTML copied to clipboard! You can paste it directly into Outlook.");

        // 2. Try mailto (only valid if short enough, usually fails for full daily updates)
        // window.location.href = `mailto:?subject=Daily Update`; 

    } catch (e) {
        alert("Failed to export: " + e.message);
    }
}

function renderNews(relevantItems, rejectedItems = []) {
    newsContainer.innerHTML = "";

    // Group by section
    const grouped = {};
    SECTIONS.forEach(s => grouped[s] = []);

    relevantItems.forEach(item => {
        let sec = item.section;
        if (!SECTIONS.includes(sec)) {
            sec = "Uncategorized";
        }

        if (grouped[sec]) {
            grouped[sec].push(item);
        }
    });

    SECTIONS.forEach(sectionName => {
        const sectionItems = grouped[sectionName];
        if (!sectionItems) return; // Should not happen with init

        const sectionEl = document.createElement('div');
        sectionEl.className = 'section';

        const headerEl = document.createElement('div');
        headerEl.className = 'section-header';
        headerEl.innerHTML = `<h2>${sectionName} (${sectionItems.length})</h2>`;
        sectionEl.appendChild(headerEl);

        const contentEl = document.createElement('div');
        contentEl.className = 'section-content';

        if (sectionItems.length === 0) {
            contentEl.innerHTML = `<div style="padding:1rem; color:#999; font-style:italic;">No items found.</div>`;
        } else {
            // Special sorting for Real-Sector
            let itemsToRender = sectionItems;
            if (sectionName === "Real-Sector Deal Flow") {
                const inr = sectionItems.filter(i => i.subsection === "INR (Infrastructure)");
                const mas = sectionItems.filter(i => i.subsection === "MAS (Manufacturing, Agribusiness, Services)");
                const others = sectionItems.filter(i => i.subsection !== "INR (Infrastructure)" && i.subsection !== "MAS (Manufacturing, Agribusiness, Services)");

                if (inr.length) {
                    contentEl.appendChild(createSubsectionHeader("INR (Infrastructure)"));
                    inr.forEach(item => contentEl.appendChild(createItemEl(item)));
                }
                if (mas.length) {
                    contentEl.appendChild(createSubsectionHeader("MAS (Manufacturing, Agribusiness, Services)"));
                    mas.forEach(item => contentEl.appendChild(createItemEl(item)));
                }
                if (others.length) {
                    contentEl.appendChild(createSubsectionHeader("General"));
                    others.forEach(item => contentEl.appendChild(createItemEl(item)));
                }
            } else {
                itemsToRender.forEach(item => {
                    contentEl.appendChild(createItemEl(item));
                });
            }
        }

        sectionEl.appendChild(contentEl);
        newsContainer.appendChild(sectionEl);
    });

    // Render Rejected Section
    if (rejectedItems.length > 0) {
        renderRejectedSection(rejectedItems);
    }
}

function renderRejectedSection(items) {
    const sectionEl = document.createElement('div');
    sectionEl.className = 'section';
    sectionEl.style.opacity = '0.8'; // Visual distinction

    const headerEl = document.createElement('div');
    headerEl.className = 'section-header';
    headerEl.innerHTML = `<h2 style="color: #888;">Rejected Candidates (${items.length})</h2>`; // Muted header
    sectionEl.appendChild(headerEl);

    const contentEl = document.createElement('div');
    contentEl.className = 'section-content';

    // items.forEach(item => contentEl.appendChild(createItemEl(item, true)));
    // We need a specialized createItemEl or modify the existing one to handle 'restore'
    items.forEach(item => {
        contentEl.appendChild(createRejectedItemEl(item));
    });

    sectionEl.appendChild(contentEl);
    newsContainer.appendChild(sectionEl);
}

function createSubsectionHeader(title) {
    const div = document.createElement('div');
    div.className = 'subsection-header';
    div.textContent = title;
    return div;
}

function createRejectedItemEl(item) {
    const el = document.createElement('div');
    el.className = 'news-item';
    el.style.borderColor = '#e5e7eb'; // Gray border
    el.style.background = '#f9fafb';
    el.id = `item-${item.id}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'item-content';

    const headline = document.createElement('div');
    headline.className = 'item-headline text-clamped';
    headline.style.color = '#6b7280'; // Muted text
    headline.textContent = item.headline;
    headline.title = item.headline;

    // Toggle expand
    headline.onclick = () => {
        headline.classList.toggle('text-clamped');
        headline.classList.toggle('text-expanded');
    };

    const meta = document.createElement('div');
    meta.className = 'item-meta';

    const sourceLink = document.createElement('a');
    sourceLink.href = item.url;
    sourceLink.target = "_blank";
    sourceLink.style = "color: inherit; text-decoration: underline;";
    sourceLink.textContent = item.source;

    meta.appendChild(sourceLink);

    contentDiv.appendChild(headline);

    // Reason
    if (item.relevance_reason) {
        const reasonEl = document.createElement('div');
        reasonEl.className = 'item-reason';
        reasonEl.style.color = '#ef4444'; // Red for rejection reason
        reasonEl.textContent = `Rejected: ${item.relevance_reason}`;
        contentDiv.appendChild(reasonEl);
    }

    contentDiv.appendChild(meta);

    // Actions
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'actions-group';

    // Add Back Button
    const addBackBtn = createIconBtn('Add Back', 'icon-add', `
        <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" style="color: #10b981;">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="16"></line>
            <line x1="8" y1="12" x2="16" y2="12"></line>
        </svg>
    `);
    addBackBtn.onclick = () => restoreItem(item.id, el, addBackBtn);

    actionsDiv.appendChild(addBackBtn);

    el.appendChild(contentDiv);
    el.appendChild(actionsDiv);

    return el;
}

function createItemEl(item) {
    const el = document.createElement('div');
    el.className = 'news-item';
    el.id = `item-${item.id}`;

    // Headline (Editable via button only)
    const contentDiv = document.createElement('div');
    contentDiv.className = 'item-content';

    const headline = document.createElement('div');
    headline.className = 'item-headline text-clamped'; // Default clamped
    headline.contentEditable = "false";
    const fullText = item.rewritten_headline || item.headline;
    headline.textContent = fullText;
    headline.title = fullText; // Showing full title on hover

    // Toggle expand on click if not editing
    headline.onclick = () => {
        if (headline.isContentEditable) return;
        headline.classList.toggle('text-clamped');
        headline.classList.toggle('text-expanded');
    };

    // Save on Blur or Enter
    const saveHandler = async () => {
        if (!headline.isContentEditable) return;

        // Disable editing
        headline.contentEditable = "false";
        headline.classList.remove('is-editing');
        headline.classList.add('text-clamped'); // Re-clamp after edit? Maybe keep expanded? Let's keep expanded for now to see result.
        headline.classList.remove('text-clamped'); // Actually, user probably wants to see what they wrote.
        headline.classList.add('text-expanded');

        await saveUpdate(item.id, headline.textContent);
    };

    headline.addEventListener('blur', saveHandler);
    headline.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            headline.blur();
        }
    });

    // Meta (Source, Link, Snippet wrapper)
    const meta = document.createElement('div');
    meta.className = 'item-meta';

    const sourceLink = document.createElement('a');
    sourceLink.href = item.url;
    sourceLink.target = "_blank";
    sourceLink.style = "color: inherit; text-decoration: underline;";
    sourceLink.textContent = item.source;

    meta.appendChild(sourceLink);

    if (item.snippet) {
        // Tooltip logic or simple title
        contentDiv.title = item.snippet; // Simple native tooltip on hover of the whole content
    }

    contentDiv.appendChild(headline);

    // Relevance Reason (New Feature)
    if (item.relevance_reason) {
        const reasonEl = document.createElement('div');
        reasonEl.className = 'item-reason';
        reasonEl.textContent = `Why: ${item.relevance_reason}`;
        contentDiv.appendChild(reasonEl);
    }

    contentDiv.appendChild(meta);

    // Actions Group
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'actions-group';

    // Edit Button
    const editBtn = createIconBtn('Edit', 'icon-edit', `
        <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
        </svg>
    `);
    editBtn.onclick = () => {
        headline.contentEditable = "true";
        headline.classList.add('is-editing');
        headline.classList.remove('text-clamped');
        headline.classList.add('text-expanded');
        headline.focus();
    };

    // Rewrite Button
    const rewriteBtn = createIconBtn('Rewrite', 'icon-rewrite', `
        <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
        </svg>
    `);
    rewriteBtn.onclick = () => triggerRewrite(item.id, headline, rewriteBtn);

    // Dismiss Button (Gray Eye/Slash - No Learning)
    const dismissBtn = createIconBtn('Dismiss (Ignore)', 'icon-dismiss', `
        <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" style="color: #9ca3af;">
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
            <line x1="1" y1="1" x2="23" y2="23"></line>
        </svg>
    `);
    dismissBtn.onclick = () => removeItem(item.id, el, false);

    // Remove Button (Red Trash - Triggers Learning)
    const removeBtn = createIconBtn('Remove & Train AI', 'icon-remove', `
        <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" style="color: #ef4444;">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            <line x1="10" y1="11" x2="10" y2="17"></line>
            <line x1="14" y1="11" x2="14" y2="17"></line>
        </svg>
    `);
    removeBtn.onclick = () => removeItem(item.id, el, true);

    actionsDiv.appendChild(editBtn);
    actionsDiv.appendChild(rewriteBtn);
    // actionsDiv.appendChild(removeBtn); // Old
    actionsDiv.appendChild(dismissBtn);
    actionsDiv.appendChild(removeBtn);

    el.appendChild(contentDiv);
    el.appendChild(actionsDiv);

    return el;
}

function createIconBtn(title, extraClass, svgContent) {
    const btn = document.createElement('button');
    btn.className = `btn-icon ${extraClass}`;
    btn.title = title;
    btn.innerHTML = svgContent;
    return btn;
}

async function saveUpdate(id, newHeadline) {
    try {
        await fetch(`${API_BASE}/news/${id}/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id, headline: newHeadline })
        });
    } catch (e) {
        console.error("Failed to save update", e);
    }
}

async function triggerRewrite(id, headlineEl, btnEl) {
    if (btnEl) btnEl.classList.add('spin-anim'); // We could add a spin class in CSS if desired
    headlineEl.style.opacity = 0.5;

    try {
        const res = await fetch(`${API_BASE}/news/${id}/rewrite`, { method: 'POST' });
        const data = await res.json();
        headlineEl.textContent = data.rewritten_headline;
    } catch (e) {
        alert("Rewrite failed: " + e.message);
    } finally {
        headlineEl.style.opacity = 1;
        if (btnEl) btnEl.classList.remove('spin-anim');
    }
}

async function restoreItem(id, listEl, btnEl) {
    if (btnEl) btnEl.classList.add('spin-anim');
    listEl.style.opacity = 0.6;

    try {
        const res = await fetch(`${API_BASE}/news/rejected/${id}/restore`, { method: 'POST' });
        if (!res.ok) throw new Error("Failed to restore");
        const restoredItem = await res.json();

        // Remove from rejected list
        listEl.style.transition = "all 0.3s ease";
        listEl.style.opacity = "0";
        listEl.style.transform = "translateX(20px)";

        setTimeout(() => {
            listEl.remove();

            // Add to relevant section strictly
            // We need to re-render or inject. 
            // Simplest is to append to the correct section if found, or just re-fetch?
            // Re-fetching is heavy. Let's inject.

            // Find section container
            let secName = restoredItem.section || "Uncategorized";

            // Look for existing section header
            const headers = Array.from(document.querySelectorAll('.section-header h2'));
            let targetSectionEl = null;

            for (let h of headers) {
                if (h.textContent.includes(secName)) {
                    targetSectionEl = h.closest('.section').querySelector('.section-content');
                    break;
                }
            }

            if (targetSectionEl) {
                const newItemEl = createItemEl(restoredItem);
                newItemEl.style.animation = "fadeInSlide 0.5s ease";
                // Insert at top or bottom? top is better for visibility
                targetSectionEl.insertBefore(newItemEl, targetSectionEl.firstChild);

                // Update count in header? 
                // Too complex to parse "Section (N)". Let's skip updating count for now or try.
            } else {
                // Section doesn't exist, reload page (or fetch current db which is fast)
                // Actually reload news content from DB
                // fetchNews() // NO, this triggers scrape.
                // We need get_news.
                refreshNewsList();
            }

        }, 300);

    } catch (e) {
        alert("Restore failed: " + e.message);
        listEl.style.opacity = 1;
        if (btnEl) btnEl.classList.remove('spin-anim');
    }
}

async function refreshNewsList() {
    try {
        const res = await fetch(`${API_BASE}/news`);
        const data = await res.json();
        // Handle new structure {relevant, rejected}
        renderNews(data.relevant, data.rejected);
    } catch (e) { console.error(e); }
}

async function removeItem(id, element, learn = false) {
    // We can rely on a custom fancy modal or just system confirm. 
    // User asked for "satisfying to click on". 
    // Let's make the row fade out satisfyingly before removing.

    // Optimistic UI? Or confirm first? 
    // User said "remove should be just a red X". often implies quick action. 
    // But safety is good. Let's keep confirm but make it cleaner? 
    // For now, system confirm is safest to avoid accidental clicks on the new easy-to-hit buttons.
    // if (!confirm("Remove this item?")) return; // DISABLED per user request (One-click remove)

    element.style.transition = "all 0.3s ease";
    element.style.opacity = "0";
    element.style.transform = "translateX(20px)";

    try {
        await fetch(`${API_BASE}/news/${id}?learn=${learn}`, { method: 'DELETE' });
        setTimeout(() => element.remove(), 300);
    } catch (e) {
        alert("Failed to delete");
        element.style.opacity = "1";
        element.style.transform = "none";
    }
}

function setLoading(isLoading) {
    const loader = document.querySelector('.loader');
    const btnText = document.querySelector('.btn-text');
    if (isLoading) {
        loader.style.display = 'block';
        btnText.style.display = 'none';
        fetchBtn.disabled = true;
    } else {
        loader.style.display = 'none';
        btnText.style.display = 'inline';
        fetchBtn.disabled = false;
    }
}
