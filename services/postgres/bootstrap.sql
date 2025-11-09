CREATE SCHEMA boobies;
SET search_path TO boobies;

CREATE TABLE examples (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

insert into examples (name) values
('Team A'),
('Team B');

-- authentik
CREATE DATABASE authentik;
CREATE USER authentik WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE authentik TO authentik;
ALTER DATABASE authentik OWNER TO authentik;