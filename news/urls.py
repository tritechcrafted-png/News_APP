from django.urls import path

from . import views

#アプリの名前を指定することで、どこのアプリのviewを参照しているのか
#わかりやすくすることができる
app_name="news"

urlpatterns=[

    #最初のページ　ホームページ
    path("", views.home, name="home"),

    #urlのその日の記事を出していく
    path("day/<int:year>/<int:month>/<int:day>/", views.day_articles, name="day"),

    #更新ボタンのフォームを押したときに送信するurl
    #@require_POSTでGETアクセスを拒否する
    path("update/", views.update_feed, name="update_feed"),

    #全記事削除ボタンの送信先(POSTだけ)
    path("clear/", views.clear_articles, name="clear_articles"),

    path("tag/<str:name>/", views.tag_articles, name= "tag"),

    #生成スタートのボタンの送信先(POSTだけ)。JSがfetchで呼ぶ
    path("generate/", views.generate_articles, name="generate_articles"),

    #進捗を聞きにくる先(JSが1秒ごとにGETする)
    path("progress/", views.generate_progress, name="generate_progress"),
]


