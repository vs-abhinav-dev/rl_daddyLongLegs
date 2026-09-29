#!/usr/bin/env bash
set -e

waydroid session stop
sleep 1

adb disconnect
sleep 1

adb kill-server
