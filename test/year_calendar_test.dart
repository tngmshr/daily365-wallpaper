import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:kyouha_nani/year_calendar.dart';

// アプリの年の解決（lib/year_calendar.dart）が tools/build_year.py と同じ結果になることを確かめる。
// Pages の年別壁紙は Python 側で作るので、ずれるとアプリ画面とロック画面の内容が食い違う。
void main() {
  late YearCalendar calendar;

  setUpAll(() async {
    calendar = await YearCalendar.load((path) async => File(path).readAsStringSync());
  });

  test('2027 年が 1 年目で、4 年で一巡する。2026 年以前は 1 年目のまま', () {
    expect([for (var y = 2024; y <= 2031; y++) YearCalendar.slotFor(y)], [1, 1, 1, 1, 2, 3, 4, 1]);
  });

  test('2026 年は全日が同梱データと同じ（同梱の壁紙を使う）', () {
    for (final key in calendar.base.keys.where((k) => k != '02-29')) {
      final parts = key.split('-').map(int.parse).toList();
      expect(calendar.entryFor(DateTime(2026, parts[0], parts[1]))!.sameAsBase, isTrue, reason: key);
    }
  });

  test('平年は 365 件、うるう年は 02-29 を含む 366 件', () {
    expect(calendar.resolve(2027).length, 365);
    expect(calendar.resolve(2028).length, 366);
    expect(calendar.resolve(2100).containsKey('02-29'), isFalse);
    expect(calendar.resolve(2400).containsKey('02-29'), isTrue);
  });

  test('1 年目は同梱データと同じで、壁紙も同梱のものを使う', () {
    for (final key in calendar.base.keys.where((k) => k != '02-29')) {
      final parts = key.split('-').map(int.parse).toList();
      expect(calendar.entryFor(DateTime(2027, parts[0], parts[1]))!.sameAsBase, isTrue, reason: key);
    }
  });

  test('ファイルが無ければ 1 年目の内容のまま動く', () async {
    final onlyBase = await YearCalendar.load((path) async {
      if (path.endsWith('calendar.json')) return File(path).readAsStringSync();
      throw const FileSystemException('missing');
    });
    expect(onlyBase.entryFor(DateTime(2028, 1, 24))!.sameAsBase, isTrue);
  });

  final python = ['python3', 'python'].firstWhere(
    (name) {
      try {
        return Process.runSync(name, ['--version']).exitCode == 0;
      } catch (_) {
        return false;
      }
    },
    orElse: () => '',
  );

  test('2026〜2034 年の解決結果が tools/build_year.py と一致する', () {
    final dir = Directory.systemTemp.createTempSync('year_calendar');
    addTearDown(() => dir.deleteSync(recursive: true));
    for (var year = 2026; year <= 2034; year++) {
      final out = '${dir.path}/$year.json';
      final result = Process.runSync(python, ['tools/build_year.py', '--year', '$year', '--out', out]);
      expect(result.exitCode, 0, reason: '${result.stderr}');
      final payload = jsonDecode(File(out).readAsStringSync()) as Map<String, dynamic>;
      final expected = <String, dynamic>{
        for (final row in [...payload['entries'] as List<dynamic>, ?payload['leap_day']])
          (row as Map<String, dynamic>)['date'] as String: row,
      };
      expect(jsonEncode(_sorted(calendar.resolve(year))), jsonEncode(_sorted(expected)), reason: '$year');
    }
  }, skip: python.isEmpty ? 'Python が無い環境では突き合わせを省略' : false);
}

Object? _sorted(Object? value) => switch (value) {
  Map() => {for (final key in (value.keys.map((k) => '$k').toList()..sort())) key: _sorted(value[key])},
  List() => value.map(_sorted).toList(),
  _ => value,
};
