document.addEventListener('DOMContentLoaded', () => {
    const btnApply = document.getElementById('btn-apply');
    const btnRealtime = document.getElementById('btn-realtime');
    const btnLoader = document.getElementById('btn-loader');
    const tbody = document.getElementById('table-body');
    const statusBadge = document.getElementById('status-badge');
    const updateMsg = document.getElementById('update-msg');

    let statisticsData = null;
    let currentPeriod = 'today';
    let currentPage = 1;

    const fetchStatistics = async () => {
        try {
            const res = await fetch('/api/statistics');
            const json = await res.json();
            if (json.status === 'success') {
                statisticsData = json.data;
                renderStatistics();
            }
        } catch (e) {
            console.error("통계 데이터를 가져오는 데 실패했습니다:", e);
        }
    };

    const renderStatistics = () => {
        if (!statisticsData || !statisticsData[currentPeriod]) return;
        const periodData = statisticsData[currentPeriod];
        
        // 1. 요약 값 업데이트
        document.getElementById('stat-total-count').textContent = `${periodData.total_count}건`;
        document.getElementById('stat-avg-impact').textContent = `${periodData.avg_impact.toFixed(1)}점`;
        
        // 2. 국가별 분포 렌더링
        const countriesList = document.getElementById('stat-countries-list');
        countriesList.innerHTML = '';
        const totalCount = periodData.total_count;
        
        if (totalCount === 0 || Object.keys(periodData.countries).length === 0) {
            countriesList.innerHTML = '<div style="font-size: 0.8rem; color: #9ca3af; text-align: center; padding: 10px 0;">기간 내 기사 없음</div>';
        } else {
            const sortedCountries = Object.entries(periodData.countries).sort((a, b) => b[1] - a[1]);
            sortedCountries.forEach(([country, count]) => {
                const percent = totalCount > 0 ? ((count / totalCount) * 100).toFixed(0) : 0;
                const barHtml = `
                    <div class="stat-bar-container">
                        <div class="stat-bar-label">
                            <span>${country}</span>
                            <span>${count}건 (${percent}%)</span>
                        </div>
                        <div class="stat-bar-outer">
                            <div class="stat-bar-inner" style="width: ${percent}%; background: linear-gradient(90deg, #3b82f6, #60a5fa);"></div>
                        </div>
                    </div>
                `;
                countriesList.insertAdjacentHTML('beforeend', barHtml);
            });
        }
        
        // 3. 투자 단계별 분포 렌더링
        const stagesList = document.getElementById('stat-stages-list');
        stagesList.innerHTML = '';
        
        if (totalCount === 0 || Object.keys(periodData.stages).length === 0) {
            stagesList.innerHTML = '<div style="font-size: 0.8rem; color: #9ca3af; text-align: center; padding: 10px 0;">기간 내 기사 없음</div>';
        } else {
            const sortedStages = Object.entries(periodData.stages).sort((a, b) => b[1] - a[1]);
            sortedStages.forEach(([stage, count]) => {
                const percent = totalCount > 0 ? ((count / totalCount) * 100).toFixed(0) : 0;
                const barHtml = `
                    <div class="stat-bar-container">
                        <div class="stat-bar-label">
                            <span>${stage}</span>
                            <span>${count}건 (${percent}%)</span>
                        </div>
                        <div class="stat-bar-outer">
                            <div class="stat-bar-inner" style="width: ${percent}%; background: linear-gradient(90deg, #10b981, #34d399);"></div>
                        </div>
                    </div>
                `;
                stagesList.insertAdjacentHTML('beforeend', barHtml);
            });
        }
    };

    // 통계 탭 클릭 리스너 부착
    document.querySelectorAll('.anal-tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.anal-tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentPeriod = btn.dataset.period;
            renderStatistics();
        });
    });

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

    ['dropdown-country', 'dropdown-stage', 'dropdown-grade'].forEach(setupCheckboxes);

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

            // 페이징 파라미터 적용
            params.append('page', currentPage);
            params.append('page_size', 20);

            const res = await fetch(`/api/articles?${params.toString()}`);
            const json = await res.json();
            
            if (json.status === 'success') {
                document.getElementById('collected-count').textContent = `검색된 딜: ${json.count} 건`;
                
                // 테이블 렌더링 전 기존 체크 상태 저장
                const checkedUrls = Array.from(document.querySelectorAll('.chk-row:checked')).map(cb => cb.dataset.url);
                renderTable(json.data, checkedUrls);
                
                // 페이지네이션 렌더링
                renderPagination(json.total_pages, json.page);
            }
        } catch (e) {
            console.error(e);
            tbody.innerHTML = `<tr><td colspan="8" style="color:red; text-align:center;">데이터를 불러오는 중 오류가 발생했습니다. 서버가 켜져 있는지 확인하세요.</td></tr>`;
        }
    };

    const renderPagination = (totalPages, activePage) => {
        const paginationControls = document.getElementById('pagination-controls');
        if (!paginationControls) return;
        paginationControls.innerHTML = '';
        
        if (totalPages <= 1) return;
        
        const createButton = (text, targetPage, active = false, disabled = false) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.textContent = text;
            btn.style.padding = '6px 12px';
            btn.style.border = '1px solid rgba(255,255,255,0.1)';
            btn.style.borderRadius = '6px';
            btn.style.cursor = disabled ? 'not-allowed' : 'pointer';
            btn.style.fontSize = '0.8rem';
            btn.style.transition = 'all 0.2s';
            
            if (active) {
                btn.style.background = 'var(--primary-color)';
                btn.style.color = '#fff';
                btn.style.borderColor = 'var(--primary-color)';
            } else {
                btn.style.background = 'rgba(255,255,255,0.03)';
                btn.style.color = 'var(--text-main)';
            }
            
            if (disabled) {
                btn.disabled = true;
                btn.style.opacity = '0.3';
            } else {
                btn.addEventListener('click', () => {
                    currentPage = targetPage;
                    fetchArticles();
                    // 페이지 이동 시 대시보드 테이블 영역으로 부드럽게 스크롤
                    const pipelineSection = document.querySelector('.preview-section');
                    if (pipelineSection) {
                        pipelineSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                });
            }
            return btn;
        };
        
        // 이전 버튼
        paginationControls.appendChild(createButton('이전', activePage - 1, false, activePage === 1));
        
        // 페이지 버튼 범위 계산 (최대 5개)
        const maxVisible = 5;
        let startPage = Math.max(1, activePage - Math.floor(maxVisible / 2));
        let endPage = Math.min(totalPages, startPage + maxVisible - 1);
        
        if (endPage - startPage + 1 < maxVisible) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }
        
        for (let i = startPage; i <= endPage; i++) {
            paginationControls.appendChild(createButton(i.toString(), i, i === activePage));
        }
        
        // 다음 버튼
        paginationControls.appendChild(createButton('다음', activePage + 1, false, activePage === totalPages));
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

            const getTodayStr = () => {
                const now = new Date();
                const year = now.getFullYear();
                const month = String(now.getMonth() + 1).padStart(2, '0');
                const day = String(now.getDate()).padStart(2, '0');
                return `${year}-${month}-${day}`;
            };
            const todayStr = getTodayStr();

            const chkAllPages = document.getElementById('chk-all-pages');
            const chkToday = document.getElementById('chk-today');

            let isChecked = checkedUrls.includes(item.link) ? 'checked' : '';
            if (chkAllPages && chkAllPages.checked) {
                isChecked = 'checked';
            } else if (chkToday && chkToday.checked && item.created_at) {
                if (item.created_at.substring(0, 10) === todayStr) {
                    isChecked = 'checked';
                }
            }
            
            let industryCellHtml = '-';
            if (item.promising_industry) {
                const parts = item.promising_industry.split('>').map(p => p.trim());
                if (parts.length >= 3) {
                    const major = parts[0];
                    const middle = parts[1];
                    const minor = parts[2];
                    const majorClass = major === 'AI' ? 'badge-major-ai' :
                                       major === 'ICT' ? 'badge-major-ict' :
                                       major === '바이오' ? 'badge-major-bio' :
                                       major === '커머스' ? 'badge-major-commerce' : 'badge-major-etc';
                    industryCellHtml = `
                        <div class="table-industry-hierarchy">
                            <span class="badge-major ${majorClass}">${major}</span>
                            <span class="sub-industry-text" title="${item.promising_industry}">${minor}</span>
                        </div>
                    `;
                } else if (parts.length === 1) {
                    industryCellHtml = `<span style="font-size: 0.85rem;">${item.promising_industry}</span>`;
                } else {
                    industryCellHtml = `<span style="font-size: 0.82rem; color: #cbd5e1;">${item.promising_industry}</span>`;
                }
            }

            tr.innerHTML = `
                <td style="text-align: center;"><input type="checkbox" class="chk-row" data-url="${item.link}" data-date="${item.created_at || ''}" ${isChecked}></td>
                <td>${item.country || '-'}</td>
                <td class="${gradeClass}" title="${gradeTooltip}" style="cursor: help;">${item.news_grade || '-'}</td>
                <td><span style="background: rgba(255,255,255,0.1); padding: 4px 8px; border-radius: 4px; font-size: 0.85em;">${item.deal_stage || '-'}</span></td>
                <td>${industryCellHtml}</td>
                <td><a href="${item.link}" target="_blank" style="color: #60a5fa; text-decoration: none;">${item.title}</a></td>
                <td style="color: #34d399; font-weight: bold;">${item.impact_score ? item.impact_score.toFixed(1) : '-'}</td>
                <td>${item.source_name || '-'}</td>
                <td>${item.created_at || '-'}</td>
            `;
            tbody.appendChild(tr);
        });

        // "전체 선택" 테이블 헤더 체크박스 상태 업데이트
        const chkAll = document.getElementById('chk-all');
        const chkAllPages = document.getElementById('chk-all-pages');
        if (chkAll) {
            chkAll.checked = chkAllPages ? chkAllPages.checked : false;
        }
    };

    const getTodayStr = () => {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    };

    // 테이블 헤더 '전체 선택' 체크박스
    const chkAllHeader = document.getElementById('chk-all');
    if (chkAllHeader) {
        chkAllHeader.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            document.querySelectorAll('.chk-row').forEach(chk => {
                chk.checked = isChecked;
            });
        });
    }

    // '전체(필터)' 상단 체크박스
    const chkAllPages = document.getElementById('chk-all-pages');
    if (chkAllPages) {
        chkAllPages.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            if (isChecked) {
                const chkToday = document.getElementById('chk-today');
                if (chkToday) chkToday.checked = false;
            }
            document.querySelectorAll('.chk-row').forEach(chk => {
                chk.checked = isChecked;
            });
            const chkAll = document.getElementById('chk-all');
            if (chkAll) chkAll.checked = isChecked;
        });
    }

    // '당일 선택' 상단 체크박스
    const chkToday = document.getElementById('chk-today');
    if (chkToday) {
        chkToday.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            if (isChecked) {
                const chkAllPages = document.getElementById('chk-all-pages');
                if (chkAllPages) chkAllPages.checked = false;
            }
            const todayStr = getTodayStr();
            document.querySelectorAll('.chk-row').forEach(chk => {
                const dateAttr = chk.dataset.date || '';
                if (isChecked) {
                    chk.checked = (dateAttr.substring(0, 10) === todayStr);
                } else {
                    chk.checked = false;
                }
            });
            const chkAll = document.getElementById('chk-all');
            if (chkAll) chkAll.checked = false;
        });
    }

    // 선택된 기사 다중 리포트 생성 버튼
    document.getElementById('btn-generate-selected-report').addEventListener('click', async () => {
        const urlBriefingModal = document.getElementById('url-briefing-modal');
        const urlBriefingInput = document.getElementById('url-briefing-input');
        const sourceOption = document.getElementById('url-source-option');
        
        // 체크된 기사 URL 수집
        const checkedBoxes = Array.from(document.querySelectorAll('.chk-row:checked'));
        const checkedUrls = checkedBoxes.map(chk => chk.dataset.url).filter(u => u);
        
        if (urlBriefingModal && urlBriefingInput) {
            if (checkedUrls.length > 0) {
                urlBriefingInput.value = checkedUrls.join('\n');
            }
            if(sourceOption) sourceOption.value = 'checked';
            urlBriefingModal.style.display = 'flex';
        }
    });

    // 전체화면 토글 기능
    const btnToggleFullscreen = document.getElementById('btn-toggle-fullscreen');
    const previewSection = document.querySelector('.preview-section');
    const fullscreenBtnText = document.getElementById('fullscreen-btn-text');

    if (btnToggleFullscreen && previewSection && fullscreenBtnText) {
        btnToggleFullscreen.addEventListener('click', () => {
            const isActive = previewSection.classList.toggle('fullscreen-active');
            if (isActive) {
                fullscreenBtnText.textContent = '원래 화면';
                btnToggleFullscreen.querySelector('span').textContent = '🗗';
            } else {
                fullscreenBtnText.textContent = '전체 화면';
                btnToggleFullscreen.querySelector('span').textContent = '⛶';
            }
        });
    }

    // 실시간 간격별 분석 리포트 접기/펴기 토글 기능
    const btnToggleStatsPanel = document.getElementById('btn-toggle-stats-panel');
    const statsPanelContent = document.getElementById('stats-panel-content');

    if (btnToggleStatsPanel && statsPanelContent) {
        // 로컬스토리지 저장 상태 로드
        const statsCollapsed = localStorage.getItem('statsPanelCollapsed') === 'true';
        if (statsCollapsed) {
            statsPanelContent.classList.add('stats-panel-collapsed');
            btnToggleStatsPanel.textContent = '▼ 리포트 열기';
        }

        btnToggleStatsPanel.addEventListener('click', () => {
            const isCollapsed = statsPanelContent.classList.toggle('stats-panel-collapsed');
            localStorage.setItem('statsPanelCollapsed', isCollapsed);
            if (isCollapsed) {
                btnToggleStatsPanel.textContent = '▼ 리포트 열기';
            } else {
                btnToggleStatsPanel.textContent = '▲ 리포트 접기';
            }
        });
    }

    btnApply.addEventListener('click', () => {
        currentPage = 1;
        fetchArticles();
        fetchStatistics();
    });

    btnRealtime.addEventListener('click', async () => {
        const checkedFilter = document.querySelector('input[name="date-filter"]:checked');
        const filterVal = checkedFilter ? checkedFilter.value : 'all';
        
        let daysLimit = 2; // 기본값: 전일
        let periodName = '전일';
        if (filterVal === 'today') {
            daysLimit = 1;
            periodName = '당일';
        } else if (filterVal === 'yesterday') {
            daysLimit = 2;
            periodName = '전일';
        } else if (filterVal === '1week') {
            daysLimit = 7;
            periodName = '일주일';
        } else if (filterVal === '1month' || filterVal === 'all') {
            daysLimit = 30;
            periodName = '한달';
        }

        btnRealtime.disabled = true;
        btnLoader.style.display = 'block';
        statusBadge.textContent = '수집 중...';
        statusBadge.classList.add('active');
        updateMsg.textContent = `${periodName} 기준 데이터 수집 및 분석을 시작합니다 (약 1~2분 소요)...`;
        document.getElementById('new-news-stats').textContent = '';
        
        try {
            const res = await fetch(`/api/crawl_now?days_limit=${daysLimit}&max_articles=50`, { method: 'POST' });
            const json = await res.json();
            if (json.status === 'success') {
                const pollInterval = setInterval(async () => {
                    try {
                        const statusRes = await fetch('/api/crawl_status');
                        const statusJson = await statusRes.json();
                        
                        // 주기적으로 테이블 새로고침하여 새로 추가된 데이터를 바로 보여줌
                        fetchArticles();
                        fetchStatistics();
                        
                        if (statusJson.status === 'success') {
                            const progress = statusJson.progress;
                            
                            // 수집 오류 발생 시 알림창 및 전용 에러 메시지 노출
                            if (progress && progress.status === 'failed') {
                                clearInterval(pollInterval);
                                updateMsg.innerHTML = `<span style="color:#ef4444; font-weight:bold;">🚨 수집 실패:</span> ${progress.message}`;
                                alert(`수집 오류가 발생했습니다.\n\n안내: ${progress.message}`);
                                
                                btnRealtime.disabled = false;
                                btnLoader.style.display = 'none';
                                statusBadge.textContent = '실패함';
                                statusBadge.classList.remove('active');
                                return;
                            }
                            
                            if (progress) {
                                updateMsg.innerHTML = `<span style="color:#f59e0b; font-weight:bold;">[${progress.percent}%]</span> ${progress.message}`;
                            }
                            
                            if (!statusJson.is_crawling) {
                                clearInterval(pollInterval);
                                updateMsg.textContent = '수집이 완료되었습니다!';
                                fetchStatistics();
                                
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
                                    updateMsg.textContent = '최신 데이터를 확인하세요.';
                                }, 5000);
                            }
                        }
                    } catch(e) {}
                }, 2000);
            } else {
                updateMsg.textContent = json.message;
                btnRealtime.disabled = false;
                btnLoader.style.display = 'none';
                statusBadge.textContent = '대기 중';
                statusBadge.classList.remove('active');
                setTimeout(() => {
                    updateMsg.textContent = '최신 데이터를 확인하세요.';
                }, 5000);
            }
        } catch (e) {
            console.error(e);
            updateMsg.textContent = '서버 통신 오류';
            btnRealtime.disabled = false;
            btnLoader.style.display = 'none';
            statusBadge.textContent = '대기 중';
            statusBadge.classList.remove('active');
            setTimeout(() => {
                updateMsg.textContent = '최신 데이터를 확인하세요.';
            }, 5000);
        }
    });

    // 초기 로드 시 데이터 가져오기
    fetchArticles();
    fetchStatistics();

    // =========================================================================
    // 글로벌 VC 산업분류 체계 (42개 소분류 & 5대 대분류 계층형 드롭다운 로직)
    // =========================================================================
    const loadIndustryHierarchy = async () => {
        try {
            const res = await fetch('/api/industries');
            const json = await res.json();
            if (json.status !== 'success' || !json.hierarchy) return;

            const container = document.getElementById('industry-tree-container');
            if (!container) return;
            container.innerHTML = '';

            const hierarchy = json.hierarchy;
            const majorList = ['AI', 'ICT', '바이오', '커머스', '기타'];

            const indContainer = document.getElementById('dropdown-industry');
            const selectBtn = indContainer ? indContainer.querySelector('.custom-select-btn') : null;
            const chkAll = document.getElementById('industry-dropdown-list').querySelector('.chk-all-opt');

            const updateIndustryBtnText = () => {
                const checkedInputs = Array.from(document.querySelectorAll('#industry-dropdown-list input[name="industry"]:checked'))
                    .filter(cb => cb.value !== '');
                if (!selectBtn) return;
                if (chkAll && chkAll.checked) {
                    selectBtn.textContent = '전체 산업';
                } else if (checkedInputs.length === 0) {
                    if (chkAll) chkAll.checked = true;
                    selectBtn.textContent = '전체 산업';
                } else if (checkedInputs.length <= 2) {
                    selectBtn.textContent = checkedInputs.map(cb => cb.dataset.name || cb.value).join(', ');
                } else {
                    selectBtn.textContent = `${checkedInputs[0].dataset.name || checkedInputs[0].value} 외 ${checkedInputs.length - 1}개`;
                }
            };

            if (chkAll) {
                chkAll.addEventListener('change', () => {
                    if (chkAll.checked) {
                        document.querySelectorAll('#industry-dropdown-list input[name="industry"]').forEach(cb => {
                            if (cb !== chkAll) cb.checked = false;
                        });
                    }
                    updateIndustryBtnText();
                });
            }

            majorList.forEach(major => {
                if (!hierarchy[major]) return;
                const majorClass = major === 'AI' ? 'badge-major-ai' :
                                   major === 'ICT' ? 'badge-major-ict' :
                                   major === '바이오' ? 'badge-major-bio' :
                                   major === '커머스' ? 'badge-major-commerce' : 'badge-major-etc';

                const block = document.createElement('div');
                block.className = 'ind-major-block';

                // 헤더
                const header = document.createElement('div');
                header.className = 'ind-major-header';
                header.innerHTML = `
                    <div class="ind-major-header-left">
                        <span class="badge-major ${majorClass}">${major}</span>
                        <span>${major}</span>
                    </div>
                    <span class="ind-toggle-icon">▶</span>
                `;

                // 내용 (중분류 + 소분류)
                const content = document.createElement('div');
                content.className = 'ind-major-content';

                header.addEventListener('click', (e) => {
                    const isOpen = content.classList.contains('open');
                    if (isOpen) {
                        content.classList.remove('open');
                        header.querySelector('.ind-toggle-icon').classList.remove('open');
                    } else {
                        content.classList.add('open');
                        header.querySelector('.ind-toggle-icon').classList.add('open');
                    }
                });

                const middles = hierarchy[major];
                Object.keys(middles).forEach(middle => {
                    const midTitle = document.createElement('div');
                    midTitle.className = 'ind-middle-title';
                    midTitle.textContent = `• ${middle}`;
                    content.appendChild(midTitle);

                    middles[middle].forEach(sub => {
                        const label = document.createElement('label');
                        label.className = 'ind-minor-label';
                        label.innerHTML = `
                            <input type="checkbox" name="industry" value="${sub.minor}" data-name="${sub.minor}" data-major="${major}">
                            <span>${sub.minor}</span>
                        `;
                        const chk = label.querySelector('input');
                        chk.addEventListener('change', () => {
                            if (chk.checked && chkAll) {
                                chkAll.checked = false;
                            }
                            updateIndustryBtnText();
                        });
                        content.appendChild(label);
                    });
                });

                block.appendChild(header);
                block.appendChild(content);
                container.appendChild(block);
            });

            // '기타/미정' 소분류 블록 추가 (애매한 항목 전용)
            const etcBlock = document.createElement('div');
            etcBlock.className = 'ind-major-block';
            etcBlock.innerHTML = `
                <div class="ind-major-header" style="cursor: default;">
                    <div class="ind-major-header-left">
                        <span class="badge-major badge-major-etc">기타</span>
                        <label class="ind-minor-label" style="padding:0; margin-left:6px; cursor: pointer;">
                            <input type="checkbox" name="industry" value="기타" data-name="기타/미정">
                            <span>기타/미정 (애매한 항목)</span>
                        </label>
                    </div>
                </div>
            `;
            const etcChk = etcBlock.querySelector('input');
            if (etcChk) {
                etcChk.addEventListener('change', () => {
                    if (etcChk.checked && chkAll) chkAll.checked = false;
                    updateIndustryBtnText();
                });
            }
            container.appendChild(etcBlock);

        } catch (e) {
            console.error("Failed to load industry hierarchy", e);
        }
    };

    // 초기 산업 분류 트리 로드
    loadIndustryHierarchy();

    // =========================================================================
    // 좌측 사이드바: 산업분류별 키워드 관리 & 탭 렌더링
    // =========================================================================
    const keywordInput = document.getElementById('custom-keyword');
    const keywordTags = document.getElementById('keyword-tags');
    const kwCategoryTabs = document.getElementById('kw-category-tabs');
    let currentKwMajorFilter = 'ALL';
    let cachedKeywords = [];

    if (kwCategoryTabs) {
        kwCategoryTabs.addEventListener('click', (e) => {
            const btn = e.target.closest('.kw-nav-tab');
            if (!btn) return;
            kwCategoryTabs.querySelectorAll('.kw-nav-tab').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentKwMajorFilter = btn.dataset.major || 'ALL';
            renderKeywords();
        });
    }

    const renderKeywords = () => {
        if (!keywordTags) return;
        keywordTags.innerHTML = '';

        const majorList = ['AI', 'ICT', '바이오', '커머스', '기타'];
        const filtered = currentKwMajorFilter === 'ALL'
            ? cachedKeywords
            : cachedKeywords.filter(k => (k.major || '기타') === currentKwMajorFilter);

        if (filtered.length === 0) {
            keywordTags.innerHTML = '<div style="font-size:0.78rem; color:#64748b; padding:8px 4px;">등록된 키워드가 없습니다.</div>';
            return;
        }

        // 대분류별 그룹핑
        const grouped = {};
        filtered.forEach(kw => {
            const m = kw.major || '기타';
            if (!grouped[m]) grouped[m] = [];
            grouped[m].push(kw);
        });

        // 탭 선택 상태에 따라 렌더링
        const displayMajors = currentKwMajorFilter === 'ALL' ? majorList : [currentKwMajorFilter];

        displayMajors.forEach(m => {
            const items = grouped[m];
            if (!items || items.length === 0) return;

            const card = document.createElement('div');
            const borderClass = m === 'AI' ? 'border-ai' :
                                m === 'ICT' ? 'border-ict' :
                                m === '바이오' ? 'border-bio' :
                                m === '커머스' ? 'border-commerce' : 'border-etc';
            card.className = `kw-group-card ${borderClass}`;

            const majorBadgeClass = m === 'AI' ? 'badge-major-ai' :
                                    m === 'ICT' ? 'badge-major-ict' :
                                    m === '바이오' ? 'badge-major-bio' :
                                    m === '커머스' ? 'badge-major-commerce' : 'badge-major-etc';

            card.innerHTML = `
                <div class="kw-group-title">
                    <span class="badge-major ${majorBadgeClass}">${m}</span>
                    <span style="font-size: 0.7rem; color: #94a3b8;">${items.length}개</span>
                </div>
                <div class="kw-tags-flex" style="display:flex; flex-wrap:wrap; gap:4px; margin-top:4px;"></div>
            `;

            const flex = card.querySelector('.kw-tags-flex');
            items.forEach(kw => {
                const tag = document.createElement('span');
                tag.className = 'kw-tag-item';
                tag.title = kw.formatted_industry ? `산업: ${kw.formatted_industry}` : `키워드: ${kw.keyword}`;
                tag.innerHTML = `
                    <span>${kw.keyword}</span>
                    ${!kw.is_builtin ? `<span class="kw-tag-del-btn" data-id="${kw.id}">×</span>` : ''}
                `;
                
                const delBtn = tag.querySelector('.kw-tag-del-btn');
                if (delBtn) {
                    delBtn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        if (confirm(`'${kw.keyword}' 키워드를 삭제하시겠습니까?`)) {
                            await deleteKeyword(kw.id);
                        }
                    });
                }
                flex.appendChild(tag);
            });

            keywordTags.appendChild(card);
        });
    };

    const deleteKeyword = async (id) => {
        try {
            const res = await fetch(`/api/keywords/${id}`, { method: 'DELETE' });
            const json = await res.json();
            if (json.status === 'success') {
                loadKeywords();
            } else {
                alert(json.message || '삭제에 실패했습니다.');
            }
        } catch (e) {
            console.error("Failed to delete keyword", e);
        }
    };

    const loadKeywords = async () => {
        try {
            const res = await fetch('/api/keywords');
            const json = await res.json();
            if (json.status === 'success') {
                cachedKeywords = json.data || [];
                renderKeywords();
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
                        if (json.classification && json.classification.formatted) {
                            console.log(`[키워드 자동 분류] '${val}' -> ${json.classification.formatted}`);
                        }
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
        // PDF 출력을 위한 새 창 열기 (A4 보고서 모드)
        const reportContainer = document.getElementById('report-content-container');
        if (!reportContainer || !reportContainer.innerHTML.trim()) {
            alert('출력할 리포트 내용이 없습니다.');
            return;
        }
        const htmlContent = reportContainer.innerHTML;
        
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <title>AI 요약 브리핑 리포트 (PDF 출력)</title>
                <style>
                    /* 인쇄 시 여백 및 스타일 초기화 */
                    @page { margin: 15mm; }
                    body { 
                        -webkit-print-color-adjust: exact; 
                        print-color-adjust: exact; 
                        background: #ffffff;
                        color: #1e293b;
                        font-family: 'Inter', 'Noto Sans KR', sans-serif;
                    }
                    .print-header {
                        font-size: 14px;
                        color: #64748b;
                        margin-bottom: 20px;
                        text-align: right;
                    }
                    .markdown-body {
                        max-width: 100%;
                        line-height: 1.8;
                    }
                    .markdown-body h1, .markdown-body h2, .markdown-body h3 {
                        color: #0f172a;
                        margin-top: 1.5em;
                        margin-bottom: 0.5em;
                        font-weight: 700;
                    }
                    .markdown-body h1 {
                        font-size: 2.2em;
                        border-bottom: 3px solid #2563eb;
                        padding-bottom: 0.3em;
                        text-align: center;
                        color: #1d4ed8;
                    }
                    .markdown-body h2 {
                        font-size: 1.6em;
                        border-bottom: 1px solid #e2e8f0;
                        padding-bottom: 0.3em;
                    }
                    .markdown-body h3 {
                        font-size: 1.3em;
                    }
                    .markdown-body table {
                        width: 100%;
                        border-collapse: collapse;
                        margin: 1.5em 0;
                        font-size: 0.95rem;
                    }
                    .markdown-body th, .markdown-body td {
                        padding: 12px 16px;
                        border: 1px solid #cbd5e1;
                    }
                    .markdown-body th {
                        background-color: #f1f5f9;
                        text-align: left;
                    }
                    .markdown-body blockquote {
                        border-left: 4px solid #cbd5e1;
                        padding-left: 1rem;
                        color: #64748b;
                        font-style: italic;
                    }
                </style>
            </head>
            <body>
                <div class="print-header">보고서 생성일: ${new Date().toISOString().split('T')[0]}</div>
                <div class="markdown-body">
                    ${htmlContent}
                </div>
                <script>
                    setTimeout(() => { window.print(); }, 500);
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
            if (urls.length >= 5) {
                document.getElementById('report-loading').textContent = `선택하신 ${urls.length}개 기사를 바탕으로 5페이지 이상의 심층 분석 리포트(산업 동향 및 기업 정보)를 작성 중입니다... (약 15~40초 소요)`;
            } else {
                document.getElementById('report-loading').textContent = `AI가 ${urls.length}개 기사 원문을 수집하고 브리핑 리포트를 생성 중입니다... (약 10~20초 소요)`;
            }
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
                    let dateOverlay = document.getElementById('report-date-overlay');
                    if (!dateOverlay) {
                        dateOverlay = document.createElement('div');
                        dateOverlay.id = 'report-date-overlay';
                        dateOverlay.style.position = 'absolute';
                        dateOverlay.style.top = '15px';
                        dateOverlay.style.left = '15px';
                        dateOverlay.style.zIndex = '1000';
                        dateOverlay.style.fontSize = '14px';
                        dateOverlay.style.color = '#334155';
                        document.querySelector('.modal-body').appendChild(dateOverlay);
                    }
                    const d = new Date();
                    const yyyy = d.getFullYear();
                    const mm = String(d.getMonth() + 1).padStart(2, '0');
                    const dd = String(d.getDate()).padStart(2, '0');
                    const hh = String(d.getHours()).padStart(2, '0');
                    const min = String(d.getMinutes()).padStart(2, '0');
                    const ss = String(d.getSeconds()).padStart(2, '0');
                    dateOverlay.innerHTML = `생성일시: ${yyyy}-${mm}-${dd} ${hh}:${min}:${ss}`;
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
        const apiKeyModal = document.getElementById('apikey-modal');
        if (apiKeyModal && e.target === apiKeyModal) apiKeyModal.style.display = 'none';
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
