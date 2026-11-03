import 'package:flutter_test/flutter_test.dart';
import 'package:kyouha_nani/day_logic.dart';

void main() {
  group('dayKey', () {
    test('月と日を2桁にそろえる', () {
      expect(dayKey(DateTime(2027, 1, 1)), '01-01');
      expect(dayKey(DateTime(2027, 12, 31, 23, 59, 59)), '12-31');
    });

    test('うるう年だけ 02-29 を引き、平年は 02-28 の翌日が 03-01', () {
      expect(dayKey(DateTime(2028, 2, 29)), '02-29');
      expect(dayKey(DateTime(2027, 2, 28).add(const Duration(days: 1))), '03-01');
      expect(dayKey(DateTime(2028, 2, 28).add(const Duration(days: 1))), '02-29');
      // 2100 年は 4 で割り切れるが平年。
      expect(dayKey(DateTime(2100, 2, 28).add(const Duration(days: 1))), '03-01');
      // 平年に 2/29 を作ると Dart は 3/1 に繰り上げる（02-29 の内容を誤って出さない）。
      expect(dayKey(DateTime(2027, 2, 29)), '03-01');
    });
  });

  group('untilNextDay', () {
    test('年末から元日 0 時まで', () {
      expect(untilNextDay(DateTime(2026, 12, 31, 23, 59, 30)), const Duration(seconds: 30));
    });

    test('うるう日の前日と、うるう日から 3 月へ', () {
      expect(untilNextDay(DateTime(2028, 2, 28, 23)), const Duration(hours: 1));
      expect(untilNextDay(DateTime(2028, 2, 29, 12)), const Duration(hours: 12));
    });

    test('0 時ちょうどは丸 1 日後、常に正の値', () {
      expect(untilNextDay(DateTime(2027, 6, 1)), const Duration(days: 1));
      expect(untilNextDay(DateTime(2027, 6, 1, 23, 59, 59, 999)) > Duration.zero, isTrue);
    });
  });

  group('pubspecBuild', () {
    test('split-per-abi で足された 1000 / 2000 を外す', () {
      expect(pubspecBuild(8), 8);
      expect(pubspecBuild(1008), 8); // armeabi-v7a
      expect(pubspecBuild(2008), 8); // arm64-v8a
      expect(pubspecBuild(4008), 8); // x86_64（配布はしていないが同じ規則）
    });
  });

  group('shouldShowUpdate', () {
    Map<String, dynamic> info(int current, int latest, {int dismissed = 0}) =>
        {'currentBuild': current, 'latestBuild': latest, 'dismissedBuild': dismissed};

    test('version.json の build が端末より大きいときだけ出す', () {
      expect(shouldShowUpdate(info(8, 9)), isTrue);
      expect(shouldShowUpdate(info(8, 8)), isFalse);
      expect(shouldShowUpdate(info(9, 8)), isFalse);
    });

    test('versionCode が % 1000 前の値でも誤って出さない／見落とさない', () {
      expect(shouldShowUpdate(info(2008, 8)), isFalse);
      expect(shouldShowUpdate(info(1008, 8)), isFalse);
      expect(shouldShowUpdate(info(2008, 9)), isTrue);
      expect(shouldShowUpdate(info(1008, 9)), isTrue);
    });

    test('「あとで」を押した版は出さず、さらに新しい版では出す', () {
      expect(shouldShowUpdate(info(8, 9, dismissed: 9)), isFalse);
      expect(shouldShowUpdate(info(8, 10, dismissed: 9)), isTrue);
    });

    test('version.json の取得失敗・未取得・壊れた値では出さない', () {
      expect(shouldShowUpdate(const {}), isFalse);
      expect(shouldShowUpdate({'currentBuild': 8, 'latestBuild': 0}), isFalse);
      expect(shouldShowUpdate({'currentBuild': 8}), isFalse);
      expect(shouldShowUpdate({'latestBuild': 9}), isFalse);
      expect(shouldShowUpdate({'currentBuild': 8, 'latestBuild': '9'}), isFalse);
      expect(shouldShowUpdate({'currentBuild': 8, 'latestBuild': -1}), isFalse);
    });
  });
}
