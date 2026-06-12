from django.contrib import admin

# Register your models here.
from .models import Article

#デコレーターを使うことで下のクラスをDjangoが扱えるようにする
@admin.register(Article)

class ArticleAdmin(admin.ModelAdmin):
    """
    管理画面でArticleモデルを管理するための設定
    """

    #一覧に表示するカラム
    list_display=("short_title_display", "source","article_date")

    #list_filter:一覧の右側にフィルターを追加する
    list_filter = ("source", "article_date")

    #管理画面に検索バーを追加する
    seach_fields=("title", "description")

    list_per_page=50

    def short_title_display(self, obj):
        """
        管理画面の一覧でタイトルに表示する値を返す
        Artcile モデルの short_title()を呼び出す
        """

        #obj = 現在の行のArticleのインスタンス
        return obj.short_title()
    
    short_title_display.short_description = "タイトル"

    