import subprocess
import re
import platform
from datetime import datetime
from matplotlib.animation import FuncAnimation
from matplotlib import pyplot as plt
import collections
import time


def scan_available_wifis():
    """Scan for all available WiFi networks using multiple methods"""
    try:
        print("Scanning for WiFi networks...")

        # Method 1: Try the basic networks command first
        commands = [
            "netsh wlan show networks mode=bssid",
            "netsh wlan show networks",
            "netsh wlan show all"
        ]

        for cmd in commands:
            try:
                print(f"Trying command: {cmd}")
                p = subprocess.Popen(cmd,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     shell=True,
                                     text=True,
                                     encoding='utf-8',
                                     errors='ignore')

                out, err = p.communicate(timeout=15)

                if err:
                    print(f"Command error: {err}")
                    continue

                if not out:
                    print("No output from command")
                    continue

                print(f"Command output length: {len(out)} characters")

                # Save output to file for debugging
                with open("wifi_scan_debug.txt", "w", encoding='utf-8') as f:
                    f.write(out)

                # Parse networks - try different patterns
                networks = {}
                current_ssid = None
                current_signal = None

                lines = out.split('\n')
                for i, line in enumerate(lines):
                    line = line.strip()

                    # Try different SSID patterns
                    ssid_patterns = [
                        r'SSID\s*\d+\s*:\s*(.+)',
                        r'SSID\s*:\s*(.+)',
                        r'Profile\s*:\s*(.+)'
                    ]

                    for pattern in ssid_patterns:
                        ssid_match = re.match(pattern, line, re.IGNORECASE)
                        if ssid_match:
                            current_ssid = ssid_match.group(1).strip()
                            if current_ssid and current_ssid not in networks:
                                networks[current_ssid] = []
                            break

                    # Try different signal patterns
                    signal_patterns = [
                        r'Signal\s*:\s*(\d+)%',
                        r'Signal\s*Quality\s*:\s*(\d+)',
                        r'Strength\s*:\s*(\d+)'
                    ]

                    for pattern in signal_patterns:
                        signal_match = re.search(pattern, line, re.IGNORECASE)
                        if signal_match:
                            current_signal = int(signal_match.group(1))
                            if current_ssid and current_signal is not None:
                                networks[current_ssid].append(current_signal)
                            break

                # For each network, use the strongest signal
                result = {}
                for ssid, signals in networks.items():
                    if signals:
                        result[ssid] = max(signals)
                    else:
                        # If no signal found, set to 0 or try to get from other methods
                        result[ssid] = 0

                if result:
                    print(f"Success with command: {cmd}")
                    print(f"Found {len(result)} networks: {list(result.keys())}")
                    return result
                else:
                    print(f"No networks found with command: {cmd}")

            except subprocess.TimeoutExpired:
                print(f"Command timed out: {cmd}")
                continue
            except Exception as e:
                print(f"Error with command {cmd}: {e}")
                continue

        # If all commands fail, try a fallback method
        print("Trying fallback method...")
        return fallback_wifi_scan()

    except Exception as e:
        print(f"Error in WiFi scan: {e}")
        return {}


def fallback_wifi_scan():
    """Fallback method using Windows native commands"""
    try:
        # Try using Windows PowerShell command
        ps_command = """
        $networks = netsh wlan show networks mode=bssid
        Write-Output $networks
        """

        p = subprocess.Popen(["powershell", "-Command", ps_command],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             text=True,
                             encoding='utf-8')

        out, err = p.communicate(timeout=20)

        if out:
            # Simple parsing - look for SSID and Signal patterns
            networks = {}
            lines = out.split('\n')

            for line in lines:
                line = line.strip()
                # Look for SSID
                if 'SSID' in line and 'BSSID' not in line:
                    ssid_match = re.search(r'SSID\s*\d*\s*:\s*(.+)', line)
                    if ssid_match:
                        ssid = ssid_match.group(1).strip()
                        networks[ssid] = networks.get(ssid, 0)

                # Look for Signal
                elif 'Signal' in line:
                    signal_match = re.search(r'(\d+)%', line)
                    if signal_match and networks:
                        signal = int(signal_match.group(1))
                        # Assign to last found SSID
                        last_ssid = list(networks.keys())[-1] if networks else None
                        if last_ssid:
                            networks[last_ssid] = max(networks[last_ssid], signal)

            # Remove networks with 0 signal
            networks = {k: v for k, v in networks.items() if v > 0}

            if networks:
                print(f"Fallback found {len(networks)} networks")
                return networks

        return {}

    except Exception as e:
        print(f"Fallback method failed: {e}")
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

        if out:
            ssid = None
            signal = None

            for line in out.split('\n'):
                line = line.strip()
                if 'SSID' in line and 'BSSID' not in line:
                    ssid_match = re.search(r'SSID\s*:\s*(.+)', line)
                    if ssid_match:
                        ssid = ssid_match.group(1).strip()

                if 'Signal' in line:
                    signal_match = re.search(r'(\d+)%', line)
                    if signal_match:
                        signal = int(signal_match.group(1))

            return ssid, signal

        return None, None

    except Exception as e:
        print(f"Error getting connected WiFi: {e}")
        return None, None


# Initialize data storage
wifi_data = collections.defaultdict(lambda: {'x': [], 'y': []})
start_time = datetime.now()

# Create the plot
print("Setting up visualization...")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
plt.subplots_adjust(hspace=0.4)


# Setup signal strength zones
def setup_signal_zones(ax):
    ax.axhspan(ymin=0, ymax=23, color='red', alpha=0.2, label='Very Weak')
    ax.axhspan(ymin=23, ymax=38, color='orange', alpha=0.2, label='Weak')
    ax.axhspan(ymin=38, ymax=53, color='yellow', alpha=0.2, label='Fair')
    ax.axhspan(ymin=53, ymax=68, color='lightgreen', alpha=0.2, label='Good')
    ax.axhspan(ymin=68, ymax=84, color='green', alpha=0.2, label='Very Good')
    ax.axhspan(ymin=84, ymax=100, color='darkgreen', alpha=0.2, label='Excellent')


setup_signal_zones(ax1)
setup_signal_zones(ax2)

# Configure plots
ax1.set_xlabel('Time (s)')
ax1.set_ylabel('Signal Strength (%)')
ax1.set_title('Available WiFi Networks')
ax1.set_ylim(0, 100)
ax1.legend()

ax2.set_xlabel('Time (s)')
ax2.set_ylabel('Signal Strength (%)')
ax2.set_title('Connected WiFi')
ax2.set_ylim(0, 100)
ax2.legend()

# Manual test first
print("\n=== MANUAL TEST ===")
print("Testing WiFi scan...")
test_networks = scan_available_wifis()
print(f"Networks found: {test_networks}")

print("\nTesting connected WiFi...")
connected_ssid, connected_signal = get_connected_wifi()
print(f"Connected to: {connected_ssid}, Signal: {connected_signal}%")

if not test_networks and connected_ssid:
    print("\nWARNING: No networks found in scan, but you are connected to a WiFi!")
    print("This suggests a permission issue. Please run as Administrator.")


def update(frame):
    try:
        current_time = (datetime.now() - start_time).total_seconds()

        # Scan for networks
        networks = scan_available_wifis()
        connected_ssid, connected_signal = get_connected_wifi()

        # Update data
        for ssid, signal in networks.items():
            wifi_data[ssid]['x'].append(current_time)
            wifi_data[ssid]['y'].append(signal)

            # Keep data manageable
            if len(wifi_data[ssid]['x']) > 50:
                wifi_data[ssid]['x'] = wifi_data[ssid]['x'][-50:]
                wifi_data[ssid]['y'] = wifi_data[ssid]['y'][-50:]

        # Clear and redraw
        ax1.clear()
        ax2.clear()
        setup_signal_zones(ax1)
        setup_signal_zones(ax2)

        # Plot available networks
        colors = plt.cm.tab10.colors
        for i, (ssid, data) in enumerate(list(wifi_data.items())[:8]):  # Limit to 8 networks
            if data['x'] and data['y']:
                color = colors[i % len(colors)]
                ax1.plot(data['x'], data['y'], 'o-', linewidth=2,
                         color=color, label=ssid[:15] + '...' if len(ssid) > 15 else ssid)
                # Add current value
                if data['y']:
                    ax1.text(current_time, data['y'][-1] + 2, f"{data['y'][-1]}%",
                             fontsize=8, color=color)

        # Plot connected network
        if connected_ssid and connected_ssid in wifi_data:
            data = wifi_data[connected_ssid]
            if data['x'] and data['y']:
                ax2.plot(data['x'], data['y'], 'bo-', linewidth=3,
                         label=f"{connected_ssid} ({connected_signal}%)")
                ax2.text(current_time, data['y'][-1] + 2, f"{data['y'][-1]}%",
                         fontsize=10, color='blue')

        # Update plot settings
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Signal Strength (%)')
        ax1.set_title(f'Available WiFi Networks ({len(networks)} found)')
        ax1.set_ylim(0, 100)
        ax1.legend(fontsize=8)

        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Signal Strength (%)')
        ax2.set_title(f'Connected: {connected_ssid or "None"}')
        ax2.set_ylim(0, 100)
        ax2.legend()

        # Auto-scale time axis
        time_window = 120  # Show last 2 minutes
        ax1.set_xlim(max(0, current_time - time_window), current_time + 5)
        ax2.set_xlim(max(0, current_time - time_window), current_time + 5)

    except Exception as e:
        print(f"Update error: {e}")

    return []


print("\n=== STARTING MONITOR ===")
print("If no networks appear, please:")
print("1. Run this script as Administrator")
print("2. Check if WiFi is enabled on your PC")
print("3. Wait a few seconds for scans to complete")

# Start animation
animation = FuncAnimation(fig, update, interval=5000, cache_frame_data=False, blit=False)
plt.show()