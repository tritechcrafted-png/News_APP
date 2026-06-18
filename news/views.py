from django.shortcuts import render, redirect

from django.http import Http404

from django.views.decorators.http import require_POST

from django.contrib import messages

from django.core.management import call_command

from django.db.models import Count

from io import StringIO

from datetime import date

import os
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

@require_POST
def clear_articles(request):
    """
    DBの記事を全部消す。
    DjangoのDBのみ削除する
    """

    #記事をすべてDBから消す
    Article.objects.all().delete()

    #タグも全部消して、まっさらにする
    Tag.objects.all().delete()

    #画面に完了のメッセージ
    messages.success(request, "DBの記事を全部削除しました")

    #ホームに戻る
    return redirect("news:home")

def _run_pipeline(count ):
    """
    別のスレッドで動く本体の部分
    画面の動き(リクエスト)とは別に、裏でずっと走らせておくためのもの

    やること
    1. generate_feed.py を動かして、PROGRESSの行を読んで進捗を更新する
    2. 全部終わったら sync_github でDBに取り込む
    """

    #generate_feed.py がある tech-news-data フォルダ (settings.pyで設定した)
    feed_dir = settings.FEED_SCRIPT_DIR

    #Windowsだと、別プロセスのprintが日本語を cp932(Shift-JIS) で出してしまう。
    #こちらは utf-8 で読むので、そのままだと文字化けエラー(0x82が読めない等)になる。
    #子プロセスに「出力は utf-8 にして」と環境変数で伝えて、文字コードを揃える。
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"            #子のPythonをUTF-8モードにする
    env["PYTHONIOENCODING"] = "utf-8"  #念のため、入出力もUTF-8に指定

    try:
        #実行するコードを先に設定する
        cmd=[sys.executable, "generate_feed.py"]

        #count が1以上の時だけ、件数を引数として足す。
        #(0=全部)の時は足さない -> generate_feed.py側は[制限なし]で動く
        if count>=1:
            cmd.append(str(count))

        #Popen:プロセスを起動して、裏で走らせたまま出力を1行ずつ読む
        #run()だと終わるまで待ってしまうので、進捗を取るにはPopenを使う
        proc = subprocess.Popen(
            [sys.executable, "generate_feed.py"],
            cwd=feed_dir,                  #tech-news-data の中で実行する
            stdout=subprocess.PIPE,        #標準出力を受け取る
            stderr=subprocess.STDOUT,      #エラー出力も同じ流れにまとめる
            text=True,
            encoding="utf-8",
            errors="replace",             #万一読めない文字が来ても、落とさず置き換える
            bufsize=1,                     #1行ずつ読めるようにする(行バッファ)
            env=env,                       #↑で作ったutf-8設定を子プロセスに渡す
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
                if total:
                    percent = int(done / total * 85)

                else:
                    percent=85
                
                progress.update_job(
                    done=done, total=total, percent=percent, 
                    message=f"要約中.... {done}/{total}件")
            else:
                #generate_feed.py が出す節目のメッセージを加えて少しずつ進めていく
                
                #ローカル保存が完了下
                if "保存しました" in line:
                    progress.update_job(percent=88, message=line)
                
                #Githubに要約した記事をpush
                elif line.startswith("GitHub"):
                    progress.update_job(percent=90, message=line)
                
                #pushが完了した場合
                elif line.startswith("完了"):
                    progress.update_job(percent=95, message=line)

                #それ以外の文の場合はそのまま表示させる
                else:
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

    #データベースに記事を取り組む
    try:
        out = StringIO()
        call_command("sync_github", stdout=out)
    except Exception as e:
        progress.update_job(running=False, error=f"DB取り込みで失敗: {e}")
        return


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
    
    #画面のドロップダウンとして何件受け取るかを習得する
    #送られてこない・数字出ない時は、安全側として1件にする
    count_raw = request.POST.get("count","1")

    try:
        count=int(count_raw)
    except ValueError:
        count=1
    
    #もしマイナスなら最低でも1にする
    #0は全部という意味なのでスルー
    if count<0:
        count=1

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