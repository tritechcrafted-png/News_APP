from django.urls import path

from . import views

#アプリの名前を指定することで、どこのアプリのviewを参照しているのか
#わかりやすくすることができる
app_name="news"

url_patterns=[

    #最初のページ　ホームページ
    path("", views.home, name="home")
]
