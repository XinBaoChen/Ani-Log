param(
  [string]$BaseUrl = 'http://127.0.0.1:8000',
  [int]$StatusPolls = 40
)

$ErrorActionPreference = 'Stop'

function Assert-Status200 {
  param([string]$Url)
  $res = Invoke-WebRequest -UseBasicParsing -Uri $Url -MaximumRedirection 5
  if ($res.StatusCode -ne 200) {
    throw "Expected 200 from $Url but got $($res.StatusCode)"
  }
  return $res
}

Write-Output "[smoke] Checking core endpoints on $BaseUrl"
$null = Assert-Status200 "$BaseUrl/api/capture/status"
$null = Assert-Status200 "$BaseUrl/api/sessions"
$null = Assert-Status200 "$BaseUrl/api/scenes"
$null = Assert-Status200 "$BaseUrl/api/summary"
$null = Assert-Status200 "$BaseUrl/api/characters"

$beforeSessions = @(Invoke-RestMethod -Uri "$BaseUrl/api/sessions").Count

$body = @{
  title = 'Manual Smoke Verification'
  fps = 2
  source = 'screen'
  performance_mode = $false
  adaptive_keyframes = $false
} | ConvertTo-Json

Write-Output "[smoke] Starting capture"
$start = Invoke-RestMethod -Uri "$BaseUrl/api/capture/start" -Method Post -ContentType 'application/json' -Body $body
$sid = $start.session_id

$observedFrames = 0
$observedSkipped = 0
$observedErrors = 0
$observedEffFps = 0.0
for ($i = 0; $i -lt $StatusPolls; $i++) {
  $status = Invoke-RestMethod -Uri "$BaseUrl/api/capture/status"
  $observedFrames = [int]$status.total_frames
  $observedSkipped = [int]($status.skipped_frames)
  $observedErrors = [int]($status.error_frames)
  $observedEffFps = [double]($status.effective_fps)
  if ($observedFrames -ge 1) { break }
}

Write-Output "[smoke] Stopping capture"
$stop = Invoke-RestMethod -Uri "$BaseUrl/api/capture/stop" -Method Post
$session = $null
$sceneRows = 0
for ($i = 0; $i -lt 10; $i++) {
  $session = Invoke-RestMethod -Uri "$BaseUrl/api/sessions/$sid"
  $sceneRows = @(Invoke-RestMethod -Uri "$BaseUrl/api/sessions/$sid/scenes").Count
  if ([int]$session.scene_count -eq $sceneRows) { break }
}
$afterSessions = @(Invoke-RestMethod -Uri "$BaseUrl/api/sessions").Count

Write-Output "[smoke] Complete"
Write-Output ("session_id={0}" -f $sid)
Write-Output ("before_sessions={0}; after_sessions={1}" -f $beforeSessions, $afterSessions)
Write-Output ("observed_frames={0}; observed_skipped={1}; observed_errors={2}; observed_effective_fps={3}" -f $observedFrames, $observedSkipped, $observedErrors, $observedEffFps)
Write-Output ("session_scene_count={0}; scene_rows={1}" -f $session.scene_count, $sceneRows)
Write-Output ("stop_status={0}; stop_total={1}; stop_skipped={2}; stop_errors={3}; stop_effective_fps={4}" -f $stop.status, $stop.total_frames, $stop.skipped_frames, $stop.error_frames, $stop.effective_fps)
