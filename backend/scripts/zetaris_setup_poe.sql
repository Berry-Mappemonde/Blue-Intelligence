-- One-off administrator setup. Never execute from an application agent.
-- Not idempotent: inspect existing objects before rerunning successful statements.
CREATE LIGHTNING DATABASE BLUE_INTEL_REST DESCRIBE BY "Blue Intelligence public PoE seed";

CREATE SCHEMASTORE CONTAINER blue_intel;

CREATE LIGHTNING REST TABLE poe_seed FROM BLUE_INTEL_REST
REQUEST(endpoint "https://raw.githubusercontent.com/Berry-Mappemonde/Blue-Intelligence/main/seed/ports_of_entry.geojson", method "get", response_type "json", http_encoding "URLENCODED")
HEADER () BODY ();

CREATE SCHEMASTORE VIEW poe_ports WITH CONTAINER blue_intel AS
SELECT
    feature.properties.id AS id,
    feature.properties.name AS name,
    feature.properties.city AS city,
    feature.properties.mrgid AS mrgid,
    feature.properties.zone_name AS zone_name,
    feature.properties.country_iso2 AS country_iso2,
    feature.properties.validated AS validated,
    feature.properties.geocode_source AS geocode_source,
    feature.properties.source_urls AS source_urls,
    feature.properties.extracted_at AS extracted_at,
    feature.geometry.coordinates[0] AS lon,
    feature.geometry.coordinates[1] AS lat
FROM blue_intel_rest.poe_seed
LATERAL VIEW explode(features) AS feature;
