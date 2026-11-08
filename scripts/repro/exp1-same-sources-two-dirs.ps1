# Controlled qcc reproducibility experiment (GENESIS RT guard binary).
$ErrorActionPreference = 'Continue'
$repo = 'C:\Users\TheBox\Desktop\QNX-hackaton\genesis-rt'
$src = "$repo\target\qnx8"
$qcc = 'E:\qnx800\host\win64\x86_64\usr\bin\qcc.exe'
$ver = (& $qcc -V 2>&1 | Out-String)
"qcc: " + ($ver -split "`n" | Select-String default | Out-String).Trim()
$gen = "$repo\artifacts\runs\op-24fecbf11df8\gen"
$root = 'C:\Users\TheBox\Desktop\QNX-hackaton\repro'
Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue
function B($name, $dir, [string[]]$extra) {
  New-Item -ItemType Directory -Force $dir | Out-Null
  Copy-Item "$gen\genesis_config_gen.h" $dir
  Push-Location $dir
  $args = @('-Vgcc_ntox86_64','-O2','-Wall','-Wextra',"-I$src\include","-I$src\common",'-I.') + $extra + @('-o','genesis_guard',"$src\common\guard_policy.c","$src\guard\genesis_guard.c",'-lm')
  & $qcc @args 2>&1 | Out-Null
  Pop-Location
  $h = (Get-FileHash "$dir\genesis_guard" -Algorithm SHA256).Hash.ToLower()
  "{0,-34} {1}  {2} bytes" -f $name, $h.Substring(0,16), (Get-Item "$dir\genesis_guard").Length
  return $h
}
"== baseline flags (as shipped)"
$a1 = B 'A1 same dir, run 1' "$root\a" @()
Copy-Item "$root\a\genesis_guard" "$root\a1.bin"
$a2 = B 'A2 same dir, run 2' "$root\a" @()
$b  = B 'B  different dir'   "$root\bbbbbbbb" @()
"same-dir identical: " + ($a1 -eq $a2) + "   cross-dir identical: " + ($a1 -eq $b)
# locate differing bytes A vs B
$x=[IO.File]::ReadAllBytes("$root\a1.bin"); $y=[IO.File]::ReadAllBytes("$root\bbbbbbbb\genesis_guard")
$n=[Math]::Min($x.Length,$y.Length); $d=0; for($i=0;$i -lt $n;$i++){ if($x[$i] -ne $y[$i]){$d++} }
"differing bytes A vs B: $d (len $($x.Length) vs $($y.Length))"
$s = [Text.Encoding]::ASCII.GetString($x)
"embedded host paths in A: " + (([regex]::Matches($s,'[A-Za-z]:[\\/][ -~]{4,120}') | ForEach-Object Value | Select-Object -Unique) -join ' | ')
"== candidate fix: -ffile-prefix-map + no build-id"
$fx = @("-ffile-prefix-map=$src=/genesis","-ffile-prefix-map=$root=/build",'-Wl,--build-id=none')
$c1 = B 'C1 fixed flags, dir a2' "$root\a2" $fx
$c2 = B 'C2 fixed flags, dir other' "$root\zz-other-path" $fx
"fixed cross-dir identical: " + ($c1 -eq $c2)
$s2 = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes("$root\a2\genesis_guard"))
"embedded host paths with fix: " + (([regex]::Matches($s2,'[A-Za-z]:[\\/][ -~]{4,120}') | ForEach-Object Value | Select-Object -Unique) -join ' | ')
"== behaviour-neutral check: section sizes"
$od = 'E:\qnx800\host\win64\x86_64\usr\bin\ntox86_64-size.exe'
if (Test-Path $od) { & $od "$root\a1.bin" "$root\a2\genesis_guard" 2>&1 | Out-String }
