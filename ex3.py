import subprocess
import re
from datetime import datetime
from matplotlib.animation import FuncAnimation
from matplotlib import pyplot as plt
import collections

# ----------------- WiFi Scanning Functions -----------------

def scan_available_wifis():
    """Scan for all available WiFi networks using multiple methods"""
    try:
        commands = [
            "netsh wlan show networks mode=bssid",
            "netsh wlan show networks",
            "netsh wlan show all"
        ]

        for cmd in commands:
            try:
                p = subprocess.Popen(cmd,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     shell=True,
                                     text=True,
                                     encoding='utf-8',
                                     errors='ignore')
                out, err = p.communicate(timeout=15)
                if not out:
                    continue

                networks = {}
                current_ssid = None
                lines = out.split('\n')

                for line in lines:
                    line = line.strip()
                    ssid_match = re.match(r'(?:SSID\s*\d*\s*|Profile\s*):\s*(.+)', line)
                    if ssid_match:
                        current_ssid = ssid_match.group(1).strip()
                        if current_ssid and current_ssid not in networks:
                            networks[current_ssid] = []
                        continue

                    signal_match = re.search(r'Signal\s*:\s*(\d+)%', line)
                    if signal_match and current_ssid:
                        networks[current_ssid].append(int(signal_match.group(1)))

                # Convert to strongest signal for each SSID
                result = {}
                for ssid, signals in networks.items():
                    if signals:
                        # convert % to dBm
                        signal_dbm = max(signals) / 2 - 100
                        result[ssid] = signal_dbm
                    else:
                        result[ssid] = -100
                if result:
                    return result
            except subprocess.TimeoutExpired:
                continue
            except Exception:
                continue
        return {}
    except Exception:
        return {}

def get_connected_wifi():
    """Get connected WiFi information"""
    try:
        p = subprocess.Popen("netsh wlan show interfaces",
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             shell=True,
                             text=True,
                             encoding='utf-8')
        out, err = p.communicate(timeout=10)
        if not out:
            return None, None

        ssid = None
        signal_dbm = None

        for line in out.split('\n'):
            line = line.strip()
            if 'SSID' in line and 'BSSID' not in line:
                ssid_match = re.search(r'SSID\s*:\s*(.+)', line)
                if ssid_match:
                    ssid = ssid_match.group(1).strip()
            if 'Signal' in line:
                signal_match = re.search(r'(\d+)%', line)
                if signal_match:
                    signal_percent = int(signal_match.group(1))
                    signal_dbm = signal_percent / 2 - 100  # convert to dBm
        return ssid, signal_dbm
    except Exception:
        return None, None

# ----------------- Data Storage -----------------

wifi_data = collections.defaultdict(lambda: {'x': [], 'y': []})
start_time = datetime.now()

# ----------------- Plot Setup -----------------

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
plt.subplots_adjust(hspace=0.4)

def setup_signal_zones(ax):
    ax.axhspan(ymin=-100, ymax=-90, color='red', alpha=0.2, label='Unusable')
    ax.axhspan(ymin=-90, ymax=-80, color='orange', alpha=0.2, label='Very Weak')
    ax.axhspan(ymin=-80, ymax=-70, color='yellow', alpha=0.2, label='Weak')
    ax.axhspan(ymin=-70, ymax=-60, color='lightgreen', alpha=0.2, label='Fair')
    ax.axhspan(ymin=-60, ymax=-50, color='green', alpha=0.2, label='Good')
    ax.axhspan(ymin=-50, ymax=-30, color='darkgreen', alpha=0.2, label='Excellent')
    ax.axhspan(ymin=-30, ymax=0, color='blue', alpha=0.2, label='Perfect')

setup_signal_zones(ax1)
setup_signal_zones(ax2)

ax1.set_xlabel('Time (s)')
ax1.set_ylabel('Signal Strength (dBm)')
ax1.set_title('Available WiFi Networks')
ax1.set_ylim(-100, 0)
ax1.legend(fontsize=8)

ax2.set_xlabel('Time (s)')
ax2.set_ylabel('Signal Strength (dBm)')
ax2.set_title('Connected WiFi')
ax2.set_ylim(-100, 0)
ax2.legend(fontsize=8)

# ----------------- Update Function -----------------

def update(frame):
    current_time = (datetime.now() - start_time).total_seconds()

    networks = scan_available_wifis()
    connected_ssid, connected_signal = get_connected_wifi()

    # Update data for all networks
    for ssid, signal_dbm in networks.items():
        wifi_data[ssid]['x'].append(current_time)
        wifi_data[ssid]['y'].append(signal_dbm)
        if len(wifi_data[ssid]['x']) > 50:
            wifi_data[ssid]['x'] = wifi_data[ssid]['x'][-50:]
            wifi_data[ssid]['y'] = wifi_data[ssid]['y'][-50:]

    ax1.clear()
    ax2.clear()
    setup_signal_zones(ax1)
    setup_signal_zones(ax2)

    colors = plt.cm.tab10.colors

    # Plot available WiFi networks
    for i, (ssid, data) in enumerate(list(wifi_data.items())[:8]):
        if data['x'] and data['y']:
            color = colors[i % len(colors)]
            ax1.plot(data['x'], data['y'], 'o-', linewidth=2,
                     color=color, label=ssid[:15] + '...' if len(ssid) > 15 else ssid)
            ax1.text(current_time, data['y'][-1] + 1, f"{data['y'][-1]:.0f}", fontsize=8, color=color)

    # Plot connected WiFi
    if connected_ssid and connected_ssid in wifi_data:
        data = wifi_data[connected_ssid]
        ax2.plot(data['x'], data['y'], 'bo-', linewidth=3, label=f"{connected_ssid}")
        ax2.text(current_time, data['y'][-1] + 1, f"{data['y'][-1]:.0f}", fontsize=10, color='blue')

    # Update axes
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Signal Strength (dBm)')
    ax1.set_title(f'Available WiFi Networks ({len(networks)} found)')
    ax1.set_ylim(-100, 0)
    ax1.legend(fontsize=8)

    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Signal Strength (dBm)')
    ax2.set_title(f'Connected: {connected_ssid or "None"}')
    ax2.set_ylim(-100, 0)
    ax2.legend(fontsize=8)

    time_window = 120
    ax1.set_xlim(max(0, current_time - time_window), current_time + 5)
    ax2.set_xlim(max(0, current_time - time_window), current_time + 5)

    return []

# ----------------- Start Animation -----------------

animation = FuncAnimation(fig, update, interval=5000, cache_frame_data=False, blit=False)
plt.show()
