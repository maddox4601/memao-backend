-- 创建非 root 用户并授权
CREATE USER IF NOT EXISTS 'memao_prod_user'@'%' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO 'memao_prod_user'@'%';
FLUSH PRIVILEGES;

-- 安全加固：限制 root 用户只能本地访问（可选）
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1');