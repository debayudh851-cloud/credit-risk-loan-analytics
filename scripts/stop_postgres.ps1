param([string]$PostgresBin = 'C:\Program Files\PostgreSQL\18\bin')
$projectRoot = Split-Path -Parent $PSScriptRoot
& (Join-Path $PostgresBin 'pg_ctl.exe') -D (Join-Path $projectRoot '.local/postgres') -m fast -w stop
