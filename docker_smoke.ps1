param(
  [string]$DashboardUrl = 'http://localhost:3001',
  [switch]$NoBuild,
  [switch]$IncludeML,
  [switch]$SkipComposeUp
)

$ErrorActionPreference = 'Stop'

function Assert-Status200 {
  param(
    [string]$Label,
    [string]$Url
  )
  $res = Invoke-WebRequest -UseBasicParsing -Uri $Url -MaximumRedirection 5 -TimeoutSec 20
  if ($res.StatusCode -ne 200) {
    throw "[$Label] Expected 200 from $Url but got $($res.StatusCode)"
  }
  Write-Output ("[ok] {0} -> {1}" -f $Label, $res.StatusCode)
  return $res
}

function Wait-Status200 {
  param(
    [string]$Label,
    [string]$Url,
    [int]$TimeoutSeconds = 45
  )
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    try {
      $res = Invoke-WebRequest -UseBasicParsing -Uri $Url -MaximumRedirection 2 -TimeoutSec 5
      if ($res.StatusCode -eq 200) {
        Write-Output ("[ok] {0} ready -> {1}" -f $Label, $res.StatusCode)
        return
      }
    } catch {
      # keep polling until timeout
    }
    Start-Sleep -Milliseconds 1000
  } while ((Get-Date) -lt $deadline)

  throw "[$Label] Timed out waiting for 200 from $Url"
}

if (-not $SkipComposeUp) {
  $composeCmd = 'docker compose'
  if ($IncludeML) {
    $composeCmd += ' --profile ml'
  }
  $composeCmd += ' up -d'
  if (-not $NoBuild) {
    $composeCmd += ' --build'
  }
  $composeCmd += ' backend frontend'

  Write-Output "[smoke] Starting Docker services"
  Write-Output ("[smoke] Running: {0}" -f $composeCmd)
  Invoke-Expression $composeCmd
  if ($LASTEXITCODE -ne 0) {
    throw "docker compose up failed"
  }
} else {
  Write-Output '[smoke] SkipComposeUp enabled; verifying existing running containers only'
}

$apiBase = "$DashboardUrl/api"

Write-Output "[smoke] Waiting for dashboard and API"
Wait-Status200 -Label 'dashboard-home' -Url "$DashboardUrl/"
Wait-Status200 -Label 'api-sessions' -Url "$apiBase/sessions"

Write-Output "[smoke] UI route checks"
$null = Assert-Status200 -Label 'home-page' -Url "$DashboardUrl/"
$null = Assert-Status200 -Label 'sessions-page' -Url "$DashboardUrl/sessions"
$null = Assert-Status200 -Label 'search-page' -Url "$DashboardUrl/search"
$null = Assert-Status200 -Label 'capture-page' -Url "$DashboardUrl/capture"

Write-Output "[smoke] API checks through frontend proxy"
$null = Assert-Status200 -Label 'capture-status' -Url "$apiBase/capture/status"
$null = Assert-Status200 -Label 'sessions-list' -Url "$apiBase/sessions"
$null = Assert-Status200 -Label 'scenes-list' -Url "$apiBase/scenes"
$null = Assert-Status200 -Label 'characters-list' -Url "$apiBase/characters"
$null = Assert-Status200 -Label 'summary-list' -Url "$apiBase/summary"
$null = Assert-Status200 -Label 'search-hybrid' -Url "$apiBase/search?q=eren&mode=hybrid&min_score=0.3"
$null = Assert-Status200 -Label 'search-semantic' -Url "$apiBase/search?q=eren&mode=semantic&min_score=0.3"
$null = Assert-Status200 -Label 'search-keyword' -Url "$apiBase/search?q=eren&mode=keyword&min_score=0.3"

Write-Output "[smoke] Session visibility and data continuity"
$sessions = @(Invoke-RestMethod -Uri "$apiBase/sessions")
$sessionsCount = $sessions.Count
if ($sessionsCount -lt 1) {
  throw "No sessions returned by $apiBase/sessions"
}
Write-Output ("[ok] sessions_count={0}" -f $sessionsCount)
Write-Output ("[info] latest_session_id={0}; title={1}" -f $sessions[0].id, $sessions[0].title)

Write-Output "[smoke] Capture action flow (mirrors Capture page controls)"
$startBody = @{
  title = 'Docker Smoke Verification'
  fps = 2
  source = 'screen'
  performance_mode = $false
  adaptive_keyframes = $false
} | ConvertTo-Json

$start = Invoke-RestMethod -Method Post -Uri "$apiBase/capture/start" -ContentType 'application/json' -Body $startBody
if (-not $start.session_id) {
  throw 'Capture start did not return session_id'
}
$sid = [string]$start.session_id
Write-Output ("[ok] capture_start session_id={0}" -f $sid)

$status = Invoke-RestMethod -Uri "$apiBase/capture/status"
Write-Output ("[info] capture_status state={0}; total={1}; skipped={2}; errors={3}; effective_fps={4}" -f $status.status, $status.total_frames, $status.skipped_frames, $status.error_frames, $status.effective_fps)

$stop = Invoke-RestMethod -Method Post -Uri "$apiBase/capture/stop"
Write-Output ("[ok] capture_stop state={0}; total={1}; skipped={2}; errors={3}; effective_fps={4}" -f $stop.status, $stop.total_frames, $stop.skipped_frames, $stop.error_frames, $stop.effective_fps)

$sessionDetail = Invoke-RestMethod -Uri "$apiBase/sessions/$sid"
$sessionScenes = @(Invoke-RestMethod -Uri "$apiBase/sessions/$sid/scenes")
Write-Output ("[ok] session_detail id={0}; scene_count={1}; returned_scene_rows={2}" -f $sessionDetail.id, $sessionDetail.scene_count, $sessionScenes.Count)

Write-Output "[smoke] Story Arc action flow (mirrors Story Arc buttons)"
$summaryBody = @{ session_id = $sid } | ConvertTo-Json
$generated = Invoke-RestMethod -Method Post -Uri "$apiBase/summary/generate" -ContentType 'application/json' -Body $summaryBody
if (-not $generated.id) {
  throw 'Summary generate did not return id'
}
$filtered = @(Invoke-RestMethod -Uri "$apiBase/summary?session_id=$sid")
if ($filtered.Count -lt 1) {
  throw "No summary rows returned for session_id=$sid"
}
Write-Output ("[ok] summary_generated id={0}; filtered_count={1}" -f $generated.id, $filtered.Count)

Write-Output "[smoke] PASS: Docker dashboard and proxied API actions validated end-to-end"
Write-Output ("[smoke] Dashboard URL: {0}" -f $DashboardUrl)
Write-Output '[smoke] Keep services running for manual UI checks in browser.'
