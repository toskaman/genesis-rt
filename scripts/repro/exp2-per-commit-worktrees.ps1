# Rebuild genesis_guard from the exact sources of two commits; compare to published digests.
$ErrorActionPreference = 'Continue'
$repo = 'C:\Users\TheBox\Desktop\QNX-hackaton\genesis-rt'
$qcc = 'E:\qnx800\host\win64\x86_64\usr\bin\qcc.exe'
$gen = "$repo\artifacts\runs\op-24fecbf11df8\gen"
$root = 'C:\Users\TheBox\Desktop\QNX-hackaton\repro2'
Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue
$want = @{ 'a465e7f' = 'b65afcb42e9830952426526947047045c93c417df64aa2261c08f8b9bf6560c9'; 'e439276' = 'f92f5e66b321f9acba7e2d48c6f97f01446a1cd37506e7897a366d1128924ae8' }
foreach ($c in 'a465e7f','e439276') {
  foreach ($run in 1,2) {
    $d = "$root\$c-run$run-" + ('x' * $run * 3)
    Push-Location $repo
    git worktree add --detach $d $c 2>&1 | Out-Null
    Pop-Location
    Copy-Item "$gen\genesis_config_gen.h" "$d\"
    Push-Location $d
    & $qcc -Vgcc_ntox86_64 -O2 -Wall -Wextra "-I$d\target\qnx8\include" "-I$d\target\qnx8\common" -I. -o genesis_guard "$d\target\qnx8\common\guard_policy.c" "$d\target\qnx8\guard\genesis_guard.c" -lm 2>&1 | Out-Null
    Pop-Location
    $h = (Get-FileHash "$d\genesis_guard" -Algorithm SHA256).Hash.ToLower()
    $ok = if ($h -eq $want[$c]) { 'MATCHES published' } else { 'differs from published ' + $want[$c].Substring(0,12) }
    "$c run$run  $($h.Substring(0,16))  $ok"
    Push-Location $repo; git worktree remove --force $d 2>&1 | Out-Null; Pop-Location
  }
}
