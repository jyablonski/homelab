CREATE SCHEMA boobies;
SET search_path TO boobies;

CREATE TABLE examples (
    id SERIAL PRIMARY KEY,
    team_name VARCHAR(50) NOT NULL,
    motto VARCHAR(100) NOT NULL
);
