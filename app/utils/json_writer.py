# ==============================================================================
# json_writer.py — JSON Writer
# ==============================================================================
# Purpose: Writes JSON data to output/ in user-friendly manner
# Sections: Imports, Public API
# ==============================================================================

# ==============================================================================
# Imports
# ==============================================================================

# Standard Library -----
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List

# Astral AI ----
from app.models.url_models import ProcessingSummary, UrlInfo, UrlSet, OnboardingResult

# ==============================================================================
# Public exports
# ==============================================================================
__all__ = [
    'JsonWriter',
    'create_timestamped_directory',
    'write_url_set',
    'write_onboarding_result',
]

# ==============================================================================
# Public API
# ==============================================================================

def create_timestamped_directory(site_id: str) -> Path:
    """Create timestamped directory in output folder for site data."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    directory_name = f"{site_id}_{timestamp}"

    output_dir = _get_project_root() / "output"
    full_directory_path = output_dir / directory_name

    full_directory_path.mkdir(parents=True, exist_ok=True)

    return full_directory_path


def write_url_set(directory: Path, url_set: List[UrlInfo], site_id: str, filename: str = "full_url_set.json") -> Path:
    """Write URL set to JSON file with metadata."""
    file_path = directory / filename
    
    url_set_data = UrlSet(
        site_id=site_id,
        timestamp=datetime.now(),
        urls=url_set,
        total_count=len(url_set)
    )

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(url_set_data.model_dump_json(indent=2))

    return file_path


def write_onboarding_result(directory: Path, result: OnboardingResult, filename: str = "onboarding_result.json") -> Path:
    """Write onboarding result to JSON file."""
    file_path = directory / filename

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(result.model_dump_json(indent=2))

    return file_path


class JsonWriter:
    """Handles JSON file writing operations for URL processing output."""
    
    def __init__(self, output_base_dir: Path = None):
        """Initialize JsonWriter with optional custom output directory."""
        if output_base_dir is None:
            self.output_base_dir = _get_project_root()
        else:
            self.output_base_dir = output_base_dir

        self._ensure_directory_exists(self.output_base_dir)
    
    def create_site_directory(self, site_id: str) -> Path:
        """Create timestamped directory for site processing results."""
        timestamp = self._format_timestamp(datetime.now())

        directory_name = f"{site_id}_{timestamp}"
        full_directory_path = self.output_base_dir / directory_name

        self._ensure_directory_exists(full_directory_path)

        return full_directory_path
    
    def write_url_set(self, site_id: str, url_set: List[UrlInfo], filename: str = "full_url_set.json") -> Path:
        """Write complete URL set with metadata to JSON file."""
        directory = self.create_site_directory(site_id)
        file_path = directory / filename

        url_set_data = UrlSet(
            site_id=site_id,
            timestamp=datetime.now(),
            urls=url_set,
            total_count=len(url_set)
        )

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(url_set_data.model_dump_json(indent=2))

        return file_path
    
    def write_onboarding_result(self, site_id: str, result: OnboardingResult, filename: str = "onboarding_result.json") -> Path:
        """Write onboarding analysis result to JSON file."""
        directory = self.create_site_directory(site_id)
        file_path = directory / filename

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(result.model_dump_json(indent=2))

        return file_path
    
    def write_processing_summary(self, site_id: str, summary: ProcessingSummary, filename: str = "processing_summary.json") -> Path:
        """Write processing summary with statistics and metadata."""
        directory = self.create_site_directory(site_id)
        file_path = directory / filename

        summary_data = {
            "site_id": site_id,
            "generated_at": datetime.now().isoformat(),
            **summary.model_dump()
        }

        with open(file_path, "w", encoding="utf=8") as file:
            json.dump(summary_data, file, indent=2, ensure_ascii=False)

        return file_path
    
    def _ensure_directory_exists(self, directory: Path) -> None:
        """Ensure output directory exists, create if necessary."""
        directory.mkdir(parents=True, exist_ok=True)
    
    def _format_timestamp(self, dt: datetime) -> str:
        """Format datetime for directory naming."""
        return dt.strftime("%Y%m%d_%H%M%S")

# ==============================================================================
# Helper Functions
# ==============================================================================
def _get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.parent.parent