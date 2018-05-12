CREATE TABLE candidate_infos (
    sha256 VARCHAR(65) PRIMARY KEY ON CONFLICT IGNORE,
    name VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    package_type VARCHAR(15) NOT NULL,
    source VARCHAR(200) NOT NULL,
    url VARCHAR(300) NOT NULL,
    requirements_cached TINYINT NOT NULL
);
CREATE TABLE requirement_infos (
    id INTEGER PRIMARY KEY,
    candidate_sha256 VARCHAR(65) NOT NULL,
    name VARCHAR(50) NOT NULL,
    specifier VARCHAR(50) NOT NULL,
    extras VARCHAR(50),
    marker VARCHAR(50),
    FOREIGN KEY (candidate_sha256) REFERENCES candidate_infos(sha256)
);
