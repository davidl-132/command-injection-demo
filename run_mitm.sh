#!/bin/bash
cd "$(dirname "$0")"
/home/ly_tran_gia_khang/is/web/.venv/bin/mitmweb -s mitm_addon_dns.py
