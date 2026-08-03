import re

content = open('frontend/script.js', 'r', encoding='utf-8').read()

# 1. Replace btnRealtime logic
realtime_pattern = r"btnRealtime\.addEventListener\('click', async \(\) => \{.*?\}\);\n"
new_realtime = '''btnRealtime.addEventListener('click', async () => {
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
                        if (statusJson.status === 'success' && !statusJson.is_crawling) {
                            clearInterval(pollInterval);
                            updateMsg.textContent = '수집 완료! 화면을 새로고침 합니다.';
                            setTimeout(() => location.reload(), 1500);
                        }
                    } catch(e) {}
                }, 5000);
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
    });\n'''
content = re.sub(realtime_pattern, new_realtime, content, flags=re.DOTALL)

# 2. Replace loadSettingsKeywords logic
kw_load_pattern = r"const loadSettingsKeywords = async \(\) => \{.*?\}\};\n"
new_kw_load = '''const loadSettingsKeywords = async () => {
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
                    
                    const badge = kw.is_builtin ? `<span style="font-size:0.7rem; background:#6b7280; color:white; padding:2px 4px; border-radius:4px; margin-left:5px;">내장</span>` : '';
                    const deleteBtn = kw.is_builtin ? '' : `<button class="btn-delete-kw" data-id="${kw.id}" style="background: #ef4444; border: none; color: white; padding: 4px 8px; border-radius: 4px; cursor: pointer;">삭제</button>`;
                    
                    li.innerHTML = `
                        <span><strong>${kw.keyword}</strong> ${badge} <small style="color:#9ca3af;">(${kw.category})</small></span>
                        ${deleteBtn}
                    `;
                    kwList.appendChild(li);
                });
                
                document.querySelectorAll('.btn-delete-kw').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        const id = e.target.getAttribute('data-id');
                        await fetch(`/api/keywords/${id}`, { method: 'DELETE' });
                        loadSettingsKeywords();
                        loadKeywords();
                    });
                });
            }
        } catch(e) { console.error(e); }
    };\n'''
content = re.sub(kw_load_pattern, new_kw_load, content, flags=re.DOTALL)

# 3. Replace btnAddKw click
add_kw_pattern = r"btnAddKw\.addEventListener\('click', async \(\) => \{.*?loadKeywords\(\);\s*\}\);"
new_add_kw = '''btnAddKw.addEventListener('click', async () => {
            const keyword = document.getElementById('setting-kw-input').value.trim();
            const type = document.getElementById('setting-kw-type').value;
            const category = document.getElementById('setting-kw-category').value;
            if(!keyword) return;
            
            const res = await fetch('/api/keywords', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keyword, type, category })
            });
            const json = await res.json();
            if (json.status === 'error') {
                alert(json.message);
                return;
            }
            document.getElementById('setting-kw-input').value = '';
            loadSettingsKeywords();
            loadKeywords();
        });'''
content = re.sub(add_kw_pattern, new_add_kw, content, flags=re.DOTALL)

# 4. Replace btnAddDomain click
add_dom_pattern = r"btnAddDomain\.addEventListener\('click', async \(\) => \{.*?loadSettingsDomains\(\);\s*\}\);"
new_add_dom = '''btnAddDomain.addEventListener('click', async () => {
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
        });'''
content = re.sub(add_dom_pattern, new_add_dom, content, flags=re.DOTALL)

# 5. Custom keyword enter key alert
custom_kw_pattern = r"const res = await fetch\('/api/keywords', \{\s*method: 'POST'.*?const json = await res\.json\(\);"
new_custom_kw = '''const res = await fetch('/api/keywords', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ keyword: val, type: 'industry', category: 'custom' })
                    });
                    const json = await res.json();
                    if (json.status === 'error') {
                        alert(json.message);
                        return;
                    }'''
content = re.sub(custom_kw_pattern, new_custom_kw, content, flags=re.DOTALL)

open('frontend/script.js', 'w', encoding='utf-8').write(content)
print('Patched successfully')
