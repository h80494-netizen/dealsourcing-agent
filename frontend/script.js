document.addEventListener('DOMContentLoaded', () => {
    const btnApply = document.getElementById('btn-apply');
    const btnRealtime = document.getElementById('btn-realtime');
    const btnLoader = document.getElementById('btn-loader');
    const tbody = document.getElementById('table-body');
    const statusBadge = document.getElementById('status-badge');
    const updateMsg = document.getElementById('update-msg');

    // 커스텀 드롭다운 토글 로직
    document.querySelectorAll('.custom-select-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const dropdown = btn.nextElementSibling;
            const isOpen = dropdown.classList.contains('open');
            document.querySelectorAll('.custom-select-dropdown').forEach(d => d.classList.remove('open'));
            if (!isOpen) dropdown.classList.add('open');
        });
    });

    document.addEventListener('click', () => {
        document.querySelectorAll('.custom-select-dropdown').forEach(d => d.classList.remove('open'));
    });

    // 드롭다운 내부 클릭 시 닫히지 않도록
    document.querySelectorAll('.custom-select-dropdown').forEach(dropdown => {
        dropdown.addEventListener('click', e => e.stopPropagation());
    });

    // 체크박스 상호작용 ('전체' vs 개별) 및 버튼 텍스트 업데이트 로직
    const setupCheckboxes = (containerId) => {
        const container = document.getElementById(containerId);
        if (!container) return;
        const btn = container.querySelector('.custom-select-btn');
        const checkboxes = container.querySelectorAll('input[type="checkbox"]');
        const chkAll = container.querySelector('.chk-all-opt');

        const updateBtnText = () => {
            if (!btn) return;
            const checked = Array.from(checkboxes).filter(cb => cb.checked && cb !== chkAll);
            if (chkAll && chkAll.checked) {
                btn.textContent = chkAll.parentElement.textContent.trim();
            } else if (checked.length > 0) {
                btn.textContent = checked.map(cb => cb.parentElement.textContent.trim().split(' (')[0]).join(', ');
            } else {
                if (chkAll) {
                    chkAll.checked = true;
                    btn.textContent = chkAll.parentElement.textContent.trim();
                } else {
                    btn.textContent = '선택됨 없음';
                }
            }
        };

        checkboxes.forEach(chk => {
            chk.addEventListener('change', (e) => {
                if (e.target === chkAll && chkAll.checked) {
                    checkboxes.forEach(cb => { if (cb !== chkAll) cb.checked = false; });
                } else {
                    if (chkAll) chkAll.checked = false;
                    const anyChecked = Array.from(checkboxes).some(cb => cb.checked);
                    if (!anyChecked && chkAll) chkAll.checked = true;
                }
                updateBtnText();
            });
        });
        updateBtnText();
    };

    ['dropdown-country', 'dropdown-stage', 'dropdown-grade', 'dropdown-industry'].forEach(setupCheckboxes);

    // 라디오 버튼(정렬, 일자) 텍스트 업데이트 로직
    ['dropdown-sort', 'dropdown-date'].forEach(containerId => {
        const container = document.getElementById(containerId);
        if (!container) return;
        const btn = container.querySelector('.custom-select-btn');
        const radios = container.querySelectorAll('input[type="radio"]');
        radios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                if(e.target.checked) {
                    btn.textContent = e.target.parentElement.textContent.trim();
                }
            });
            // 초기 텍스트 세팅
            if(radio.checked) {
                btn.textContent = radio.parentElement.textContent.trim();
            }
        });
    });


    const fetchArticles = async () => {
        try {
            const getSelected = (name) => Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map(cb => cb.value).filter(val => val !== "");
            const countries = getSelected('country');
            const dealStages = getSelected('deal-stage');
            const newsGrades = getSelected('news-grade');
            const industries = getSelected('industry');
            const sortByNode = document.querySelector('input[name="sort-by"]:checked');
            const sortBy = sortByNode ? sortByNode.value : 'latest';
            const dateFilterNode = document.querySelector('input[name="date-filter"]:checked');
            const dateFilter = dateFilterNode ? dateFilterNode.value : 'all';

            const params = new URLSearchParams();
            countries.forEach(c => params.append('country', c));
            dealStages.forEach(d => params.append('deal_stage', d));
            newsGrades.forEach(n => params.append('news_grade', n));
            industries.forEach(i => params.append('promising_industry', i));
            if (sortBy) params.append('sort_by', sortBy);
            
            // 일자 필터 적용
            if (dateFilter && dateFilter !== 'all') params.append('date_filter', dateFilter);

            const res = await fetch(`/api/articles?${params.toString()}`);
            const json = await res.json();
            
            if (json.status === 'success') {
                document.getElementById('collected-count').textContent = `검색된 딜: ${json.count} 건`;
                
                // --- 동적 유망산업 필터 연동 ---
                const industryDropdownList = document.getElementById('industry-dropdown-list');
                if (industryDropdownList) {
                    const existingValues = Array.from(industryDropdownList.querySelectorAll('input[type="checkbox"]')).map(cb => cb.value);
                    let changed = false;
                    json.data.forEach(item => {
                        if (item.promising_industry && item.promising_industry !== '기타/미정') {
                            item.promising_industry.split(',').forEach(ind => {
                                const cleanInd = ind.trim();
                                if (cleanInd && !existingValues.includes(cleanInd)) {
                                    const label = document.createElement('label');
                                    label.className = 'checkbox-label';
                                    label.innerHTML = `<input type="checkbox" name="industry" value="${cleanInd}"> ${cleanInd}`;
                                    
                                    // 이벤트 리스너 부착
                                    const chk = label.querySelector('input');
                                    const chkAll = industryDropdownList.querySelector('.chk-all-opt');
                                    chk.addEventListener('change', () => {
                                        if (chkAll) chkAll.checked = false;
                                        const anyChecked = Array.from(industryDropdownList.querySelectorAll('input[type="checkbox"]')).some(cb => cb.checked);
                                        if (!anyChecked && chkAll) chkAll.checked = true;
                                        // Update button text logic manually
                                        const btn = document.getElementById('dropdown-industry').querySelector('.custom-select-btn');
                                        const checked = Array.from(industryDropdownList.querySelectorAll('input[type="checkbox"]')).filter(cb => cb.checked && cb !== chkAll);
                                        if (chkAll && chkAll.checked) {
                                            btn.textContent = chkAll.parentElement.textContent.trim();
                                        } else if (checked.length > 0) {
                                            btn.textContent = checked.map(cb => cb.parentElement.textContent.trim()).join(', ');
                                        }
                                    });
                                    
                                    industryDropdownList.appendChild(label);
                                    existingValues.push(cleanInd);
                                    changed = true;
                                }
                            });
                        }
                    });
                }
                
                // 테이블 렌더링 전 기존 체크 상태 저장
                const checkedUrls = Array.from(document.querySelectorAll('.chk-row:checked')).map(cb => cb.dataset.url);
                renderTable(json.data, checkedUrls);
            }
        } catch (e) {
            console.error(e);
            tbody.innerHTML = `<tr><td colspan="8" style="color:red; text-align:center;">데이터를 불러오는 중 오류가 발생했습니다. 서버가 켜져 있는지 확인하세요.</td></tr>`;
        }
    };

    const renderTable = (data, checkedUrls = []) => {
        tbody.innerHTML = '';
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="empty-state">데이터가 없습니다.</td></tr>';
            return;
        }

        data.forEach(item => {
            const tr = document.createElement('tr');
            
            // 뉴스 등급 스타일링
            let gradeClass = '';
            let gradeTooltip = '';
            if(item.news_grade === 'S') { 
                gradeClass = 'news-grade-S'; 
                gradeTooltip = 'S 등급 (95~100점): 초대형 메가 딜, 글로벌 시장 판도를 바꾸는 M&A 등'; 
            } else if(item.news_grade === 'AAA') { 
                gradeClass = 'news-grade-AAA'; 
                gradeTooltip = 'AAA 등급 (90~94점): 대규모 투자 유치, 주요 상장(IPO) 등 결정적 기사'; 
            } else if(item.news_grade === 'AA') { 
                gradeClass = 'news-grade-AA'; 
                gradeTooltip = 'AA 등급 (85~89점): 핵심 파트너십 체결, 주요 규제 통과 등 큰 호재'; 
            } else if(item.news_grade === 'A') { 
                gradeClass = 'news-grade-A'; 
                gradeTooltip = 'A 등급 (80~84점): 시리즈 B/C 이상의 유의미한 후속 투자 유치'; 
            } else if(item.news_grade === 'BBB') { 
                gradeClass = 'news-grade-BBB'; 
                gradeTooltip = 'BBB 등급 (70~79점): 시리즈 A/B 등 중간 규모 투자, 주요 실적 발표'; 
            } else if(item.news_grade === 'BB') { 
                gradeClass = 'news-grade-BB'; 
                gradeTooltip = 'BB 등급 (60~69점): 초기 시드 투자(팁스 등), 유의미한 신제품 출시'; 
            } else if(item.news_grade === 'B') { 
                gradeClass = 'news-grade-B'; 
                gradeTooltip = 'B 등급 (50~59점): 일반적인 산업 동향, 벤처 관련 일반 기사'; 
            } else { 
                gradeClass = 'news-grade-기타'; 
                gradeTooltip = '기타 등급 (50점 미만): 영향력이 미미하거나 벤처 투자와 무관한 가십/광고'; 
            }

            const isChecked = checkedUrls.includes(item.link) ? 'checked' : '';
            tr.innerHTML = `
                <td style="text-align: center;"><input type="checkbox" class="chk-row" data-url="${item.link}" ${isChecked}></td>
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

        // "전체 선택" 체크박스 상태 초기화
        const chkAll = document.getElementById('chk-all');
        if (chkAll) {
            chkAll.checked = false;
        }
    };

    // 체크박스 전체 선택/해제 이벤트
    document.getElementById('chk-all').addEventListener('change', (e) => {
        const isChecked = e.target.checked;
        document.querySelectorAll('.chk-row').forEach(chk => {
            chk.checked = isChecked;
        });
    });

    // 선택된 기사 다중 리포트 생성 버튼
    document.getElementById('btn-generate-selected-report').addEventListener('click', () => {
        const urlBriefingModal = document.getElementById('url-briefing-modal');
        const urlBriefingInput = document.getElementById('url-briefing-input');
        const sourceOption = document.getElementById('url-source-option');
        
        if (urlBriefingModal && urlBriefingInput) {
            if(sourceOption) sourceOption.value = 'checked'; // 기본값: 체크된 기사
            if(sourceOption) sourceOption.dispatchEvent(new Event('change'));
            urlBriefingModal.style.display = 'flex';
        }
    });

    btnApply.addEventListener('click', () => {
        fetchArticles();
    });

    btnRealtime.addEventListener('click', async () => {
        btnRealtime.disabled = true;
        btnLoader.style.display = 'block';
        statusBadge.textContent = '수집 중...';
        statusBadge.classList.add('active');
        updateMsg.textContent = '데이터 수집 및 분석을 시작합니다 (약 1~2분 소요)...';
        document.getElementById('new-news-stats').textContent = '';
        
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
                            updateMsg.textContent = '수집이 완료되었습니다!';
                            
                            // 결과 표시
                            if (statusJson.result && Object.keys(statusJson.result).length > 0) {
                                let stats = [];
                                for (let [country, count] of Object.entries(statusJson.result)) {
                                    stats.push(`${country} ${count}건`);
                                }
                                document.getElementById('new-news-stats').textContent = `[신규 추가] ${stats.join(', ')}`;
                            } else {
                                document.getElementById('new-news-stats').textContent = '[신규 추가] 0건 (최신 유지 중)';
                            }
                            
                            btnRealtime.disabled = false;
                            btnLoader.style.display = 'none';
                            statusBadge.textContent = '완료됨';
                            statusBadge.classList.remove('active');
                            setTimeout(() => {
                                statusBadge.textContent = '대기 중';
                            }, 5000);
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

    document.getElementById('btn-report').addEventListener('click', async () => {
        reportModal.style.display = 'flex';
        document.getElementById('report-loading').style.display = 'block';
        const revealContainer = document.getElementById('reveal-container');
        if (revealContainer) revealContainer.style.display = 'none';
        
        try {
            const res = await fetch('/api/report');
            const json = await res.json();
            if (json.status === 'success') {
                const markdownText = json.report;
                const reportHtml = marked.parse(markdownText);
                document.getElementById('report-content-container').innerHTML = reportHtml;
                
                document.getElementById('report-loading').style.display = 'none';
                document.getElementById('report-content-container').style.display = 'block';
                
                
            } else {
                document.getElementById('report-loading').textContent = '리포트 생성 실패: ' + (json.message || '알 수 없는 오류');
            }
        } catch (e) {
            console.error(e);
            document.getElementById('report-loading').textContent = '리포트 생성 중 오류 발생';
        }
    });

    document.getElementById('btn-print-pdf').addEventListener('click', () => {
        // PDF 출력을 위한 새 창 열기 (Reveal.js print-pdf 모드 활용)
        const textarea = document.querySelector('#reveal-slides textarea');
        if (!textarea) return;
        const md = textarea.value;
        
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <title>AI 요약 브리핑 리포트 (PDF 출력)</title>
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/reveal.min.css">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/theme/night.min.css">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/css/print/pdf.min.css">
                <style>
                    /* 인쇄 시 왼쪽 상단에 날짜 표시 */
                    @page { margin: 0; }
                    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                    .print-header {
                        position: fixed;
                        top: 20px;
                        left: 20px;
                        font-size: 14px;
                        color: #ccc;
                        z-index: 1000;
                    }
                </style>
            </head>
            <body>
                <div class="print-header">생성일: ${new Date().toISOString().split('T')[0]}</div>
                <div class="reveal">
                    <div class="slides">
                        <section data-markdown data-separator="^---"><textarea data-template>${md}</textarea></section>
                    </div>
                </div>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/reveal.min.js"><\/script>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/plugin/markdown/markdown.js"><\/script>
                <script>
                    Reveal.initialize({
                        plugins: [ RevealMarkdown ],
                        width: 1024,
                        height: 768,
                        margin: 0.1,
                        pdfSeparateFragments: false
                    }).then(() => {
                        // Reveal.js 렌더링 완료 후 인쇄 다이얼로그 호출
                        setTimeout(() => { window.print(); }, 1500);
                    });
                <\/script>
            </body>
            </html>
        `);
        printWindow.document.close();
    });

    document.getElementById('btn-close-report').addEventListener('click', () => {
        reportModal.style.display = 'none';
    });
    
    // URL Briefing Modal Logic
    const urlBriefingModal = document.getElementById('url-briefing-modal');
    if (urlBriefingModal) {
        document.getElementById('btn-open-url-briefing').addEventListener('click', () => {
            const sourceOption = document.getElementById('url-source-option');
            if (sourceOption) {
                sourceOption.value = 'checked';
                sourceOption.dispatchEvent(new Event('change'));
            }
            urlBriefingModal.style.display = 'flex';
        });
        
        document.getElementById('btn-close-url-briefing').addEventListener('click', () => {
            urlBriefingModal.style.display = 'none';
        });

        const sourceOptionEl = document.getElementById('url-source-option');
        if (sourceOptionEl) {
            sourceOptionEl.addEventListener('change', (e) => {
                const opt = e.target.value;
                let urls = [];
                if (opt === 'checked') {
                    urls = Array.from(document.querySelectorAll('.chk-row:checked')).map(chk => chk.dataset.url);
                } else {
                    urls = Array.from(document.querySelectorAll('.chk-row')).map(chk => chk.dataset.url);
                }
                document.getElementById('url-briefing-input').value = urls.join('\n');
            });
        }

        document.getElementById('btn-generate-url-briefing').addEventListener('click', async () => {
            const text = document.getElementById('url-briefing-input').value;
            const urls = text.split('\n').map(u => u.trim()).filter(u => u);
            
            if (urls.length === 0) {
                alert('URL을 1개 이상 입력(또는 선택)해주세요.');
                return;
            }

            urlBriefingModal.style.display = 'none'; // 입력창 닫기
            
            // 결과 모달창 띄우기
            reportModal.style.display = 'flex';
            document.getElementById('report-loading').style.display = 'block';
            document.getElementById('report-loading').textContent = 'AI가 기사 원문을 수집하고 브리핑 리포트를 생성 중입니다... (약 10~30초 소요)';
            const revealContainer = document.getElementById('reveal-container');
            if (revealContainer) revealContainer.style.display = 'none';

            try {
                const res = await fetch('/api/generate_url_briefing', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ urls: urls, grade_option: "ALL" })
                });
                const json = await res.json();
                if (json.status === 'success') {
                    const markdownText = json.report;
                    const reportHtml = marked.parse(markdownText);
                    document.getElementById('report-content-container').innerHTML = reportHtml;
                    
                    document.getElementById('report-loading').style.display = 'none';
                    document.getElementById('report-content-container').style.display = 'block';
                    
                    // 왼쪽 상단 일자 표시
                    if (!document.getElementById('report-date-overlay')) {
                        const dateOverlay = document.createElement('div');
                        dateOverlay.id = 'report-date-overlay';
                        dateOverlay.style.position = 'absolute';
                        dateOverlay.style.top = '15px';
                        dateOverlay.style.left = '15px';
                        dateOverlay.style.zIndex = '1000';
                        dateOverlay.style.fontSize = '14px';
                        dateOverlay.style.color = '#334155';
                        const d = new Date();
                        const yyyy = d.getFullYear();
                        const mm = String(d.getMonth() + 1).padStart(2, '0');
                        const dd = String(d.getDate()).padStart(2, '0');
                        dateOverlay.innerHTML = `생성일: ${yyyy}-${mm}-${dd}`;
                        document.querySelector('.modal-body').appendChild(dateOverlay);
                    }
                } else {
                    document.getElementById('report-loading').textContent = '생성 실패: ' + (json.message || '알 수 없는 오류');
                }
            } catch (e) {
                console.error(e);
                document.getElementById('report-loading').textContent = '요청 중 오류가 발생했습니다.';
            }
        });
    }
    
    // Close on click outside
    window.addEventListener('click', (e) => {
        if (e.target === settingsModal) settingsModal.style.display = 'none';
        if (e.target === reportModal) reportModal.style.display = 'none';
        if (urlBriefingModal && e.target === urlBriefingModal) urlBriefingModal.style.display = 'none';
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

    // API Key Modal Logic
    const apiKeyModal = document.getElementById('apikey-modal');
    const btnOpenApiKey = document.getElementById('btn-open-apikey');
    const btnCloseApiKey = document.getElementById('btn-close-apikey');
    const btnSaveApiKey = document.getElementById('btn-save-apikey');
    const inputApiKey = document.getElementById('input-api-key');

    if (btnOpenApiKey && apiKeyModal) {
        btnOpenApiKey.addEventListener('click', () => {
            inputApiKey.value = '';
            apiKeyModal.style.display = 'flex';
        });
        
        btnCloseApiKey.addEventListener('click', () => {
            apiKeyModal.style.display = 'none';
        });
        
        btnSaveApiKey.addEventListener('click', async () => {
            const newKey = inputApiKey.value.trim();
            if (!newKey) {
                alert('API 키를 입력해주세요.');
                return;
            }
            
            btnSaveApiKey.textContent = '저장 중...';
            btnSaveApiKey.disabled = true;
            
            try {
                const res = await fetch('/api/update_api_key', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ api_key: newKey })
                });
                const json = await res.json();
                
                if (json.status === 'success') {
                    alert('API 키가 성공적으로 변경되었습니다! 서버가 재시작될 수 있으니 잠시 후 사용해주세요.');
                    apiKeyModal.style.display = 'none';
                } else {
                    alert('오류 발생: ' + (json.message || '알 수 없는 오류'));
                }
            } catch (e) {
                console.error(e);
                alert('API 키 업데이트 중 오류가 발생했습니다.');
            } finally {
                btnSaveApiKey.textContent = '저장 및 적용';
                btnSaveApiKey.disabled = false;
            }
        });
    }
});
