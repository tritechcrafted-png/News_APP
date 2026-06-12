from django.shortcuts import render

# Create your views here.


def home(request):
    """
    記事一覧のホームページを返す
    """

    #"news/home.html":どこのテンプレートに情報の渡すかのファイルパス
    return render(request, "news/home.html")