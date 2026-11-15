# コードガイド：src/main.rs の構造と言語解説

## 1. プログラムの全体構造

```
src/main.rs
│
├── use（インポート宣言）
├── type AppState          # 型エイリアス
│
├── struct Item            # DBのレコードに対応するデータ型
├── struct ItemsTemplate   # Askamaテンプレートに渡すデータ型
├── struct HtmlTemplate<T> # テンプレートをHTTPレスポンスに変換するラッパー
│   └── impl IntoResponse
│
├── async fn index         # GET /  ハンドラ（HTML）
├── async fn api_items     # GET /api/items ハンドラ（JSON）
└── async fn main          # 起動処理（DB接続・ルーティング・サーバー）
```

---

## 2. use（インポート宣言）

```rust
use askama::Template;
use axum::{Router, extract::State, ...};
use sqlx::PgPool;
use std::sync::Arc;
```

他のクレート（ライブラリ）や標準ライブラリから必要な型・関数を取り込む。
`use` で宣言しておくことで、コード中で完全なパスを省略して記述できる。

---

## 3. 型エイリアス

```rust
type AppState = Arc<PgPool>;
```

`Arc<PgPool>` という長い型に `AppState` という短い別名をつける。
コード各所で `Arc<PgPool>` と書く代わりに `AppState` と書けるようになる。

### Arc（Atomic Reference Counted）

`Arc<T>` は、複数の箇所から同じデータを **安全に共有する** ためのスマートポインタ。
Webサーバーでは複数のリクエストが同時に処理されるため、DBコネクションプールを
全ハンドラで共有するのに使う。`Arc` が参照カウントを管理し、誰も使わなくなった
タイミングでメモリを解放する（GCなしで安全な共有を実現する仕組み）。

---

## 4. struct と derive（データ型の定義）

```rust
#[derive(Serialize, sqlx::FromRow)]
struct Item {
    id: i32,
    name: String,
    description: Option<String>,
}
```

### struct

データをまとめる型。他言語のクラス（フィールドのみ）に相当する。

### #[derive(...)]

`derive` はコンパイル時に指定したトレイト（インターフェース）の実装を自動生成する
アトリビュート（属性）。

| derive | 効果 |
|---|---|
| `Serialize` | JSON文字列へ変換できるようになる（serde クレート） |
| `sqlx::FromRow` | SQLの結果行を自動的に `Item` 構造体にマッピングする |

### Option\<String\>

`Option<T>` は「値があるかもしれないし、ないかもしれない」を表す型。
NULL許容カラムに対応する。

| 値 | 意味 |
|---|---|
| `Some("説明文")` | 値あり |
| `None` | NULLまたは値なし |

Rustには `null` がなく、NULLの可能性は必ず `Option` で明示する。
これにより、NULLチェック忘れによるバグをコンパイル時に防げる。

---

## 5. ジェネリクスと型制約

```rust
struct HtmlTemplate<T>(T);

impl<T: Template> IntoResponse for HtmlTemplate<T> {
    fn into_response(self) -> Response { ... }
}
```

### ジェネリクス `<T>`

`T` は「任意の型」を表すプレースホルダー。
`HtmlTemplate<ItemsTemplate>` のように具体的な型を当てはめて使う。
型ごとに同じコードを書き直す必要がなくなる。

### トレイト制約 `T: Template`

「`T` は `Template` トレイトを実装している型に限る」という制約。
この制約があることで、`T` に対して `.render()` メソッドを安全に呼び出せる。

### impl（トレイト実装）

`impl IntoResponse for HtmlTemplate<T>` は
「`HtmlTemplate<T>` に `IntoResponse` というトレイトを実装する」という宣言。
Axum は `IntoResponse` を実装した型ならハンドラの戻り値として受け取れる。

### match（パターンマッチ）

```rust
match self.0.render() {
    Ok(html) => Html(html).into_response(),
    Err(_)   => StatusCode::INTERNAL_SERVER_ERROR.into_response(),
}
```

`render()` の戻り値 `Result<String, Error>` を分岐して処理する。
`Ok(html)` なら成功、`Err(_)` ならエラー（`_` は値を使わないことを示す）。
Rustでは `if/else` より `match` を使った網羅的な分岐が推奨される。

---

## 6. 非同期処理（async / await）

```rust
async fn index(...) -> Result<...> {
    let items = sqlx::query_as::<_, Item>(...)
        .fetch_all(pool.as_ref())
        .await
        ...;
}
```

### async fn

非同期関数の宣言。呼び出しただけでは実行されず、`.await` したタイミングで実行される。
I/O（DB通信・ネットワーク）の待ち時間中に他のリクエストを処理できるため、
スレッドを大量に使わずに高い並行性を実現できる。

### tokio

Rustの非同期ランタイム。`async/await` を実際に動かすエンジン。

```rust
#[tokio::main]
async fn main() { ... }
```

`#[tokio::main]` アトリビュートにより、`main` 関数を非同期関数として実行できるようになる。

---

## 7. Result 型とエラーハンドリング

```rust
async fn index(...) -> Result<HtmlTemplate<ItemsTemplate>, StatusCode> {
    let items = ...
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(HtmlTemplate(ItemsTemplate { items }))
}
```

### Result\<T, E\>

成功（`Ok(T)`）か失敗（`Err(E)`）を表す型。
Rustには例外（Exception）がなく、エラーは必ず `Result` で返す。

### `?` 演算子

`Err` だった場合に即座に関数から `Err` を返す省略記法。
これがないと `match` でエラー処理を毎回書く必要がある。

### map_err

`Err` の中身の型を変換する。
ここでは sqlx のエラー型を `StatusCode`（HTTPステータスコード）に変換している。

---

## 8. State（依存性の注入）

```rust
async fn index(State(pool): State<AppState>) -> ... {
```

Axumの `State` は、ハンドラ関数にアプリケーション共有データを注入する仕組み。
`main` で `with_state(state)` に渡した `AppState`（DBプール）を、
各ハンドラが `State(pool)` という引数で受け取れる。

Laravelの依存性注入（サービスコンテナ）に相当するが、
型で管理されるためコンパイル時に整合性が保証される。

---

## 9. 起動フロー（main 関数）

```
1. dotenvy::dotenv()       .env ファイルを環境変数として読み込む
2. PgPool::connect()       PostgreSQLへ接続し、コネクションプールを作成
3. sqlx::migrate!().run()  migrations/ 配下のSQLを実行（未適用分のみ）
4. Arc::new(pool)          プールを Arc で包み、複数ハンドラで共有できる形にする
5. Router::new()           ルーティングを定義
6. axum::serve()           TCPポート3000でサーバーを起動
```

---

## 10. クレート（ライブラリ）一覧

| クレート | 役割 |
|---|---|
| `axum` | Webフレームワーク。ルーティング・ハンドラ・レスポンス |
| `tokio` | 非同期ランタイム |
| `sqlx` | PostgreSQL非同期クライアント。コンパイル時クエリ検証対応 |
| `askama` | コンパイル時テンプレートエンジン。型安全なHTML生成 |
| `serde` | シリアライズ/デシリアライズ（JSON変換など） |
| `dotenvy` | `.env` ファイルの読み込み |
