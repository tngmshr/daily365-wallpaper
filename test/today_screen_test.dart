import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kyouha_nani/main.dart';

// 画面が「今日」の項目を出し、開いたまま／復帰で日付が変わったときに切り替わることを確かめる。
// 画面に文字で出るのは仕事メモ（work_tip）なので、それで日付を見分ける。
void main() {
  final payload = jsonDecode(File('assets/data/calendar.json').readAsStringSync()) as Map<String, dynamic>;
  final tips = <String, String>{
    for (final row in [...payload['entries'] as List<dynamic>, payload['leap_day']])
      (row as Map<String, dynamic>)['date'] as String: row['work_tip'] as String,
  };
  const channel = MethodChannel('daily365/wallpaper');
  Map<String, dynamic>? update;

  setUp(() {
    update = null;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(channel, (call) async {
      switch (call.method) {
        case 'status':
          return <String, dynamic>{'enabled': false};
        case 'checkUpdate':
          return update;
        default:
          return null;
      }
    });
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(channel, null);
  });

  Future<void> show(WidgetTester tester, DateTime Function() clock) async {
    // 壁紙（縦長）の下にある仕事メモまで一度に組み立てられるよう、縦に長い画面にする。
    tester.view.physicalSize = const Size(420, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(MaterialApp(home: TodayScreen(
      clock: clock,
      loadAsset: (path) async => File(path).readAsStringSync(),
      wallpaperUrl: (date) => Uri.parse('https://example.invalid/${date.year}.jpg'),
    )));
    await tester.pump();
    expect(find.byType(CircularProgressIndicator), findsNothing, reason: 'calendar.json を読み込めなかった');
  }

  Future<void> resume(WidgetTester tester) async {
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();
  }

  testWidgets('開いたまま 0 時を過ぎると、うるう日のページに替わる', (tester) async {
    var now = DateTime(2028, 2, 28, 23, 59, 58);
    await show(tester, () => now);
    expect(find.text(tips['02-28']!), findsOneWidget);

    now = DateTime(2028, 2, 29, 0, 0, 1);
    await tester.pump(const Duration(seconds: 3));
    expect(find.text(tips['02-29']!), findsOneWidget);
    expect(find.text(tips['02-28']!), findsNothing);
  });

  testWidgets('平年は 2/28 の次に 3/1 を出す', (tester) async {
    var now = DateTime(2027, 2, 28, 23, 59, 58);
    await show(tester, () => now);
    now = DateTime(2027, 3, 1, 0, 0, 1);
    await tester.pump(const Duration(seconds: 3));
    expect(find.text(tips['03-01']!), findsOneWidget);
  });

  testWidgets('大晦日に開いたまま年を越すと元日のページに替わる', (tester) async {
    var now = DateTime(2026, 12, 31, 23, 59, 59);
    await show(tester, () => now);
    expect(find.text(tips['12-31']!), findsOneWidget);

    now = DateTime(2027, 1, 1, 0, 0, 1);
    await tester.pump(const Duration(seconds: 2));
    expect(find.text(tips['01-01']!), findsOneWidget);
  });

  testWidgets('前日に開いたまま裏に回し、翌朝に復帰すると今日のページを出す', (tester) async {
    // Web（iPhone のホーム画面）と同じく、端末側から状態が返らない場合。
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(channel, (call) async => null);
    var now = DateTime(2027, 2, 3, 22);
    await show(tester, () => now);
    expect(find.text(tips['02-03']!), findsOneWidget);

    // タイマーが止まっていた（端末のスリープなど）想定で、時刻だけ進めて復帰させる。
    now = DateTime(2027, 2, 4, 7);
    await resume(tester);
    expect(find.text(tips['02-04']!), findsOneWidget);
  });

  // 年別の内容。2026 年は 4 年目（slot4）、2028 年は slot2、2029 年は立春が 02-03 に移る。
  final slot4 = jsonDecode(File('assets/data/years/slot4.json').readAsStringSync()) as Map<String, dynamic>;
  final slot2 = jsonDecode(File('assets/data/years/slot2.json').readAsStringSync()) as Map<String, dynamic>;
  final titles = <String, String>{
    for (final row in [...payload['entries'] as List<dynamic>, payload['leap_day']])
      (row as Map<String, dynamic>)['date'] as String: row['title'] as String,
  };
  Finder baseImage(String key) => find.byWidgetPredicate((w) =>
      w is Image && w.image is AssetImage && (w.image as AssetImage).assetName == 'assets/wallpapers/$key.webp');
  final textCard = find.byKey(const ValueKey('wallpaper-text-card'));

  testWidgets('差し替えのない日は同梱の壁紙を出す', (tester) async {
    await show(tester, () => DateTime(2027, 5, 1, 12));
    expect(baseImage('05-01'), findsOneWidget);
    expect(textCard, findsNothing);
  });

  testWidgets('2026 年（4 年目）の差し替え日は slot4 の内容を出し、1 年目の壁紙は出さない', (tester) async {
    final key = (slot4.keys.toList()..sort()).last; // 年内に残る日（12-18）
    final row = slot4[key] as Map<String, dynamic>;
    final parts = key.split('-').map(int.parse).toList();
    await show(tester, () => DateTime(2026, parts[0], parts[1], 9));
    expect(find.text(row['work_tip'] as String), findsOneWidget);
    expect(find.text(tips[key]!), findsNothing);
    expect(baseImage(key), findsNothing);
    // 年別の壁紙を読めない（テストではネットにつながらない）ので、正しい文章のカードを出す。
    await tester.pump();
    expect(textCard, findsOneWidget);
    expect(find.text(row['title'] as String), findsOneWidget);
  });

  testWidgets('2028 年は slot2 の差し替えを出す', (tester) async {
    final row = slot2['01-24'] as Map<String, dynamic>;
    await show(tester, () => DateTime(2028, 1, 24, 9));
    expect(find.text(row['work_tip'] as String), findsOneWidget);
    expect(find.text(tips['01-24']!), findsNothing);
  });

  testWidgets('2029 年は立春が 02-03、もとの 02-03 の題材は 02-04 に移る', (tester) async {
    var now = DateTime(2029, 2, 3, 9);
    await show(tester, () => now);
    await tester.pump(); // 年別の壁紙が読めず、文章のカードに替わる
    expect(find.text(tips['02-04']!), findsOneWidget); // 立春の仕事メモ
    expect(find.textContaining('2月3日'), findsOneWidget);
    expect(find.text(titles['02-04']!), findsOneWidget);

    now = DateTime(2029, 2, 4, 9);
    await resume(tester);
    await tester.pump();
    expect(find.text(tips['02-03']!), findsOneWidget);
    expect(find.text(titles['02-03']!), findsOneWidget);
    expect(find.textContaining('2月4日'), findsOneWidget);
  });

  testWidgets('arm64 版（versionCode 2008）で version.json が 9 ならお知らせを出す', (tester) async {
    update = {'currentBuild': 2008, 'latestBuild': 9, 'latestVersion': '1.3.3', 'notes': <String>[]};
    await show(tester, () => DateTime(2027, 5, 1, 12));
    expect(find.text('新しい版 v1.3.3 があります'), findsOneWidget);
  });

  testWidgets('同じ版（versionCode 1008 と build 8）ではお知らせを出さない', (tester) async {
    update = {'currentBuild': 1008, 'latestBuild': 8, 'latestVersion': '1.3.2', 'notes': <String>[]};
    await show(tester, () => DateTime(2027, 5, 1, 12));
    expect(find.textContaining('新しい版'), findsNothing);
  });

  testWidgets('version.json を取得できない（null・例外）ときもページは出る', (tester) async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(channel, (call) async {
      if (call.method == 'checkUpdate') throw PlatformException(code: 'offline');
      return null;
    });
    await show(tester, () => DateTime(2027, 5, 1, 12));
    expect(find.text(tips['05-01']!), findsOneWidget);
    expect(find.textContaining('新しい版'), findsNothing);
  });
}
