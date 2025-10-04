"""
SVG Feature Support Registry.

Provides centralized access to SVG feature support information loaded from
external JSON data file. Uses caching for performance.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from functools import lru_cache


class FeatureRegistry:
    """
    Centralized registry for SVG feature support information.

    Loads feature support data from JSON file and provides query methods
    with caching for performance.
    """

    _DATA_FILE = Path(__file__).parent / "feature_data.json"
    _cache: Optional[Dict[str, Any]] = None

    @classmethod
    @lru_cache(maxsize=1)
    def load(cls) -> Dict[str, Any]:
        """
        Load and cache feature data from JSON file.

        Returns:
            Complete feature support data dictionary

        Raises:
            FileNotFoundError: If feature_data.json is missing
            json.JSONDecodeError: If JSON is malformed
        """
        if cls._cache is None:
            try:
                with open(cls._DATA_FILE, 'r', encoding='utf-8') as f:
                    cls._cache = json.load(f)
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Feature data file not found: {cls._DATA_FILE}. "
                    "Ensure feature_data.json exists in core/analyze/"
                )
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(
                    f"Invalid JSON in feature_data.json: {e.msg}",
                    e.doc,
                    e.pos
                )

        return cls._cache

    @classmethod
    def get_all_features(cls) -> Dict[str, Any]:
        """
        Get complete feature support matrix.

        Returns:
            Dictionary with keys:
            - version: API version string
            - last_updated: ISO date string
            - categories: Dict of feature categories
            - policy_capabilities: Policy feature matrices
            - color_spaces: Color space support info

        Example:
            >>> features = FeatureRegistry.get_all_features()
            >>> features['version']
            '1.0.0'
            >>> features['categories']['filters']['support_level']
            'partial'
        """
        return cls.load()

    @classmethod
    def get_category(cls, category: str) -> Dict[str, Any]:
        """
        Get specific feature category.

        Args:
            category: Category name (e.g., 'filters', 'gradients', 'paths')

        Returns:
            Dictionary with keys:
            - version: API version
            - category: Category name
            - details: Category feature details

        Raises:
            ValueError: If category doesn't exist

        Example:
            >>> filters = FeatureRegistry.get_category('filters')
            >>> filters['details']['native_support']
            ['feGaussianBlur', 'feDropShadow', ...]
        """
        data = cls.load()

        if category not in data["categories"]:
            available = ", ".join(sorted(data["categories"].keys()))
            raise ValueError(
                f"Category '{category}' not found. "
                f"Available categories: {available}"
            )

        return {
            "version": data["version"],
            "category": category,
            "details": data["categories"][category]
        }

    @classmethod
    def get_version(cls) -> str:
        """
        Get API version string.

        Returns:
            Semantic version string (e.g., "1.0.0")

        Example:
            >>> FeatureRegistry.get_version()
            '1.0.0'
        """
        return cls.load()["version"]

    @classmethod
    def get_last_updated(cls) -> str:
        """
        Get last update date.

        Returns:
            ISO format date string

        Example:
            >>> FeatureRegistry.get_last_updated()
            '2025-10-04'
        """
        return cls.load()["last_updated"]

    @classmethod
    def get_policy_capabilities(cls, policy: Optional[str] = None) -> Dict[str, Any]:
        """
        Get policy capability information.

        Args:
            policy: Optional policy name ('speed', 'balanced', 'quality').
                   If None, returns all policies.

        Returns:
            Policy capabilities dictionary

        Raises:
            ValueError: If policy doesn't exist

        Example:
            >>> balanced = FeatureRegistry.get_policy_capabilities('balanced')
            >>> balanced['features']
            ['all shapes', 'all paths', ...]
        """
        data = cls.load()
        policies = data["policy_capabilities"]

        if policy is None:
            return policies

        if policy not in policies:
            available = ", ".join(sorted(policies.keys()))
            raise ValueError(
                f"Policy '{policy}' not found. "
                f"Available policies: {available}"
            )

        return policies[policy]

    @classmethod
    def list_categories(cls) -> List[str]:
        """
        List all available feature categories.

        Returns:
            Sorted list of category names

        Example:
            >>> FeatureRegistry.list_categories()
            ['animations', 'basic_shapes', 'clipping_masking', ...]
        """
        data = cls.load()
        return sorted(data["categories"].keys())

    @classmethod
    def list_policies(cls) -> List[str]:
        """
        List all available conversion policies.

        Returns:
            Sorted list of policy names

        Example:
            >>> FeatureRegistry.list_policies()
            ['balanced', 'quality', 'speed']
        """
        data = cls.load()
        return sorted(data["policy_capabilities"].keys())

    @classmethod
    def clear_cache(cls):
        """
        Clear cached feature data.

        Useful for testing or when feature data is updated at runtime.
        The cache will be reloaded on next access.
        """
        cls._cache = None
        cls.load.cache_clear()


# Convenience factory function
def create_feature_registry() -> FeatureRegistry:
    """
    Factory function to create feature registry instance.

    Returns:
        FeatureRegistry class (stateless, uses class methods)

    Note:
        FeatureRegistry is designed as a singleton-like class with
        class methods. This factory exists for API consistency.
    """
    return FeatureRegistry
