@echo off
rem Connecteur agent cvlynk (Multi-Agent Orchestrator)
set PYTHON="C:\Users\AKE\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
cd /d "%~dp0"
title Agent cvlynk - api.cvlynk.com
%PYTHON% cvlynk_agent.py
pause
