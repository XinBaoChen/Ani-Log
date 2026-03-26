$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:8010'

$startBody = @{
  title = 'MVP Perf Verification'
  fps = 6
  source = 'screen'
  performance_mode = $true
  adaptive_keyframes = $true
} | ConvertTo-Json

$start = Invoke-RestMethod -Uri ($base + '/api/capture/start') -Method Post -ContentType 'application/json' -Body $startBody
$sid = $start.session_id

Start-Sleep -Seconds 120

$stop = Invoke-RestMethod -Uri ($base + '/api/capture/stop') -Method Post
$session = Invoke-RestMethod -Uri ($base + '/api/sessions/' + $sid)
$scenes = Invoke-RestMethod -Uri ($base + '/api/sessions/' + $sid + '/scenes')
$chars = Invoke-RestMethod -Uri ($base + '/api/characters?sort_by=appearance_count&limit=200')

$elapsed = ([datetime]$session.ended_at) - ([datetime]$session.started_at)
$runtimeSec = [Math]::Max(1.0, $elapsed.TotalSeconds)
$effectiveFps = $session.total_frames / $runtimeSec
$sceneCount = @($scenes).Count

$autoChars = @($chars | Where-Object { $_.name -like 'Detected Character*' })
$uniqueAutoNames = @($autoChars | Select-Object -ExpandProperty name -Unique)
$dupNameCount = [Math]::Max(0, $autoChars.Count - $uniqueAutoNames.Count)
$persistentChars = @($chars | Where-Object { $_.appearance_count -ge 3 }).Count

Write-Output ('SID={0}' -f $sid)
Write-Output ('RuntimeSec={0:N1}; Frames={1}; SceneRows={2}; EffectiveFPS={3:N2}' -f $runtimeSec, $session.total_frames, $sceneCount, $effectiveFps)
Write-Output ('AutoChars={0}; AutoNameDuplicates={1}; PersistentChars(appearance>=3)={2}' -f $autoChars.Count, $dupNameCount, $persistentChars)
Write-Output ('CaptureStopMessage={0}' -f $stop.message)
