#!/usr/bin/env python
"""Gera mocks de rating de CNPJ a partir dos arquivos de referencia em json/
e opcionalmente publica os arquivos gerados no S3 do ambiente informado.
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rating_mock")

SOURCE_CNPJ = "00009838000146"
JSON_DIR = Path(__file__).resolve().parent / "json"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# suffixo do arquivo de referencia -> prefixo S3 (bureau) de destino
FILE_DESTINATIONS = {
    "_liquidez.json": "bronze/input/bureaus/nuclea/cnpj/json",
    "_quod.json": "bronze/input/bureaus/quod/cnpj/json",
    "_quod.bevoc": "bronze/input/bureaus/quod/cnpj/bevoc",
    "_proscore.json": "bronze/input/bureaus/proscore/cnpj/json",
    "_proscore_kyc.json": "bronze/input/bureaus/proscore/cnpj/json",
    "_basic_data.json": "bronze/input/bureaus/bigdatacorp/cnpj/json",
    "_history_basic_data.json": "bronze/input/bureaus/bigdatacorp/cnpj/json",
    "_economic_group_relationships.json": "bronze/input/bureaus/bigdatacorp/cnpj/json",
    "_registration_data.json": "bronze/input/bureaus/bigdatacorp/cnpj/json",
    "_kyc_pj.json": "bronze/input/bureaus/bigdatacorp/cnpj/json",
    "_negative_media.json": "bronze/input/bureaus/kappi/cnpj/json",
}

ENVIRONMENTS = {
    "dev": {"bucket": "dev-bevoc-datalake", "profile": "grafeno-dev"},
    "stg": {"bucket": "stg-bevoc-datalake", "profile": "grafeno-stg"},
    "prd": {"bucket": "prd-bevoc-datalake", "profile": "grafeno-prd"},
}


@dataclass
class PlannedFile:
    source: Path
    target_name: str
    s3_prefix: str


def normalize_cnpj(raw_cnpj: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", raw_cnpj).upper()
    if len(cleaned) != 14:
        raise ValueError(
            f"CNPJ invalido: '{raw_cnpj}' -> {len(cleaned)} caractere(s) alfanumerico(s), esperado 14."
        )
    return cleaned


def plan_files(cnpj: str) -> list[PlannedFile]:
    planned = []
    for suffix, s3_prefix in FILE_DESTINATIONS.items():
        source = JSON_DIR / f"{SOURCE_CNPJ}{suffix}"
        if not source.exists():
            log.warning("Arquivo de referencia nao encontrado, pulando: %s", source)
            continue
        planned.append(PlannedFile(source=source, target_name=f"{cnpj}{suffix}", s3_prefix=s3_prefix))
    if not planned:
        raise FileNotFoundError(f"Nenhum arquivo de referencia encontrado em {JSON_DIR}")
    return planned


def build_mock_content(source: Path, cnpj: str) -> str:
    content = source.read_text(encoding="utf-8")
    return content.replace(SOURCE_CNPJ, cnpj)


def write_local_mocks(planned: list[PlannedFile], cnpj: str) -> list[Path]:
    dest_dir = OUTPUT_DIR / cnpj
    dest_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for item in planned:
        content = build_mock_content(item.source, cnpj)
        out_path = dest_dir / item.target_name
        out_path.write_text(content, encoding="utf-8")
        written.append(out_path)
        log.info("Mock gerado: %s", out_path)
    return written


def upload_to_s3(planned: list[PlannedFile], cnpj: str, env: str) -> None:
    env_cfg = ENVIRONMENTS[env]
    bucket = env_cfg["bucket"]
    profile = env_cfg["profile"]

    session = boto3.Session(profile_name=profile)
    s3 = session.client("s3")

    for item in planned:
        content = build_mock_content(item.source, cnpj)
        key = f"{item.s3_prefix}/{item.target_name}"
        content_type = (
            "application/json"
            if item.target_name.endswith(".json")
            else "binary/octet-stream"
        )
        try:
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            log.error("Falha ao enviar s3://%s/%s: %s", bucket, key, exc)
            raise
        log.info("Enviado: s3://%s/%s (profile=%s)", bucket, key, profile)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "cnpj",
        help="CNPJ de destino (com ou sem mascara), 14 caracteres alfanumericos.",
    )
    parser.add_argument(
        "--env",
        choices=sorted(ENVIRONMENTS),
        help="Ambiente de destino para upload no S3 (dev, stg ou prd). "
        "Se omitido, apenas gera os arquivos localmente.",
    )
    parser.add_argument(
        "--no-local",
        action="store_true",
        help="Nao escrever copia local em output/<cnpj>/ (apenas enviar ao S3).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria feito, sem enviar nada ao S3.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        cnpj = normalize_cnpj(args.cnpj)
    except ValueError as exc:
        log.error(str(exc))
        return 1

    planned = plan_files(cnpj)

    if not args.no_local:
        write_local_mocks(planned, cnpj)

    if args.env:
        if args.dry_run:
            env_cfg = ENVIRONMENTS[args.env]
            log.info(
                "[dry-run] seria enviado para s3://%s (profile=%s):",
                env_cfg["bucket"],
                env_cfg["profile"],
            )
            for item in planned:
                log.info("  - %s/%s", item.s3_prefix, item.target_name)
        else:
            upload_to_s3(planned, cnpj, args.env)

    return 0


if __name__ == "__main__":
    sys.exit(main())
