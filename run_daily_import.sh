#!/bin/zsh
cd /Users/nicholasdrennan/Desktop/tcg-price-tracker
/Users/nicholasdrennan/Desktop/tcg-price-tracker/venv/bin/python import_market_history.py >> logs/daily_import.log 2>> logs/daily_import_error.log
