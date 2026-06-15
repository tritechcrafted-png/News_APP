from django.shortcuts import render, redirect

from django.http import Http404

from django.views.decorators.http import require_POST

from django.contrib import messages

from django.core.management import call_command

from django.db.models import Count

from io import StringIO

from datetime import date

from .models import Article

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
        .order_by("-article_data")
    )

    context={
        "date_list":date_list,
        "total":Article.objetcs.count(),
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
    except:
        #存在しない日付の場合はエラーページを出す
        raise Http404("この日付は存在しません")
    
    #指定した日付の記事のみにフィルタリングする
    articles =  Article.objects.filter(article_data=target_date)

    context={
        "target_date": target_date,
        "articles": articles,
    }

    #指定した日付の記事をテンプレートに渡す
    return render(request, "news/day.html", context)
#(デコレーターがよくわからない)
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