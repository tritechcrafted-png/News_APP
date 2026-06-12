from django.db import models

# Create your models here.

class Article(models.Model):
    """
    一つのニュース記事を示すモデル
    GitHubリポジトリのjsonファイルに対応する形で表示する
    """

    #記事のタイトルを保管
    title= models.CharField(max_length=500)

    #urlを保管
    #unique=Trueで同じ記事が存在しない仕組みにする
    url= models.URLField(unique=True, max_length=1000)

    #記事の説明文を保管
    #CLaudeなどで要約した記事がここに入る
    
    #TextField: 文字数制限なしの長いテキストを用意
    #blank=True: 空でも保存できる
    description= models.TextField(blank=True)

    #どこからその記事をとってきたのか
    #そのソース
    source = models.CharField(max_length=100, blank =True)

    #何日に要約した記事なのかを保管
    #DateField:日時のみ保管
    article_date=models.DateField()

    class Meta:
        #Meta:モデルの設定の置き場所
        #設定したデータをどう扱うか
        
        #ordering: 記事をDBから引き出す時のデフォルトの並び順
        #-article_date:新しいから古い順で並べる
        ordering=["-article_date"]
    
    def __str__(self):
        """
        Djangoの管理画面でオブジェクトを表示する時の文字列を返す
        """
        return self.title
    
    def short_title(self):
        """
        タイトルを最大60文字にする
        """
        if len(self.title)>60:
            return self.title[:60]+"..."
        return self.title