param([string]$PostgresBin = 'C:\Program Files\PostgreSQL\18\bin')
$projectRoot = Split-Path -Parent $PSScriptRoot
$clusterPath = Join-Path $projectRoot '.local/postgres'
$logPath = Join-Path $projectRoot '.local/postgres.log'
if (!(Test-Path -LiteralPath $clusterPath)) {
    New-Item -ItemType Directory -Force (Join-Path $projectRoot '.local') | Out-Null
    & (Join-Path $PostgresBin 'initdb.exe') -D $clusterPath -U credora --auth=trust --encoding=UTF8 --locale=C
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL initialisation failed' }
}
& (Join-Path $PostgresBin 'pg_ctl.exe') -D $clusterPath -l $logPath -o '-h 127.0.0.1 -p 6543' -w start
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL startup failed or server already running' }
& (Join-Path $PostgresBin 'psql.exe') -h 127.0.0.1 -p 6543 -U credora -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='credora'" | ForEach-Object { $script:dbExists = $_.Trim() }
if ($script:dbExists -ne '1') {
    & (Join-Path $PostgresBin 'createdb.exe') -h 127.0.0.1 -p 6543 -U credora credora
}
Write-Output 'Set CREDORA_DATABASE_URL=postgresql://credora@127.0.0.1:6543/credora'
