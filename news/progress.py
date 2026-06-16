# news/progress.py
# 「記事を生成」ボタンの進捗を入れておく場所
# バックグラウンドのスレッドが書き込んで、画面のJSが読みにくる
import threading

# 同時に2つのスレッドが触ると中身が壊れるので、鍵をかけるためのLock
_lock = threading.Lock()

# 今どこまで進んでいるかをまとめた辞書
# 最初は「何もしていない」状態にしておく
_job = {
    "running": False,    # 今動いているかどうか
    "done": 0,           # 終わった件数
    "total": 0,          # 全部で何件か
    "percent": 0,        # 進捗のパーセント (0〜100)
    "message": "待機中",  # 画面に出す説明の文
    "error": None,       # 失敗したらここにエラーの文を入れる
}


def get_job():
    """
    今の状態を返す
    dict()でコピーを渡すことで、呼び出した側がいじっても元は壊れないようにする
    """
    with _lock:
        return dict(_job)


def reset_job():
    """
    新しく始めるときに呼ぶ
    数字を全部0に戻して、running=True にする
    """
    with _lock:
        _job.update(running=True, done=0, total=0, percent=0,
                    message="開始中...", error=None)


def update_job(**kwargs):
    """
    渡されたところだけ上書きする
    例: update_job(percent=70, message="...")
    """
    with _lock:
        _job.update(kwargs)
