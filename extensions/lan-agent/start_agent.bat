@echo off
rem ---------------------------------------------------------------
rem  Lance l'agent LAN (port 8010) et l'enregistre aupres de
rem  l'orchestrateur 192.168.1.35:8000
rem ---------------------------------------------------------------
set PYTHON="C:\Users\AKE\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
cd /d "%~dp0"
title Agent LAN 8010 - orchestrateur 192.168.1.35
%PYTHON% agent.py --register --port 8010
pause
