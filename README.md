# rust_project

Rust言語による開発実験プロジェクト。
AI-DDD（AIネイティブ・ドキュメント駆動開発）の手法に基づいて運用する。

## 開発方針

ドキュメントを **Source of Truth（正）** とし、コードはその副産物として扱う。
`docs/` 配下を常に最新に保つことで、AIのコンテキストを維持し、実装精度を最大化する。

詳細は [docs/overview.md](docs/overview.md) を参照。

## ドキュメント構造

- [docs/overview.md](docs/overview.md) — AI-DDDの概要・思想
- [docs/ai-ddd-guide.md](docs/ai-ddd-guide.md) — 4フェーズの完全ガイド
- [docs/ai-ddd-standards.md](docs/ai-ddd-standards.md) — 標準規約・行動規範
- [docs/ai-ddd-glossary.md](docs/ai-ddd-glossary.md) — 用語集・役割分担

## セッション開始プロトコル

作業開始時は必ず以下を問いかける。

> 「今の状況を教えて」

AIが `docs/progress-status.md` と `docs/` 配下をスキャンし、コンテキストを同期する。

## 開発環境

- 言語: Rust (edition 2021)
- 環境: WSL2 / Linux
- ビルド: `cargo build`
- テスト: `cargo test`
