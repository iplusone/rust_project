use askama::Template;
use axum::{
    Router,
    extract::State,
    http::StatusCode,
    response::{Html, IntoResponse, Json, Response},
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

#[derive(Template)]
#[template(path = "items.html")]
struct ItemsTemplate {
    items: Vec<Item>,
}

struct HtmlTemplate<T>(T);

// AskamaテンプレートをAxumのHTTPレスポンスに変換する汎用ラッパー
impl<T: Template> IntoResponse for HtmlTemplate<T> {
    fn into_response(self) -> Response {
        match self.0.render() {
            Ok(html) => Html(html).into_response(),
            Err(_) => StatusCode::INTERNAL_SERVER_ERROR.into_response(),
        }
    }
}

// GET / : DBからアイテム一覧を取得し、HTMLテンプレートで描画して返す
async fn index(State(pool): State<AppState>) -> Result<HtmlTemplate<ItemsTemplate>, StatusCode> {
    let items = sqlx::query_as::<_, Item>(
        "SELECT id, name, description FROM items ORDER BY id",
    )
    .fetch_all(pool.as_ref())
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(HtmlTemplate(ItemsTemplate { items }))
}

// GET /api/items : DBからアイテム一覧を取得し、JSON形式で返す
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
// アプリケーションのエントリーポイント。DB接続・マイグレーション・ルーティング・サーバー起動を行う
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
