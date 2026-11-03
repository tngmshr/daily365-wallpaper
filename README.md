# きょうは何の日？ 365日の日めくり

## アプリを使う

- iPhone: [日めくりを開く](https://tngmshr.github.io/daily365-wallpaper/)（Safari で開いてホーム画面に追加）
- Android: [最新版をダウンロード（GitHub Releases）](https://github.com/tngmshr/daily365-wallpaper/releases/latest)

今日の日付に合わせて、記念日・年中行事の短い説明、仕事メモ、テーマ挿絵を表示するアプリです。通常の365日分に加え、うるう年の2月29日用データも収録しています。

内容と、日付・説明文を画像内に組み込んだ壁紙はインストール時に端末へ入ります。日常利用にChatGPT、生成AI、アカウント、サーバー処理、従量課金APIは必要ありません。インターネットを使うのは、出典リンクを開くとき、iPhoneの自動壁紙を切り替えるとき、Android版が翌日分の壁紙（2年目以降の入れ替えと節気の日付を反映したもの）と更新のお知らせ（`version.json`）をGitHub Pagesから取得するときです。取得できない場合、Android版は端末内の壁紙を使います。

## 配布方法

- **iPhone:** GitHub PagesのURLをSafariで開き、共有メニューから「ホーム画面に追加」。壁紙の毎日更新は「iPhoneの設定手順」から配布ショートカットを追加し、0時1分のオートメーションを設定します。配布リンクがまだない場合は手作業の手順を使えます。
- **Android:** GitHub Releasesから「Android版をダウンロード」を選んでAPKをインストールします。アプリ内のスイッチをオンにすると、ロック画面を毎日0時ごろ更新します。省電力の状態により時刻が前後することがあります。

## GitHub Pagesで公開する

.github/workflows/deploy-pages.yml が main への更新後にWebアプリをビルドしてPagesへ配置します。配置の前に `tools/validate_calendar.py`、Pythonのテスト、`flutter analyze`、`flutter test` を実行し、どれかが失敗すると公開しません。

1. GitHubに daily365-wallpaper などの**公開リポジトリ**を作ります。
2. このプロジェクトを main ブランチへpushします。
3. GitHubのリポジトリ設定でPagesの公開元を「GitHub Actions」にします。
4. Actionsの完了後、https://tngmshr.github.io/daily365-wallpaper/ を配布します。

GitHub FreeでPagesを無料利用するには公開リポジトリが必要です。ソース、366日分の暦データと壁紙は公開され、APKはGitHub Releasesで配布します。Pagesの公開と自動ビルドに有料サービスやAPIキーは使いません。

## ローカルで作る

Flutter 3.47.2、Android SDK、Python 3、Pillowが必要です。

    flutter pub get
    flutter analyze
    flutter test
    python tools/validate_calendar.py
    python -m unittest discover -s tools -p 'test_*.py'
    flutter build web --release --no-web-resources-cdn --base-href "/REPOSITORY/"
    python tools/package_web.py

`--no-web-resources-cdn` はCanvasKitをgstaticではなくPagesから配るための指定です。これがないと、ホーム画面に追加したWeb版がオフラインで真っ白になります。`tools/package_web.py` は `service-worker.js` のキャッシュ名に収録ファイルのハッシュを入れるので、内容を変えて公開すると、ホーム画面のWeb版も次回起動時に新しい内容へ入れ替わります（変わっていないファイルは再ダウンロードしません）。同じビルドに2回かけるとエラーになるので、やり直すときは `flutter build web` からやり直します。

`validate_calendar.py` は通常年・うるう日・2〜4年目（`assets/data/years/slot*.json`）について、日付の重複・欠け・順序、文字数、`theme` が `docs/themes.json` と挿絵にあるか、年で日付が動く節目（節分・春分など）に `solar_term` があるか、`solar_terms.json` の各年に日付がそろっているか、壁紙のカードに文章が収まるか（Pillowとフォントが必要。`--skip-layout` で省略）を確かめます。

壁紙素材は `python tools/compose_wallpapers.py` で生成します。挿絵は `assets/illustrations/MM-DD.webp`（PNG・JPGも可）、暦文は `assets/data/calendar.json` を入力にします。挿絵は日付ごとの場面（`scene`）をもとに画像生成AIで作ったものです。Noto Sans JP可変フォント（`tools/fonts/NotoSansJP[wght].ttf`）を使い、1440×3200のマスターから1080×2400のWebPを366枚出力します。指定日のみなら `--only 01-03 09-27`、各月1日の一覧も作るなら `--preview` を付けます。文章が指定の行数に収まらない場合は日付を示して停止します。

Web公開時は `tools/package_web.py` がWebPを1080×2400のJPEGに変換し、iPhoneショートカット用の `/wallpapers/MM-DD.jpg` を作ります。2年目以降の差し替え（`assets/data/years/slot*.json`）と節気の移動を反映した年別の `/wallpapers/YYYY/MM-DD.jpg` も今年分と来年分を作ります。アプリ画面も同じ規則（`lib/year_calendar.dart`）で年を解決し、1年目と内容が違う日はこの年別画像を表示します。Android版のロック画面も同じ規則（`YearRotation.kt`）で、その日の年別画像を使います。取得できていない日は、1年目の壁紙（別の題材）ではなく、その日の文章を載せた画像を入れ、取得でき次第差し替えます。

build_calendar.py は日付記事の要約を再生成する補助ツールです。更新する場合だけ collect_date_articles.py でWikipediaからデータを取得し、その後に build_calendar.py と compose_wallpapers.py を実行します。完成したアプリはその取得処理を呼びません。

## Android APKを署名して配布する

`android/key.properties` を作り、`storePassword`、`keyPassword`、`keyAlias`、絶対パスの `storeFile` を設定します。署名鍵とこのファイルはリポジトリに含めません。設定がなければreleaseビルドは失敗します。更新時も同じ鍵を使います。

    flutter build apk --release --split-per-abi

生成された `build/app/outputs/flutter-apk/app-arm64-v8a-release.apk` を `daily365-arm64-v8a.apk` に、`app-armeabi-v7a-release.apk` を `daily365-armeabi-v7a.apk` にリネームし、両方をリポジトリのReleasesに登録します。

    gh release create v1.1.0 daily365-arm64-v8a.apk daily365-armeabi-v7a.apk --title "v1.1.0"

### 更新のお知らせ

Android版は起動・復帰時（12時間に1回まで）にPagesの `version.json` を読み、`pubspec.yaml` のビルド番号（`+6` の部分）が端末の版より大きければ画面上部にお知らせを出します。`--split-per-abi` のAPKは versionCode にABIごとの1000・2000が足されるため、端末側は versionCode を1000で割った余りで比べます。そのためビルド番号は1〜999にします（`package_web.py` が範囲外を止めます）。取得に失敗したときは前回取得した結果を使い、一度も取得できていなければお知らせは出ません。「あとで」を押すとその版では再表示しません。`version.json` は `tools/package_web.py` が `pubspec.yaml` と `tools/whats_new.json`（版ごとの変更点、3行まで表示）から作ります。

順序に注意: **Releasesに新しいAPKを登録してから** `main` に反映します。`main` へのpushでPagesの `version.json` が先に更新されると、ダウンロードボタンが古いAPKを指します。

お知らせの見た目は `flutter build web --dart-define=PREVIEW_UPDATE_NOTICE=true` のWeb版で確認できます。

iPhoneのショートカットをリンクで配布する場合は `web/ios-shortcut.html` の `SHORTCUT_URL` に共有URLを設定します。空欄の間は追加ボタンが非表示で、手作業の作成手順を使えます。

## データとライセンス

日ごとの暦データは日本語版Wikipediaの日付記事をもとに短く整え、各日のアプリ画面に出典記事と、記事中に掲載された参考資料へのリンクを表示します。暦テキストは **CC BY-SA 4.0**、アプリのソースコードとオリジナル挿絵は **MIT License**、フォントは **SIL OFL 1.1** です。詳しくは [CONTENT-LICENSE.md](CONTENT-LICENSE.md) を参照してください。

個人情報の入力欄、広告、トラッキング、利用時のAI検索はありません。
