param([int]$Port = 8501)
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
python -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port $Port --server.headless true
