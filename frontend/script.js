document.addEventListener('DOMContentLoaded', () => {
    const btnApply = document.getElementById('btn-apply');
    const btnRealtime = document.getElementById('btn-realtime');
    const btnLoader = document.getElementById('btn-loader');
    const tbody = document.getElementById('table-body');
    const statusBadge = document.getElementById('status-badge');
    const updateMsg = document.getElementById('update-msg');

    // 다중 선택(Ctrl 없이) 및 '전체' 단일 클릭 로직
    document.querySelectorAll('.multi-select').forEach(select => {
        // 최초 상태로 '전체' 자동 선택
        if(select.options.length > 0) select.options[0].selected = true;
        
        select.addEventListener('mousedown', function(e) {
            e.preventDefault();
            const option = e.target;
            if (option.tagName === 'OPTION') {
                const originalSelected = option.selected;
                
                if (option.value === "") {
                    // '전체' 클릭 시 나머지 해제
                    Array.from(this.options).forEach(opt => opt.selected = false);
                    option.selected = true;
                } else {
                    // 다른 항목 클릭 시 '전체' 해제
                    if(this.options.length > 0 && this.options[0].value === "") {
                        this.options[0].selected = false;
                    }
                    option.selected = !originalSelected;
                    
                    // 만약 모두 해제되었다면 '전체' 다시 선택
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
                document.getElementById('collected-count').textContent = `검색된 딜: ${json.count} 건`;
                
                // --- 동적 유망산업 필터 연동 ---
                const industrySelect = document.getElementById('industry');
                if (industrySelect) {
                    const existingValues = Array.from(industrySelect.options).map(o => o.value);
                    json.data.forEach(item => {
                        if (item.promising_industry && item.promising_industry !== '기타/미정') {
                            item.promising_industry.split(',').forEach(ind => {
                                const cleanInd = ind.trim();
                                if (cleanInd && !existingValues.includes(cleanInd)) {
                                    const opt = document.createElement('option');
                                    opt.value = cleanInd;
                                    opt.textContent = cleanInd;
                                    industrySelect.appendChild(opt);
                                    existingValues.push(cleanInd);
                                }
                            });
                        }
                    });
                }
                
                renderTable(json.data);
            }
        } catch (e) {
            console.error(e);
            tbody.innerHTML = `<tr><td colspan="8" style="color:red; text-align:center;">데이터를 불러오는 중 오류가 발생했습니다. 서버가 켜져 있는지 확인하세요.</td></tr>`;
        }
    };

    const renderTable = (data) => {
        tbody.innerHTML = '';
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="empty-state">데이터가 없습니다.</td></tr>';
            return;
        }

        data.forEach(item => {
            const tr = document.createElement('tr');
            
            // 뉴스 등급 스타일링
            let gradeClass = '';
            let gradeTooltip = '';
            if(item.news_grade === 'S') { 
                gradeClass = 'news-grade-S'; 
                gradeTooltip = 'S 등급 (80~100점): 대규모 투자 유치, M&A, 확실한 흑자 전환 등 핵심 시그널'; 
            } else if(item.news_grade === 'A') { 
                gradeClass = 'news-grade-A'; 
                gradeTooltip = 'A 등급 (60~79점): 유의미한 실적 개선, 중간 규모 투자, 주요 파트너십'; 
            } else if(item.news_grade === 'B') { 
                gradeClass = 'news-grade-B'; 
                gradeTooltip = 'B 등급 (40~59점): 일반적인 산업 동향, 신제품 출시, 초기 시드 투자'; 
            } else { 
                gradeClass = 'news-grade-C'; 
                gradeTooltip = 'C 등급 (40점 미만): 벤처 투자와 무관한 단순 기사 (수집 안 됨)'; 
            }

            tr.innerHTML = `
                <td>${item.country || '-'}</td>
                <td class="${gradeClass}" title="${gradeTooltip}" style="cursor: help;">${item.news_grade || '-'}</td>
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
        statusBadge.textContent = '수집 중...';
        statusBadge.classList.add('active');
        updateMsg.textContent = '데이터 수집 및 분석을 시작합니다 (약 1~2분 소요)...';
        
        try {
            const res = await fetch('/api/crawl_now', { method: 'POST' });
            const json = await res.json();
            if (json.status === 'success') {
                const pollInterval = setInterval(async () => {
                    try {
                        const statusRes = await fetch('/api/crawl_status');
                        const statusJson = await statusRes.json();
                        
                        // 주기적으로 테이블 새로고침하여 새로 추가된 데이터를 바로 보여줌
                        fetchArticles();
                        
                        if (statusJson.status === 'success' && !statusJson.is_crawling) {
                            clearInterval(pollInterval);
                            updateMsg.textContent = '수집 완료! 화면을 새로고침 합니다.';
                            setTimeout(() => location.reload(), 1500);
                        }
                    } catch(e) {}
                }, 3000); // 3초 간격으로 더 빠르게 업데이트
            } else {
                updateMsg.textContent = json.message;
                btnRealtime.disabled = false;
                btnLoader.style.display = 'none';
                statusBadge.textContent = '대기 중';
                statusBadge.classList.remove('active');
            }
        } catch (e) {
            console.error(e);
            updateMsg.textContent = '서버 통신 오류';
            btnRealtime.disabled = false;
            btnLoader.style.display = 'none';
            statusBadge.textContent = '대기 중';
            statusBadge.classList.remove('active');
        }
    });

    // 초기 로드 시 데이터 가져오기
    fetchArticles();

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
                    if (json.status === 'error') {
                        alert(json.message);
                        return;
                    }
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
            btnAnalyzeUrl.textContent = '분석중...';
            
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
                    alert('수동 분석이 완료되었습니다!');
                } else {
                    alert('분석 실패: ' + json.message);
                }
            } catch (e) {
                console.error(e);
                alert('요청 중 오류가 발생했습니다.');
            } finally {
                btnAnalyzeUrl.disabled = false;
                btnAnalyzeUrl.textContent = '분석';
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
                        <button class="btn-delete-kw" data-id="${kw.id}" style="background: #ef4444; border: none; color: white; padding: 4px 8px; border-radius: 4px; cursor: pointer;">삭제</button>
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
                        <button class="btn-delete-domain" data-id="${d.id}" style="background: #ef4444; border: none; color: white; padding: 4px 8px; border-radius: 4px; cursor: pointer; margin-left: 10px;">삭제</button>
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
            
            const res = await fetch('/api/keywords', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ keyword: val, type: 'industry', category: 'custom' })
                    });
                    const json = await res.json();
                    if (json.status === 'error') {
                        alert(json.message);
                        return;
                    }
            if (json.status === 'error') {
                alert(json.message);
                return;
            }
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
            
            if(!url) { alert('URL은 필수입니다'); return; }
            
            const res = await fetch('/api/domains', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, url, rss_url: rss_url || null, purpose, country, category })
            });
            const json = await res.json();
            if (json.status === 'error') {
                alert(json.message);
                return;
            }
            
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
        document.getElementById('markdown-container').style.display = 'none';
        
        try {
            const res = await fetch('/api/report');
            const json = await res.json();
            if (json.status === 'success') {
                const markdownText = json.report;
                const markdownContainer = document.getElementById('markdown-container');
                markdownContainer.innerHTML = marked.parse(markdownText);
                
                document.getElementById('report-loading').style.display = 'none';
                markdownContainer.style.display = 'block';
                
            } else {
                document.getElementById('report-loading').textContent = '리포트 생성 실패: ' + (json.message || '알 수 없는 오류');
            }
        } catch (e) {
            console.error(e);
            document.getElementById('report-loading').textContent = '리포트 생성 중 오류 발생';
        }
    });

    document.getElementById('btn-print-pdf').addEventListener('click', () => {
        // 모달창만 인쇄되도록 설정
        const originalBody = document.body.innerHTML;
        const modalContent = document.querySelector('.reveal').innerHTML;
        document.body.innerHTML = `<div style="color: black; background: white;">${modalContent}</div>`;
        window.print();
        document.body.innerHTML = originalBody;
        location.reload(); // 리로드하여 이벤트 리스너 복구
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

document.addEventListener('DOMContentLoaded', () => {
    // Add Industry from Sidebar
    const btnAddIndustry = document.getElementById('btn-add-industry');
    const inputNewIndustry = document.getElementById('new-industry-input');
    const industrySelect = document.getElementById('industry');
    
    if (btnAddIndustry) {
        btnAddIndustry.addEventListener('click', async () => {
            const val = inputNewIndustry.value.trim();
            if (!val) return;
            
            try {
                const res = await fetch('/api/keywords', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ keyword: val, type: 'industry', category: 'promising_industry' })
                });
                const json = await res.json();
                if (json.status === 'error') {
                    alert(json.message);
                } else {
                    const opt = document.createElement('option');
                    opt.value = val;
                    opt.textContent = val;
                    opt.selected = true;
                    industrySelect.appendChild(opt);
                    
                    inputNewIndustry.value = '';
                    if(typeof loadSettingsKeywords === 'function') loadSettingsKeywords();
                    alert('유망산업이 추가되었습니다!');
                }
            } catch (e) {
                console.error(e);
            }
        });
    }

    
    // Delete Industry from Sidebar
    const btnDeleteIndustry = document.getElementById('btn-delete-industry');
    if (btnDeleteIndustry) {
        btnDeleteIndustry.addEventListener('click', async () => {
            const selected = Array.from(industrySelect.selectedOptions).map(opt => opt.value).filter(v => v !== "");
            if (selected.length === 0) {
                alert('삭제할 유망산업을 먼저 클릭(선택)해주세요.');
                return;
            }
            if (!confirm(`선택한 유망산업(${selected.join(', ')})을 삭제하시겠습니까?`)) return;
            
            try {
                const res = await fetch('/api/keywords');
                const json = await res.json();
                if (json.status === 'success') {
                    for (const kw of json.data) {
                        if (selected.includes(kw.keyword)) {
                            if (kw.is_builtin) {
                                alert(`'${kw.keyword}'은(는) 내장 키워드라 삭제할 수 없습니다.`);
                            } else {
                                await fetch(`/api/keywords/${kw.id}`, { method: 'DELETE' });
                                // Remove from select
                                Array.from(industrySelect.options).forEach(opt => {
                                    if(opt.value === kw.keyword) opt.remove();
                                });
                            }
                        }
                    }
                    if(typeof loadSettingsKeywords === 'function') loadSettingsKeywords();
                    alert('삭제가 완료되었습니다.');
                }
            } catch (e) {
                console.error(e);
            }
        });
    }

    // Load industries dynamically on boot
    const loadIndustryOptions = async () => {
        try {
            const res = await fetch('/api/keywords');
            const json = await res.json();
            if (json.status === 'success') {
                const existingValues = Array.from(industrySelect.options).map(o => o.value);
                json.data.forEach(kw => {
                    if (kw.category === 'promising_industry' || kw.category === 'industry') {
                        if (!existingValues.includes(kw.keyword)) {
                            const opt = document.createElement('option');
                            opt.value = kw.keyword;
                            opt.textContent = kw.keyword;
                            industrySelect.appendChild(opt);
                            existingValues.push(kw.keyword);
                        }
                    }
                });
            }
        } catch(e) {}
    };
    if (industrySelect) loadIndustryOptions();
});
