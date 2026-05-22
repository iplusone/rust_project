# AI連携用語事典：AI-Native DDD用語集

## 1. AI-Native DDDとは

AI-Native DDDはドキュメントを開発のエンジンとする手法です。本資料では「ドキュメント駆動開発（Document Driven Development）」に焦点を当て、ドメイン駆動設計（Domain Driven Design）とは区別します。

| 項目 | Document Driven Development | Domain Driven Design |
|---|---|---|
| 略称 | DDD | DDD |
| 焦点 | 開発プロセス・対話・記録 | ソフトウェア内部の設計構造 |
| 目的 | ドキュメントを正とし、AIと人間の認識を同期する | ビジネスルールをコード構造に反映する |
| 初心者のイメージ | 完璧な地図を描き、AIを走らせる手法 | 業務ルールに基づく堅牢な設計手法 |

## 2. AIツールチェーンの役割分担事典

AI-Native DDDでは、主要なAIツールを役割ごとに分けて活用します。

### ① NotebookLM: アナリスト

* 役割: 分析官
* 得意: 会議録音や断片的なメモから構造を抽出し、資料を作成する
* アウトプット: PRD、インフォグラフィック、プレゼン資料案

### ② Codex: アーキテクト

* 役割: 校閲者
* 得意: ドキュメントの論理的矛盾を突き、逆質問を行う
* アウトプット: Q&Aログ、補完された要件定義

### ③ Claude Code: エンジニア

* 役割: プログラマー
* 得意: 仕様から実装へ、テスト実行まで自律的に行う
* アウトプット: ソースコード、Issue、Unitテスト結果、更新されたREADME

## 3. 開発のライフサイクル

AI-Native DDDの主要フェーズ:

1. 抽出 (Extraction)
2. 審議 (Refinement)
3. 設計と分解 (Decomposition)
4. 自律実装と検証 (Implementation)
5. 昇華 (Sublimation)

### フェーズ別ポイント

* 抽出: 生の素材をAIが理解できる構造化データへ
* 審議: AIに仕様の穴を突かせ、合意を固める
* 設計と分解: AC付きのIssueへ分解し、実装準備を整える
* 実装と検証: AIがテストを通過するまで修正を繰り返す
* 昇華: 実装データを再度NotebookLMで価値ある資産に変換する

## 4. 「今の状況を教えて」の文脈

開発者はVS Code起動時に必ず「今の状況を教えて」とAIに問いかけます。AIは以下をスキャンし、コンテキストを復元します。

1. `docs/progress-status.md`
2. GitHubのオープンIssue
3. `docs/` 配下の最新設計書とコードの整合性

## 5. 主要コマンドとドキュメント

### 標準コマンド

* `今の状況を教えて`
* `docker-compose up`
* `php artisan test`
* `npm run test:unit`

### 重要ドキュメント

* `docs/requirements/architecture.md`
* `docs/requirements/db.md`
* `docs/requirements/api.md`
* `docs/requirements/decisions/`
* `docs/progress-status.md`
* `README.md`

## 6. 用語集

* Source of Truth: 正しい参照元、ここでは `docs/` がそれにあたる
* Acceptance Criteria (AC): 終了条件、Issueの完了基準
* ハルシネーション: AIが生成するもっともらしい誤答
* 自律実装: AIがテストを実行し、自己修正を繰り返すプロセス
* 昇華: 開発記録をビジネス価値のある資料へ変換するプロセス
