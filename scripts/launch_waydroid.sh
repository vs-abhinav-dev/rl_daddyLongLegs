#!/usr/bin/env bash
set -e

APP="com.setsnail.daddylonglegs"

echo "[*] Starting Waydroid session"
waydroid session start > /tmp/waydroid-session.log 2>&1 &
sleep 1

while [[ "$(waydroid status | awk '$1 ~ /Session:/ {print $2}')" != "RUNNING" ]]; do
    echo "[*] waiting..."
    sleep 1
done

while [[ "$(waydroid status | awk '$1 ~ /IP/ {print $2}')" == "UNKNOWN" ]]; do
    echo "[*] IP address is UNKNOWN waiting..."
    sleep 1
done

WAYDROID_HOST=$(waydroid status | awk '$1 ~ /IP/ {print $3}')
WAYDROID_PORT=5555

if [[ -z "${WAYDROID_HOST}" ]]; then
    echo "[!] waydroid host value is empty"
    exit 1
fi

echo "[*] waydroid active at: ${WAYDROID_HOST}:${WAYDROID_PORT}"

echo "[*] start adb server "
adb start-server
sleep 2

echo "[*] adb connect the container"
adb connect ${WAYDROID_HOST}:${WAYDROID_PORT}

echo "[*] Waiting for Android..."
adb wait-for-device

until adb shell getprop sys.boot_completed | grep -q "1"; do
    sleep 1
done

echo "[*] Starting frida-server..."
sudo -v || exit 1
sudo waydroid shell /data/local/tmp/frida-server &

echo "[*] Launching game..."
adb shell am start -n ${APP}/com.unity3d.player.UnityPlayerActivity

echo "[*] Waiting for process..."
until frida-ps -U | grep -q Daddy; do
    sleep 1
done

echo "[*] Set waydroid to not sleep in background"
waydroid prop set persist.waydroid.suspend false

echo "Ready!"
