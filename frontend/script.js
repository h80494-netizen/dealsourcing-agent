document.addEventListener('DOMContentLoaded', () => {
    const btnApply = document.getElementById('btn-apply');
    const btnRealtime = document.getElementById('btn-realtime');
    const btnLoader = document.getElementById('btn-loader');
    const tbody = document.getElementById('table-body');
    const statusBadge = document.getElementById('status-badge');
    const updateMsg = document.getElementById('update-msg');

    // ?¤ì¤‘ ? íƒ(Ctrl ?†ì´) ë°?'?„ì²´' ?¨ì¼ ?´ë¦­ ë¡œì§
    document.querySelectorAll('.multi-select').forEach(select => {
        // ìµœì´ˆ ?íƒœë¡?'?„ì²´' ?ë™ ? íƒ
        if(select.options.length > 0) select.options[0].selected = true;
        
        select.addEventListener('mousedown', function(e) {
            e.preventDefault();
            const option = e.target;
            if (option.tagName === 'OPTION') {
                const originalSelected = option.selected;
                
                if (option.value === "") {
                    // '?„ì²´' ?´ë¦­ ???˜ë¨¸ì§€ ?´ì œ
                    Array.from(this.options).forEach(opt => opt.selected = false);
                    option.selected = true;
                } else {
                    // ?¤ë¥¸ ??ª© ?´ë¦­ ??'?„ì²´' ?´ì œ
                    if(this.options.length > 0 && this.options[0].value === "") {
                        this.options[0].selected = false;
                    }
                    option.selected = !originalSelected;
                    
                    // ë§Œì•½ ëª¨ë‘ ?´ì œ?˜ì—ˆ?¤ë©´ '?„ì²´' ?¤ì‹œ ? íƒ
                    const anySelected = Array.from(this.options).some(opt => opt.selected);
                    if (!anySelected && this.options.length > 0 && this.options[0].value === "") {
                        this.options[0].selected = true;
                    }
                }
                this.focus();
            }
        });
    });

    const fetchArticles = async () => {
        try {
            const getSelected = (id) => Array.from(document.getElementById(id).selectedOptions).map(opt => opt.value).filter(val => val !== "");
            const countries = getSelected('country');
            const dealStages = getSelected('deal-stage');
            const newsGrades = getSelected('news-grade');
            const industries = getSelected('industry');
            const sortBy = document.getElementById('sort-by').value;

            const params = new URLSearchParams();
            countries.forEach(c => params.append('country', c));
            dealStages.forEach(d => params.append('deal_stage', d));
            newsGrades.forEach(n => params.append('news_grade', n));
            industries.forEach(i => params.append('promising_industry', i));
            if (sortBy) params.append('sort_by', sortBy);

            const res = await fetch(`/api/articles?${params.toString()}`);
            const json = await res.json();
            
            if (json.status === 'success') {
                document.getElementById('collected-count').textContent = `ê²€?‰ëœ ?? ${json.count} ê±?;
                renderTable(json.data);
            }
        } catch (e) {
            console.error(e);
            tbody.innerHTML = `<tr><td colspan="8" style="color:red; text-align:center;">?°ì´?°ë? ë¶ˆëŸ¬?¤ëŠ” ì¤??¤ë¥˜ê°€ ë°œìƒ?ˆìŠµ?ˆë‹¤. ?œë²„ê°€ ì¼œì ¸ ?ˆëŠ”ì§€ ?•ì¸?˜ì„¸??</td></tr>`;
        }
    };

    const renderTable = (data) => {
        tbody.innerHTML = '';
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty-state">?°ì´?°ê? ?†ìŠµ?ˆë‹¤.</td></tr>';
            return;
        }

        data.forEach(item => {
            const tr = document.createElement('tr');
            
            // ?´ìŠ¤ ?±ê¸‰ ?¤í??¼ë§
            let gradeClass = '';
            if(item.news_grade === 'S') gradeClass = 'news-grade-S';
            else if(item.news_grade === 'A') gradeClass = 'news-grade-A';
            else if(item.news_grade === 'B') gradeClass = 'news-grade-B';
            else gradeClass = 'news-grade-C';

            tr.innerHTML = `
                <td>${item.country || '-'}</td>
                <td class="${gradeClass}">${item.news_grade || '-'}</td>
                <td><span style="background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 4px; font-size: 0.85em;">${item.deal_stage || '-'}</span></td>
                <td>${item.promising_industry || '-'}</td>
                <td><a href="${item.link}" target="_blank" style="color: #60a5fa; text-decoration: none;">${item.title}</a></td>
                <td style="color: #34d399; font-weight: bold;">${item.impact_score ? item.impact_score.toFixed(1) : '-'}</td>
                <td>${item.source_name || '-'}</td>
                <td>${item.created_at || '-'}</td>
            `;
            tbody.appendChild(tr);
        });
    };

    btnApply.addEventListener('click', () => {
        fetchArticles();
    });

    btnRealtime.addEventListener('click', async () => {
        btnRealtime.disabled = true;
        btnLoader.style.display = 'block';
        statusBadge.textContent = '?˜ì§‘ ì¤?..';
        statusBadge.classList.add('active');
        updateMsg.textContent = '?¤ì‹œê°??˜ì§‘ ?Œì´?„ë¼?¸ì´ ?¤í–‰?˜ì—ˆ?µë‹ˆ?? ë°±ê·¸?¼ìš´?œì—???´ìŠ¤ë¥?ë¶„ì„ ì¤‘ì…?ˆë‹¤.';
        
        try {
            const res = await fetch('/api/crawl_now', { method: 'POST' });
            const json = await res.json();
            if (json.status === 'success') {
                updateMsg.textContent = '?¤ì‹œê°??˜ì§‘ ëª…ë ¹ ?„ì†¡ ?„ë£Œ! ??1~2ë¶????¤ì‹œ ì¡°íšŒ?´ì£¼?¸ìš”.';
                setTimeout(() => {
                    fetchArticles(); // 5ì´????œë²ˆ ë¦¬í”„?ˆì‹œ
                }, 5000);
            }
        } catch (e) {
            console.error(e);
            updateMsg.textContent = '?¤ì‹œê°??…ë°?´íŠ¸ ?”ì²­ ?¤íŒ¨';
        } finally {
            setTimeout(() => {
                btnRealtime.disabled = false;
                btnLoader.style.display = 'none';
                statusBadge.textContent = '?€ê¸?ì¤?;
                statusBadge.classList.remove('active');
            }, 3000);
        }
    });

    // ì´ˆê¸° ë¡œë“œ ???°ì´??ê°€?¸ì˜¤ê¸?    fetchArticles();

    // Keyword Handling
    const keywordInput = document.getElementById('custom-keyword');
    const keywordTags = document.getElementById('keyword-tags');

    const loadKeywords = async () => {
        try {
            const res = await fetch('/api/keywords');
            const json = await res.json();
            if (json.status === 'success') {
                keywordTags.innerHTML = '';
                json.data.forEach(kw => {
                    const tag = document.createElement('span');
                    tag.style.background = 'rgba(59, 130, 246, 0.3)';
                    tag.style.padding = '4px 8px';
                    tag.style.borderRadius = '12px';
                    tag.style.fontSize = '0.8rem';
                    tag.textContent = kw.keyword;
                    keywordTags.appendChild(tag);
                });
            }
        } catch (e) {
            console.error("Failed to load keywords", e);
        }
    };
    
    if(keywordInput) {
        keywordInput.addEventListener('keypress', async (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const val = keywordInput.value.trim();
                if (!val) return;
                try {
                    const res = await fetch('/api/keywords', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ keyword: val, type: 'industry', category: 'custom' })
                    });
                    const json = await res.json();
                    if (json.status === 'success') {
                        keywordInput.value = '';
                        loadKeywords();
                    }
                } catch (err) {
                    console.error("Failed to add keyword", err);
                }
            }
        });
    }

    loadKeywords();

    // Custom URL Analysis
    const btnAnalyzeUrl = document.getElementById('btn-analyze-url');
    const inputCustomUrl = document.getElementById('custom-url');

    if(btnAnalyzeUrl) {
        btnAnalyzeUrl.addEventListener('click', async () => {
            const url = inputCustomUrl.value.trim();
            if (!url) return;
            
            btnAnalyzeUrl.disabled = true;
            btnAnalyzeUrl.textContent = 'ë¶„ì„ì¤?..';
            
            try {
                const res = await fetch('/api/analyze_url', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });
                const json = await res.json();
                if (json.status === 'success') {
                    inputCustomUrl.value = '';
                    fetchArticles(); // Refresh table
                    alert('?˜ë™ ë¶„ì„???„ë£Œ?˜ì—ˆ?µë‹ˆ??');
                } else {
                    alert('ë¶„ì„ ?¤íŒ¨: ' + json.message);
                }
            } catch (e) {
                console.error(e);
                alert('?”ì²­ ì¤??¤ë¥˜ê°€ ë°œìƒ?ˆìŠµ?ˆë‹¤.');
            } finally {
                btnAnalyzeUrl.disabled = false;
                btnAnalyzeUrl.textContent = 'ë¶„ì„';
            }
        });
    }

    // Modal Logic
    const settingsModal = document.getElementById('settings-modal');
    const reportModal = document.getElementById('report-modal');
    
    // Settings CRUD Logic
    const kwList = document.getElementById('setting-kw-list');
    const domainList = document.getElementById('setting-domain-list');
    
    const loadSettingsKeywords = async () => {
        try {
            const res = await fetch('/api/keywords');
            const json = await res.json();
            if (json.status === 'success') {
                kwList.innerHTML = '';
                json.data.forEach(kw => {
                    const li = document.createElement('li');
                    li.style.display = 'flex';
                    li.style.justifyContent = 'space-between';
                    li.style.alignItems = 'center';
                    li.style.background = 'rgba(255,255,255,0.05)';
                    li.style.padding = '8px';
                    li.style.borderRadius = '4px';
                    li.innerHTML = `
                        <span><strong>${kw.keyword}</strong> <small style="color:#9ca3af;">(${kw.category} / ${kw.type})</small></span>
                        <button class="btn-delete-kw" data-id="${kw.id}" style="background: #ef4444; border: none; color: white; padding: 4px 8px; border-radius: 4px; cursor: pointer;">?? œ</button>
                    `;
                    kwList.appendChild(li);
                });
                
                document.querySelectorAll('.btn-delete-kw').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        const id = e.target.getAttribute('data-id');
                        await fetch(`/api/keywords/${id}`, { method: 'DELETE' });
                        loadSettingsKeywords();
                        loadKeywords(); // update dashboard tags
                    });
                });
            }
        } catch(e) { console.error(e); }
    };
    
    const loadSettingsDomains = async () => {
        try {
            const res = await fetch('/api/domains');
            const json = await res.json();
            if (json.status === 'success') {
                domainList.innerHTML = '';
                json.data.forEach(d => {
                    const li = document.createElement('li');
                    li.style.display = 'flex';
                    li.style.justifyContent = 'space-between';
                    li.style.alignItems = 'center';
                    li.style.background = 'rgba(255,255,255,0.05)';
                    li.style.padding = '8px';
                    li.style.borderRadius = '4px';
                    li.innerHTML = `
                        <div style="flex: 1;">
                            <strong>${d.name || d.url}</strong> <small style="color:#9ca3af;">(${d.country} / ${d.category})</small>
                            <div style="font-size: 0.8rem; color: #60a5fa; margin-top: 2px;">URL: ${d.url}</div>
                            ${d.rss_url ? `<div style="font-size: 0.8rem; color: #34d399; margin-top: 2px;">RSS: ${d.rss_url}</div>` : ''}
                        </div>
                        <button class="btn-delete-domain" data-id="${d.id}" style="background: #ef4444; border: none; color: white; padding: 4px 8px; border-radius: 4px; cursor: pointer; margin-left: 10px;">?? œ</button>
                    `;
                    domainList.appendChild(li);
                });
                
                document.querySelectorAll('.btn-delete-domain').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        const id = e.target.getAttribute('data-id');
                        await fetch(`/api/domains/${id}`, { method: 'DELETE' });
                        loadSettingsDomains();
                    });
                });
            }
        } catch(e) { console.error(e); }
    };

    const btnAddKw = document.getElementById('btn-add-kw');
    if (btnAddKw) {
        btnAddKw.addEventListener('click', async () => {
            const keyword = document.getElementById('setting-kw-input').value.trim();
            const type = document.getElementById('setting-kw-type').value;
            const category = document.getElementById('setting-kw-category').value;
            if(!keyword) return;
            
            await fetch('/api/keywords', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keyword, type, category })
            });
            document.getElementById('setting-kw-input').value = '';
            loadSettingsKeywords();
            loadKeywords();
        });
    }

    const btnAddDomain = document.getElementById('btn-add-domain');
    if (btnAddDomain) {
        btnAddDomain.addEventListener('click', async () => {
            const name = document.getElementById('setting-domain-name').value.trim();
            const url = document.getElementById('setting-domain-url').value.trim();
            const rss_url = document.getElementById('setting-domain-rss').value.trim();
            const purpose = document.getElementById('setting-domain-purpose').value.trim();
            const country = document.getElementById('setting-domain-country').value;
            const category = document.getElementById('setting-domain-category').value;
            
            if(!url) { alert('URL?€ ?„ìˆ˜?…ë‹ˆ??'); return; }
            
            await fetch('/api/domains', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, url, rss_url: rss_url || null, purpose, country, category })
            });
            
            document.getElementById('setting-domain-name').value = '';
            document.getElementById('setting-domain-url').value = '';
            document.getElementById('setting-domain-rss').value = '';
            document.getElementById('setting-domain-purpose').value = '';
            loadSettingsDomains();
        });
    }

    document.getElementById('btn-settings').addEventListener('click', () => {
        loadSettingsKeywords();
        loadSettingsDomains();
        settingsModal.style.display = 'flex';
    });
    
    document.getElementById('btn-close-settings').addEventListener('click', () => {
        settingsModal.style.display = 'none';
    });

    let revealInstance = null;

    document.getElementById('btn-report').addEventListener('click', async () => {
        reportModal.style.display = 'flex';
        document.getElementById('report-loading').style.display = 'block';
        document.getElementById('reveal-container').style.display = 'none';
        
        try {
            const res = await fetch('/api/report');
            const json = await res.json();
            if (json.status === 'success') {
                const markdownText = json.report;
                
                // --- ë¡?êµ¬ë¶„??ë§ˆí¬?¤ìš´???¬ë¼?´ë“œë¡?ë³€??                const slidesContainer = document.getElementById('reveal-slides');
                slidesContainer.innerHTML = ''; // ì´ˆê¸°??                
                const slideContents = markdownText.split('---').map(s => s.trim()).filter(s => s.length > 0);
                slideContents.forEach(content => {
                    const section = document.createElement('section');
                    section.setAttribute('data-markdown', '');
                    const textarea = document.createElement('textarea');
                    textarea.setAttribute('data-template', '');
                    textarea.value = content;
                    section.appendChild(textarea);
                    slidesContainer.appendChild(section);
                });
                
                document.getElementById('report-loading').style.display = 'none';
                document.getElementById('reveal-container').style.display = 'block';
                
                // Reveal.js ì´ˆê¸°??(ì¤‘ë³µ ë°©ì?)
                if (revealInstance) {
                    revealInstance.destroy();
                }
                revealInstance = new Reveal(document.getElementById('reveal-container'), {
                    embedded: true,
                    plugins: [ RevealMarkdown ],
                    slideNumber: true,
                    hash: false,
                    width: '100%',
                    height: '100%',
                    margin: 0.1
                });
                revealInstance.initialize();
                
            } else {
                document.getElementById('report-loading').textContent = 'ë¦¬í¬???ì„± ?¤íŒ¨: ' + (json.message || '?????†ëŠ” ?¤ë¥˜');
            }
        } catch (e) {
            console.error(e);
            document.getElementById('report-loading').textContent = 'ë¦¬í¬???ì„± ì¤??¤ë¥˜ ë°œìƒ';
        }
    });

    document.getElementById('btn-print-pdf').addEventListener('click', () => {
        // ëª¨ë‹¬ì°½ë§Œ ?¸ì‡„?˜ë„ë¡??¤ì •
        const originalBody = document.body.innerHTML;
        const modalContent = document.querySelector('.reveal').innerHTML;
        document.body.innerHTML = `<div style="color: black; background: white;">${modalContent}</div>`;
        window.print();
        document.body.innerHTML = originalBody;
        location.reload(); // ë¦¬ë¡œ?œí•˜???´ë²¤??ë¦¬ìŠ¤??ë³µêµ¬
    });

    document.getElementById('btn-close-report').addEventListener('click', () => {
        reportModal.style.display = 'none';
    });
    
    // Close on click outside
    window.addEventListener('click', (e) => {
        if (e.target === settingsModal) settingsModal.style.display = 'none';
        if (e.target === reportModal) reportModal.style.display = 'none';
    });
});
