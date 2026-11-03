// 画面に依存しない日付・更新判定の処理。テストから直接呼べるよう main.dart から分けている。

/// calendar.json と assets/wallpapers/ の日付キー（MM-DD）。端末のローカル日付で引く。
String dayKey(DateTime date) =>
    '${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';

/// 次のローカル日付の 0 時までの時間。開いたまま日付が変わったときの再描画に使う。
/// DateTime(y, m, d + 1) は月末・年末・うるう日をまたいでも正しい翌日 0 時になる。
Duration untilNextDay(DateTime now) {
  final next = DateTime(now.year, now.month, now.day + 1);
  final wait = next.difference(now);
  // 夏時間などで負や 0 になる地域でも、すぐに再計算できる最小値にする。
  return wait > Duration.zero ? wait : const Duration(seconds: 1);
}

/// split-per-abi の APK は versionCode に 1000（armeabi-v7a）/ 2000（arm64-v8a）が足される。
/// version.json の build は pubspec.yaml の「+N」なので、1000 未満の部分だけで比べる。
int pubspecBuild(int versionCode) => versionCode % 1000;

/// 更新のお知らせを出すか。値は Android の UpdateChecker.check() が返す Map。
/// - latestBuild: Pages の version.json の build（取得失敗・未取得なら 0）
/// - currentBuild: 端末の versionCode（% 1000 済みでも、未処理でもよい）
/// - dismissedBuild: 「あとで」を押した版
bool shouldShowUpdate(Map<String, dynamic> update) {
  final latest = update['latestBuild'];
  if (latest is! int || latest <= 0) return false;
  final current = update['currentBuild'];
  // 端末の版が分からないときは誤って案内しない。
  if (current is! int) return false;
  if (latest <= pubspecBuild(current)) return false;
  return latest != (update['dismissedBuild'] as int? ?? 0);
}
