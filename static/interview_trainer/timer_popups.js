(function(){
    // Timer popups script: polls the session timer endpoint and shows lightweight pop-ups
    // Expects window.sessionData (in chat.html it is provided as #session-data json)
    try {
        const sessionScript = document.getElementById('session-data');
        if (!sessionScript) return;
        const sessionData = JSON.parse(sessionScript.textContent || '{}');
        const sessionId = sessionData.currentSessionId || null;
        if (!sessionId) return; // nothing to do

    const POLL_INTERVAL = 8000; // ms
    const TICK_SECONDS = 8; // seconds to report on tick
    // Milliseconds a popup stays visible (10 seconds)
    const MAX_VISIBLE = 10000;
    // When the same message was shown recently (ms), skip repeat popups
    const DEDUPE_MS = 30000; // 30 seconds

        // Create popup container
        const popupContainer = document.createElement('div');
        popupContainer.id = 'timer-popup-container';
        popupContainer.style.position = 'fixed';
    popupContainer.style.right = '20px';
    // Place popups in the top-right corner instead of bottom-right
    popupContainer.style.top = '20px';
        popupContainer.style.zIndex = '4000';
        popupContainer.style.display = 'flex';
        popupContainer.style.flexDirection = 'column';
    // ensure new popups flow downward from the top-right
    popupContainer.style.alignItems = 'flex-end';
        popupContainer.style.gap = '12px';
        document.body.appendChild(popupContainer);

        const csrftoken = (function(){
            const name = 'csrftoken=';
            const cookies = document.cookie.split(';');
            for (let c of cookies) {
                c = c.trim();
                if (c.indexOf(name) === 0) return decodeURIComponent(c.substring(name.length));
            }
            return '';
        })();

        // track when messages were last shown to avoid spamming duplicates
        const shownMessages = new Map();

        function showPopup(message, kind='info'){
            const el = document.createElement('div');
            el.className = 'alert alert-secondary';
            el.style.minWidth = '260px';
            el.style.boxShadow = '0 8px 24px rgba(0,0,0,0.12)';
            el.style.borderRadius = '12px';
            el.style.padding = '10px 14px';
            el.style.transition = 'transform 300ms ease, opacity 300ms ease';
            el.style.opacity = '0';
            el.style.transform = 'translateY(8px)';

            const title = document.createElement('div');
            title.style.fontWeight = '600';
            title.style.marginBottom = '4px';
            title.textContent = kind === 'warning' ? 'Consejo' : 'Motivación';
            const p = document.createElement('div');
            p.style.fontSize = '0.95rem';
            p.style.color = '#111827';
            p.textContent = message;
            el.appendChild(title);
            el.appendChild(p);
            popupContainer.appendChild(el);

            // animate in
            requestAnimationFrame(() => {
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
            });

            // remove after timeout
            setTimeout(() => {
                el.style.opacity = '0';
                el.style.transform = 'translateY(8px)';
                setTimeout(()=> el.remove(), 320);
            }, MAX_VISIBLE);
        }

        async function pollStatus(){
            try {
                const statusRes = await fetch(`/api/sessions/${sessionId}/timer/`, { credentials: 'same-origin' });
                if (!statusRes.ok) return;
                const status = await statusRes.json();
                if (!status || !status.message) return;

                // Only show message when running; skip when paused or ended
                if (status.status === 'RUNNING'){
                    // dedupe: only show the same base message if it wasn't shown recently
                    if (status.message) {
                        const last = shownMessages.get(status.message) || 0;
                        const now = Date.now();
                        if (now - last > DEDUPE_MS) {
                            // compute elapsed time when possible (total allowed from template)
                            const totalAllowed = parseInt(sessionData.totalTimeAllowed || 900, 10);
                            let display = status.message;
                            if (typeof status.remaining_seconds === 'number') {
                                const remaining = parseInt(status.remaining_seconds, 10);
                                const elapsed = Math.max(0, totalAllowed - remaining);
                                // format elapsed as MM:SS
                                const mins = Math.floor(elapsed / 60);
                                const secs = elapsed % 60;
                                const mm = String(mins).padStart(2, '0');
                                const ss = String(secs).padStart(2, '0');
                                display = `${status.message} — Tiempo transcurrido: ${mm}:${ss}`;
                            }

                            showPopup(display, 'info');
                            shownMessages.set(status.message, now);
                            // prune old entries occasionally
                            if (shownMessages.size > 100) {
                                for (const [k, v] of Array.from(shownMessages.entries())) {
                                    if (now - v > DEDUPE_MS * 2) shownMessages.delete(k);
                                }
                            }
                        }
                    }
                    // send a tick to persist progress on server (optional)
                    try {
                        await fetch(`/api/sessions/${sessionId}/timer/tick/`, {
                            method: 'POST',
                            credentials: 'same-origin',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': csrftoken
                            },
                            body: JSON.stringify({ seconds_passed: TICK_SECONDS })
                        });
                    } catch(e) {
                        // noop
                    }
                } else if (status.status === 'PAUSED'){
                    // show a gentle pause reminder once
                    // avoid spamming: show only occasionally
                } else if (status.status === 'ENDED'){
                    showPopup('Tu práctica ha finalizado. Revisa la evaluación cuando esté lista.', 'warning');
                }
            } catch (e){
                // ignore polling errors
                //console.warn('Timer polling error', e);
            } finally {
                setTimeout(pollStatus, POLL_INTERVAL);
            }
        }

        // start polling after small delay to let page load
        setTimeout(pollStatus, 2000);

    } catch (e) {
        console.error('timer_popups init error', e);
    }
})();
