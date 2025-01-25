from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseHeuristic(ABC):
    """Base class for all heuristics"""

    @abstractmethod
    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze data and return scores

        Args:
            data: Dictionary containing relevant data for analysis

        Returns:
            Dictionary containing:
              - score components as float values
              - 'metrics' key containing additional data dictionary
        """
        pass

    def normalize_score(self, value: float, min_val: float = 0, max_val: float = 1) -> float:
        """Normalize score to range [0,1]"""
        return float(max(min_val, min(max_val, value)))