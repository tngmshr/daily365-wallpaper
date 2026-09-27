# きょうは何の日？ 365日の日めくり

今日の日付に合わせて、記念日・年中行事の短い説明、仕事メモ、テーマ挿絵を表示するアプリです。通常の365日分に加え、うるう年の2月29日用データも収録しています。

内容と、日付・説明文を画像内に組み込んだ壁紙はインストール時に端末へ入ります。日常利用にChatGPT、生成AI、アカウント、サーバー処理、従量課金APIは必要ありません。出典リンクを開くときと、iPhoneの自動壁紙を切り替えるときだけインターネットを使います。

## 配布方法

- **iPhone:** GitHub PagesのURLをSafariで開き、共有メニューから「ホーム画面に追加」。壁紙の毎日更新は「iPhoneの設定手順」から配布ショートカットを追加し、0時1分のオートメーションを設定します。配布リンクがまだない場合は手作業の手順を使えます。
- **Android:** GitHub Releasesから「Android版をダウンロード」を選んでAPKをインストールします。アプリ内のスイッチをオンにすると、ロック画面を毎日0時ごろ更新します。省電力の状態により時刻が前後することがあります。

## GitHub Pagesで公開する

.github/workflows/deploy-pages.yml が main への更新後にWebアプリをビルドしてPagesへ配置します。

1. GitHubに daily365-wallpaper などの**公開リポジトリ**を作ります。
2. このプロジェクトを main ブランチへpushします。
3. GitHubのリポジトリ設定でPagesの公開元を「GitHub Actions」にします。
4. Actionsの完了後、https://tngmshr.github.io/daily365-wallpaper/ を配布します。

GitHub FreeでPagesを無料利用するには公開リポジトリが必要です。ソース、366日分の暦データと壁紙は公開され、APKはGitHub Releasesで配布します。Pagesの公開と自動ビルドに有料サービスやAPIキーは使いません。

## ローカルで作る

Flutter 3.47.2、Android SDK、Python 3、Pillowが必要です。

    flutter pub get
    flutter analyze
    flutter build web --release --base-href "/REPOSITORY/"
    python tools/package_web.py

壁紙素材は `python tools/compose_wallpapers.py` で生成します。挿絵は `assets/illustrations/MM-DD.png`、暦文は `assets/data/calendar.json` を入力にします。現在のJPG挿絵もPNGへの差し替えまでは読み込めます。Noto Sans JP可変フォント（`tools/fonts/NotoSansJP[wght].ttf`）を使い、1440×3200のマスターから1080×2400のWebPを366枚出力します。指定日のみなら `--only 01-03 09-27`、各月1日の一覧も作るなら `--preview` を付けます。文章が指定の行数に収まらない場合は日付を示して停止します。

Web公開時は `tools/package_web.py` がWebPを1080×2400のJPEGに変換し、iPhoneショートカット用の `/wallpapers/MM-DD.jpg` を作ります。

build_calendar.py は日付記事の要約を再生成する補助ツールです。更新する場合だけ collect_date_articles.py でWikipediaからデータを取得し、その後に build_calendar.py と compose_wallpapers.py を実行します。完成したアプリはその取得処理を呼びません。

## Android APKを署名して配布する

`android/key.properties` を作り、`storePassword`、`keyPassword`、`keyAlias`、絶対パスの `storeFile` を設定します。署名鍵とこのファイルはリポジトリに含めません。設定がなければreleaseビルドは失敗します。更新時も同じ鍵を使います。

    flutter build apk --release --split-per-abi

生成された `build/app/outputs/flutter-apk/app-arm64-v8a-release.apk` を `daily365-arm64-v8a.apk` に、`app-armeabi-v7a-release.apk` を `daily365-armeabi-v7a.apk` にリネームし、両方をリポジトリのReleasesに登録します。

    gh release create v1.1.0 daily365-arm64-v8a.apk daily365-armeabi-v7a.apk --title "v1.1.0"

iPhoneのショートカットをリンクで配布する場合は `web/ios-shortcut.html` の `SHORTCUT_URL` に共有URLを設定します。空欄の間は追加ボタンが非表示で、手作業の作成手順を使えます。

## データとライセンス

日ごとの暦データは日本語版Wikipediaの日付記事をもとに短く整え、各日のアプリ画面に出典記事と、記事中に掲載された参考資料へのリンクを表示します。暦テキストは **CC BY-SA 4.0**、アプリのソースコードとオリジナル挿絵は **MIT License**、フォントは **SIL OFL 1.1** です。詳しくは [CONTENT-LICENSE.md](CONTENT-LICENSE.md) を参照してください。

個人情報の入力欄、広告、トラッキング、利用時のAI検索はありません。
