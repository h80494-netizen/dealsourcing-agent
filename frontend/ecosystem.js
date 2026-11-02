/**
 * ecosystem.js
 * THE VC 벤치마킹 6대 메뉴 통합 네비게이션 · 통합검색 · 기업DB(DART/NICE) · 펀드(DIVA) · 중기부 정책/레지스트리 · 지원사업/특허 컨트롤러
 */
document.addEventListener('DOMContentLoaded', () => {
    const navButtons = document.querySelectorAll('.eco-nav-btn');
    const viewSections = document.querySelectorAll('.eco-view-section');

    const switchTab = (targetView) => {
        navButtons.forEach(b => b.classList.toggle('active', b.dataset.view === targetView));
        viewSections.forEach(sec => sec.classList.toggle('active', sec.id === `view-${targetView}`));

        if (targetView === 'overview') loadOverviewSummary();
        else if (targetView === 'companies') loadCompanies();
        else if (targetView === 'funds') loadFunds(1);
        else if (targetView === 'policy') loadVenturePolicy();
        else if (targetView === 'grants-ip') {
            loadGrants(1);
            loadSavedPatents();
        }
    };

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.view));
    });

    window.switchEcoTab = switchTab;

    const fmtNum = (v, digits = 1) => {
        if (v === null || v === undefined || v === '') return '-';
        const n = Number(v);
        if (Number.isNaN(n)) return v;
        return n.toLocaleString('ko-KR', { maximumFractionDigits: digits });
    };

    // =========================================================================
    // 1. 통합 오버뷰 & 통합검색
    // =========================================================================
    const loadOverviewSummary = async () => {
        try {
            const res = await fetch('/api/overview_summary');
            const json = await res.json();
            if (json.status !== 'success') return;

            const c = json.counts || {};
            const vs = json.latest_venture_scale || {};

            const setTxt = (id, txt) => {
                const el = document.getElementById(id);
                if (el) el.textContent = txt;
            };

            setTxt('ov-cnt-articles', `${fmtNum(c.articles, 0)}건`);
            setTxt('ov-sub-articles', `🏛️ 공공브리핑 ${fmtNum(c.public_gov_articles, 0)}건 포함`);
            setTxt('ov-cnt-companies', `${fmtNum(c.companies, 0)}개사`);
            setTxt('ov-cnt-funds', `${fmtNum(c.funds, 0)}개 조합`);
            setTxt('ov-cnt-grants', `${fmtNum(c.grants, 0)}건`);
            setTxt('ov-cnt-inv-scale', `${vs.new_investment_trillion || '-'}조원`);
            setTxt('ov-sub-inv-scale', `${vs.period || ''} 신규 벤처투자 (${vs.yoy_growth_pct >= 0 ? '+' : ''}${vs.yoy_growth_pct || 0}%)`);
            setTxt('ov-cnt-fund-scale', `${vs.new_fund_trillion || '-'}조원`);

            // 최근 등록 펀드
            const fundBox = document.getElementById('ov-recent-funds');
            if (fundBox) {
                fundBox.innerHTML = (json.recent_funds || []).map(f => `
                    <div class="eco-list-item">
                        <div style="min-width:0;">
                            <div style="font-weight:600; color:#f8fafc; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                                ${f.motae_backed ? '<span class="eco-badge eco-badge-motae" style="margin-right:4px;">모태출자</span>' : ''}
                                ${f.fund_name}
                            </div>
                            <div style="font-size:0.76rem; color:#94a3b8;">GP: ${f.gp_name} · 분야: ${f.invest_field || '-'}</div>
                        </div>
                        <div style="text-align:right; flex-shrink:0;">
                            <div style="color:#34d399; font-weight:700;">${f.commitment_krw ? fmtNum(f.commitment_krw) + '억' : '-'}</div>
                            <div style="font-size:0.73rem; color:#64748b;">${f.reg_date || ''}</div>
                        </div>
                    </div>
                `).join('') || '<div style="color:#64748b; padding:12px 0;">데이터가 없습니다.</div>';
            }

            // 마감 임박 지원사업
            const grantBox = document.getElementById('ov-active-grants');
            if (grantBox) {
                grantBox.innerHTML = (json.active_grants || []).map(g => {
                    const urgent = g.d_day && (g.d_day === 'D-Day' || (g.d_day.startsWith('D-') && parseInt(g.d_day.slice(2), 10) <= 7));
                    return `
                        <div class="eco-list-item">
                            <div style="min-width:0;">
                                <a href="${g.detail_url}" target="_blank" style="color:#93c5fd; text-decoration:none; font-weight:500;">[${g.category || '지원'}] ${g.title}</a>
                                <div style="font-size:0.75rem; color:#94a3b8;">${g.ministry || ''} · ${g.executor || ''}</div>
                            </div>
                            <span class="eco-badge ${urgent ? 'eco-badge-dday-urgent' : 'eco-badge-dday-normal'}">${g.d_day || '진행중'}</span>
                        </div>
                    `;
                }).join('') || '<div style="color:#64748b; padding:12px 0;">진행 중인 공고가 없습니다.</div>';
            }

            // 최신 기업 DB
            const compBox = document.getElementById('ov-recent-companies');
            if (compBox) {
                if (!json.recent_companies || json.recent_companies.length === 0) {
                    compBox.innerHTML = `
                        <div style="padding:14px; text-align:center; color:#94a3b8;">
                            저장된 기업이 없습니다.
                            <button type="button" class="eco-btn-sm eco-btn-accent" style="margin-left:8px;" onclick="window.syncFeaturedCompaniesFromOverview()">⚡ 대표 유니콘·벤처 DART 실데이터 불러오기</button>
                        </div>`;
                } else {
                    compBox.innerHTML = json.recent_companies.map(cp => `
                        <div class="eco-list-item">
                            <div>
                                <strong style="color:#f8fafc;">${cp.corp_name}</strong>
                                <span style="font-size:0.75rem; color:#94a3b8; margin-left:6px;">${cp.corp_cls || ''} · 대표 ${cp.ceo_name || '-'}</span>
                                <div style="font-size:0.75rem; color:#38bdf8;">등급: ${cp.credit_grade || '-'} (${cp.latest_bsns_year || '-'}년 결산)</div>
                            </div>
                            <div style="text-align:right;">
                                <div style="font-size:0.82rem; color:#e2e8f0;">매출 <strong>${fmtNum(cp.revenue_krw)}억</strong></div>
                                <div style="font-size:0.75rem; color:${(cp.op_profit_krw || 0) >= 0 ? '#34d399' : '#f43f5e'};">영업이익 ${fmtNum(cp.op_profit_krw)}억</div>
                            </div>
                        </div>
                    `).join('');
                }
            }

            // 최신 뉴스 & 공공브리핑
            const artBox = document.getElementById('ov-recent-articles');
            if (artBox) {
                artBox.innerHTML = (json.recent_articles || []).map(a => `
                    <div class="eco-list-item">
                        <div style="min-width:0;">
                            ${a.source_type === 'public_gov' ? '<span class="eco-badge eco-badge-gov" style="margin-right:4px;">🏛️ 공공</span>' : ''}
                            <a href="${a.link}" target="_blank" style="color:#e2e8f0; text-decoration:none;">${a.title}</a>
                            <div style="font-size:0.74rem; color:#94a3b8;">${a.source_name || ''} · ${a.created_at || ''}</div>
                        </div>
                        <span class="news-grade-${a.news_grade || 'C'}">${a.news_grade || 'C'}</span>
                    </div>
                `).join('') || '<div style="color:#64748b; padding:12px 0;">수집된 뉴스가 없습니다.</div>';
            }
        } catch (err) {
            console.error('Overview load error:', err);
        }
    };

    window.syncFeaturedCompaniesFromOverview = async () => {
        await triggerFeaturedCompaniesSync();
        loadOverviewSummary();
    };

    // 통합 검색 실행
    const globalSearchInput = document.getElementById('global-search-input');
    const btnGlobalSearch = document.getElementById('btn-global-search');
    const searchResultPanel = document.getElementById('integrated-search-results');

    const executeIntegratedSearch = async () => {
        const q = (globalSearchInput ? globalSearchInput.value : '').trim();
        if (!q) return;
        switchTab('overview');
        if (searchResultPanel) {
            searchResultPanel.style.display = 'block';
            searchResultPanel.innerHTML = `<div style="padding:12px; color:#38bdf8;">🔎 '<strong>${q}</strong>'에 대한 기업·DART·펀드·뉴스·지원사업·특허 통합 검색 중...</div>`;
        }
        try {
            const res = await fetch(`/api/integrated_search?q=${encodeURIComponent(q)}`);
            const json = await res.json();
            if (json.status !== 'success') return;

            const dartBtns = (json.dart_candidates || []).map(d => `
                <button type="button" class="eco-btn-sm" style="margin:3px;" onclick="window.fetchDartCompanyByCode('${d.corp_code}', '${d.corp_name.replace(/'/g, '')}')">
                    📥 ${d.corp_name} ${d.stock_code ? '(' + d.stock_code + ')' : '(비상장/외감)'} 재무조회
                </button>
            `).join('');

            searchResultPanel.innerHTML = `
                <div class="eco-card-header">
                    <h3>🔎 '${json.query}' 통합 검색 결과</h3>
                    <button type="button" class="eco-btn-sm" onclick="document.getElementById('integrated-search-results').style.display='none'">닫기 &times;</button>
                </div>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:12px;">
                    <div style="background:rgba(15,23,42,0.55); padding:10px; border-radius:8px;">
                        <h4 style="font-size:0.88rem; color:#38bdf8; margin-bottom:6px;">🏢 기업 DB (${json.companies.length}) & DART 법인 후보 (${(json.dart_candidates || []).length})</h4>
                        ${json.companies.map(c => `<div style="font-size:0.82rem; padding:4px 0;">• <strong>${c.corp_name}</strong> (${c.corp_cls || ''}) | 매출 ${fmtNum(c.revenue_krw)}억 | 등급 ${c.credit_grade || '-'}</div>`).join('')}
                        ${dartBtns ? `<div style="margin-top:6px; border-top:1px dashed rgba(255,255,255,0.1); padding-top:6px;"><div style="font-size:0.74rem; color:#94a3b8; margin-bottom:4px;">클릭 시 실시간 DART 재무제표 DB 적재:</div>${dartBtns}</div>` : ''}
                    </div>
                    <div style="background:rgba(15,23,42,0.55); padding:10px; border-radius:8px;">
                        <h4 style="font-size:0.88rem; color:#34d399; margin-bottom:6px;">💰 관련 벤처펀드 (${json.funds.length})</h4>
                        ${json.funds.map(f => `<div style="font-size:0.82rem; padding:4px 0;">• <strong>${f.fund_name}</strong> (${f.gp_name}) · ${fmtNum(f.commitment_krw)}억</div>`).join('') || '<div style="font-size:0.8rem; color:#64748b;">일치하는 펀드 없음</div>'}
                    </div>
                    <div style="background:rgba(15,23,42,0.55); padding:10px; border-radius:8px;">
                        <h4 style="font-size:0.88rem; color:#fcd34d; margin-bottom:6px;">📰 뉴스·공공브리핑 (${json.articles.length}) & 🎯 지원사업 (${json.grants.length})</h4>
                        ${json.articles.slice(0, 4).map(a => `<div style="font-size:0.8rem; padding:3px 0;"><a href="${a.link}" target="_blank" style="color:#e2e8f0; text-decoration:none;">• [${a.source_type === 'public_gov' ? '공공' : '뉴스'}] ${a.title}</a></div>`).join('')}
                        ${json.grants.slice(0, 3).map(g => `<div style="font-size:0.8rem; padding:3px 0;"><a href="${g.detail_url}" target="_blank" style="color:#93c5fd; text-decoration:none;">• [지원사업 ${g.d_day}] ${g.title}</a></div>`).join('')}
                    </div>
                </div>
            `;
        } catch (e) {
            searchResultPanel.innerHTML = `<div style="color:#f43f5e;">검색 중 오류: ${e.message}</div>`;
        }
    };

    if (btnGlobalSearch) btnGlobalSearch.addEventListener('click', executeIntegratedSearch);
    if (globalSearchInput) {
        globalSearchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                executeIntegratedSearch();
            }
        });
    }

    // 공공브리핑 즉시 수집 버튼 (뉴스 탭)
    const btnSyncPublicNews = document.getElementById('btn-sync-public-news');
    if (btnSyncPublicNews) {
        btnSyncPublicNews.addEventListener('click', async () => {
            const orig = btnSyncPublicNews.textContent;
            btnSyncPublicNews.disabled = true;
            btnSyncPublicNews.textContent = '🏛️ 수집 중...';
            try {
                const res = await fetch('/api/sync_public_news', { method: 'POST' });
                const json = await res.json();
                if (json.status === 'success') {
                    alert(`정부부처(중기부·과기부·금융위·산업부·특허청) 공식 브리핑 ${json.added}건이 신규 추가되었습니다.`);
                    if (window.refreshNewsPipeline) window.refreshNewsPipeline();
                } else {
                    alert('수집 오류: ' + json.message);
                }
            } finally {
                btnSyncPublicNews.disabled = false;
                btnSyncPublicNews.textContent = orig;
            }
        });
    }

    // =========================================================================
    // 2. 기업 · 재무 인텔리전스 DB (DART + 금융위 + NICE 업로드)
    // =========================================================================
    let cachedCompanies = [];

    const loadCompanies = async () => {
        const q = (document.getElementById('comp-search-input')?.value || '').trim();
        const cls = (document.getElementById('comp-cls-filter')?.value || '').trim();
        const tbody = document.getElementById('companies-tbody');
        if (!tbody) return;

        try {
            const res = await fetch(`/api/companies?q=${encodeURIComponent(q)}&corp_cls=${encodeURIComponent(cls)}`);
            const json = await res.json();
            if (json.status !== 'success') return;
            cachedCompanies = json.data || [];

            const cntEl = document.getElementById('comp-total-count');
            if (cntEl) cntEl.textContent = `저장된 기업 프로필: ${cachedCompanies.length}개사`;

            if (cachedCompanies.length === 0) {
                tbody.innerHTML = `<tr><td colspan="10" class="empty-state">등록된 기업이 없습니다. 상단 <strong>[⚡ 대표 벤처·유니콘 DART 동기화]</strong> 또는 <strong>[DART 실시간 법인 조회]</strong>를 실행해 보세요!</td></tr>`;
                return;
            }

            tbody.innerHTML = cachedCompanies.map((c, idx) => `
                <tr>
                    <td>
                        <div style="font-weight:700; color:#f8fafc;">${c.corp_name}</div>
                        <div style="font-size:0.74rem; color:#94a3b8;">${c.corp_cls || '-'} ${c.stock_code ? '(' + c.stock_code + ')' : ''}</div>
                    </td>
                    <td>
                        <div>${c.ceo_name || '-'}</div>
                        <div style="font-size:0.74rem; color:#64748b;">설립 ${c.est_dt || '-'}</div>
                    </td>
                    <td style="font-size:0.8rem; color:#cbd5e1;">${c.biz_reg_no || '-'}</td>
                    <td><span class="eco-badge eco-badge-dday-normal">${c.credit_grade || '-'}</span></td>
                    <td style="text-align:right; font-weight:600; color:#e2e8f0;">${fmtNum(c.revenue_krw)}억 <span style="font-size:0.7rem; color:#64748b;">(${c.latest_bsns_year || '-'})</span></td>
                    <td style="text-align:right; font-weight:600; color:${(c.op_profit_krw || 0) >= 0 ? '#34d399' : '#f43f5e'};">${fmtNum(c.op_profit_krw)}억</td>
                    <td style="text-align:right; color:#cbd5e1;">${fmtNum(c.total_equity_krw)}억</td>
                    <td style="text-align:center;">${c.employee_count ? fmtNum(c.employee_count, 0) + '명' : '-'}</td>
                    <td style="font-size:0.76rem; color:#94a3b8;">${c.data_source || 'DART'}</td>
                    <td>
                        <div style="display:flex; gap:5px; flex-wrap:wrap;">
                            <button type="button" class="eco-btn-sm" style="padding:4px 8px; font-size:0.75rem;" onclick="window.showCompanyDetail(${idx})">재무/증자</button>
                            <button type="button" class="eco-btn-sm eco-btn-accent" style="padding:4px 8px; font-size:0.75rem;" onclick="window.launchCompanyIc(${idx})">IC심사</button>
                        </div>
                    </td>
                </tr>
            `).join('');
        } catch (err) {
            console.error(err);
        }
    };

    window.showCompanyDetail = (idx) => {
        const c = cachedCompanies[idx];
        const drawer = document.getElementById('comp-detail-drawer');
        if (!c || !drawer) return;
        const finRows = (c.financial_history || []).map(f => `
            <tr>
                <td>${f.year}년 (${f.fs_div || '개별'})</td>
                <td>${fmtNum(f.revenue_krw)}억</td>
                <td style="color:${(f.op_profit_krw || 0) >= 0 ? '#34d399' : '#f43f5e'};">${fmtNum(f.op_profit_krw)}억</td>
                <td>${fmtNum(f.net_income_krw)}억</td>
                <td>${fmtNum(f.total_assets_krw)}억</td>
                <td>${fmtNum(f.total_liab_krw)}억</td>
                <td>${fmtNum(f.total_equity_krw)}억</td>
            </tr>
        `).join('') || '<tr><td colspan="7" style="text-align:center; color:#64748b;">연도별 감사보고서 재무내역 없음</td></tr>';

        drawer.style.display = 'block';
        drawer.innerHTML = `
            <div class="eco-card-header">
                <h3>🏢 ${c.corp_name} — 3개년 요약재무 및 유상증자(RCPS/보통주) 공시 상세</h3>
                <button type="button" class="eco-btn-sm" onclick="document.getElementById('comp-detail-drawer').style.display='none'">닫기 &times;</button>
            </div>
            <div style="font-size:0.83rem; color:#cbd5e1; margin-bottom:10px;">
                📍 주소: ${c.address || '-'} | 🌐 홈페이지: ${c.homepage_url ? `<a href="${c.homepage_url}" target="_blank" style="color:#38bdf8;">${c.homepage_url}</a>` : '-'} | 👥 임직원: ${c.employee_count || '-'}명 ${c.avg_salary_est_krw ? `(평균급여 약 ${fmtNum(c.avg_salary_est_krw, 0)}만원)` : ''}
            </div>
            <div class="table-container" style="margin-bottom:10px;">
                <table>
                    <thead><tr><th>결산연도</th><th>매출액</th><th>영업이익</th><th>당기순이익</th><th>자산총계</th><th>부채총계</th><th>자본총계</th></tr></thead>
                    <tbody>${finRows}</tbody>
                </table>
            </div>
            <div style="background:rgba(15,23,42,0.7); padding:10px 12px; border-radius:8px; font-size:0.82rem; color:#bae6fd; white-space:pre-line;">
                <strong>📌 자본변동 · 유상증자(RCPS/CPS/보통주) 내역:</strong>\n${c.capital_increase_summary || '최근 사업보고서 내 특이 유상증자 내역 없음 (또는 비외감/미공시)'}
            </div>
        `;
        drawer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    };

    window.launchCompanyIc = (idx) => {
        const c = cachedCompanies[idx];
        if (!c) return;
        const ctx = `[기업 DB 연동 요약] 대표자: ${c.ceo_name || '-'}, 설립일: ${c.est_dt || '-'}, 최근(${c.latest_bsns_year || '-'}년) 매출액 ${fmtNum(c.revenue_krw)}억원, 영업이익 ${fmtNum(c.op_profit_krw)}억원, 자본총계 ${fmtNum(c.total_equity_krw)}억원, 등급: ${c.credit_grade || '-'}${c.homepage_url ? '\n공식 홈페이지: ' + c.homepage_url : ''}`;
        if (window.openCompanyIcMemo) window.openCompanyIcMemo(c.corp_name, ctx);
    };

    window.fetchDartCompanyByCode = async (corpCode, corpName = '') => {
        const statusEl = document.getElementById('dart-candidates-box');
        if (statusEl) statusEl.innerHTML = `<span style="color:#38bdf8;">⏳ DART 전자공시에서 <strong>${corpName || corpCode}</strong>의 기업개황·3개년 재무제표·증자이력을 가져오는 중...</span>`;
        try {
            const res = await fetch('/api/companies/fetch_dart', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ corp_code: corpCode, company_name: corpName })
            });
            const json = await res.json();
            if (json.status === 'success') {
                switchTab('companies');
                await loadCompanies();
                if (statusEl) statusEl.innerHTML = `<span style="color:#34d399;">✅ <strong>${json.data.corp_name}</strong> DART 실데이터 연동 완료!</span>`;
            } else {
                alert(json.message || '조회 실패');
                if (statusEl) statusEl.innerHTML = '';
            }
        } catch (err) {
            alert('DART 조회 오류: ' + err.message);
        }
    };

    const btnCompFilter = document.getElementById('btn-comp-filter');
    if (btnCompFilter) btnCompFilter.addEventListener('click', loadCompanies);

    const btnDartLookup = document.getElementById('btn-dart-live-lookup');
    if (btnDartLookup) {
        btnDartLookup.addEventListener('click', async () => {
            const q = (document.getElementById('comp-search-input')?.value || '').trim();
            if (!q) {
                alert('검색창에 조회할 기업명(예: 리벨리온, 세미파이브, 비바리퍼블리카, 컬리, 루닛)을 입력해주세요.');
                return;
            }
            const box = document.getElementById('dart-candidates-box');
            if (box) {
                box.style.display = 'block';
                box.innerHTML = `<span style="color:#38bdf8;">🔎 DART 10만 법인 인덱스에서 '${q}' 검색 중 (최초 1회 인덱스 다운로드 시 약 3~5초 소요)...</span>`;
            }
            const res = await fetch(`/api/companies/dart_search?q=${encodeURIComponent(q)}`);
            const json = await res.json();
            if (json.status === 'success' && json.data && json.data.length > 0) {
                box.innerHTML = `<div style="font-size:0.8rem; color:#cbd5e1; margin-bottom:6px;">원하시는 법인을 클릭하면 실시간 DART 개황·3개년 재무·유상증자 내역을 가져옵니다:</div>` +
                    json.data.map(d => `<button type="button" class="eco-btn-sm" style="margin:3px;" onclick="window.fetchDartCompanyByCode('${d.corp_code}', '${d.corp_name.replace(/'/g, '')}')">📥 ${d.corp_name} ${d.stock_code ? '[상장:' + d.stock_code + ']' : '[비상장/외감]'} (${d.corp_code})</button>`).join('');
            } else {
                box.innerHTML = `<span style="color:#fcd34d;">⚠️ DART 외감/공시 대상 법인에서 '${q}'을(를) 찾지 못했습니다. 비외감 초기 스타트업은 우측 [📤 NICE/재무 파일 업로드]를 이용해 주세요.</span>`;
            }
        });
    }

    const triggerFeaturedCompaniesSync = async () => {
        const btn = document.getElementById('btn-sync-featured-comp');
        const orig = btn ? btn.textContent : '';
        if (btn) {
            btn.disabled = true;
            btn.textContent = '⏳ DART 실데이터 동기화 중...';
        }
        try {
            const res = await fetch('/api/companies/sync_featured', { method: 'POST' });
            const json = await res.json();
            if (json.status === 'success') {
                await loadCompanies();
                alert(`대표 유니콘·벤처기업 ${json.synced_count}개사(${(json.companies || []).join(', ')})의 DART 재무·개황 데이터를 성공적으로 연동했습니다.`);
            } else {
                alert('동기화 실패: ' + json.message);
            }
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = orig;
            }
        }
    };

    const btnSyncFeatured = document.getElementById('btn-sync-featured-comp');
    if (btnSyncFeatured) btnSyncFeatured.addEventListener('click', triggerFeaturedCompaniesSync);

    const niceFileInput = document.getElementById('nice-upload-input');
    const btnNiceUpload = document.getElementById('btn-nice-upload');
    if (btnNiceUpload && niceFileInput) {
        btnNiceUpload.addEventListener('click', () => niceFileInput.click());
        niceFileInput.addEventListener('change', async (e) => {
            const f = e.target.files[0];
            if (!f) return;
            const fallbackName = (document.getElementById('comp-search-input')?.value || '').trim();
            const fd = new FormData();
            fd.append('company_name', fallbackName);
            fd.append('file', f);
            const res = await fetch('/api/companies/upload_report', { method: 'POST', body: fd });
            const json = await res.json();
            if (json.status === 'success') {
                alert(`${json.count}건의 기업/신용 리포트 데이터가 기업 DB에 반영되었습니다.`);
                loadCompanies();
            } else {
                alert(json.message || '업로드 실패');
            }
            niceFileInput.value = '';
        });
    }

    // =========================================================================
    // 3. 벤처펀드 설정 · GP 현황 (DIVA 전자공시)
    // =========================================================================
    let currentFundPage = 1;

    const loadFunds = async (page = 1) => {
        currentFundPage = page;
        const q = (document.getElementById('fund-search-q')?.value || '').trim();
        const gp = (document.getElementById('fund-search-gp')?.value || '').trim();
        const motaeOnly = document.getElementById('fund-motae-only')?.checked || false;
        const tbody = document.getElementById('funds-tbody');
        if (!tbody) return;

        const res = await fetch(`/api/funds?q=${encodeURIComponent(q)}&gp=${encodeURIComponent(gp)}&motae_only=${motaeOnly}&page=${page}`);
        const json = await res.json();
        if (json.status !== 'success') return;

        const metaEl = document.getElementById('funds-summary-meta');
        if (metaEl) {
            metaEl.innerHTML = `총 조회 조합: <strong style="color:#38bdf8;">${fmtNum(json.count, 0)}개</strong> | 표시 그룹 약정총액 합계: <strong style="color:#34d399;">${fmtNum(json.sum_commitment_krw)}억원</strong> (약 ${fmtNum((json.sum_commitment_krw || 0) / 10000, 2)}조원)`;
        }

        tbody.innerHTML = (json.data || []).map(f => `
            <tr>
                <td>${f.reg_date || '-'}</td>
                <td>
                    <span style="font-weight:700; color:#f8fafc;">${f.fund_name}</span>
                    ${f.motae_backed ? '<span class="eco-badge eco-badge-motae" style="margin-left:6px;">모태출자/정책</span>' : ''}
                </td>
                <td style="color:#93c5fd; font-weight:600;">${f.gp_name}</td>
                <td style="text-align:right; color:#34d399; font-weight:700;">${f.commitment_krw ? fmtNum(f.commitment_krw) + '억' : '-'}</td>
                <td>${f.maturity_date || '-'}</td>
                <td>${f.invest_field || '-'}</td>
                <td>${f.support_type && f.support_type !== '해당없음' ? f.support_type : (f.purpose_type || '-')}</td>
                <td style="font-size:0.75rem; color:#94a3b8;"><a href="${f.source_url || 'http://diva.kvca.or.kr'}" target="_blank" style="color:#94a3b8;">${f.source_name}</a></td>
            </tr>
        `).join('') || '<tr><td colspan="8" class="empty-state">조건에 해당하는 조합이 없습니다.</td></tr>';

        const pagEl = document.getElementById('funds-pagination');
        if (pagEl) {
            let html = '';
            for (let p = 1; p <= Math.min(json.total_pages || 1, 8); p++) {
                html += `<button type="button" class="eco-btn-sm ${p === page ? 'eco-btn-accent' : ''}" onclick="window.goFundPage(${p})">${p}</button>`;
            }
            pagEl.innerHTML = html;
        }
    };

    window.goFundPage = (p) => loadFunds(p);

    document.getElementById('btn-fund-search')?.addEventListener('click', () => loadFunds(1));
    document.getElementById('fund-motae-only')?.addEventListener('change', () => loadFunds(1));

    const btnFundSync = document.getElementById('btn-fund-diva-sync');
    if (btnFundSync) {
        btnFundSync.addEventListener('click', async () => {
            const gp = (document.getElementById('fund-search-gp')?.value || '').trim();
            const q = (document.getElementById('fund-search-q')?.value || '').trim();
            const orig = btnFundSync.textContent;
            btnFundSync.disabled = true;
            btnFundSync.textContent = '⏳ DIVA 수집 중...';
            try {
                const res = await fetch('/api/funds/sync', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pages: 3, gp_keyword: gp, fund_keyword: q })
                });
                const json = await res.json();
                if (json.status === 'success') {
                    await loadFunds(1);
                    alert(`DIVA 전자공시 동기화 완료! (신규 ${json.added}건 추가, 기존 ${json.updated}건 갱신)`);
                }
            } finally {
                btnFundSync.disabled = false;
                btnFundSync.textContent = orig;
            }
        });
    }

    // =========================================================================
    // 4. 중기부 벤처산업 펀딩규모 · 제도 · 동적 설정 레지스트리 허브
    // =========================================================================
    let policyScaleSeries = [];

    const renderBreakdownBars = (item) => {
        const titleEl = document.getElementById('policy-selected-period-title');
        const secEl = document.getElementById('policy-sector-bars');
        const stgEl = document.getElementById('policy-stage-bars');
        if (!item) return;
        if (titleEl) titleEl.textContent = `📊 ${item.period_label} 업종별 · 업력별 투자 비중 상세`;

        if (secEl) {
            secEl.innerHTML = Object.entries(item.sector_share || {}).map(([k, pct]) => `
                <div style="margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:3px;">
                        <span>${k}</span><strong style="color:#38bdf8;">${pct}%</strong>
                    </div>
                    <div style="height:7px; background:rgba(255,255,255,0.08); border-radius:4px; overflow:hidden;">
                        <div style="width:${Math.min(pct * 2, 100)}%; height:100%; background:linear-gradient(90deg, #3b82f6, #38bdf8);"></div>
                    </div>
                </div>
            `).join('');
        }
        if (stgEl) {
            stgEl.innerHTML = Object.entries(item.stage_share || {}).map(([k, pct]) => `
                <div style="margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:3px;">
                        <span>${k}</span><strong style="color:#34d399;">${pct}%</strong>
                    </div>
                    <div style="height:7px; background:rgba(255,255,255,0.08); border-radius:4px; overflow:hidden;">
                        <div style="width:${Math.min(pct * 1.8, 100)}%; height:100%; background:linear-gradient(90deg, #10b981, #34d399);"></div>
                    </div>
                </div>
            `).join('') + `<div style="margin-top:10px; font-size:0.8rem; color:#cbd5e1; line-height:1.5;">💡 ${item.summary || ''}</div>`;
        }
    };

    const loadVenturePolicy = async () => {
        const res = await fetch('/api/venture_policy');
        const json = await res.json();
        if (json.status !== 'success') return;

        policyScaleSeries = json.scale_series || [];
        const chartEl = document.getElementById('policy-scale-chart');
        if (chartEl && policyScaleSeries.length > 0) {
            const maxVal = Math.max(...policyScaleSeries.map(s => Math.max(s.new_investment_krw || 0, s.new_fund_formation_krw || 0)), 180000);
            chartEl.innerHTML = policyScaleSeries.map((s, idx) => {
                const invH = Math.max(12, Math.round(((s.new_investment_krw || 0) / maxVal) * 130));
                const fndH = Math.max(12, Math.round(((s.new_fund_formation_krw || 0) / maxVal) * 130));
                const invTril = ((s.new_investment_krw || 0) / 10000).toFixed(2);
                const fndTril = ((s.new_fund_formation_krw || 0) / 10000).toFixed(2);
                return `
                    <div class="policy-bar-group ${idx === policyScaleSeries.length - 1 ? 'selected' : ''}" onclick="window.selectPolicyYear(${idx})">
                        <div style="font-size:0.72rem; color:#93c5fd;">투자 ${invTril}조</div>
                        <div style="font-size:0.72rem; color:#6ee7b7;">결성 ${fndTril}조</div>
                        <div class="policy-bars-pair">
                            <div class="policy-bar policy-bar-inv" style="height:${invH}px;" title="신규 벤처투자 ${invTril}조원"></div>
                            <div class="policy-bar policy-bar-fund" style="height:${fndH}px;" title="신규 펀드결성 ${fndTril}조원"></div>
                        </div>
                        <div style="font-size:0.8rem; font-weight:700; color:#f8fafc;">${s.period_label.replace(' 연간', '')}</div>
                        <div style="font-size:0.72rem; color:${(s.yoy_growth_pct || 0) >= 0 ? '#34d399' : '#f43f5e'};">${(s.yoy_growth_pct || 0) >= 0 ? '+' : ''}${s.yoy_growth_pct || 0}%</div>
                    </div>
                `;
            }).join('');
            renderBreakdownBars(policyScaleSeries[policyScaleSeries.length - 1]);
        }

        // 모태펀드 방향
        const motaeBox = document.getElementById('policy-motae-box');
        if (motaeBox) {
            motaeBox.innerHTML = (json.motae_directions || []).map(m => `
                <div style="background:rgba(16,185,129,0.08); border-left:3px solid #10b981; padding:12px; border-radius:6px; margin-bottom:10px;">
                    <div style="font-weight:700; color:#6ee7b7; margin-bottom:6px;">${m.title} (모태출자 약 ${((m.motae_budget_krw || 0) / 10000).toFixed(2)}조원 기준)</div>
                    <div style="font-size:0.84rem; color:#e2e8f0; line-height:1.6;">${m.summary}</div>
                </div>
            `).join('');
        }

        // 실시간 정책 브리핑
        const liveBox = document.getElementById('policy-live-trends');
        if (liveBox) {
            liveBox.innerHTML = (json.live_trends || []).map(t => `
                <div class="eco-list-item">
                    <div>
                        <span class="eco-badge eco-badge-gov" style="margin-right:6px;">${t.ministry}</span>
                        <a href="${t.source_url}" target="_blank" style="color:#f1f5f9; text-decoration:none;">${t.title}</a>
                    </div>
                    <span style="font-size:0.75rem; color:#94a3b8; flex-shrink:0;">${t.published_date || ''}</span>
                </div>
            `).join('') || '<div style="font-size:0.82rem; color:#94a3b8; padding:8px 0;">우측 상단 [🔄 중기부·KVIC 최신 정책브리핑 수집]을 클릭하면 최신 정책 뉴스를 실시간 연동합니다.</div>';
        }

        // 동적 설정 레지스트리 (법령·세무·의무비율 파라미터)
        const regTbody = document.getElementById('config-registry-tbody');
        if (regTbody) {
            regTbody.innerHTML = (json.legal_tax_registry || []).map(r => `
                <tr>
                    <td><span class="eco-badge ${r.config_group === 'venture_tax_incentives' ? 'eco-badge-gov' : 'eco-badge-motae'}">${r.config_group === 'venture_tax_incentives' ? '세제 인센티브' : '조합/운용 법규'}</span></td>
                    <td>
                        <div style="font-weight:600; color:#f8fafc;">${r.config_label}</div>
                        <div style="font-size:0.74rem; color:#94a3b8;">${r.description || ''}</div>
                    </td>
                    <td style="font-weight:800; color:#38bdf8; font-size:0.95rem;">${r.config_value}${r.unit || ''}</td>
                    <td style="font-size:0.8rem; color:#cbd5e1;">${r.legal_basis || '-'}</td>
                    <td style="font-size:0.78rem; color:#94a3b8;">${r.effective_date || '-'}</td>
                    <td>
                        <button type="button" class="eco-btn-sm" style="padding:4px 8px; font-size:0.74rem;" onclick="window.editRegistryValue('${r.config_key}', '${r.config_label.replace(/'/g, '')}', '${r.config_value}', '${r.unit || ''}')">수정</button>
                    </td>
                </tr>
            `).join('');
        }
    };

    window.selectPolicyYear = (idx) => {
        document.querySelectorAll('.policy-bar-group').forEach((el, i) => el.classList.toggle('selected', i === idx));
        renderBreakdownBars(policyScaleSeries[idx]);
    };

    window.editRegistryValue = async (key, label, curVal, unit) => {
        const nextVal = prompt(`[동적 설정 레지스트리 수정]\n항목: ${label}\n새로운 기준값(${unit})을 입력하세요:`, curVal);
        if (nextVal === null || nextVal.trim() === '') return;
        const res = await fetch(`/api/config_registry/${encodeURIComponent(key)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config_value: nextVal.trim() })
        });
        const json = await res.json();
        if (json.status === 'success') {
            loadVenturePolicy();
        } else {
            alert(json.message);
        }
    };

    document.getElementById('btn-policy-sync')?.addEventListener('click', async (e) => {
        const btn = e.currentTarget;
        const orig = btn.textContent;
        btn.disabled = true;
        btn.textContent = '⏳ 수집 중...';
        try {
            await fetch('/api/venture_policy/sync', { method: 'POST' });
            await loadVenturePolicy();
        } finally {
            btn.disabled = false;
            btn.textContent = orig;
        }
    });

    // =========================================================================
    // 5. 정부 지원사업(기업마당/K-Startup) & 기업 특허/IP(KIPRIS/Google Patents)
    // =========================================================================
    const loadGrants = async (page = 1) => {
        const q = (document.getElementById('grant-search-q')?.value || '').trim();
        const cat = (document.getElementById('grant-cat-filter')?.value || '').trim();
        const activeOnly = document.getElementById('grant-active-only')?.checked ?? true;
        const tbody = document.getElementById('grants-tbody');
        if (!tbody) return;

        const res = await fetch(`/api/grants?q=${encodeURIComponent(q)}&category=${encodeURIComponent(cat)}&active_only=${activeOnly}&page=${page}`);
        const json = await res.json();
        if (json.status !== 'success') return;

        const cntEl = document.getElementById('grant-total-meta');
        if (cntEl) cntEl.textContent = `조회된 공고: ${fmtNum(json.count, 0)}건`;

        tbody.innerHTML = (json.data || []).map(g => {
            const urgent = g.d_day && (g.d_day === 'D-Day' || (g.d_day.startsWith('D-') && parseInt(g.d_day.slice(2), 10) <= 7));
            return `
                <tr>
                    <td><span class="eco-badge ${urgent ? 'eco-badge-dday-urgent' : 'eco-badge-dday-normal'}">${g.d_day}</span></td>
                    <td>${g.category || '-'}</td>
                    <td><a href="${g.detail_url}" target="_blank" style="color:#60a5fa; text-decoration:none; font-weight:500;">${g.title}</a></td>
                    <td>${g.ministry || '-'}</td>
                    <td>${g.executor || '-'}</td>
                    <td style="font-size:0.8rem;">${g.apply_period || '-'}</td>
                    <td style="font-size:0.75rem; color:#94a3b8;">${g.source_name}</td>
                </tr>
            `;
        }).join('') || '<tr><td colspan="7" class="empty-state">지원사업 공고가 없습니다.</td></tr>';
    };

    document.getElementById('btn-grant-search')?.addEventListener('click', () => loadGrants(1));
    document.getElementById('grant-cat-filter')?.addEventListener('change', () => loadGrants(1));
    document.getElementById('grant-active-only')?.addEventListener('change', () => loadGrants(1));

    document.getElementById('btn-grant-sync')?.addEventListener('click', async (e) => {
        const btn = e.currentTarget;
        const orig = btn.textContent;
        btn.disabled = true;
        btn.textContent = '⏳ 최신 공고 수집 중...';
        try {
            const res = await fetch('/api/grants/sync?pages=3', { method: 'POST' });
            const json = await res.json();
            await loadGrants(1);
            if (json.status === 'success') alert(`정부 지원사업 신규 ${json.added}건 반영 완료!`);
        } finally {
            btn.disabled = false;
            btn.textContent = orig;
        }
    });

    const renderPatentRows = (rows) => {
        const tbody = document.getElementById('patents-tbody');
        if (!tbody) return;
        tbody.innerHTML = (rows || []).map(p => `
            <tr>
                <td style="font-weight:600; color:#f8fafc;">${p.applicant_name || '-'}</td>
                <td style="font-family:monospace; font-size:0.8rem; color:#93c5fd;">${p.application_number || '-'}</td>
                <td style="font-weight:500; color:#e2e8f0;">${p.invention_title || '-'}</td>
                <td>${p.application_date || '-'}</td>
                <td><span class="eco-badge ${p.registration_status === '등록' ? 'eco-badge-motae' : 'eco-badge-dday-normal'}">${p.registration_status || '공개'}</span></td>
                <td style="font-size:0.78rem; color:#cbd5e1; max-width:340px;">${(p.abstract_text || '-').slice(0, 140)}${(p.abstract_text || '').length > 140 ? '...' : ''}</td>
                <td style="font-size:0.75rem; color:#94a3b8;">${p.source_name || 'KIPRIS'}</td>
            </tr>
        `).join('') || '<tr><td colspan="7" class="empty-state">기업명(예: 리벨리온, 루닛, 레인보우로보틱스)을 입력하고 [특허/IP 실시간 검색]을 실행해 보세요.</td></tr>';
    };

    const loadSavedPatents = async () => {
        const res = await fetch('/api/patents');
        const json = await res.json();
        if (json.status === 'success') renderPatentRows(json.data);
    };

    document.getElementById('btn-patent-search')?.addEventListener('click', async (e) => {
        const cname = (document.getElementById('patent-company-input')?.value || '').trim();
        if (!cname) {
            alert('특허를 조회할 출원인/기업명을 입력해주세요.');
            return;
        }
        const btn = e.currentTarget;
        const orig = btn.textContent;
        btn.disabled = true;
        btn.textContent = '🔎 특허 검색 중...';
        try {
            const res = await fetch('/api/patents/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ company_name: cname, max_rows: 15 })
            });
            const json = await res.json();
            if (json.status === 'success') {
                renderPatentRows(json.data);
                const meta = document.getElementById('patent-source-meta');
                if (meta) meta.textContent = `연동 소스: ${json.source} (신규 ${json.added}건 DB 적재)`;
            }
        } finally {
            btn.disabled = false;
            btn.textContent = orig;
        }
    });

    // =========================================================================
    // 6. 다중 데이터소스 API 키 상태 조회 & 일괄 저장 모달 확장
    // =========================================================================
    const loadApiKeysModalStatus = async () => {
        try {
            const res = await fetch('/api/api_keys_status');
            const json = await res.json();
            if (json.status !== 'success') return;
            const k = json.keys || {};
            const setStatus = (elId, info) => {
                const el = document.getElementById(elId);
                if (!el || !info) return;
                el.textContent = info.configured ? `✅ 설정됨 (${info.masked})` : '⚪ 미설정';
                el.style.color = info.configured ? '#34d399' : '#94a3b8';
            };
            setStatus('st-gemini-key', k.GEMINI_API_KEY);
            setStatus('st-dart-key', k.DART_API_KEY);
            setStatus('st-datagokr-key', k.DATA_GO_KR_SERVICE_KEY);
            setStatus('st-kipris-key', k.KIPRIS_API_KEY);
            setStatus('st-nice-key', k.NICE_API_KEY);
        } catch (e) {}
    };

    document.getElementById('btn-open-apikey')?.addEventListener('click', loadApiKeysModalStatus);
    document.getElementById('btn-save-multi-apikeys')?.addEventListener('click', async () => {
        const payload = {
            gemini_api_key: document.getElementById('input-api-key')?.value || '',
            dart_api_key: document.getElementById('input-dart-key')?.value || '',
            data_go_kr_service_key: document.getElementById('input-datagokr-key')?.value || '',
            kipris_api_key: document.getElementById('input-kipris-key')?.value || '',
            nice_api_key: document.getElementById('input-nice-key')?.value || ''
        };
        const res = await fetch('/api/update_api_key', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const json = await res.json();
        alert(json.message || '저장 완료');
        await loadApiKeysModalStatus();
    });

    // 초기 진입 시 통합 오버뷰 백그라운드 프리로드
    loadOverviewSummary();
});

