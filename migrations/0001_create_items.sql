CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO items (name, description) VALUES
    ('Rust',    'システムプログラミング言語。安全性と高速性を両立する'),
    ('Axum',    'Rustの非同期Webフレームワーク。tokioベース'),
    ('sqlx',    'RustのPostgreSQL/MySQL非同期クライアント。コンパイル時クエリ検証対応'),
    ('Docker',  'コンテナ型仮想化プラットフォーム。DB環境をローカルで再現する'),
    ('AI-DDD',  'AIネイティブ・ドキュメント駆動開発。ドキュメントをエンジンとして活用する');
