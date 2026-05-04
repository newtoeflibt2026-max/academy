async function loadSettings() {
    const data = await api('/settings');
    if (!data) return;
    document.getElementById('toggle-writing').checked = data.show_writing == '1';
    document.getElementById('toggle-speaking').checked = data.show_speaking == '1';
    document.getElementById('toggle-vault').checked = data.vault_locked == '1';
    document.getElementById('set-usage-cap').value = data.usage_cap || 3;
    document.getElementById('set-wallet').value = data.wallet_number || '0798919150';
    document.getElementById('toggle-strict').checked = data.speaking_strict == '1';
    document.getElementById('toggle-bitrate').checked = data.speaking_bitrate_check == '1';
}

async function toggleSetting(key, checked) {
    await api('/save_setting', { key, value: checked ? '1' : '0' });
    showToast('✅ ' + (checked ? 'تم التفعيل' : 'تم التعطيل'));
}
