from django.shortcuts import render, redirect

from django.http import Http404

from django.views.decorators.http import require_POST

from django.contrib import messages

from django.core.management import call_command

from django.db.models import Count

from io import StringIO

from datetime import date

import sys
import threading
import subprocess

from django.conf import settings

from django.http import JsonResponse

from . import progress

from .models import Article, Tag

# Create your views here.


def home(request):
    """
    記事一覧のホームページを返す

    date_listは[{"article_date":日付, "count":記事数}]
    """

    date_list=(
        #.values:グループでまとめる
        #今回の場合は同じ日付でまとめる
        Article.objects.values("article_date")

        #.annotate():各グループに何件の記事があるのかの部分をDBに追加する
        # Count("id")で各日付の記事数を数える
        .annotate(count=Count("id"))

        #新しい日付が上に来るように降順で並べる
        .order_by("-article_date")
    )

    context={
        "date_list":date_list,
        "total":Article.objects.count(),
        "all_tags":Tag.objects.all(),
    }

    #"news/home.html":どこのテンプレートに情報の渡すかのファイルパス
    return render(request, "news/home.html", context)

def day_articles(request, year, month, day):
    """
    日付ページ；指定された日の記事一覧を表示する

    存在しない日付の場合は404ページでエラーを出す
    """
    try:
        #日付オブジェクト作成
        target_date=date(year, month, day)
    except ValueError:
        #存在しない日付の場合はエラーページを出す
        raise Http404("この日付は存在しません")
    
    #指定した日付の記事のみにフィルタリングする
    articles =  Article.objects.filter(article_date=target_date)

    context={
        "target_date": target_date,
        "articles": articles,
    }

    #指定した日付の記事をテンプレートに渡す
    return render(request, "news/day.html", context)

def tag_articles(request, name):
    """
    指定されたタグがついた記事を新しい順に表示する
    """

    #tags__name=nameでタグ名が一致するもののみを絞り込む
    articles=Article.objects.filter(tags__name=name)

    context={
        "tag_name": name,
        "articles":articles,
    }

    return render(request, "news/tags.html", context)

@require_POST
#デコレーターでDjangoにこの関数を渡して、Django側から呼び出せるようにする
def update_feed(request):
    """
    GitHubから新しい記事をDBに同期する

    sync_github　を呼び出して、ホームにリダイレクトする
    """

    out=StringIO()
    
    #sync_githubコマンドを実行する
    #standout=outで (よくわからない)
    call_command("sync_github", stdout=out)

    #同期に成功したらメッセージを表示
    messages.success(request, "GitHubから記事を同期しました。")

    #同期に成功したら、ホームに戻る
    return redirect("news:home")


def _run_pipeline():
    """
    別のスレッドで動く本体の部分
    画面の動き(リクエスト)とは別に、裏でずっと走らせておくためのもの

    やること
    1. generate_feed.py を動かして、PROGRESSの行を読んで進捗を更新する
    2. 全部終わったら sync_github でDBに取り込む
    """

    #generate_feed.py がある tech-news-data フォルダ (settings.pyで設定した)
    feed_dir = settings.FEED_SCRIPT_DIR

    try:
        #Popen:プロセスを起動して、裏で走らせたまま出力を1行ずつ読む
        #run()だと終わるまで待ってしまうので、進捗を取るにはPopenを使う
        proc = subprocess.Popen(
            [sys.executable, "generate_feed.py"],
            cwd=feed_dir,                  #tech-news-data の中で実行する
            stdout=subprocess.PIPE,        #標準出力を受け取る
            stderr=subprocess.STDOUT,      #エラー出力も同じ流れにまとめる
            text=True,
            encoding="utf-8",
            bufsize=1,                     #1行ずつ読めるようにする(行バッファ)
        )

        #スクリプトが出す行を、出てくるそばから1行ずつ読んでいく
        for line in proc.stdout:
            line = line.strip()

            #空っぽの行は飛ばす
            if not line:
                continue

            #"PROGRESS 14 20" みたいな行なら、進捗の数字として読む
            if line.startswith("PROGRESS"):
                #スペースで分けて ["PROGRESS","14","20"]
                _, done_s, total_s = line.split()
                done, total = int(done_s), int(total_s)

                #パーセントを計算する。totalが0の時は割り算できないので100にする
                percent = int(done / total * 100) if total else 100

                progress.update_job(
                    done=done, total=total, percent=percent,
                    message=f"要約中... {done}/{total}件",
                )
            else:
                #PROGRESS以外の行は、そのまま説明文として画面に出す
                progress.update_job(message=line)

        #出力を読み終わった = プロセスが終わった、ということ
        #終了コードを確認して、0以外なら失敗
        proc.wait()
        if proc.returncode != 0:
            progress.update_job(running=False, error="記事の生成に失敗しました")
            return

    except Exception as e:
        #そもそもプロセスを動かせなかった時など
        progress.update_job(running=False, error=str(e))
        return

    #ここまで来たら生成成功。次にDBへ取り込む
    progress.update_job(message="DBに取り込み中...")
    out = StringIO()
    call_command("sync_github", stdout=out)

    #完了。running=Falseにすると、画面側がポーリング(1秒ごとの確認)をやめる
    progress.update_job(running=False, percent=100, message="完了しました")


@require_POST
def generate_articles(request):
    """
    ボタンから呼ばれるview
    バックグラウンドのスレッドを始めるだけして、すぐに返す
    (重い処理を待たずに、画面はすぐ次に進める)
    """

    #もうすでに動いているなら、二重で始めない
    if progress.get_job()["running"]:
        return JsonResponse({"started": False, "reason": "すでに実行中です"})

    #進捗を0に戻してからスレッドを開始する
    progress.reset_job()

    #daemon=True:サーバーが止まる時に一緒に止まる(取り残されないように)
    threading.Thread(target=_run_pipeline, daemon=True).start()

    return JsonResponse({"started": True})


def generate_progress(request):
    """
    今の進捗をJSONで返すだけのview
    画面のJSが1秒ごとにここを見にくる
    """
    return JsonResponse(progress.get_job())