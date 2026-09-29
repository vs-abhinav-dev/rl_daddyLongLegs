#!/usr/bin/env bash
set -e

waydroid session stop
sudo systemctl stop waydroid-container
sudo waydroid container stop
sudo systemctl start waydroid-container


killall adb 
