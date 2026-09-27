import 'dart:convert';

import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

void main() => runApp(const DailyApp());

class DayEntry {
  const DayEntry({
    required this.date,
    required this.title,
    required this.kind,
    required this.summary,
    required this.workTip,
    required this.sources,
    required this.visual,
  });

  final String date;
  final String title;
  final String kind;
  final String summary;
  final String workTip;
  final String visual;
  final List<Map<String, String>> sources;

  factory DayEntry.fromJson(Map<String, dynamic> json) => DayEntry(
    date: json['date'] as String,
    title: json['title'] as String,
    kind: json['kind'] as String,
    summary: json['summary'] as String,
    workTip: json['work_tip'] as String,
    visual: json['visual'] as String? ?? 'people',
    sources: (json['sources'] as List<dynamic>)
        .map((source) => Map<String, String>.from(source as Map))
        .toList(),
  );
}

class ThemeStyle {
  const ThemeStyle(this.color, this.icon);

  final Color color;
  final IconData icon;
}

ThemeStyle styleFor(String visual) => switch (visual) {
  'nature' => const ThemeStyle(Color(0xff4e7855), Icons.eco),
  'water' => const ThemeStyle(Color(0xff2f7784), Icons.water),
  'travel' => const ThemeStyle(Color(0xff326d7a), Icons.travel_explore),
  'history' => const ThemeStyle(Color(0xff785c49), Icons.account_balance),
  'people' => const ThemeStyle(Color(0xffb76556), Icons.groups),
  'peace' => const ThemeStyle(Color(0xff47795e), Icons.spa),
  'sports' => const ThemeStyle(Color(0xff4d855d), Icons.sports_soccer),
  'science' => const ThemeStyle(Color(0xff4c6684), Icons.science),
  'space' => const ThemeStyle(Color(0xff51588d), Icons.rocket_launch),
  'culture' => const ThemeStyle(Color(0xff91694b), Icons.auto_stories),
  'food' => const ThemeStyle(Color(0xffa66f3e), Icons.restaurant),
  'health' => const ThemeStyle(Color(0xff498273), Icons.favorite),
  'technology' => const ThemeStyle(Color(0xff3c6873), Icons.memory),
  'work' => const ThemeStyle(Color(0xff68624f), Icons.work_outline),
  'seasonal' => const ThemeStyle(Color(0xff647a54), Icons.wb_sunny_outlined),
  _ => const ThemeStyle(Color(0xff276052), Icons.auto_awesome),
};

class DailyApp extends StatelessWidget {
  const DailyApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'きょうは何の日？',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff276052)),
      scaffoldBackgroundColor: const Color(0xfff4f1e9),
    ),
    home: const TodayScreen(),
  );
}

class TodayScreen extends StatefulWidget {
  const TodayScreen({super.key});

  @override
  State<TodayScreen> createState() => _TodayScreenState();
}

class _TodayScreenState extends State<TodayScreen> {
  late final Future<Map<String, DayEntry>> entries = _loadEntries();
  bool _wallpaperEnabled = false;

  @override
  void initState() {
    super.initState();
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      const MethodChannel('daily365/wallpaper')
          .invokeMethod<bool>('isEnabled')
          .then((enabled) {
            if (mounted) setState(() => _wallpaperEnabled = enabled ?? false);
          });
    }
  }

  Future<Map<String, DayEntry>> _loadEntries() async {
    final payload = jsonDecode(
      await rootBundle.loadString('assets/data/calendar.json'),
    ) as Map<String, dynamic>;
    final list = payload['entries'] as List<dynamic>;
    final loaded = <String, DayEntry>{
      for (final row in list)
        (row as Map<String, dynamic>)['date'] as String: DayEntry.fromJson(row),
    };
    final leapDay = payload['leap_day'] as Map<String, dynamic>?;
    if (leapDay != null) {
      loaded[leapDay['date'] as String] = DayEntry.fromJson(leapDay);
    }
    return loaded;
  }

  String _keyFor(DateTime date) =>
      '${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now();
    return Scaffold(
      body: SafeArea(
        child: FutureBuilder<Map<String, DayEntry>>(
          future: entries,
          builder: (context, snapshot) {
            if (snapshot.hasError) {
              return _message('データを読み込めません', 'アプリに収録した日付データを確認してください。');
            }
            if (!snapshot.hasData) {
              return const Center(child: CircularProgressIndicator());
            }
            final item = snapshot.data![_keyFor(today)];
            if (item == null) {
              return _message(
                '${today.month}月${today.day}日',
                '今日のページを準備しています。',
              );
            }
            return _page(today, item);
          },
        ),
      ),
    );
  }

  Widget _message(String title, String body) => Center(
    child: Padding(
      padding: const EdgeInsets.all(28),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.auto_awesome, size: 44, color: Color(0xff276052)),
          const SizedBox(height: 14),
          Text(title, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(body, textAlign: TextAlign.center),
        ],
      ),
    ),
  );

  Future<void> _toggleDailyWallpaper(bool enabled) async {
    try {
      await const MethodChannel('daily365/wallpaper')
          .invokeMethod<bool>(enabled ? 'enableDaily' : 'disableDaily');
      if (!mounted) return;
      setState(() => _wallpaperEnabled = enabled);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            enabled ? '今日のロック画面を設定し、毎日0時ごろの更新を予約しました。' : '毎日の自動更新を停止しました。',
          ),
        ),
      );
    } on PlatformException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('設定できませんでした: ${error.message ?? '画像を確認してください。'}'),
        ),
      );
    }
  }

  Future<void> _openSource(String url) async {
    try {
      final opened = await launchUrl(
        Uri.parse(url),
        mode: LaunchMode.externalApplication,
      );
      if (!opened && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('出典を開けませんでした。インターネット接続をご確認ください。')),
        );
      }
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('出典を開けませんでした。')));
    }
  }

  Future<void> _openIosGuide() async {
    await launchUrl(
      Uri.base.resolve('ios-shortcut.html'),
      mode: LaunchMode.platformDefault,
    );
  }

  Future<void> _downloadAndroidApk() async {
    await launchUrl(
      Uri.parse('https://github.com/tngmshr/daily365-wallpaper/releases/latest/download/daily365-arm64-v8a.apk'),
      mode: LaunchMode.platformDefault,
    );
  }

  Future<void> _downloadAndroid32Apk() async {
    await launchUrl(
      Uri.parse('https://github.com/tngmshr/daily365-wallpaper/releases/latest/download/daily365-armeabi-v7a.apk'),
      mode: LaunchMode.platformDefault,
    );
  }

  void _showCredits() {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        scrollable: true,
        title: const Text('このアプリについて'),
        content: const Text(
          '通常の365日分と、うるう日用の内容を事前収録しています。日常利用にAI検索や外部APIは必要ありません。\n\n'
          '暦の見出しと由来は日本語版Wikipediaの日付記事をもとに短く整えています。各日の出典記事と、記事にある参考資料へのリンクを表示します。暦の文章はCC BY-SA 4.0で利用できます。壁紙の背景挿絵とアプリアイコンはこのアプリ用のオリジナル作品で、壁紙には日付、見出し、説明、出典を載せています。',
        ),
        actions: [
          TextButton(
            onPressed: () => _openSource(
              'https://creativecommons.org/licenses/by-sa/4.0/deed.ja',
            ),
            child: const Text('ライセンス'),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('閉じる'),
          ),
        ],
      ),
    );
  }

  Widget _art(DayEntry item, ThemeStyle style) => AspectRatio(
    aspectRatio: 9 / 20,
    child: ClipRRect(
      borderRadius: BorderRadius.circular(24),
      child: Image.asset(
        'assets/wallpapers/${item.date}.webp',
        fit: BoxFit.cover,
        errorBuilder: (context, error, stack) => Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [style.color.withValues(alpha: .2), style.color],
            ),
          ),
          child: Center(
            child: Icon(
              style.icon,
              size: 120,
              color: Colors.white.withValues(alpha: .88),
            ),
          ),
        ),
      ),
    ),
  );

  Widget _page(DateTime date, DayEntry item) {
    final style = styleFor(item.visual);
    final isAndroid =
        !kIsWeb && defaultTargetPlatform == TargetPlatform.android;

    return CustomScrollView(
      slivers: [
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
          sliver: SliverList.list(
            children: [
              Row(
                children: [
                  Icon(Icons.wb_sunny_outlined, color: style.color),
                  const SizedBox(width: 8),
                  Text(
                    '365日の日めくり',
                    style: Theme.of(context).textTheme.labelLarge,
                  ),
                  const Spacer(),
                  IconButton(
                    tooltip: 'このアプリについて',
                    onPressed: _showCredits,
                    icon: const Icon(Icons.info_outline),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 520),
                  child: _art(item, style),
                ),
              ),
              const SizedBox(height: 19),
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xffe8f0eb),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '今日の仕事メモ',
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: const Color(0xff194a3e),
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(item.workTip),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              Text(
                '参考にした情報',
                style: Theme.of(context).textTheme.titleSmall
                    ?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 6),
              for (final source in item.sources)
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: () => _openSource(source['url']!),
                    icon: const Icon(Icons.open_in_new, size: 16),
                    label: Text(source['label']!, textAlign: TextAlign.left),
                    style: TextButton.styleFrom(foregroundColor: style.color),
                  ),
                ),
              if (isAndroid)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Card(
                    color: const Color(0xffe8f0eb),
                    child: SwitchListTile.adaptive(
                      value: _wallpaperEnabled,
                      onChanged: _toggleDailyWallpaper,
                      secondary: const Icon(Icons.wallpaper),
                      title: const Text('ロック画面を毎日自動更新'),
                      subtitle: const Text('毎日0時ごろ。省電力設定により時刻が前後する場合があります。'),
                    ),
                  ),
                ),
              if (kIsWeb)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'iPhoneではSafariからホーム画面に追加できます。壁紙の毎日変更はショートカットで設定します。',
                      ),
                      TextButton.icon(
                        onPressed: _openIosGuide,
                        icon: const Icon(Icons.phone_iphone),
                        label: const Text('iPhoneの設定手順'),
                      ),
                      TextButton.icon(
                        onPressed: _downloadAndroidApk,
                        icon: const Icon(Icons.android),
                        label: const Text('Android版をダウンロード'),
                      ),
                      TextButton(
                        onPressed: _downloadAndroid32Apk,
                        child: const Text('古い機種（32bit）はこちら', style: TextStyle(fontSize: 12)),
                      ),
                    ],
                  ),
                ),
              const SizedBox(height: 12),
              const Text(
                '日付の内容と挿絵は事前収録。利用中のAI検索やAPI通信はありません。',
                textAlign: TextAlign.center,
                style: TextStyle(color: Color(0xff647078), fontSize: 12),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
