#!/bin/bash
cd "$(dirname "$0")"
bash scripts/start-hive.sh
echo ""
read -p "Bu pencereyi kapatmak için Enter'a basın (HIVE arka planda çalışmaya devam eder)..."
