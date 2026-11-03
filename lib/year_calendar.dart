// 年ごとの暦（2〜4 年目の差し替えと、年で日付が動く節気）を解決する。
// tools/build_year.py の resolve_year と同じ規則。Pages の wallpapers/YYYY/ もこの規則で作られるので、
// アプリ画面とロック画面（Android の年別画像・iPhone のショートカット）の内容がそろう。
// 規則を変えるときは両方を直す（test/year_calendar_test.dart が Python の出力と突き合わせる）。

import 'dart:convert';

import 'day_logic.dart';

typedef JsonRow = Map<String, dynamic>;

class YearCalendar {
  YearCalendar({required this.base, required this.slots, required this.solarTerms});

  /// assets/data/ の各ファイルを読む。slot ファイルや solar_terms.json が無ければ 1 年目のまま使う。
  static Future<YearCalendar> load(Future<String> Function(String path) read) async {
    final payload = jsonDecode(await read('assets/data/calendar.json')) as JsonRow;
    final base = <String, JsonRow>{
      for (final row in payload['entries'] as List<dynamic>) (row as JsonRow)['date'] as String: row,
    };
    final leap = payload['leap_day'];
    if (leap is JsonRow) base[leap['date'] as String] = leap;

    Future<JsonRow> optional(String path) async {
      try {
        return jsonDecode(await read(path)) as JsonRow;
      } catch (_) {
        return const {};
      }
    }

    return YearCalendar(
      base: base,
      slots: {for (final slot in const [2, 3, 4]) slot: await optional('assets/data/years/slot$slot.json')},
      solarTerms: await optional('assets/data/solar_terms.json'),
    );
  }

  final Map<String, JsonRow> base;
  final Map<int, JsonRow> slots;
  final JsonRow solarTerms;
  final Map<int, Map<String, JsonRow>> _years = {};

  /// 2027 年が 1 年目。4 年で一巡し、2026 年は 4 年目にあたる（Python と同じ計算）。
  static int slotFor(int year) => (year - 2027) % 4 + 1;

  static bool isLeap(int year) => year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);

  /// その日の項目。1 年目と同じ内容かどうかも返す（同じなら同梱の壁紙をそのまま使える）。
  ({JsonRow entry, bool sameAsBase})? entryFor(DateTime date) {
    final key = dayKey(date);
    final entry = resolve(date.year)[key];
    if (entry == null) return null;
    return (entry: entry, sameAsBase: _sameJson(entry, base[key]));
  }

  /// その年の全項目（日付 → 項目）。平年は 02-29 を含まない。
  Map<String, JsonRow> resolve(int year) => _years.putIfAbsent(year, () => _resolve(year));

  Map<String, JsonRow> _resolve(int year) {
    final rows = <String, JsonRow>{for (final e in base.entries) e.key: Map<String, dynamic>.of(e.value)};
    final slot = slotFor(year);
    if (slot != 1) {
      (slots[slot] ?? const {}).forEach((key, replacement) {
        // 壊れた差し替えは使わず、1 年目の内容を残す（build_year.py ではエラーで公開前に止まる）。
        if (!rows.containsKey(key) || replacement is! JsonRow) return;
        if ((replacement['date'] ?? key) != key) return;
        rows[key] = {...replacement, 'date': key};
      });
    }

    final dates = solarTerms['$year'];
    if (dates is JsonRow) {
      final terms = [
        for (final row in rows.values)
          if (row['solar_term'] is String) row['solar_term'] as String,
      ];
      final targets = [for (final term in terms) if (dates[term] is String) dates[term] as String];
      if (terms.toSet().length == terms.length && targets.toSet().length == targets.length) {
        for (final term in terms) {
          final target = dates[term];
          if (target is! String) continue;
          if (!rows.containsKey(target) || (target == '02-29' && !isLeap(year))) continue;
          final source = rows.entries.firstWhere((e) => e['solar_term'] == term).key;
          if (source == target) continue;
          for (final key in [source, target]) {
            rows[key]!.putIfAbsent('illustration_date', () => rows[key]!['date']);
          }
          final moved = rows[source]!;
          rows[source] = rows[target]!..['date'] = source;
          rows[target] = moved..['date'] = target;
        }
      }
    }

    if (!isLeap(year)) rows.remove('02-29');
    return rows;
  }

  static bool _sameJson(Object? a, Object? b) => jsonEncode(a) == jsonEncode(b);
}

extension on MapEntry<String, JsonRow> {
  Object? operator [](String key) => value[key];
}
