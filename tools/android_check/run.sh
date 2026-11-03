#!/usr/bin/env bash
# Android の YearRotation.kt を tools/build_year.py と突き合わせ、Kotlin のソースが
# Android API に対してコンパイルできることを確かめる（Android SDK・Gradle なしで動く）。
#
#   bash tools/android_check/run.sh
#
# 必要なもの: Java 17 以上、Python 3、ネット（初回だけ Kotlin コンパイラと
# Robolectric の android-all.jar（約 190MB）を ~/.cache/daily365-android-check に取得）。
# androidx.work は WorkStubs.kt の最小限の宣言で代用する（コンパイル確認だけに使う）。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/daily365-android-check"
KOTLIN=2.2.20
ANDROID_ALL=15-robolectric-13954326
mkdir -p "$CACHE"
if [ ! -x "$CACHE/kotlinc/bin/kotlinc" ]; then
  curl -fsSL -o "$CACHE/kotlinc.zip" "https://github.com/JetBrains/kotlin/releases/download/v$KOTLIN/kotlin-compiler-$KOTLIN.zip"
  unzip -q -o "$CACHE/kotlinc.zip" -d "$CACHE"
fi
if [ ! -f "$CACHE/android-all.jar" ]; then
  curl -fsSL -o "$CACHE/android-all.jar" \
    "https://repo.maven.apache.org/maven2/org/robolectric/android-all/$ANDROID_ALL/android-all-$ANDROID_ALL.jar"
fi
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
for year in $(seq 2025 2034); do
  python3 "$ROOT/tools/build_year.py" --year "$year" --out "$WORK/py/$year.json" >/dev/null 2>&1
done
KT="$ROOT/android/app/src/main/kotlin/jp/nichimekuri/kyouha_nani"
# MainActivity は Flutter の embedding が要るので除く。
"$CACHE/kotlinc/bin/kotlinc" -jvm-target 17 -nowarn -cp "$CACHE/android-all.jar" \
  "$KT/YearRotation.kt" "$KT/WallpaperCard.kt" "$KT/DailyWallpaperScheduler.kt" "$KT/UpdateChecker.kt" \
  "$ROOT/tools/android_check/WorkStubs.kt" "$ROOT/tools/android_check/YearRotationCheck.kt" -d "$WORK/out"
java -cp "$WORK/out:$CACHE/kotlinc/lib/kotlin-stdlib.jar:$CACHE/android-all.jar" YearRotationCheckKt "$ROOT" "$WORK/py"
