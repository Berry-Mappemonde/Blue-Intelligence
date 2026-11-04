-- One-off administrator setup. Never execute from an application agent.
-- Independent port registries, read in place from Zetaris platform storage:
--   UN/LOCODE port entries (UNECE, https://unlocode.unece.org/downloads/unlocode-latest.zip)
--   World Port Index, NGA Pub 150 (US public domain, https://msi.nga.mil/Publications/WPI)
-- zetaris_setup.py --part registries downloads both, keeps the fields below, writes
-- {registry_dir}/unlocode_ports.csv and {registry_dir}/wpi_ports.csv, then runs this file.
-- Requires the blue_intel schemastore container (zetaris_setup_poe.sql).
CREATE LIGHTNING DATABASE BLUE_INTEL_REGISTRIES DESCRIBE BY "Independent port registries, UN-LOCODE by UNECE and World Port Index by NGA";

CREATE LIGHTNING FILESTORE TABLE unlocode_csv FROM BLUE_INTEL_REGISTRIES FORMAT CSV
OPTIONS (PATH "{registry_dir}/unlocode_ports.csv", header "true", inferSchema "false");

CREATE LIGHTNING FILESTORE TABLE wpi_csv FROM BLUE_INTEL_REGISTRIES FORMAT CSV
OPTIONS (PATH "{registry_dir}/wpi_ports.csv", header "true", inferSchema "false");

CREATE OR REPLACE SCHEMASTORE VIEW unlocode_ports WITH CONTAINER blue_intel AS
SELECT country_iso2, location, code, name, name_ascii, subdivision, function_code, status,
       CAST(lat AS DOUBLE) AS lat, CAST(lon AS DOUBLE) AS lon
FROM blue_intel_registries.unlocode_csv;

CREATE OR REPLACE SCHEMASTORE VIEW wpi_ports WITH CONTAINER blue_intel AS
SELECT wpi_number, name, alternate_name, country_name, country_iso2, unlocode,
       CAST(lat AS DOUBLE) AS lat, CAST(lon AS DOUBLE) AS lon,
       first_port_of_entry, quarantine_pratique, quarantine_sanitation, quarantine_other, harbor_use
FROM blue_intel_registries.wpi_csv;
