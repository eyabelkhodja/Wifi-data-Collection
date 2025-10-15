import subprocess
import re
import platform
from datetime import datetime
from matplotlib.animation import FuncAnimation
from matplotlib import pyplot as plt
import collections
import numpy as np
from scipy.stats import norm
import matplotlib.patches as patches


def scan_available_wifis():
    """Scan for all available WiFi networks"""
    try:
        cmd = "netsh wlan show networks mode=bssid"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, encoding='utf-8')

        networks = {}
        current_ssid = None

        if result.returncode == 0:
            lines = result.stdout.split('\n')

            for line in lines:
                line = line.strip()

                # SSID detection
                ssid_match = re.match(r'SSID\s*\d+\s*:\s*(.+)', line, re.IGNORECASE)
                if ssid_match:
                    current_ssid = ssid_match.group(1).strip()
                    if current_ssid not in networks:
                        networks[current_ssid] = []

                # Signal detection
                signal_match = re.search(r'Signal\s*:\s*(\d+)%', line, re.IGNORECASE)
                if signal_match and current_ssid:
                    signal_strength = int(signal_match.group(1))
                    networks[current_ssid].append(signal_strength)

        return networks

    except Exception as e:
        print(f"Error scanning WiFi: {e}")
        return {}


def get_connected_wifi():
    """Get connected WiFi information"""
    try:
        cmd = "netsh wlan show interfaces"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5, encoding='utf-8')

        ssid = None
        signal = None

        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                line = line.strip()
                if 'SSID' in line and 'BSSID' not in line:
                    ssid_match = re.search(r'SSID\s*:\s*(.+)', line)
                    if ssid_match:
                        ssid = ssid_match.group(1).strip()
                elif 'Signal' in line:
                    signal_match = re.search(r'(\d+)%', line)
                    if signal_match:
                        signal = int(signal_match.group(1))

        return ssid, signal

    except Exception as e:
        print(f"Error getting connected WiFi: {e}")
        return None, None


# Data storage
wifi_data = collections.defaultdict(lambda: {'signals': [], 'timestamps': [], 'gaussian_params': None})
start_time = datetime.now()

# Create figure with subplots
print("Setting up WiFi Gaussian distribution monitoring...")
fig = plt.figure(figsize=(15, 10))

# Create 3 subplots
ax1 = plt.subplot2grid((2, 2), (0, 0))  # Real-time signal strength
ax2 = plt.subplot2grid((2, 2), (0, 1))  # Gaussian distributions
ax3 = plt.subplot2grid((2, 2), (1, 0), colspan=2)  # Connected network analysis

plt.tight_layout(pad=4.0)

# Color setup
colors = plt.cm.Set3(np.linspace(0, 1, 12))


def create_gaussian_distribution(signals):
    """Create Gaussian distribution from signal strength data"""
    if len(signals) < 2:
        # If not enough data, create a default distribution
        mean = signals[0] if signals else 50
        std = 10
    else:
        mean = np.mean(signals)
        std = np.std(signals)
        # Ensure minimum standard deviation for visibility
        std = max(std, 5)

    return mean, std


def update(frame):
    try:
        current_time = (datetime.now() - start_time).total_seconds()

        # Scan for networks
        networks = scan_available_wifis()
        connected_ssid, connected_signal = get_connected_wifi()

        # Update data for all networks
        for ssid, signals in networks.items():
            if signals:
                wifi_data[ssid]['signals'].extend(signals)
                wifi_data[ssid]['timestamps'].extend([current_time] * len(signals))

                # Keep last 100 measurements
                if len(wifi_data[ssid]['signals']) > 100:
                    wifi_data[ssid]['signals'] = wifi_data[ssid]['signals'][-100:]
                    wifi_data[ssid]['timestamps'] = wifi_data[ssid]['timestamps'][-100:]

                # Update Gaussian parameters
                if len(wifi_data[ssid]['signals']) >= 2:
                    mean, std = create_gaussian_distribution(wifi_data[ssid]['signals'])
                    wifi_data[ssid]['gaussian_params'] = (mean, std)

        # Clear plots
        ax1.clear()
        ax2.clear()
        ax3.clear()

        # Plot 1: Real-time signal strength over time
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Signal Strength (%)')
        ax1.set_title('Real-time WiFi Signal Strength')
        ax1.set_ylim(0, 100)
        ax1.grid(True, alpha=0.3)

        # Plot 2: Gaussian distributions
        ax2.set_xlabel('Signal Strength (%)')
        ax2.set_ylabel('Probability Density')
        ax2.set_title('WiFi Signal Strength Distributions (Gaussian)')
        ax2.set_xlim(0, 100)
        ax2.grid(True, alpha=0.3)

        # Plot 3: Connected network analysis
        ax3.set_xlabel('Signal Strength (%)')
        ax3.set_ylabel('Probability Density')
        ax3.set_title('Connected Network Detailed Analysis')
        ax3.set_xlim(0, 100)
        ax3.grid(True, alpha=0.3)

        # Plot real-time data (top-left)
        sorted_networks = sorted([(ssid, data) for ssid, data in wifi_data.items()
                                  if data['signals']],
                                 key=lambda x: x[1]['signals'][-1] if x[1]['signals'] else 0,
                                 reverse=True)

        for i, (ssid, data) in enumerate(sorted_networks[:6]):  # Top 6 networks
            if data['timestamps'] and data['signals']:
                color = colors[i % len(colors)]
                ax1.plot(data['timestamps'], data['signals'], 'o-',
                         linewidth=1.5, markersize=3, color=color,
                         label=f"{ssid[:12]}..." if len(ssid) > 12 else ssid,
                         alpha=0.7)

        ax1.legend(fontsize=8, loc='upper right')

        # Plot Gaussian distributions (top-right)
        networks_with_gaussian = [(ssid, data) for ssid, data in wifi_data.items()
                                  if data['gaussian_params'] is not None]

        # Sort by mean signal strength (strongest first)
        networks_with_gaussian.sort(key=lambda x: x[1]['gaussian_params'][0], reverse=True)

        x_plot = np.linspace(0, 100, 200)

        for i, (ssid, data) in enumerate(networks_with_gaussian[:8]):  # Top 8 distributions
            mean, std = data['gaussian_params']
            color = colors[i % len(colors)]

            # Create Gaussian curve
            y_plot = norm.pdf(x_plot, mean, std)
            # Normalize for better visualization
            y_plot = y_plot / np.max(y_plot) * 0.8

            ax2.plot(x_plot, y_plot, '-', linewidth=2, color=color,
                     label=f"{ssid[:10]}... (μ={mean:.1f}%, σ={std:.1f})")

            # Fill under the curve
            ax2.fill_between(x_plot, 0, y_plot, alpha=0.3, color=color)

            # Add vertical line at mean
            ax2.axvline(x=mean, color=color, linestyle='--', alpha=0.5)

            # Add current signal strength as a point
            if data['signals']:
                current_signal = data['signals'][-1]
                y_current = norm.pdf(current_signal, mean, std) / np.max(norm.pdf(x_plot, mean, std)) * 0.8
                ax2.plot(current_signal, y_current, 'o', markersize=6,
                         color=color, markeredgecolor='black', markeredgewidth=1)

        ax2.legend(fontsize=7, loc='upper right')

        # Plot detailed analysis for connected network (bottom)
        if connected_ssid and connected_ssid in wifi_data:
            connected_data = wifi_data[connected_ssid]

            if connected_data['gaussian_params']:
                mean, std = connected_data['gaussian_params']

                # Main Gaussian curve
                x_detailed = np.linspace(max(0, mean - 3 * std), min(100, mean + 3 * std), 200)
                y_detailed = norm.pdf(x_detailed, mean, std)
                y_detailed = y_detailed / np.max(y_detailed)  # Normalize

                ax3.plot(x_detailed, y_detailed, 'b-', linewidth=3,
                         label=f'Gaussian Distribution (μ={mean:.1f}%, σ={std:.1f})')
                ax3.fill_between(x_detailed, 0, y_detailed, alpha=0.3, color='blue')

                # Current signal strength
                if connected_data['signals']:
                    current_signal = connected_data['signals'][-1]
                    y_current = norm.pdf(current_signal, mean, std) / np.max(norm.pdf(x_detailed, mean, std))
                    ax3.plot(current_signal, y_current, 'ro', markersize=10,
                             label=f'Current: {current_signal}%')

                # Signal quality zones
                zones = [
                    (0, 23, 'Very Weak', 'red'),
                    (23, 38, 'Weak', 'orange'),
                    (38, 53, 'Fair', 'yellow'),
                    (53, 68, 'Good', 'lightgreen'),
                    (68, 84, 'Very Good', 'green'),
                    (84, 100, 'Excellent', 'darkgreen')
                ]

                for zone_min, zone_max, zone_label, zone_color in zones:
                    ax3.axvspan(zone_min, zone_max, alpha=0.1, color=zone_color, label=zone_label)

                # Statistics
                stats_text = f"""
                Connected: {connected_ssid}
                Current: {current_signal}%
                Mean (μ): {mean:.1f}%
                Std Dev (σ): {std:.1f}%
                Samples: {len(connected_data['signals'])}
                Reliability: {'High' if std < 15 else 'Medium' if std < 25 else 'Low'}
                """

                ax3.text(0.02, 0.98, stats_text, transform=ax3.transAxes,
                         verticalalignment='top', fontfamily='monospace',
                         bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

                ax3.legend(loc='upper right')

        # Auto-scale time axis for real-time plot
        time_window = 120
        ax1.set_xlim(max(0, current_time - time_window), current_time + 5)

        plt.tight_layout(pad=4.0)

        print(f"Update: {len(networks)} networks, {len(networks_with_gaussian)} with Gaussian models")

    except Exception as e:
        print(f"Update error: {e}")
        import traceback
        traceback.print_exc()

    return []


print("\nStarting WiFi Gaussian Distribution Monitoring...")
print("This will show:")
print("1. Real-time signal strength over time")
print("2. Gaussian distributions for each WiFi network")
print("3. Detailed analysis of connected network")

animation = FuncAnimation(fig, update, interval=3000, cache_frame_data=False, blit=False)
plt.show()