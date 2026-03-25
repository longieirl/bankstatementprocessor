"""Template registry for loading and managing bank templates."""

from __future__ import annotations

import json
import logging
import os
from importlib.resources import files
from pathlib import Path

from bankstatements_core.templates.template_model import (
    BankTemplate,
    TemplateDetectionConfig,
    TemplateExtractionConfig,
    TemplateProcessingConfig,
)

logger = logging.getLogger(__name__)


class TemplateRegistry:
    """Registry for loading and managing bank statement templates."""

    def __init__(self, templates: dict[str, BankTemplate], default_template_id: str):
        """Initialize registry with templates.

        Args:
            templates: Dictionary mapping template IDs to BankTemplate objects
            default_template_id: ID of the default template to use
        """
        self._templates = templates
        self._default_template_id = default_template_id

        if default_template_id not in templates:
            raise ValueError(
                f"Default template '{default_template_id}' not found in templates"
            )

    @classmethod
    def from_json(cls, config_path: Path) -> "TemplateRegistry":
        """Load templates from JSON configuration file.

        Args:
            config_path: Path to JSON configuration file

        Returns:
            TemplateRegistry instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Template config not found: {config_path}")

        with open(config_path, "r") as f:
            config = json.load(f)

        # Validate config structure
        if "templates" not in config:
            raise ValueError("Config must contain 'templates' key")

        if "default_template" not in config:
            raise ValueError("Config must contain 'default_template' key")

        # Parse templates
        templates = {}
        for template_id, template_data in config["templates"].items():
            try:
                template = cls._parse_template(template_id, template_data)
                templates[template_id] = template
                logger.debug(f"Loaded template: {template_id} ({template.name})")
            except (ValueError, KeyError, TypeError) as e:
                # Expected errors: invalid values, missing keys, type errors in template config
                logger.error(f"Failed to parse template '{template_id}': {e}")
                raise ValueError(f"Invalid template '{template_id}': {e}") from e
            # Let unexpected errors bubble up

        default_template_id = config["default_template"]

        logger.info(
            f"Loaded {len(templates)} templates from {config_path} "
            f"(default: {default_template_id})"
        )

        return cls(templates, default_template_id)

    @classmethod
    def from_default_config(cls) -> "TemplateRegistry":
        """Load templates from default or configured directory.

        Supports custom template directory for user-added templates.

        Loading priority:
        1. Custom templates from CUSTOM_TEMPLATES_DIR (highest priority)
        2. Built-in templates from BANK_TEMPLATES_DIR or ./templates
        3. Default template used as fallback

        Environment Variables:
            BANK_TEMPLATES_DIR: Built-in templates (default: ./templates)
            CUSTOM_TEMPLATES_DIR: Custom developer templates (optional)

        Returns:
            TemplateRegistry instance with all templates merged

        Example:
            # Create custom template in custom_templates/mybank.json
            export CUSTOM_TEMPLATES_DIR=./custom_templates
            # Your custom template will be loaded and available
        """
        default_dir_str = os.getenv("BANK_TEMPLATES_DIR")
        default_dir: Path
        if not default_dir_str:
            # Resolve bundled templates from the installed package using importlib.resources.
            # This works correctly whether the package is installed from PyPI, as an
            # editable install, or run from a source checkout.
            default_dir = Path(str(files("bankstatements_core.templates")))
        else:
            default_dir = Path(default_dir_str)

        custom_dir_str = os.getenv("CUSTOM_TEMPLATES_DIR")

        # If custom directory specified, load both custom and default
        if custom_dir_str:
            return cls.from_multiple_directories([Path(custom_dir_str), default_dir])
        else:
            return cls.from_directory(default_dir)

    @classmethod
    def from_directory(cls, templates_dir: Path | str) -> "TemplateRegistry":
        """Load all templates from a directory.

        Args:
            templates_dir: Path to directory containing template JSON files

        Returns:
            TemplateRegistry with all loaded templates

        Raises:
            FileNotFoundError: If directory doesn't exist
            ValueError: If no valid templates found
        """
        templates_path = Path(templates_dir)
        if not templates_path.exists():
            raise FileNotFoundError(f"Templates directory not found: {templates_path}")

        # Find all JSON files
        template_files = list(templates_path.glob("*.json"))
        if not template_files:
            raise ValueError(f"No template files found in {templates_path}")

        # Load templates from each file
        all_templates: dict[str, BankTemplate] = {}
        for template_file in template_files:
            try:
                template = cls._load_single_template(template_file)
                if template:
                    all_templates[template.id] = template
                    logger.info(
                        f"Loaded template: {template.id} from {template_file.name}"
                    )
            except (ValueError, KeyError, TypeError, OSError) as e:
                # Expected errors: invalid template format, missing keys, file I/O errors
                logger.warning(f"Failed to load {template_file.name}: {e}")
                continue
            # Let unexpected errors bubble up

        if not all_templates:
            raise ValueError(f"No valid templates loaded from {templates_path}")

        # Determine default template
        default_id = os.getenv("DEFAULT_TEMPLATE")
        if default_id and default_id not in all_templates:
            logger.warning(
                f"DEFAULT_TEMPLATE '{default_id}' not found, using first enabled"
            )
            default_id = None

        if not default_id:
            # Use first enabled template as default
            enabled_templates = [t for t in all_templates.values() if t.enabled]
            default_id = (
                enabled_templates[0].id
                if enabled_templates
                else list(all_templates.keys())[0]
            )

        logger.info(
            f"Loaded {len(all_templates)} templates: "
            f"{', '.join(t.name for t in all_templates.values())} "
            f"(default: {default_id})"
        )

        return cls(templates=all_templates, default_template_id=default_id)

    @classmethod
    def from_multiple_directories(
        cls, directories: list[Path | str]
    ) -> "TemplateRegistry":
        """Load templates from multiple directories with priority order.

        Templates from earlier directories have higher priority and can override
        templates from later directories (based on template ID).

        Args:
            directories: List of directories to load templates from (in priority order)

        Returns:
            TemplateRegistry with all templates merged

        Raises:
            ValueError: If no valid templates found in any directory

        Example:
            # Load custom templates first, then built-in templates
            registry = TemplateRegistry.from_multiple_directories([
                Path("./custom_templates"),
                Path("./templates")
            ])
        """
        all_templates: dict[str, BankTemplate] = {}
        template_sources: dict[str, str] = {}  # Track where each template came from

        # Load templates from each directory in order
        for directory in directories:
            templates_path = Path(directory)

            # Skip if directory doesn't exist (custom dir may be optional)
            if not templates_path.exists():
                logger.info(f"Skipping non-existent directory: {templates_path}")
                continue

            # Find all JSON files
            template_files = list(templates_path.glob("*.json"))
            if not template_files:
                logger.info(f"No template files found in {templates_path}")
                continue

            # Load templates from each file
            for template_file in template_files:
                try:
                    template = cls._load_single_template(template_file)
                    if template:
                        # Check if template already exists
                        # (higher priority dir loaded it first)
                        if template.id in all_templates:
                            logger.info(
                                f"Template '{template.id}' from "
                                f"{template_sources[template.id]} "
                                f"(higher priority) - skipping "
                                f"{template_file.name}"
                            )
                            continue  # Skip, keep higher priority one

                        # Add new template
                        all_templates[template.id] = template
                        template_sources[template.id] = template_file.name
                        logger.info(
                            f"Loaded template: {template.id} from {template_file.name}"
                        )
                except (ValueError, KeyError, TypeError, OSError) as e:
                    # Expected errors: invalid template format, missing keys, file I/O errors
                    logger.warning(f"Failed to load {template_file.name}: {e}")
                    continue
                # Let unexpected errors bubble up

        if not all_templates:
            raise ValueError("No valid templates loaded from any directory")

        # Determine default template
        default_id = os.getenv("DEFAULT_TEMPLATE")
        if default_id and default_id not in all_templates:
            logger.warning(
                f"DEFAULT_TEMPLATE '{default_id}' not found, using first enabled"
            )
            default_id = None

        if not default_id:
            # Use first enabled template as default, prioritizing "default" if it exists
            if "default" in all_templates and all_templates["default"].enabled:
                default_id = "default"
            else:
                enabled_templates = [t for t in all_templates.values() if t.enabled]
                default_id = (
                    enabled_templates[0].id
                    if enabled_templates
                    else list(all_templates.keys())[0]
                )

        template_names = ", ".join(t.name for t in all_templates.values())
        logger.info(
            f"Loaded {len(all_templates)} templates from "
            f"{len(directories)} directories: "
            f"{template_names} (default: {default_id})"
        )

        return cls(templates=all_templates, default_template_id=default_id)

    @classmethod
    def _load_single_template(cls, template_file: Path) -> BankTemplate | None:
        """Load a single template from a JSON file.

        Args:
            template_file: Path to template JSON file

        Returns:
            BankTemplate if valid, None if invalid
        """
        with open(template_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Single template format (new)
        if "id" in data:
            return cls._parse_template(data["id"], data)

        # Legacy format with templates dict (for backward compatibility)
        if "templates" in data and len(data["templates"]) == 1:
            template_id = list(data["templates"].keys())[0]
            template_data = data["templates"][template_id]
            return cls._parse_template(template_id, template_data)

        logger.warning(f"Invalid template format in {template_file.name}")
        return None

    @staticmethod
    def _parse_template(template_id: str, data: dict) -> BankTemplate:
        """Parse template from JSON data.

        Args:
            template_id: Unique template identifier
            data: Template configuration dictionary

        Returns:
            BankTemplate instance
        """
        # Parse detection config
        detection_data = data.get("detection", {})

        # NEW: Parse document_identifiers (supports both new and legacy formats)
        document_identifiers = {}

        if "document_identifiers" in detection_data:
            # New format: document_identifiers dictionary
            document_identifiers = detection_data["document_identifiers"]
        elif "iban_patterns" in detection_data:
            # Legacy format: wrap iban_patterns for backward compatibility
            document_identifiers = {"iban_patterns": detection_data["iban_patterns"]}

        # Extract legacy iban_patterns for backward compatibility
        iban_patterns = document_identifiers.get("iban_patterns", [])

        detection = TemplateDetectionConfig(
            iban_patterns=iban_patterns,  # Legacy field
            document_identifiers=document_identifiers,  # NEW
            filename_patterns=detection_data.get("filename_patterns", []),
            header_keywords=detection_data.get("header_keywords", []),
            column_headers=detection_data.get("column_headers", []),
            exclude_keywords=detection_data.get("exclude_keywords", []),
        )

        # Parse extraction config
        extraction_data = data.get("extraction", {})
        if not extraction_data:
            raise ValueError("Template must contain 'extraction' configuration")

        columns = {}
        for col_name, coords in extraction_data.get("columns", {}).items():
            if not isinstance(coords, list) or len(coords) != 2:
                raise ValueError(
                    f"Column '{col_name}' must have [x_start, x_end] coordinates"
                )
            columns[col_name] = tuple(coords)

        # Parse per-page overrides (NEW)
        from bankstatements_core.templates.template_model import PerPageBoundaries

        per_page_overrides = {}
        if "per_page_overrides" in extraction_data:
            for page_str, override_data in extraction_data[
                "per_page_overrides"
            ].items():
                page_num = int(page_str)
                per_page_overrides[page_num] = PerPageBoundaries(
                    table_top_y=override_data.get("table_top_y"),
                    table_bottom_y=override_data.get("table_bottom_y"),
                    header_check_top_y=override_data.get("header_check_top_y"),
                )

        extraction = TemplateExtractionConfig(
            table_top_y=extraction_data.get("table_top_y"),
            table_bottom_y=extraction_data.get("table_bottom_y"),
            columns=columns,
            enable_page_validation=extraction_data.get("enable_page_validation", True),
            enable_header_check=extraction_data.get("enable_header_check"),
            header_check_top_y=extraction_data.get("header_check_top_y"),
            per_page_overrides=per_page_overrides,  # NEW
        )

        # Parse processing config (optional)
        processing_data = data.get("processing", {})
        processing = TemplateProcessingConfig(
            supports_multiline=processing_data.get("supports_multiline", False),
            date_format=processing_data.get("date_format", "%d/%m/%Y"),
            currency_symbol=processing_data.get("currency_symbol", "€"),
            decimal_separator=processing_data.get("decimal_separator", "."),
        )

        # Parse document_type with default fallback
        document_type = data.get("document_type", "bank_statement")

        return BankTemplate(
            id=template_id,
            name=data.get("name", template_id),
            enabled=data.get("enabled", True),
            detection=detection,
            extraction=extraction,
            processing=processing,
            document_type=document_type,
        )

    def get_template(self, template_id: str) -> BankTemplate | None:
        """Get template by ID.

        Args:
            template_id: Template identifier

        Returns:
            BankTemplate if found and enabled, None otherwise
        """
        template = self._templates.get(template_id)

        if template and not template.enabled:
            logger.warning(f"Template '{template_id}' is disabled")
            return None

        return template

    def get_default(self) -> BankTemplate:
        """Get the default template.

        Returns:
            Default BankTemplate
        """
        return self._templates[self._default_template_id]

    def get_default_template(self) -> BankTemplate:
        """Get the default template (alias for backwards compatibility).

        Returns:
            Default BankTemplate
        """
        return self.get_default()

    def get_all_templates(self) -> list[BankTemplate]:
        """Get all enabled templates.

        Returns:
            List of enabled BankTemplate objects
        """
        return [t for t in self._templates.values() if t.enabled]

    def get_templates_by_type(self, document_type: str) -> list[BankTemplate]:
        """Get all enabled templates for a specific document type.

        Args:
            document_type: Document type to filter by ("bank_statement", "credit_card_statement", etc.)

        Returns:
            List of enabled templates matching the document type.
            Returns empty list if no templates found for that type.
        """
        filtered = [
            t
            for t in self._templates.values()
            if t.enabled and t.document_type == document_type
        ]

        logger.debug(
            f"Found {len(filtered)} enabled templates for document_type='{document_type}'"
        )
        return filtered

    def get_default_for_type(self, document_type: str) -> BankTemplate:
        """Get default template for a specific document type.

        Args:
            document_type: Document type ("bank_statement", "credit_card_statement", etc.)

        Returns:
            Default template for that document type, or global default if not found.
        """
        # Look for document-type-specific default (e.g., "credit_card_default")
        type_default_id = f"{document_type.replace('_statement', '')}_default"

        if (
            type_default_id in self._templates
            and self._templates[type_default_id].enabled
        ):
            logger.debug(f"Using type-specific default: {type_default_id}")
            return self._templates[type_default_id]

        # Fallback to first enabled template of that type
        type_templates = self.get_templates_by_type(document_type)
        if type_templates:
            logger.debug(
                f"Using first enabled template for {document_type}: {type_templates[0].id}"
            )
            return type_templates[0]

        # Final fallback to global default
        logger.debug(f"No templates found for {document_type}, using global default")
        return self.get_default()

    def list_enabled(self) -> list[BankTemplate]:
        """Get all enabled templates (alias for get_all_templates).

        Returns:
            List of enabled BankTemplate objects
        """
        return self.get_all_templates()

    def list_all(self) -> list[BankTemplate]:
        """Get all templates regardless of enabled status.

        Returns:
            List of all BankTemplate objects
        """
        return list(self._templates.values())

    def get_template_ids(self) -> list[str]:
        """Get all template IDs.

        Returns:
            List of template IDs
        """
        return list(self._templates.keys())

    def filtered_by_ids(self, ids: set[str]) -> "TemplateRegistry":
        """Return a new registry containing only the templates with the given IDs.

        The shared registry is never mutated. The default template is preserved if
        it is in the filtered set; otherwise the first matching template is used.

        Args:
            ids: Set of template IDs to include

        Returns:
            New TemplateRegistry containing only the specified templates

        Raises:
            ValueError: If none of the given IDs exist in this registry
        """
        filtered = {tid: t for tid, t in self._templates.items() if tid in ids}
        if not filtered:
            raise ValueError(f"No templates matched the given IDs: {ids}")

        default_id = (
            self._default_template_id
            if self._default_template_id in filtered
            else next(iter(filtered))
        )
        return TemplateRegistry(filtered, default_id)
