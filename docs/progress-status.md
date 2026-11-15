# 進捗ステータス

## 現在のフェーズ

**環境構築フェーズ（完了）→ 実験開始待ち**

## 構築済み環境

| 項目 | 内容 |
|---|---|
| 言語 | Rust (edition 2021) |
| DB | PostgreSQL 16（Dockerコンテナ） |
| Rustビルド | WSL2ネイティブ（`cargo build`） |
| DB接続URL | `postgres://rust_user:password@localhost:5432/rust_dev` |

## DBコンテナの起動・停止

```bash
# 起動
docker-compose up -d

# 停止
docker-compose down

# ログ確認
docker-compose logs db
```

## 今後やりたいこと（実験リスト）

- [ ] Rustの基礎文法・所有権・ライフタイム
- [ ] DB接続（sqlx または diesel）
- [ ] Web API（Axum または Actix-web）
- [ ] DB + Web の統合（REST API）

## 次のアクション

実験したい内容を決めて開始する。

## 現在地

- 2026-11-15: AI-DDD の共通部分 v7・フック（Claude Code・Codex）・改善の記録を入れ、CLAUDE.md を @AGENTS.md の形にした（ai-ddd #47）
