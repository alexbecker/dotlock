CREATE TABLE candidate_infos (
    hash_val VARCHAR(65) PRIMARY KEY ON CONFLICT IGNORE,
    hash_alg VARCHAR(20) NOT NULL,
    name VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    package_type VARCHAR(15) NOT NULL,
    source VARCHAR(200) NOT NULL,
    location VARCHAR(300) NOT NULL,
    requirements_cached TINYINT NOT NULL
);
CREATE TABLE requirement_infos (
    id INTEGER PRIMARY KEY,
    candidate_hash VARCHAR(65) NOT NULL,
    name VARCHAR(50) NOT NULL,
    specifier VARCHAR(300),
    extras VARCHAR(50),
    marker VARCHAR(50),
    FOREIGN KEY (candidate_hash) REFERENCES candidate_infos(hash_val)
);
