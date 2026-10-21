import 'dart:convert';
import 'dart:io';

import 'package:kyouha_nani/main.dart';
import 'package:flutter_test/flutter_test.dart';

// 収録データと壁紙画像がすべての日付でそろっていることを確かめる。
// アプリは日付ごとに calendar.json の項目と assets/wallpapers/MM-DD.webp を引くため、
// 1日でも欠けると「今日のページを準備しています」や壁紙の設定失敗になる。
void main() {
  final payload = jsonDecode(File('assets/data/calendar.json').readAsStringSync()) as Map<String, dynamic>;
  final entries = (payload['entries'] as List<dynamic>).cast<Map<String, dynamic>>();
  final leap = payload['leap_day'] as Map<String, dynamic>;
  String key(DateTime d) => '${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  test('うるう年の全366日に、ちょうど1件ずつ項目がある', () {
    final dates = [...entries.map((e) => e['date'] as String), leap['date'] as String];
    expect(dates.toSet().length, dates.length, reason: '同じ日付が重複している');
    final expected = <String>{
      for (var d = DateTime(2028, 1, 1); d.year == 2028; d = d.add(const Duration(days: 1))) key(d),
    };
    expect(dates.toSet(), expected);
  });

  test('すべての項目がアプリの読み込み処理で読め、本文と出典が空でない', () {
    for (final row in [...entries, leap]) {
      final entry = DayEntry.fromJson(row);
      expect(entry.title.trim(), isNotEmpty, reason: entry.date);
      expect(entry.summary.trim(), isNotEmpty, reason: entry.date);
      expect(entry.sources, isNotEmpty, reason: entry.date);
    }
  });

  test('すべての日付に端末内の壁紙画像がある', () {
    final missing = [
      for (final row in [...entries, leap])
        if (!File('assets/wallpapers/${row['date']}.webp').existsSync()) row['date'],
    ];
    expect(missing, isEmpty);
  });
}
