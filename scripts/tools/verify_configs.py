import glob
import logging
import os
import sys

import yaml
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class SelectorConfig(BaseModel):
    title: str | list[str]
    body: str | list[str]
    # Optional fields
    date: str | list[str] | None = None
    address_hint: str | list[str] | None = None


class UrlPatterns(BaseModel):
    intro_top: str | None = None
    detail_article: str | None = None
    skip: list[str] | None = None


class MunicipalConfig(BaseModel):
    name: str
    pref: str
    city: str
    start_urls: list[str]
    url_patterns: UrlPatterns | None = None
    selectors: SelectorConfig
    # Optional
    pagination: dict | None = None
    address_patterns: list[str] | None = None
    keywords: dict | None = None


def verify_configs() -> int:
    config_dir = "configs/municipal"
    files = glob.glob(os.path.join(config_dir, "*.yaml"))

    if not files:
        logger.error(f"No config files found in {config_dir}")
        return 1

    error_count = 0

    for file_path in files:
        filename = os.path.basename(file_path)
        try:
            with open(file_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Validate against schema
            # Some configs might be partial or have different structures,
            # but they should generally follow the MunicipalConfig schema.
            # Special case: municipal_tokyo_metropolitan.yaml might be different?

            MunicipalConfig(**data)
            logger.info(f"✅ {filename}: Valid")

        except ValidationError as e:
            logger.error(f"❌ {filename}: Validation Error")
            for err in e.errors():
                logger.error(f"  - {err['loc']}: {err['msg']}")
            error_count += 1
        except Exception as e:
            logger.error(f"❌ {filename}: Failed to load ({e})")
            error_count += 1

    if error_count > 0:
        logger.error(f"Verification failed with {error_count} errors.")
        return 1

    logger.info("All configs verified successfully.")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(verify_configs())
