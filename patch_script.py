import re

content = open('frontend/script.js', 'r', encoding='utf-8').read()

# 1. Update loadSettingsDomains
old_domains_func = r"const loadSettingsDomains = async \(\) => \{.*?\}\};\n"
new_domains_func = '''const loadSettingsDomains = async () => {
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
                    
                    const badge = d.is_builtin ? `<span style="font-size:0.7rem; background:#6b7280; color:white; padding:2px 4px; border-radius:4px; margin-left:5px;">내장</span>` : '';
                    const deleteBtn = d.is_builtin ? '' : `<button class="btn-delete-domain" data-id="${d.id}" style="background: #ef4444; border: none; color: white; padding: 4px 8px; border-radius: 4px; cursor: pointer; margin-left: 10px;">삭제</button>`;
                    
                    li.innerHTML = `
                        <div style="flex: 1;">
                            <strong>${d.name || d.url}</strong> ${badge} <small style="color:#9ca3af;">(${d.country} / ${d.category})</small>
                            <div style="font-size: 0.8rem; color: #60a5fa; margin-top: 2px;">URL: ${d.url}</div>
                            ${d.rss_url ? `<div style="font-size: 0.8rem; color: #34d399; margin-top: 2px;">RSS: ${d.rss_url}</div>` : ''}
                        </div>
                        ${deleteBtn}
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
    };\n'''
content = re.sub(old_domains_func, new_domains_func, content, flags=re.DOTALL)

# 2. Add btnDeleteIndustry logic
inject_pattern = r"// Load industries dynamically on boot"
delete_industry_logic = '''
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

    // Load industries dynamically on boot'''
content = content.replace(inject_pattern, delete_industry_logic)

open('frontend/script.js', 'w', encoding='utf-8').write(content)
