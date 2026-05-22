use axum::{
    Router,
    extract::State,
    http::StatusCode,
    response::{Html, Json},
    routing::get,
};
use serde::Serialize;
use sqlx::PgPool;
use std::sync::Arc;

type AppState = Arc<PgPool>;

#[derive(Serialize, sqlx::FromRow)]
struct Item {
    id: i32,
    name: String,
    description: Option<String>,
}

async fn index(State(pool): State<AppState>) -> Result<Html<String>, StatusCode> {
    let items = sqlx::query_as::<_, Item>(
        "SELECT id, name, description FROM items ORDER BY id",
    )
    .fetch_all(pool.as_ref())
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let rows = items
        .iter()
        .map(|item| {
            format!(
                "<tr><td>{}</td><td>{}</td><td>{}</td></tr>",
                item.id,
                item.name,
                item.description.as_deref().unwrap_or("-")
            )
        })
        .collect::<Vec<_>>()
        .join("\n");

    let html = format!(
        r#"<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>rust_project</title>
  <style>
    body {{ font-family: sans-serif; padding: 2rem; background: #fafafa; }}
    h1 {{ color: #333; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 700px; background: #fff; }}
    th, td {{ border: 1px solid #ddd; padding: 0.6rem 1rem; text-align: left; }}
    th {{ background: #f0f0f0; font-weight: bold; }}
    tr:hover {{ background: #f9f9f9; }}
    a {{ color: #0066cc; }}
  </style>
</head>
<body>
  <h1>Items（PostgreSQL から取得）</h1>
  <table>
    <thead><tr><th>ID</th><th>名前</th><th>説明</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <p style="margin-top:1rem"><a href="/api/items">JSON API → /api/items</a></p>
</body>
</html>"#,
        rows = rows
    );

    Ok(Html(html))
}

async fn api_items(State(pool): State<AppState>) -> Result<Json<Vec<Item>>, StatusCode> {
    let items = sqlx::query_as::<_, Item>(
        "SELECT id, name, description FROM items ORDER BY id",
    )
    .fetch_all(pool.as_ref())
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(items))
}

#[tokio::main]
async fn main() {
    dotenvy::dotenv().ok();

    let database_url = std::env::var("DATABASE_URL").expect("DATABASE_URL must be set");

    let pool = PgPool::connect(&database_url)
        .await
        .expect("DB接続に失敗しました");

    sqlx::migrate!("./migrations")
        .run(&pool)
        .await
        .expect("マイグレーションに失敗しました");

    let state: AppState = Arc::new(pool);

    let app = Router::new()
        .route("/", get(index))
        .route("/api/items", get(api_items))
        .with_state(state);

    println!("サーバー起動: http://localhost:3000");

    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000")
        .await
        .unwrap();
    axum::serve(listener, app).await.unwrap();
}
