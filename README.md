# きょうは何の日？ 365日の日めくり

今日の日付に合わせて、記念日・年中行事の短い説明、仕事メモ、テーマ挿絵を表示するアプリです。通常の365日分に加え、うるう年の2月29日用データも収録しています。

内容と、日付・説明文を画像内に組み込んだ壁紙はインストール時に端末へ入ります。日常利用にChatGPT、生成AI、アカウント、サーバー処理、従量課金APIは必要ありません。出典リンクを開くときと、iPhoneの自動壁紙を切り替えるときだけインターネットを使います。

## 配布方法

- **iPhone:** GitHub PagesのURLをSafariで開き、共有メニューから「ホーム画面に追加」。壁紙の毎日更新は、アプリ内の「iPhoneの設定手順」に従ってショートカットを一度設定します。
- **Android:** GitHub Pagesから「Android版をダウンロード」を選んでAPKをインストールします。アプリ内のスイッチをオンにすると、ロック画面を毎朝7時ごろ更新します。省電力の状態により時刻が前後することがあります。

## GitHub Pagesで公開する

.github/workflows/deploy-pages.yml が main への更新後にWebアプリをビルドしてPagesへ配置します。

1. GitHubに daily365-wallpaper などの**公開リポジトリ**を作ります。
2. このプロジェクトを main ブランチへpushします。
3. GitHubのリポジトリ設定でPagesの公開元を「GitHub Actions」にします。
4. Actionsの完了後、https://tngmshr.github.io/daily365-wallpaper/ を配布します。

GitHub FreeでPagesを無料利用するには公開リポジトリが必要です。ソース、365日分の暦データ、壁紙、APKも公開されます。Pagesの公開と自動ビルドに有料サービスやAPIキーは使いません。

## ローカルで作る

Flutter 3.47.2、Android SDK、Python 3、Pillowが必要です。

    flutter pub get
    flutter analyze
    flutter build apk --release
    flutter build web --release --base-href "/REPOSITORY/"
    python tools/package_web.py

壁紙素材を作り直す場合は、次の順に実行します。元の挿絵は `assets/illustrations/`、日付・見出し・説明・出典を組み込んだ配布壁紙は `assets/wallpapers/` に保存されます。

    python tools/generate_visual_assets.py
    python tools/compose_wallpapers.py

build_calendar.py は日付記事の要約を再生成する補助ツールです。更新する場合だけ collect_date_articles.py でWikipediaからデータを取得し、その後に build_calendar.py、generate_visual_assets.py、compose_wallpapers.py を実行します。完成したアプリはその取得処理を呼びません。

公開ページからAndroid APKも配る場合は、ビルドしたAPKを web/downloads/app-release.apk に置いてからWebビルドします。初回APKはこのプロジェクトを作成したWindows環境のdebug署名です。同じ署名で更新するには同じ端末のdebug keystoreを保持してください。Play Store用の署名・公開設定は含みません。

## データとライセンス

日ごとの暦データは日本語版Wikipediaの日付記事をもとに短く整え、各日のアプリ画面に出典記事と、記事中に掲載された参考資料へのリンクを表示します。暦テキストは **CC BY-SA 4.0**、アプリのソースコードとオリジナル挿絵は **MIT License** です。詳しくは [CONTENT-LICENSE.md](CONTENT-LICENSE.md) を参照してください。

個人情報の入力欄、広告、トラッキング、利用時のAI検索はありません。
