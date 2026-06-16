# news/progress.py
# 「記事を生成」ジョブの進捗を、サーバーのメモリ内で共有するための小さな入れ物。
# バックグラウンドのスレッドが書き込み、/progress/ を見にくるブラウザが読み取る。
import threading

# Lock: 2つのスレッドが同時に辞書を触って壊すのを防ぐ「鍵」。
_lock = threading.Lock()

# 今のジョブの状態。最初は「待機中・何もしていない」。
_job = {
    "running": False,    # 実行中かどうか
    "done": 0,           # 終わった件数
    "total": 0,          # 全件数
    "percent": 0,        # 進捗％（0〜100）
    "message": "待機中",  # 画面に出す説明文
    "error": None,       # 失敗したらエラー文を入れる
}


def get_job():
    """今の状態を返す。コピーを返すので、呼び出し側が触っても元は壊れない。"""
    with _lock:
        return dict(_job)


def reset_job():
    """新しいジョブの開始。数字を0に戻して running=True にする。"""
    with _lock:
        _job.update(running=True, done=0, total=0, percent=0,
                    message="開始中...", error=None)


def update_job(**kwargs):
    """渡されたキーだけ上書きする。例: update_job(percent=70, message='...')。"""
    with _lock:
        _job.update(kwargs)
