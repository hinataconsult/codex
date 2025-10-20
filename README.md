# 議事録自動生成・管理アプリ

議事録の要約生成から履歴管理、エクスポート、アクションアイテム通知までを一貫して行える Web アプリケーションです。自由入力テキストや箇条書きメモを元に、会議の目的・決定事項・宿題（アクションアイテム）・議事要旨の 4 セクションを 1000 文字以内で自動整形します。

## 構成

- `backend/`: FastAPI ベースの REST API サーバー
  - `/api/minutes/generate`: 要約生成
  - `/api/minutes`: 議事録の登録・更新・検索
  - `/api/minutes/{id}/history`: 履歴差分
  - `/api/minutes/{id}/export/pdf`: PDF 出力
  - `/api/minutes/export/csv`: CSV エクスポート
  - `/api/minutes/{id}/notifications`: 宿題通知（ログ記録）
- `frontend/`: バニラ JS/HTML/CSS で構成したシングルページ UI

## セットアップ

### バックエンドの起動

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

初回起動時に SQLite データベース (`backend/minutes.db`) が生成されます。

### フロントエンドの利用

`frontend/` ディレクトリ直下の静的ファイルを任意の HTTP サーバーで配信してください。例えば Python の `http.server` を使う場合は以下の通りです。

```bash
cd frontend
python -m http.server 5173
```

ブラウザで `http://localhost:5173` にアクセスし、バックエンド (`http://localhost:8000`) との同一ホスト運用を前提にしています。別ホストで運用する場合は `frontend/app.js` 内の `API_BASE` を調整してください。

## 主な機能

- 自由入力／箇条書きモードに対応した要約生成エンジン
- 会議の目的・決定事項・宿題・議事要旨の 4 セクションを 1000 文字以内に収める文字数制御
- 編集履歴（差分表示）とリマインダー通知ログ
- タイトル・参加者・開催日での検索／フィルタ
- PDF／CSV エクスポート

## テストデータ投入

バックエンド起動後、以下のコマンドで簡易的に API を試せます。

```bash
curl -X POST http://localhost:8000/api/minutes/generate \
  -H "Content-Type: application/json" \
  -d '{
        "title": "開発定例",
        "meeting_date": "2025-10-19",
        "participants": ["田中", "佐藤"],
        "text": "目的: リリース準備\n決定事項: QA を 10/25 までに完了\n宿題: 田中 -> テスト計画更新\n議事要旨: 全体の進捗は順調",
        "input_mode": "free"
      }'
```

## セキュリティと運用上の注意

- HTTPS 経由でのデプロイと OAuth/SSO 連携は別途インフラ構成で対応してください。
- 通知機能はデモ目的でログに記録するのみです。実際のメール／チャット送信処理は `backend/app/services/notifications.py` を拡張してください。
- API レスポンスは 3 秒以内の返答を想定した軽量アルゴリズムで実装しています。
