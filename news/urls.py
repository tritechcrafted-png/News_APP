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

    path("tag/<str:name>/", views.tag_articles, name= "tag"),
]


