# Guard for the confirmed handover.  The other OpenCode session keeps
# re-running its daily step (run_one -> render -> upload) and even
# restored the deleted old renders from the sample folder - it would
# upload before the owner confirms and burn the daily cap.  This loop
# retires anything of that session inside the factory, never anything
# carrying "beethoven" (the confirmed pair), never this guard itself,
# never the confirm script, never the scheduled daily - and never
# anything after 09:45, when the 10:00 daily owns the machine.
while ($true) {
    $deadline = (Get-Date).Date.AddHours(9).AddMinutes(45)
    if ((Get-Date) -ge $deadline) { break }
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $c = $_.CommandLine
        if (-not $c) { return $false }
        if ($c -match '_hold_line|_confirm_and_upload|daily_local|daily_task') { return $false }
        if ($c -match 'run_one\.py') { return $true }
        if ($c -match 'upload\.py' -and $c -notmatch 'beethoven') { return $true }
        if ($c -match 'chess-repo.factory' -and $c -notmatch 'beethoven') { return $true }
        return $false
    } | ForEach-Object {
        try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch { }
    }
    Start-Sleep -Seconds 5
}
