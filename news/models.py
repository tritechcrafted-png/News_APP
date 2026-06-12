from django.db import models

# Create your models here.

class Article(models.Model):
    """
    一つのニュース記事を示すモデル
    GitHubリポジトリのjsonファイルに対応する形で表示する
    """

    