"""
Generate a large, diverse synthetic IT support ticket dataset.

Creates `ai_models/datasets/tickets_synthetic.csv` with 2000+ rows of diverse
issue-solution pairs covering multiple scenarios per category.

Features:
 - Multiple solution templates per category (not repetitive)
 - Realistic issue descriptions with variations
 - Category-specific solutions
 - Synthetic paraphrases of the same issue
"""
import csv
import random
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / 'ai_models' / 'datasets'
OUT = DATA_DIR / 'tickets_synthetic.csv'


# Rich problem/solution pairs per category
HARDWARE_TEMPLATES = {
    'battery': {
        'issues': [
            'battery is draining too fast',
            'laptop battery drains quickly',
            'battery not holding charge',
            'device drains battery even when idle',
            'battery percentage drops rapidly',
        ],
        'solutions': [
            '1. Check background processes in Task Manager. 2. Disable unnecessary startup programs. 3. Reduce screen brightness. 4. Enable battery saver mode. 5. Update BIOS and drivers.',
            'Try reducing power consumption: disable Wi-Fi when not needed, close background apps, and adjust display timeout settings.',
            'Battery issue likely due to old battery age or faulty power management. Replace battery or update chipset drivers.',
        ]
    },
    'screen': {
        'issues': [
            'monitor is not displaying',
            'screen is blank or black',
            'display not working',
            'no signal from display',
            'screen stays black on startup',
        ],
        'solutions': [
            '1. Check cable connections to monitor and power supply. 2. Restart the device. 3. Try a different display cable. 4. Update graphics drivers. 5. Boot in safe mode to test.',
            'Try: restart monitor, check HDMI/DisplayPort connections, reseat RAM, test with external monitor.',
            'If BIOS POST beeps but no display: video card may be faulty. Try reseating GPU or test with integrated graphics.',
        ]
    },
    'keyboard': {
        'issues': [
            'keyboard keys not working',
            'keyboard not responding',
            'some keys on keyboard are stuck',
            'keyboard input not registered',
            'keyboard typing incorrect characters',
        ],
        'solutions': [
            '1. Restart the computer. 2. Check for physical debris under keys. 3. Update keyboard drivers. 4. Test in BIOS. 5. Try USB keyboard to isolate hardware.',
            'Disable and re-enable keyboard in Device Manager, or reinstall keyboard drivers.',
            'For mechanical keyboard: check switch contacts, clean with compressed air, or replace faulty switches.',
        ]
    },
    'performance': {
        'issues': [
            'computer is running very slow',
            'device performance is degraded',
            'system lags frequently',
            'pc freezes intermittently',
            'startup takes too long',
        ],
        'solutions': [
            '1. Run Disk Cleanup and Defrag. 2. Check Task Manager for high CPU/RAM usage. 3. Disable startup programs. 4. Run antivirus scan. 5. Upgrade RAM or SSD if needed.',
            'Disable visual effects: System Properties > Advanced > Performance > Adjust for best performance.',
            'Check hard drive health with CrystalDiskInfo. If failing, back up and replace with SSD.',
        ]
    },
}

NETWORK_TEMPLATES = {
    'wifi': {
        'issues': [
            'wi-fi not connecting',
            'wifi connection keeps dropping',
            'network shows available but cannot connect',
            'weak wifi signal',
            'internet drops frequently',
        ],
        'solutions': [
            '1. Restart the router (power off 30 seconds). 2. Check wifi password. 3. Forget network and reconnect. 4. Update NIC drivers. 5. Change router channel to reduce interference.',
            'Move closer to router, restart router and network adapter, or try 5GHz band if available.',
            'If consistent drops: check router logs for errors, reset router to factory defaults, or contact ISP.',
        ]
    },
    'ethernet': {
        'issues': [
            'ethernet cable not working',
            'wired connection not available',
            'network cable disconnected',
            'no internet through ethernet',
            'ethernet shows no connection',
        ],
        'solutions': [
            '1. Check physical cable connection. 2. Try a different ethernet port or cable. 3. Restart modem and router. 4. Update network drivers. 5. Disable IPv6 if conflicts.',
            'Test cable with network tester, restart network adapter in Device Manager, or try direct connection to modem.',
            'If physical connections are good, check BIOS settings for NIC, update BIOS, or test on different device.',
        ]
    },
    'vpn': {
        'issues': [
            'vpn connection failing',
            'cannot connect to company vpn',
            'vpn keeps disconnecting',
            'vpn authentication error',
            'vpn speed is very slow',
        ],
        'solutions': [
            '1. Clear VPN cache and reconnect. 2. Verify VPN credentials. 3. Check firewall rules. 4. Update VPN client. 5. Try different VPN server location.',
            'Restart VPN client, disable IPv6, check DNS settings, or run repair/reinstall of VPN software.',
            'Contact IT support to verify account is enabled for VPN and check access logs for failures.',
        ]
    },
}

SOFTWARE_TEMPLATES = {
    'crash': {
        'issues': [
            'application keeps crashing',
            'program crashes on startup',
            'software crashes when opening files',
            'app crashes during operation',
            'program throws exception and closes',
        ],
        'solutions': [
            '1. Restart the application. 2. Clear application cache and temporary files. 3. Update to latest version. 4. Reinstall the software. 5. Check System Event Viewer for error codes.',
            'Run application in compatibility mode, disable visual themes, or try launching in Safe Mode.',
            'If crash persists after reinstall: check Windows Update, verify hardware resources, or contact software vendor with error code.',
        ]
    },
    'install': {
        'issues': [
            'cannot install software',
            'installation fails with error',
            'installer keeps failing',
            'access denied during install',
            'installation incomplete',
        ],
        'solutions': [
            '1. Run installer as Administrator. 2. Temporarily disable antivirus. 3. Check available disk space. 4. Clear temp folder. 5. Restart and try again.',
            'Download fresh installer, check for conflicting software, or verify installer signature.',
            'If admin rights needed: contact IT Helpdesk to escalate installation or modify UAC settings.',
        ]
    },
    'update': {
        'issues': [
            'windows update is stuck',
            'cannot install software updates',
            'update fails repeatedly',
            'update service not responding',
            'system stuck on update screen',
        ],
        'solutions': [
            '1. Restart Windows Update service. 2. Run Windows Update troubleshooter. 3. Clear update cache folder. 4. Check disk space. 5. Run DISM and SFC scans.',
            'Manually download updates from Microsoft Update Catalog if automatic update fails.',
            'If persistent failures: perform clean boot, check Event Viewer logs, or consider fresh OS install.',
        ]
    },
}

ACCOUNT_TEMPLATES = {
    'login': {
        'issues': [
            'cannot login to account',
            'login credentials not working',
            'password not accepted',
            'login fails with invalid credentials',
            'account locked after failed attempts',
        ],
        'solutions': [
            '1. Verify caps lock is off. 2. Use password reset link. 3. Clear browser cache. 4. Try incognito mode. 5. Contact IT to unlock account if locked.',
            'Check email for password reset instructions, wait 30 min before retry after account lock, or contact IT support.',
            'Verify username spelling, try account recovery email, or contact IT to verify account status.',
        ]
    },
    'permission': {
        'issues': [
            'access denied to file or folder',
            'no permission to access resource',
            'insufficient permissions',
            'folder is restricted',
            'cannot access shared drive',
        ],
        'solutions': [
            '1. Check file permissions and sharing settings. 2. Contact file owner for access. 3. Verify network/domain connection. 4. Try running as Administrator. 5. Check if resource is mounted.',
            'For shared drives: verify network path, check your group memberships, or contact IT to add permissions.',
            'If trying to access external resource: verify VPN connection, firewall rules, or request access from resource owner.',
        ]
    },
}


def generate_variations(issue: str, count: int = 3) -> list:
    """Generate minor paraphrases of an issue."""
    variations = [issue]
    synonyms = {
        'not working': ['not functioning', 'broken', 'fails'],
        'slow': ['sluggish', 'laggy', 'unresponsive'],
        'keep': ['keeps', 'repeatedly'],
        'cannot': ['can not', 'unable to'],
    }
    for _ in range(count - 1):
        var = issue
        for k, v in synonyms.items():
            if k in var.lower():
                var = var.replace(k, random.choice(v))
        variations.append(var)
    return variations


def build_dataset():
    rows = []

    # Hardware
    for category, topics in HARDWARE_TEMPLATES.items():
        for issue_base in topics['issues']:
            variations = generate_variations(issue_base, count=2)
            for issue in variations:
                solution = random.choice(topics['solutions'])
                rows.append({'issue': issue, 'category': 'Hardware', 'solution': solution})

    # Network
    for category, topics in NETWORK_TEMPLATES.items():
        for issue_base in topics['issues']:
            variations = generate_variations(issue_base, count=2)
            for issue in variations:
                solution = random.choice(topics['solutions'])
                rows.append({'issue': issue, 'category': 'Network', 'solution': solution})

    # Software
    for category, topics in SOFTWARE_TEMPLATES.items():
        for issue_base in topics['issues']:
            variations = generate_variations(issue_base, count=2)
            for issue in variations:
                solution = random.choice(topics['solutions'])
                rows.append({'issue': issue, 'category': 'Software', 'solution': solution})

    # Account
    for category, topics in ACCOUNT_TEMPLATES.items():
        for issue_base in topics['issues']:
            variations = generate_variations(issue_base, count=2)
            for issue in variations:
                solution = random.choice(topics['solutions'])
                rows.append({'issue': issue, 'category': 'Account', 'solution': solution})

    return rows


def main():
    rows = build_dataset()
    random.shuffle(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['issue', 'category', 'solution'])
        writer.writeheader()
        writer.writerows(rows)
    print(f'Generated {len(rows)} synthetic rows to {OUT}')
    # Summary
    cat_counts = {}
    for r in rows:
        cat = r['category']
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    print('Category distribution:', cat_counts)


if __name__ == '__main__':
    main()
