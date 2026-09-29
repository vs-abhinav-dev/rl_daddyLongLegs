#!/usr/bin/env bash
set -e

APP="com.setsnail.daddylonglegs"

echo "[*] Starting Waydroid session"
waydroid session start &
sleep 1

WAYDROID_HOST=$(waydroid status | awk '$1 ~/IP/ {print $3}')
WAYDROID_PORT=5555

echo 

if [[ -z "${WAYDROID_HOST}" ]]; then
    echo "waydroid host value is empty"
    exit 1
fi

echo "[*] waydroid active at: ${WAYDROID_HOST}:${WAYDROID_PORT}"

echo "[*] unfreezing container"
sudo waydroid container unfreeze
sleep 1

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
sudo waydroid shell /data/local/tmp/frida-server &

sleep 2
echo "[*] Launching game..."
adb shell am start -n ${APP}/com.unity3d.player.UnityPlayerActivity

echo "[*] Waiting for process..."
until frida-ps -U | grep -q Daddy; do
    sleep 1
done

echo "Ready!"
