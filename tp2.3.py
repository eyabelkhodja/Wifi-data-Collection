import subprocess
import re
import platform
import numpy as np
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt

# ────────────────────────────────────────────────
# 🔹 Lecture des réseaux Wi-Fi visibles
# ────────────────────────────────────────────────
def read_networks_from_cmd():
    if platform.system() != "Windows":
        raise Exception("⚠️ Ce script ne fonctionne que sur Windows.")

    try:
        # Lecture avec encodage Windows (plus fiable que unicode_escape)
        out = subprocess.check_output(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            shell=True,
            encoding="utf-8",
            errors="ignore"
        )
    except Exception:
        # Si utf-8 échoue, on retente avec un autre encodage courant
        out = subprocess.check_output(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            shell=True,
            encoding="cp1252",
            errors="ignore"
        )

    # Nettoyage des caractères parasites
    text = out.replace("Â", "").replace("", "").replace("\r", "")

    # Expression régulière pour SSID, Signal, Canal (FR + EN)
    pattern = r"(?:SSID\s*\d*\s*:\s*|Nom du réseau\s*:\s*)(.*?)\s*(?:.*?\n){0,6}.*?(?:Signal\s*:\s*|Strength\s*:\s*)(\d+)%.*?(?:Canal\s*:\s*|Channel\s*:\s*)(\d+)"
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

    networks = []
    for ssid, signal, channel in matches:
        ssid = ssid.strip() or "(hidden)"
        try:
            networks.append((ssid, int(signal), int(channel)))
        except ValueError:
            continue

    return networks


# ────────────────────────────────────────────────
# 🔹 Fonction gaussienne (modélisation bande passante)
# ────────────────────────────────────────────────
def gaussian(x, mu, amplitude, sigma=1.5):
    return amplitude * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


# ────────────────────────────────────────────────
# 🔹 Préparation du graphique
# ────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
ax.set_xlim(1, 13)
ax.set_ylim(0, 100)
ax.set_xlabel("Canal Wi-Fi (2.4 GHz)")
ax.set_ylabel("Puissance du signal (%)")
ax.set_title("Spectre Wi-Fi en temps réel")
ax.grid(True, linestyle="--", alpha=0.4)


# ────────────────────────────────────────────────
# 🔹 Mise à jour du graphique en temps réel
# ────────────────────────────────────────────────
def update(frame):
    ax.clear()
    ax.set_xlim(1, 13)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Canal Wi-Fi (2.4 GHz)")
    ax.set_ylabel("Puissance du signal (%)")
    ax.set_title("Spectre Wi-Fi en temps réel")
    ax.grid(True, linestyle="--", alpha=0.4)

    networks = read_networks_from_cmd()

    if not networks:
        ax.text(6, 50, "⚠️ Aucun réseau Wi-Fi détecté", ha="center", va="center", color="red", fontsize=12)
        return []

    x = np.linspace(1, 13, 400)
    for ssid, signal, channel in networks:
        y = gaussian(x, channel, signal)
        ax.plot(x, y, linewidth=2, label=f"{ssid} ({signal}%)")

    ax.legend(loc="upper right", fontsize=8)
    return []


# ────────────────────────────────────────────────
# 🔹 Animation en direct
# ────────────────────────────────────────────────
ani = FuncAnimation(fig, update, interval=2500, cache_frame_data=False)
plt.tight_layout()
plt.show()
