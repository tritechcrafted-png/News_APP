import json
import urllib.request
import urllib.error
import ssl       
import certifi   


#urlib.rquest: Httpリクエストを送るためのPython標準のライブラリ
#urlib.error:接続エラーなどの例外を処理するライブラリ

from datetime import datetime

#すべての管理コマンドが継承しないといけないクラス
from django.core.management.base import BaseCommand

#settings: Djangoのsettings.pyの値にアクセスするための
from django.conf import settings

#記事のデータベースをimportする
from news.models import Article, Tag

def fetch_json(url):
    """
    URLからJSONをダウンロードして辞書型にして返す
    """

    #urlopen():urlにgetリクエストを送る
    # .read():受け取ったbyteを読み込む
    #.decode():受け取ったbyteを文字列に変換
    #json.loads(): jsonの文字列を listと辞書型に変換する

    # ssl.create_default_context: 信頼された証明書を積んだ「検証器」を作る
    # cafile=certifi.where(): certifi のバンドル（信頼リスト）を指定する
    context = ssl.create_default_context(cafile=certifi.where())

    # context=context: 「空の既定の検証器ではなく、コレを使え」と urlopen に伝える
    with urllib.request.urlopen(url, context=context) as response:
        return json.loads(response.read().decode("utf-8"))
    

class Command(BaseCommand):
    """
    Githubから新しい記事のファイルをダウンロードしてDBに保存する
    使い方としては：python manage.py sync_github
    """
    
    #python manage.py help sync_github で表示する説明文
    help="GitHubリポジトリから新しい記事をDBに保存"

    def handle(self, *args, **options):
        """
        コマンドを実行したときにDjangoが呼び出すメインの関数

        処理の流れ
        1.index.jsonを取得
        2.未取得の記事ファイルをダウンロード、DBに保存
        """

        #すべての記事ファイル共通するURLを設定する
        base_url=settings.GITHUB_BASE_URL

        #もし共通のURLがない場合はエラーを出す
        if not base_url:
            self.stdout.write(self.style.ERROR(
                "GIT_BASE_URLがsettings.pyに設定されていません"
            ))

            return
        
        #目次(index.jsonを取得)
        self.stdout.write(f"目次を取得中: {base_url}index.json")
        try:
            #indexの中身
            #baseurl+記事ごとの個別のurl
            index = fetch_json(base_url + "index.json")
        
        except urllib.error.URLError as e:
            #URLが間違っているなどの場合エラー分を出して終わりにする
            self.stdout.write(self.style.ERROR(f"接続エラー： {e}"))
            return
        
        #すでにある記事をダウンロードの候補からなくす
        existing_urls= set(Article.objects.values_list("url", flat=True))

        #新しい記事を保管する用のリスト
        new_entries = []

        for e in index:
            #記事のurlをfor loopでひとつづつ確認

            #もしurlがすでに保存しているurlに存在していないなら
            if e["url"] not in existing_urls:
                #新しい記事をリストに保管
                new_entries.append(e)

        #もし新しい記事がないなら
        if not new_entries:
            self.stdout.write("新しい記事はありません")
            return
        
        #ダウンロードする記事に関するメッセージを出す
        self.stdout.write(f"{len(new_entries)}件の新しい記事をダウンロード中...\n")
                          
        created_count=0

        #新しい記事を一つずつDBに保管するループ
        for entry in new_entries:
            #記事のファイルパスを入手　
            path = entry["path"]

            #パスを "/"で分割　["articles", "2026-06-12", "0001.json"]
            #[1]＝日付フォルダの名前
            date_str=path.split("/")[1]
            
            #strptime:文字列を日付に変更
            #.date()で日付だけにする
            article_date= datetime.strptime(date_str, "%Y-%m-%d").date()

            try:
                #一つの記事のJSONファイルをダウンロードする
                data = fetch_json(base_url + path)

            except urllib.error.URLError:
                self.stdout.write(self.style.WARNING(f"スキップ(取得失敗): {path}"))

                #1ファイルの失敗で全体を止めずに、スキップして次に進む
                continue
            
            #ダウンロードした記事をDBの新しい行として保管する
            article= Article.objects.create(
                title=data.get("title",""),
                url=data.get("url", ""),
                #description = 見出しの下に出す短いリード文
                description=data.get("description", ""),
                #detail = やさしい言葉でのくわしい説明。古い記事には無いので空をデフォルトにする
                detail=data.get("detail", ""),
                source=data.get("source", ""),
                article_date=article_date,
            )

            #JSONの"tags"を1ずつ処理する
            for tag_name in data.get("tags", []):
                #get_or_cretae:そのタグがすでにあれば習得、なければ作る
                #return is objects

                tag, _ = Tag.objects.get_or_create(name=tag_name)

                #多対多　のつなぎを一本にする
                article.tags.add(tag)


            #どこまでの記事を追加できたのかの数を更新
            created_count +=1 

            #記事のタイトルをDBに書き込む
            self.stdout.write(f" + {data.get('title', '')[:60]}")
        
        self.stdout.write(
            self.style.SUCCESS(f"\n 完了{created_count}件の記事を追加しました")
        )

        




        

