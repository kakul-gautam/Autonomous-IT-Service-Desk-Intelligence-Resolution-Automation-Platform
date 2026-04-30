"""Augment tickets_diverse.csv with broader solution diversity across all issue types."""

from __future__ import annotations

import csv
import random
from pathlib import Path


DATASET_PATH = Path(__file__).resolve().parents[1] / 'datasets' / 'tickets_diverse.csv'


ISSUE_PATTERNS = [
    {
        'name': 'battery',
        'category': 'Hardware',
        'keywords': ['battery', 'charge', 'charging', 'power drain', 'draining'],
        'issues': [
            'battery drops from 100% to 20% overnight',
            'laptop says charging but battery percent does not increase',
            'battery backup reduced drastically after recent update',
            'device shuts down at 30 percent battery suddenly',
            'battery drains when laptop is in sleep mode',
            'charging takes too long and discharges quickly',
        ],
        'solutions': [
            'Battery health diagnostics:\n1. Run powercfg /batteryreport\n2. Check designed vs full charge capacity\n3. Disable high-drain startup apps\n4. Recalibrate battery from 100% to 5% once\n5. Replace battery if health is below 65%',
            'Power profile optimization:\n1. Open Control Panel > Power Options\n2. Select Balanced profile\n3. Reduce display brightness and timeout\n4. Disable keyboard backlight when idle\n5. Restart and monitor battery trend for 24 hours',
            'Charging path validation:\n1. Test with original charger only\n2. Check charging port for dust\n3. Update battery + chipset drivers\n4. Disable USB selective suspend for testing\n5. If issue persists, inspect charging IC hardware',
        ],
    },
    {
        'name': 'keyboard',
        'category': 'Hardware',
        'keywords': ['keyboard', 'key', 'typing', 'stuck key'],
        'issues': [
            'keyboard letters repeat automatically while typing',
            'few keys not responding after cleaning keyboard',
            'external keyboard disconnects randomly on usb',
            'stuck ctrl key causing shortcut issues everywhere',
            'keyboard types wrong symbols instead of letters',
            'laptop keyboard stopped after update and reboot',
        ],
        'solutions': [
            'Input driver reset:\n1. Open Device Manager > Keyboards\n2. Uninstall keyboard driver\n3. Restart device for auto reinstall\n4. Install OEM keyboard driver package\n5. Test in Notepad and browser',
            'Layout and sticky key checks:\n1. Confirm language layout is correct\n2. Disable Sticky Keys and Filter Keys\n3. Toggle NumLock/FnLock state\n4. Test On-Screen Keyboard\n5. Update keyboard firmware if available',
            'Physical troubleshooting:\n1. Power off and disconnect charger\n2. Clean keycaps with compressed air\n3. Re-seat ribbon connector if serviceable\n4. Test external USB keyboard\n5. Replace keyboard assembly on hardware failure',
        ],
    },
    {
        'name': 'screen',
        'category': 'Hardware',
        'keywords': ['screen', 'display', 'flicker', 'black screen', 'monitor'],
        'issues': [
            'screen flickers only when charger is connected',
            'laptop display goes black after login but works on external monitor',
            'display has vertical lines after accidental drop',
            'monitor keeps turning off after few minutes',
            'screen brightness stuck at very low value',
            'internal display not detected in windows settings',
        ],
        'solutions': [
            'Display driver recovery:\n1. Boot into Safe Mode\n2. Remove graphics drivers with cleanup utility\n3. Install latest stable GPU driver\n4. Disable adaptive brightness\n5. Reboot and verify refresh rate settings',
            'Panel and cable isolation:\n1. Test external display to confirm GPU health\n2. Run LCD built-in diagnostics\n3. Inspect display cable for loose connection\n4. Check lid sensor behavior\n5. Replace panel/cable if artifacts persist',
            'Power and firmware approach:\n1. Update BIOS/UEFI and chipset package\n2. Reset BIOS to defaults\n3. Disable panel self refresh in graphics panel\n4. Use native resolution only\n5. Escalate for hardware replacement if unchanged',
        ],
    },
    {
        'name': 'wifi',
        'category': 'Network',
        'keywords': ['wifi', 'wireless', 'ssid', 'hotspot'],
        'issues': [
            'wifi connected but no internet for only this laptop',
            'wireless disconnects every 5 minutes during meetings',
            'cannot discover office ssid on one floor',
            'wifi speed drops when bluetooth headset is connected',
            'connection stable on phone but unstable on laptop',
            'saved network profile keeps asking password repeatedly',
        ],
        'solutions': [
            'Wireless stack reset:\n1. Forget the WiFi profile\n2. Run netsh winsock reset\n3. Run netsh int ip reset\n4. Reboot and reconnect\n5. Set adapter power mode to Maximum Performance',
            'Adapter optimization:\n1. Update WLAN driver from OEM site\n2. Disable adapter power saving\n3. Lock preferred band to 5GHz when available\n4. Set channel width to Auto\n5. Test near access point for baseline',
            'Network-side validation:\n1. Reboot AP/controller\n2. Check DHCP lease pool\n3. Verify DNS server reachability\n4. Change AP channel to reduce interference\n5. Validate captive portal / ACL policies',
        ],
    },
    {
        'name': 'vpn',
        'category': 'Network',
        'keywords': ['vpn', 'tunnel', 'secure access', 'remote access'],
        'issues': [
            'vpn connects then disconnects in under one minute',
            'cannot access internal servers after vpn login',
            'vpn fails only on home network but works on mobile hotspot',
            'multi factor prompt appears but login never completes',
            'vpn client update caused certificate mismatch error',
            'split tunnel routes internet incorrectly after connect',
        ],
        'solutions': [
            'VPN profile rebuild:\n1. Remove existing VPN profile\n2. Import fresh config from IT portal\n3. Sync system date/time\n4. Re-authenticate MFA token\n5. Reconnect and validate internal DNS resolution',
            'Certificate and auth fix:\n1. Clear cached credentials\n2. Reinstall VPN root certificates\n3. Regenerate user certificate if expired\n4. Update VPN client version\n5. Retry with alternate gateway',
            'Routing diagnostics:\n1. Run ipconfig and route print\n2. Confirm corporate routes after connect\n3. Disable conflicting local proxy\n4. Flush DNS cache\n5. Escalate logs to network security team',
        ],
    },
    {
        'name': 'ethernet',
        'category': 'Network',
        'keywords': ['ethernet', 'lan', 'wired', 'network cable'],
        'issues': [
            'ethernet shows unplugged even when cable is connected',
            'wired internet works only at 100mbps instead of 1gbps',
            'lan connection drops during file transfer',
            'dock ethernet adapter not detected after reboot',
            'link light on switch is blinking red for this port',
            'static ip settings lost after windows update',
        ],
        'solutions': [
            'Wired adapter baseline:\n1. Test with known-good Cat6 cable\n2. Update NIC driver\n3. Disable/enable adapter\n4. Force speed/duplex to Auto\n5. Reboot and retest throughput',
            'Port and switch checks:\n1. Move cable to different switch port\n2. Validate VLAN assignment\n3. Check port error counters\n4. Replace patch cable\n5. Reapply endpoint network profile',
            'IP configuration recovery:\n1. Save static config details\n2. Re-enter IPv4 settings manually\n3. Flush DNS and renew lease\n4. Disable unused virtual adapters\n5. Verify gateway reachability',
        ],
    },
    {
        'name': 'slow-internet',
        'category': 'Network',
        'keywords': ['slow internet', 'lag', 'high ping', 'buffering'],
        'issues': [
            'video calls lag even with strong wifi signal',
            'downloads are slow only during office hours',
            'high ping spikes every few minutes while gaming',
            'browser pages time out before loading fully',
            'upload speed much slower than expected',
            'cloud sync takes hours for small files',
        ],
        'solutions': [
            'Bandwidth triage:\n1. Run speed test on wired and wireless\n2. Identify heavy processes in Resource Monitor\n3. Pause background sync and updates\n4. Set QoS for video conferencing app\n5. Retest latency and jitter',
            'DNS and path tuning:\n1. Change DNS to trusted resolver\n2. Run traceroute to target service\n3. Compare packet loss on different routes\n4. Reboot modem/router\n5. Raise ISP ticket with evidence',
            'Local contention cleanup:\n1. Disconnect non-essential devices\n2. Disable cloud backup temporarily\n3. Scan for malware network abuse\n4. Update router firmware\n5. Move high-traffic apps to ethernet',
        ],
    },
    {
        'name': 'app-crash',
        'category': 'Software',
        'keywords': ['crash', 'not responding', 'freeze', 'hang'],
        'issues': [
            'application crashes when opening large reports',
            'software freezes after recent plugin installation',
            'program closes immediately after splash screen',
            'app hangs while saving files to network drive',
            'random crash occurs when exporting pdf',
            'software not responding during startup',
        ],
        'solutions': [
            'Crash isolation routine:\n1. Launch app in safe mode\n2. Disable third-party plugins\n3. Clear app cache/profile\n4. Apply latest patch level\n5. Validate with test file',
            'System dependency repair:\n1. Update .NET/VC++ runtime\n2. Reinstall graphics driver\n3. Run sfc /scannow\n4. Run DISM health restore\n5. Reboot and retest',
            'Data-path troubleshooting:\n1. Test with local file instead of network path\n2. Verify permissions on working folder\n3. Disable antivirus real-time scan for app folder\n4. Check event viewer crash signatures\n5. Reinstall application cleanly',
        ],
    },
    {
        'name': 'install-update',
        'category': 'Software',
        'keywords': ['install', 'installation', 'update failed', 'patch'],
        'issues': [
            'installer rolls back at 90 percent every time',
            'software update downloads but fails to apply',
            'setup reports missing prerequisites unexpectedly',
            'application cannot be installed due to permission error',
            'msi package returns generic error code',
            'update process stuck in pending reboot state',
        ],
        'solutions': [
            'Installer pre-checks:\n1. Verify free disk space\n2. Run setup as administrator\n3. Disable conflicting antivirus policy\n4. Install required runtime dependencies\n5. Retry with offline installer',
            'Windows update path:\n1. Stop Windows Update service\n2. Clear SoftwareDistribution cache\n3. Restart update services\n4. Run update troubleshooter\n5. Retry patch cycle',
            'Enterprise package fix:\n1. Pull fresh package from repository\n2. Validate checksum/signature\n3. Install in clean boot state\n4. Capture MSI verbose logs\n5. Escalate log bundle to packaging team',
        ],
    },
    {
        'name': 'performance',
        'category': 'Software',
        'keywords': ['slow', 'lagging', 'high cpu', 'high memory', 'disk 100'],
        'issues': [
            'laptop becomes very slow after login each morning',
            'cpu spikes to 100 percent with browser open',
            'disk usage stays at 100 percent all day',
            'system lags when switching between applications',
            'memory usage keeps increasing until restart',
            'startup time doubled after recent app install',
        ],
        'solutions': [
            'Performance cleanup:\n1. Review startup apps in Task Manager\n2. Disable non-essential startups\n3. Run disk cleanup and temp purge\n4. Update storage/chipset drivers\n5. Reboot and benchmark',
            'Resource pressure remediation:\n1. Identify top CPU and RAM processes\n2. Update or remove problematic app\n3. Increase page file to system-managed\n4. Check thermal throttling and fan health\n5. Upgrade RAM/SSD if bottleneck persists',
            'Health and malware checks:\n1. Run full antivirus scan\n2. Check scheduled tasks for unknown entries\n3. Validate SMART disk health\n4. Run memory diagnostics\n5. Apply latest OS cumulative updates',
        ],
    },
    {
        'name': 'login-account',
        'category': 'Account',
        'keywords': ['login', 'password', 'locked account', 'mfa', 'otp'],
        'issues': [
            'account gets locked after one failed attempt',
            'valid password rejected on web portal',
            'mfa code not delivered to registered phone',
            'cannot sign in after password reset',
            'domain login works on one pc only',
            'single sign on loops back to login page',
        ],
        'solutions': [
            'Access recovery flow:\n1. Confirm username format\n2. Reset password via approved portal\n3. Wait for account unlock window\n4. Clear browser auth cookies\n5. Retry with correct domain prefix',
            'MFA and identity checks:\n1. Sync authenticator app time\n2. Regenerate backup codes\n3. Verify registered phone/email\n4. Re-enroll MFA device\n5. Ask IAM team to clear stale tokens',
            'SSO troubleshooting:\n1. Test login in private browser session\n2. Disable problematic extensions\n3. Verify system date/time and timezone\n4. Flush DNS and retry\n5. Escalate with correlation ID from error page',
        ],
    },
    {
        'name': 'permissions',
        'category': 'Account',
        'keywords': ['permission', 'access denied', 'shared folder', 'not authorized'],
        'issues': [
            'access denied when opening team shared drive',
            'read permission available but write permission missing',
            'cannot access project folder after role change',
            'new employee does not have app permissions yet',
            'file share opens but cannot save edits',
            'temporary contractor account missing required groups',
        ],
        'solutions': [
            'Permission alignment:\n1. Verify user group membership\n2. Compare effective permissions\n3. Add required AD/security groups\n4. Force policy refresh (gpupdate /force)\n5. Re-login and retest access',
            'Shared drive repair:\n1. Validate network path and ownership\n2. Confirm share + NTFS permissions both\n3. Remove stale mapped drive\n4. Re-map with correct credentials\n5. Validate read/write with test file',
            'Role-based access workflow:\n1. Submit access request with manager approval\n2. Apply least-privilege role template\n3. Document granted access expiration\n4. Audit access in IAM console\n5. Notify user once propagation completes',
        ],
    },
]


def _row_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        (row.get('issue') or '').strip().lower(),
        (row.get('category') or '').strip().lower(),
        (row.get('solution') or '').strip().lower(),
    )


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f'Dataset not found: {DATASET_PATH}')

    with DATASET_PATH.open('r', encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))

    existing_keys = {_row_key(r) for r in rows}
    new_rows: list[dict[str, str]] = []

    for pattern in ISSUE_PATTERNS:
        issues = pattern['issues']
        solutions = pattern['solutions']
        category = pattern['category']

        for issue in issues:
            for solution in solutions:
                candidate = {
                    'issue': issue.strip(),
                    'category': category,
                    'solution': solution.strip(),
                }
                key = _row_key(candidate)
                if key in existing_keys:
                    continue
                existing_keys.add(key)
                new_rows.append(candidate)

    all_rows = rows + new_rows
    random.seed(42)
    random.shuffle(all_rows)

    with DATASET_PATH.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['issue', 'category', 'solution'])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f'Original rows: {len(rows)}')
    print(f'Added rows: {len(new_rows)}')
    print(f'Final rows: {len(all_rows)}')


if __name__ == '__main__':
    main()
