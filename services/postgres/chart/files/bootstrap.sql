CREATE SCHEMA bootstrap_example;
SET search_path TO bootstrap_example;

CREATE TABLE examples (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

insert into examples (name) values
('Team A'),
('Team B');
