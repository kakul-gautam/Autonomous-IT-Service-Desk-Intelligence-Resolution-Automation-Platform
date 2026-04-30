"""
Generate a large, diverse synthetic IT support ticket dataset (enhanced version).

Creates `ai_models/datasets/tickets_synthetic_large.csv` with 1000+ rows.
"""
import csv
import random
from pathlib import Path
from itertools import product


DATA_DIR = Path(__file__).resolve().parents[2] / 'ai_models' / 'datasets'
OUT = DATA_DIR / 'tickets_synthetic_large.csv'


# Rich problem/solution pairs per category with more variations
HARDWARE_DATA = {
    'battery': {
        'issue_templates': [
            'my {device} battery drains too quickly',
            '{device} battery not holding charge',
            'battery level drops fast even when idle',
            'laptop loses {pct}% battery in {time}',
            '{device} battery is dead quickly',
            'cannot keep device charged',
            'battery percentage decreases rapidly',
        ],
        'devices': ['laptop', 'computer', 'device', 'pc', 'system'],
        'pct': ['50%', '75%', '25%'],
        'time': ['1 hour', '30 minutes', '2 hours'],
        'solutions': [
            '1. Check background processes in Task Manager. 2. Disable unnecessary startup programs. 3. Reduce screen brightness. 4. Enable battery saver mode. 5. Update BIOS and drivers.',
            'Try reducing power consumption: disable Wi-Fi when not needed, close background apps, and adjust display timeout settings.',
            'Battery issue likely due to old battery age or faulty power management. Replace battery or update chipset drivers.',
            'Use battery report tool to check health. If battery age shows >80% wear, consider replacement.',
        ]
    },
    'screen': {
        'issue_templates': [
            '{device} monitor is not displaying',
            'screen is blank or black',
            'no signal from my display',
            '{device} screen stays black',
            'display not responding',
            'monitor has no signal',
        ],
        'devices': ['laptop', 'desktop', 'computer'],
        'solutions': [
            '1. Check cable connections to monitor and power supply. 2. Restart the device. 3. Try a different display cable. 4. Update graphics drivers. 5. Boot in safe mode to test.',
            'Try: restart monitor, check HDMI/DisplayPort connections, reseat RAM, test with external monitor.',
            'If BIOS POST beeps but no display: video card may be faulty. Try reseating GPU or test with integrated graphics.',
        ]
    },
    'keyboard': {
        'issue_templates': [
            '{keys} keys on keyboard not working',
            'keyboard not responding to input',
            '{keys} keys are stuck or stuck',
            'keyboard input not being registered',
            'some keyboard keys broken',
        ],
        'keys': ['some', 'several', 'multiple', 'a few'],
        'solutions': [
            '1. Restart the computer. 2. Check for physical debris under keys. 3. Update keyboard drivers. 4. Test in BIOS. 5. Try USB keyboard to isolate hardware.',
            'Disable and re-enable keyboard in Device Manager, or reinstall keyboard drivers.',
            'For mechanical keyboard: check switch contacts, clean with compressed air, or replace faulty switches.',
        ]
    },
    'performance': {
        'issue_templates': [
            '{device} is running very slow',
            'device performance is very degraded',
            'system {behavior} frequently',
            '{device} takes {time} to start up',
        ],
        'device': ['computer', 'laptop', 'pc', 'system'],
        'behavior': ['lags', 'freezes', 'stutters', 'hangs'],
        'time': ['too long', 'forever', 'minutes'],
        'solutions': [
            '1. Run Disk Cleanup and Defrag. 2. Check Task Manager for high CPU/RAM usage. 3. Disable startup programs. 4. Run antivirus scan. 5. Upgrade RAM or SSD if needed.',
            'Disable visual effects: System Properties > Advanced > Performance > Adjust for best performance.',
            'Check hard drive health with CrystalDiskInfo. If failing, back up and replace with SSD.',
        ]
    },
}

NETWORK_DATA = {
    'wifi': {
        'issue_templates': [
            'wi-fi not connecting to network',
            'wifi connection keeps {action}',
            'network shows available but {result}',
            'weak wifi signal quality',
            'internet {action} frequently',
        ],
        'action': ['dropping', 'disconnecting', 'failing', 'breaking'],
        'result': ['cannot connect', 'won\'t connect', 'fails to connect'],
        'solutions': [
            '1. Restart the router (power off 30 seconds). 2. Check wifi password. 3. Forget network and reconnect. 4. Update NIC drivers. 5. Change router channel to reduce interference.',
            'Move closer to router, restart router and network adapter, or try 5GHz band if available.',
            'If consistent drops: check router logs for errors, reset router to factory defaults, or contact ISP.',
        ]
    },
    'ethernet': {
        'issue_templates': [
            'ethernet cable not working',
            '{connection} connection not available',
            'network cable {action}',
            'no internet through {connection}',
        ],
        'connection': ['wired', 'ethernet', 'LAN'],
        'action': ['disconnected', 'loose', 'broken'],
        'solutions': [
            '1. Check physical cable connection. 2. Try a different ethernet port or cable. 3. Restart modem and router. 4. Update network drivers. 5. Disable IPv6 if conflicts.',
            'Test cable with network tester, restart network adapter in Device Manager, or try direct connection to modem.',
            'If physical connections are good, check BIOS settings for NIC, update BIOS, or test on different device.',
        ]
    },
    'vpn': {
        'issue_templates': [
            'vpn connection {action}',
            'cannot connect to company vpn',
            'vpn {problem} frequently',
            'vpn {problem} error',
        ],
        'action': ['failing', 'not working', 'broken'],
        'problem': ['disconnects', 'fails', 'throws'],
        'solutions': [
            '1. Clear VPN cache and reconnect. 2. Verify VPN credentials. 3. Check firewall rules. 4. Update VPN client. 5. Try different VPN server location.',
            'Restart VPN client, disable IPv6, check DNS settings, or run repair/reinstall of VPN software.',
            'Contact IT support to verify account is enabled for VPN and check access logs for failures.',
        ]
    },
}

SOFTWARE_DATA = {
    'crash': {
        'issue_templates': [
            'application keeps {action}',
            'program {action} on startup',
            'software {action} when opening files',
            '{app} {action} during operation',
        ],
        'action': ['crashing', 'crashing', 'freezing and crashing', 'closing unexpectedly'],
        'app': ['app', 'application', 'program', 'software'],
        'solutions': [
            '1. Restart the application. 2. Clear application cache and temporary files. 3. Update to latest version. 4. Reinstall the software. 5. Check System Event Viewer for error codes.',
            'Run application in compatibility mode, disable visual themes, or try launching in Safe Mode.',
            'If crash persists after reinstall: check Windows Update, verify hardware resources, or contact software vendor with error code.',
        ]
    },
    'install': {
        'issue_templates': [
            'cannot install {software}',
            'installation {action}',
            'installer keeps {action}',
            '{action} access denied during install',
        ],
        'software': ['software', 'application', 'program', 'package'],
        'action': ['fails', 'failing', 'error', 'getting'],
        'solutions': [
            '1. Run installer as Administrator. 2. Temporarily disable antivirus. 3. Check available disk space. 4. Clear temp folder. 5. Restart and try again.',
            'Download fresh installer, check for conflicting software, or verify installer signature.',
            'If admin rights needed: contact IT Helpdesk to escalate installation or modify UAC settings.',
        ]
    },
    'update': {
        'issue_templates': [
            'windows update is {action}',
            'cannot install software updates',
            'update {action} repeatedly',
            'update service not {action}',
        ],
        'action': ['stuck', 'failing', 'responding'],
        'solutions': [
            '1. Restart Windows Update service. 2. Run Windows Update troubleshooter. 3. Clear update cache folder. 4. Check disk space. 5. Run DISM and SFC scans.',
            'Manually download updates from Microsoft Update Catalog if automatic update fails.',
            'If persistent failures: perform clean boot, check Event Viewer logs, or consider fresh OS install.',
        ]
    },
}

ACCOUNT_DATA = {
    'login': {
        'issue_templates': [
            'cannot login to {account}',
            'login credentials not {action}',
            'password {action}',
            'login {action} with invalid credentials',
        ],
        'account': ['account', 'system', 'application', 'server'],
        'action': ['working', 'accepted', 'fails'],
        'solutions': [
            '1. Verify caps lock is off. 2. Use password reset link. 3. Clear browser cache. 4. Try incognito mode. 5. Contact IT to unlock account if locked.',
            'Check email for password reset instructions, wait 30 min before retry after account lock, or contact IT support.',
            'Verify username spelling, try account recovery email, or contact IT to verify account status.',
        ]
    },
    'permission': {
        'issue_templates': [
            'access denied to {resource}',
            'no permission to access {resource}',
            'insufficient permissions for {resource}',
            '{resource} is restricted',
        ],
        'resource': ['file', 'folder', 'drive', 'resource', 'directory'],
        'solutions': [
            '1. Check file permissions and sharing settings. 2. Contact file owner for access. 3. Verify network/domain connection. 4. Try running as Administrator. 5. Check if resource is mounted.',
            'For shared drives: verify network path, check your group memberships, or contact IT to add permissions.',
            'If trying to access external resource: verify VPN connection, firewall rules, or request access from resource owner.',
        ]
    },
}


def build_large_dataset():
    rows = []
    
    # Hardware
    for category, data in HARDWARE_DATA.items():
        templates = data['issue_templates']
        solutions = data['solutions']
        
        # Get available substitution keys
        keys = [k for k in data.keys() if k not in ['issue_templates', 'solutions']]
        
        # Generate combinations
        if keys:
            key_values = [data.get(k, ['']) for k in keys]
            for combo in product(*key_values):
                subs = dict(zip(keys, combo))
                for template in templates:
                    try:
                        issue = template.format(**subs)
                        solution = random.choice(solutions)
                        rows.append({'issue': issue, 'category': 'Hardware', 'solution': solution})
                    except:
                        pass
        else:
            for template in templates:
                for solution in solutions:
                    rows.append({'issue': template, 'category': 'Hardware', 'solution': solution})
    
    # Network
    for category, data in NETWORK_DATA.items():
        templates = data['issue_templates']
        solutions = data['solutions']
        keys = [k for k in data.keys() if k not in ['issue_templates', 'solutions']]
        
        if keys:
            key_values = [data.get(k, ['']) for k in keys]
            for combo in product(*key_values):
                subs = dict(zip(keys, combo))
                for template in templates:
                    try:
                        issue = template.format(**subs)
                        solution = random.choice(solutions)
                        rows.append({'issue': issue, 'category': 'Network', 'solution': solution})
                    except:
                        pass
        else:
            for template in templates:
                for solution in solutions:
                    rows.append({'issue': template, 'category': 'Network', 'solution': solution})
    
    # Software
    for category, data in SOFTWARE_DATA.items():
        templates = data['issue_templates']
        solutions = data['solutions']
        keys = [k for k in data.keys() if k not in ['issue_templates', 'solutions']]
        
        if keys:
            key_values = [data.get(k, ['']) for k in keys]
            for combo in product(*key_values):
                subs = dict(zip(keys, combo))
                for template in templates:
                    try:
                        issue = template.format(**subs)
                        solution = random.choice(solutions)
                        rows.append({'issue': issue, 'category': 'Software', 'solution': solution})
                    except:
                        pass
        else:
            for template in templates:
                for solution in solutions:
                    rows.append({'issue': template, 'category': 'Software', 'solution': solution})
    
    # Account
    for category, data in ACCOUNT_DATA.items():
        templates = data['issue_templates']
        solutions = data['solutions']
        keys = [k for k in data.keys() if k not in ['issue_templates', 'solutions']]
        
        if keys:
            key_values = [data.get(k, ['']) for k in keys]
            for combo in product(*key_values):
                subs = dict(zip(keys, combo))
                for template in templates:
                    try:
                        issue = template.format(**subs)
                        solution = random.choice(solutions)
                        rows.append({'issue': issue, 'category': 'Account', 'solution': solution})
                    except:
                        pass
        else:
            for template in templates:
                for solution in solutions:
                    rows.append({'issue': template, 'category': 'Account', 'solution': solution})
    
    return rows


def main():
    rows = build_large_dataset()
    random.shuffle(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    
    # Dedupe
    seen = set()
    unique_rows = []
    for r in rows:
        key = (r['issue'].lower().strip(), r['solution'][:50])
        if key not in seen:
            seen.add(key)
            unique_rows.append(r)
    
    with OUT.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['issue', 'category', 'solution'])
        writer.writeheader()
        writer.writerows(unique_rows)
    
    print(f'Generated {len(unique_rows)} unique synthetic rows to {OUT}')
    
    # Summary
    cat_counts = {}
    for r in unique_rows:
        cat = r['category']
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    print('Category distribution:', cat_counts)


if __name__ == '__main__':
    main()
